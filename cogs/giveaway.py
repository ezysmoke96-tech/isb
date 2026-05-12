import re
import time
import random
import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.db import (
    save_giveaway,
    get_giveaway,
    get_latest_giveaway_in_channel,
    add_giveaway_entry,
    get_giveaway_entries,
    mark_giveaway_ended,
    get_active_giveaways_ending_before,
)


def parse_duration(s: str) -> datetime.timedelta | None:
    match = re.fullmatch(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", s.strip())
    if not match or not any(match.groups()):
        return None
    delta = datetime.timedelta(
        days=int(match.group(1) or 0),
        hours=int(match.group(2) or 0),
        minutes=int(match.group(3) or 0),
        seconds=int(match.group(4) or 0),
    )
    return delta if delta.total_seconds() > 0 else None


def duration_label(s: str) -> str:
    delta = parse_duration(s)
    if not delta:
        return s
    parts = []
    d = delta.days
    h, rem = divmod(delta.seconds, 3600)
    m, sec = divmod(rem, 60)
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if sec: parts.append(f"{sec}s")
    return " ".join(parts) or "0s"


def giveaway_embed(prize: str, num_winners: int, end_at: int, ended: bool = False, winners: list[str] = None) -> discord.Embed:
    if ended:
        color = discord.Color.greyple()
        title = "🎉 Giveaway Ended!"
    else:
        color = discord.Color.gold()
        title = "🎉 GIVEAWAY! 🎉"

    embed = discord.Embed(title=title, description=f"**Prize:** {prize}", color=color)
    embed.add_field(name="Winners", value=str(num_winners), inline=True)

    if ended:
        if winners:
            embed.add_field(
                name="🏆 Winner(s)",
                value="\n".join(f"<@{w}>" for w in winners),
                inline=False,
            )
        else:
            embed.add_field(name="🏆 Winner(s)", value="No valid entries.", inline=False)
    else:
        embed.add_field(name="Ends", value=discord.utils.format_dt(datetime.datetime.fromtimestamp(end_at, tz=datetime.timezone.utc), style="R"), inline=True)
        embed.set_footer(text="Click 🎉 to enter!")

    return embed


async def pick_and_announce_winners(bot: discord.Client, giveaway: dict, reroll: bool = False):
    guild = bot.get_guild(int(giveaway["guild_id"]))
    if not guild:
        return
    channel = guild.get_channel(int(giveaway["channel_id"]))
    if not channel:
        return
    try:
        message = await channel.fetch_message(int(giveaway["message_id"]))
    except Exception:
        return

    entries = await get_giveaway_entries(giveaway["message_id"])
    # Filter to users still in the server
    valid = []
    for uid in entries:
        m = guild.get_member(int(uid))
        if m and not m.bot:
            valid.append(uid)

    num_winners = giveaway["num_winners"]
    winners = random.sample(valid, min(num_winners, len(valid))) if valid else []

    await mark_giveaway_ended(giveaway["message_id"])

    # Edit the giveaway message
    view = discord.ui.View()  # empty view — removes the button
    embed = giveaway_embed(giveaway["prize"], giveaway["num_winners"], giveaway["end_at"], ended=True, winners=winners)
    try:
        await message.edit(embed=embed, view=view)
    except Exception:
        pass

    # Announce winners
    if winners:
        mentions = " ".join(f"<@{w}>" for w in winners)
        if reroll:
            await channel.send(f"🔄 **Giveaway rerolled!** New winner(s) for **{giveaway['prize']}**: {mentions} 🎉")
        else:
            await channel.send(f"🎉 Congratulations {mentions}! You won **{giveaway['prize']}**!")
    else:
        await channel.send(f"😔 The giveaway for **{giveaway['prize']}** ended with no valid entries.")


class GiveawayView(discord.ui.View):
    """Persistent enter button attached to every giveaway message."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎉 Enter",
        style=discord.ButtonStyle.primary,
        custom_id="giveaway_enter_persistent",
    )
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = await get_giveaway(str(interaction.message.id))

        if not giveaway:
            await interaction.response.send_message("❌ This giveaway no longer exists.", ephemeral=True)
            return
        if giveaway["ended"]:
            await interaction.response.send_message("❌ This giveaway has already ended.", ephemeral=True)
            return
        if int(time.time()) > giveaway["end_at"]:
            await interaction.response.send_message("❌ This giveaway has expired.", ephemeral=True)
            return

        entered = await add_giveaway_entry(str(interaction.message.id), str(interaction.user.id))
        if entered:
            await interaction.response.send_message("✅ You have entered the giveaway! Good luck!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ You have already entered this giveaway.", ephemeral=True)


class GiveawayCog(commands.Cog, name="Giveaway"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.giveaway_loop.start()

    def cog_unload(self):
        self.giveaway_loop.cancel()

    @tasks.loop(seconds=15)
    async def giveaway_loop(self):
        now = int(time.time())
        expired = await get_active_giveaways_ending_before(now)
        for giveaway in expired:
            await pick_and_announce_winners(self.bot, giveaway)

    @giveaway_loop.before_loop
    async def before_giveaway_loop(self):
        await self.bot.wait_until_ready()

    # ── /giveaway ─────────────────────────────────────────────────────────────

    @app_commands.command(name="giveaway", description="Start a giveaway in this channel")
    @app_commands.describe(
        duration="How long the giveaway runs: 1d, 2h, 30m, 1h30m",
        prize="What is being given away",
        winners="Number of winners (default: 1)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(
        self,
        interaction: discord.Interaction,
        duration: str,
        prize: str,
        winners: app_commands.Range[int, 1, 20] = 1,
    ):
        delta = parse_duration(duration)
        if delta is None:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Invalid Duration", description="Use formats like `30m`, `2h`, `1d`, or `1d12h`.", color=discord.Color.red()),
                ephemeral=True,
            )
            return

        end_at = int(time.time() + delta.total_seconds())
        view = GiveawayView()
        embed = giveaway_embed(prize, winners, end_at)
        embed.set_footer(text=f"Hosted by {interaction.user} • Click 🎉 to enter!")

        await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=view)

        await save_giveaway(str(msg.id), str(interaction.channel.id), str(interaction.guild.id), prize, winners, end_at)

    # ── /gend ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="gend", description="End the current giveaway in this channel early and pick winners")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def gend(self, interaction: discord.Interaction):
        giveaway = await get_latest_giveaway_in_channel(str(interaction.channel.id), active_only=True)
        if not giveaway:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ No Active Giveaway", description="There is no active giveaway in this channel.", color=discord.Color.red()),
                ephemeral=True,
            )
            return

        await interaction.response.send_message("🎉 Ending giveaway and picking winners...", ephemeral=True)
        await pick_and_announce_winners(self.bot, giveaway)

    # ── /greroll ──────────────────────────────────────────────────────────────

    @app_commands.command(name="greroll", description="Reroll the winner of the last giveaway in this channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greroll(self, interaction: discord.Interaction):
        giveaway = await get_latest_giveaway_in_channel(str(interaction.channel.id), active_only=False)
        if not giveaway:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ No Giveaway Found", description="No giveaway found in this channel.", color=discord.Color.red()),
                ephemeral=True,
            )
            return

        await interaction.response.send_message("🔄 Rerolling winner...", ephemeral=True)

        # Re-mark as not ended so pick_and_announce_winners can write it again
        giveaway["ended"] = 0
        await pick_and_announce_winners(self.bot, giveaway, reroll=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
