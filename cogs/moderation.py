import re
import time
import datetime

import discord
from discord.ext import commands, tasks
from discord import app_commands

from utils.db import save_timed_ban, get_expired_timed_bans, delete_timed_ban

BANNED_IMAGE = "https://placehold.co/700x120/8B0000/ffffff.png?text=BANNED"


def parse_duration(s: str) -> datetime.timedelta | None:
    """Parse '1d2h30m' style strings. Returns None for permanent."""
    if s.lower() in ("permanent", "perm", "forever", "perma"):
        return None
    match = re.fullmatch(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", s.strip())
    if not match or not any(match.groups()):
        return None
    days    = int(match.group(1) or 0)
    hours   = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)
    delta = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return delta if delta.total_seconds() > 0 else None


def duration_label(s: str) -> str:
    if s.lower() in ("permanent", "perm", "forever", "perma"):
        return "Permanent"
    delta = parse_duration(s)
    if delta is None:
        return s
    parts = []
    d = delta.days
    rem = delta.seconds
    h, rem = divmod(rem, 3600)
    m, sec = divmod(rem, 60)
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if sec: parts.append(f"{sec}s")
    return " ".join(parts) or "0s"


class Moderation(commands.Cog):
    """Moderation slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.unban_loop.start()

    def cog_unload(self):
        self.unban_loop.cancel()

    # ── Background timed-unban task ───────────────────────────────────────────

    @tasks.loop(seconds=30)
    async def unban_loop(self):
        now = int(time.time())
        for guild in self.bot.guilds:
            expired = await get_expired_timed_bans(str(guild.id), now)
            for discord_id in expired:
                try:
                    await guild.unban(discord.Object(id=int(discord_id)), reason="Timed ban expired")
                except Exception:
                    pass
                await delete_timed_ban(discord_id, str(guild.id))

    @unban_loop.before_loop
    async def before_unban_loop(self):
        await self.bot.wait_until_ready()

    # ── /kick ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if member == interaction.user:
            await interaction.response.send_message(
                embed=discord.Embed(title="Action Blocked", description="You cannot kick yourself.", color=discord.Color.orange()),
                ephemeral=True,
            )
            return
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=discord.Embed(title="Action Blocked", description="I cannot kick someone with an equal or higher role than me.", color=discord.Color.orange()),
                ephemeral=True,
            )
            return

        try:
            await member.send(embed=discord.Embed(
                title="You have been kicked",
                description=f"**Reason:** {reason}\n**Server:** {interaction.guild.name}\n**By:** {interaction.user}",
                color=discord.Color.orange(),
            ))
        except Exception:
            pass

        await member.kick(reason=f"{reason} — by {interaction.user}")

        embed = discord.Embed(title="Member Kicked", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ── /ban ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user_id="User mention, name, or Discord ID (works even if they left the server)",
        reason="Reason for the ban",
        duration="Duration: 1d, 2h, 30m, 1d12h — or 'permanent' (default)",
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "No reason provided",
        duration: str = "permanent",
    ):
        await interaction.response.defer()

        # Resolve user — try member first, then raw ID
        target_user = None
        target_member = None
        raw_id = user_id.strip("<@!>")
        if raw_id.isdigit():
            target_member = interaction.guild.get_member(int(raw_id))
            if not target_member:
                try:
                    target_user = await self.bot.fetch_user(int(raw_id))
                except discord.NotFound:
                    pass
        else:
            # Try by name
            target_member = discord.utils.find(lambda m: m.name.lower() == raw_id.lower() or m.display_name.lower() == raw_id.lower(), interaction.guild.members)

        target = target_member or target_user
        if target is None:
            await interaction.followup.send(
                embed=discord.Embed(title="❌ User Not Found", description=f"Could not find user `{user_id}`. Provide a mention, username, or Discord ID.", color=discord.Color.red()),
                ephemeral=True,
            )
            return

        if target_member and target_member == interaction.user:
            await interaction.followup.send(embed=discord.Embed(title="Action Blocked", description="You cannot ban yourself.", color=discord.Color.orange()), ephemeral=True)
            return
        if target_member and target_member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send(embed=discord.Embed(title="Action Blocked", description="I cannot ban someone with an equal or higher role than me.", color=discord.Color.orange()), ephemeral=True)
            return

        dur_label = duration_label(duration)
        delta = parse_duration(duration) if duration.lower() not in ("permanent", "perm", "forever", "perma") else None

        # DM the user before banning
        dm_embed = discord.Embed(
            title="🚫 You have been banned [ISB]!",
            color=0x8B0000,
        )
        dm_embed.description = (
            f"You have been banned **{reason}** for **{dur_label}**, by **{interaction.user}**."
        )
        dm_embed.add_field(name="Server", value=interaction.guild.name, inline=True)
        dm_embed.add_field(name="Duration", value=dur_label, inline=True)
        dm_embed.add_field(name="Reason", value=reason, inline=False)
        dm_embed.set_image(url=BANNED_IMAGE)
        dm_embed.set_footer(text="Imperial Security Bureau — TGEAR Galactic Empire")
        try:
            await target.send(embed=dm_embed)
        except Exception:
            pass

        # Perform the ban
        ban_obj = discord.Object(id=target.id)
        await interaction.guild.ban(ban_obj, reason=f"{reason} — by {interaction.user}", delete_message_days=0)

        # Save timed ban if not permanent
        if delta:
            unban_at = int(time.time()) + int(delta.total_seconds())
            await save_timed_ban(str(target.id), str(interaction.guild.id), unban_at)

        # Server confirmation embed
        embed = discord.Embed(title="🚫 Member Banned", color=0x8B0000)
        embed.add_field(name="User", value=f"{target} (`{target.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=dur_label, inline=True)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=True)
        embed.set_image(url=BANNED_IMAGE)
        if hasattr(target, "display_avatar"):
            embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.followup.send(embed=embed)

    # ── /unban ────────────────────────────────────────────────────────────────

    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user_id="The Discord user ID or username#tag to unban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
    ):
        await interaction.response.defer()

        raw_id = user_id.strip("<@!>")
        target_user = None

        if raw_id.isdigit():
            try:
                target_user = await self.bot.fetch_user(int(raw_id))
            except discord.NotFound:
                pass
        else:
            # Search through ban list by name
            async for ban_entry in interaction.guild.bans():
                if ban_entry.user.name.lower() == raw_id.lower():
                    target_user = ban_entry.user
                    break

        if target_user is None:
            await interaction.followup.send(
                embed=discord.Embed(title="❌ User Not Found", description=f"Could not find `{user_id}` in the ban list.", color=discord.Color.red()),
                ephemeral=True,
            )
            return

        try:
            await interaction.guild.unban(target_user, reason=f"Unbanned by {interaction.user}")
        except discord.NotFound:
            await interaction.followup.send(
                embed=discord.Embed(title="❌ Not Banned", description=f"{target_user} is not currently banned.", color=discord.Color.orange()),
                ephemeral=True,
            )
            return

        await delete_timed_ban(str(target_user.id), str(interaction.guild.id))

        embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green())
        embed.add_field(name="User", value=f"{target_user} (`{target_user.id}`)", inline=False)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=False)
        embed.set_thumbnail(url=target_user.display_avatar.url)
        await interaction.followup.send(embed=embed)

    # ── /mute ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="mute", description="Timeout (mute) a member for a set duration")
    @app_commands.describe(
        member="The member to mute",
        duration="Duration: 1d, 2h, 30m, 1h30m (max 28 days)",
        reason="Reason for the mute",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "No reason provided",
    ):
        if member == interaction.user:
            await interaction.response.send_message(embed=discord.Embed(title="Action Blocked", description="You cannot mute yourself.", color=discord.Color.orange()), ephemeral=True)
            return
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(embed=discord.Embed(title="Action Blocked", description="I cannot mute someone with an equal or higher role than me.", color=discord.Color.orange()), ephemeral=True)
            return

        delta = parse_duration(duration)
        if delta is None:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Invalid Duration", description="Use a format like `30m`, `2h`, `1d`, or `1h30m`.", color=discord.Color.red()),
                ephemeral=True,
            )
            return

        max_timeout = datetime.timedelta(days=28)
        if delta > max_timeout:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Duration Too Long", description="Discord timeout cannot exceed **28 days**.", color=discord.Color.red()),
                ephemeral=True,
            )
            return

        until = discord.utils.utcnow() + delta
        await member.timeout(until, reason=f"{reason} — by {interaction.user}")

        dur_label = duration_label(duration)
        try:
            await member.send(embed=discord.Embed(
                title="🔇 You have been muted",
                description=f"**Server:** {interaction.guild.name}\n**Duration:** {dur_label}\n**Reason:** {reason}\n**By:** {interaction.user}",
                color=discord.Color.orange(),
            ))
        except Exception:
            pass

        embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Duration", value=dur_label, inline=True)
        embed.add_field(name="Expires", value=discord.utils.format_dt(until, style="R"), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ── /purge ────────────────────────────────────────────────────────────────

    @app_commands.command(name="purge", description="Delete messages from this channel")
    @app_commands.describe(amount="Number of messages to delete (default: 10)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100] = 10,
    ):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(title="Messages Purged", description=f"Deleted **{len(deleted)}** message(s).", color=discord.Color.blurple())
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
