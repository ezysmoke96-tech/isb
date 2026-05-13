import secrets
import string

import discord
from discord import app_commands
from discord.ext import commands

from utils import roblox as rapi
from utils.db import (
    add_game_ban,
    delete_pending_verification,
    delete_verified_user,
    get_config,
    get_pending_verification,
    get_verified_user,
    get_verified_user_by_roblox,
    is_game_banned,
    remove_game_ban,
    save_pending_verification,
    save_verified_user,
)

MAIN_GROUP_ID = 36051087


def _gen_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "VRF-" + "".join(secrets.choice(chars) for _ in range(10))


# ── Shared helpers ─────────────────────────────────────────────────────────────

async def _discord_banned(interaction: discord.Interaction, roblox_username: str, main_guild_id_str: str | None) -> bool:
    if not main_guild_id_str:
        return False
    entry = await get_verified_user_by_roblox(roblox_username)
    if not entry:
        return False
    guild = interaction.client.get_guild(int(main_guild_id_str))
    if not guild:
        return False
    try:
        await guild.fetch_ban(discord.Object(id=int(entry["discord_id"])))
        return True
    except discord.NotFound:
        return False


async def _build_roblox_embed(
    interaction: discord.Interaction,
    roblox_username: str,
    *,
    title_prefix: str = "Roblox Info",
) -> discord.Embed | None:
    """
    Shared logic for /info and /whois. Returns a built embed or None if user not found.
    """
    user_data = await rapi.get_user_by_username(roblox_username)
    if not user_data:
        return None

    user_id = user_data["id"]
    display_name = user_data.get("displayName", roblox_username)
    rblx_banned = user_data.get("isBanned", False)

    info = await rapi.get_user_info(user_id)
    created_at = info.get("created", "") if info else ""
    description_text = (info.get("description") or "").strip() if info else ""
    age_days = rapi.account_age_days(created_at) if created_at else 0

    groups = await rapi.get_user_groups(user_id)
    group_map = {g["group"]["id"]: g for g in groups}

    in_main = MAIN_GROUP_ID in group_map
    main_rank = group_map[MAIN_GROUP_ID]["role"]["name"] if in_main else "Not a member"

    ally_groups = await rapi.get_group_allies(MAIN_GROUP_ID)
    ally_id_set = {g["id"] for g in ally_groups}

    ally_memberships = []
    for g in groups:
        gid = g["group"]["id"]
        if gid in ally_id_set:
            ally_memberships.append({"name": g["group"]["name"], "rank": g["role"]["name"]})

    member_group_ids = {g["group"]["id"] for g in groups}
    non_member_allies = [g for g in ally_groups if g["id"] not in member_group_ids]
    pending_groups = await rapi.get_user_pending_in_groups(user_id, non_member_allies)

    game_banned = await is_game_banned(roblox_username)
    main_guild_id_str = await get_config("main_guild_id")
    discord_banned = await _discord_banned(interaction, roblox_username, main_guild_id_str)

    embed = discord.Embed(
        title=f"{title_prefix} — {roblox_username}",
        url=f"https://www.roblox.com/users/{user_id}/profile",
        color=discord.Color.blurple(),
    )
    embed.description = f"**Display Name:** {display_name}"

    embed.add_field(name="Account Age", value=f"{age_days} days", inline=True)
    embed.add_field(name="Roblox Banned", value="Yes ❌" if rblx_banned else "No ✅", inline=True)
    embed.add_field(name="Discord Banned", value=("Yes ❌" if discord_banned else "No ✅") if main_guild_id_str else "N/A ⚙️", inline=True)
    embed.add_field(name="Game Banned", value="Yes ❌" if game_banned else "No ✅", inline=True)

    embed.add_field(
        name="Galactic Army Rank (TGEAR Main Group)",
        value=f"{'✅' if in_main else '❌'} {main_rank}",
        inline=False,
    )

    if ally_memberships:
        lines = [f"• **{m['name']}** — {m['rank']}" for m in ally_memberships]
        embed.add_field(name=f"Allied Divisions — Member ({len(ally_memberships)})", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Allied Divisions — Member", value="Not in any allied divisions", inline=False)

    if pending_groups:
        lines = [f"• **{g['name']}**" for g in pending_groups]
        embed.add_field(name=f"Allied Divisions — Pending ({len(pending_groups)})", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Allied Divisions — Pending", value="No pending requests", inline=False)

    if description_text:
        short_desc = description_text[:512] + ("…" if len(description_text) > 512 else "")
        embed.add_field(name="Roblox Description", value=short_desc, inline=False)
    else:
        embed.add_field(name="Roblox Description", value="*No description set*", inline=False)

    embed.set_footer(text=f"Roblox ID: {user_id}")
    return embed


# ── Persistent View ────────────────────────────────────────────────────────────

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ I've added the code — Verify me!", style=discord.ButtonStyle.green, custom_id="verify_done_persistent")
    async def verify_done(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        pending = await get_pending_verification(str(interaction.user.id))
        if not pending:
            await interaction.followup.send("❌ No pending verification found. Please run `/verify` again.", ephemeral=True)
            return

        roblox_username = pending["roblox_username"]
        code = pending["code"]

        user_data = await rapi.get_user_by_username(roblox_username)
        if not user_data:
            await interaction.followup.send(f"❌ Could not find Roblox user `{roblox_username}`.", ephemeral=True)
            return

        found = await rapi.check_profile_for_code(user_data["id"], code)
        if not found:
            await interaction.followup.send(f"❌ The code `{code}` wasn't found in your Roblox **About Me**.\nMake sure you saved it, then try again.", ephemeral=True)
            return

        await delete_pending_verification(str(interaction.user.id))
        await save_verified_user(str(interaction.user.id), str(user_data["id"]), roblox_username)

        guild_id = await get_config("main_guild_id")
        verified_role_id = await get_config("verified_role")
        unverified_role_id = await get_config("unverified_role")
        candidate_role_id = await get_config("candidate_role")

        roles_applied = False
        nick_applied = False
        warning_lines = []

        if guild_id:
            guild = interaction.client.get_guild(int(guild_id))
            if guild:
                try:
                    member = await guild.fetch_member(interaction.user.id)
                except (discord.NotFound, discord.HTTPException):
                    member = None

                if member:
                    to_add, to_remove = [], []
                    for rid in [verified_role_id, candidate_role_id]:
                        if rid:
                            r = guild.get_role(int(rid))
                            if r:
                                to_add.append(r)
                    if unverified_role_id:
                        r = guild.get_role(int(unverified_role_id))
                        if r:
                            to_remove.append(r)
                    try:
                        if to_add:
                            await member.add_roles(*to_add, reason="Roblox verification")
                        if to_remove:
                            await member.remove_roles(*to_remove, reason="Roblox verification")
                        roles_applied = True
                    except discord.Forbidden:
                        warning_lines.append("⚠️ Could not apply roles — missing **Manage Roles** permission.")
                    except discord.HTTPException as e:
                        warning_lines.append(f"⚠️ Role update failed: {e}")
                    try:
                        await member.edit(nick=roblox_username, reason="Roblox verification")
                        nick_applied = True
                    except discord.Forbidden:
                        warning_lines.append("⚠️ Could not set nickname.")
                else:
                    warning_lines.append("⚠️ You don't appear to be in the main server.")
            else:
                warning_lines.append("⚠️ Main server not found in bot's cache.")
        else:
            warning_lines.append("⚠️ Main server not configured (`/setup`).")

        applied_parts = []
        if roles_applied:
            applied_parts.append("✅ Roles updated")
        if nick_applied:
            applied_parts.append(f"✅ Nickname set to **{roblox_username}**")

        description = f"You are now verified as **[{roblox_username}](https://www.roblox.com/users/{user_data['id']}/profile)**."
        if applied_parts:
            description += "\n" + " · ".join(applied_parts)
        if warning_lines:
            description += "\n\n" + "\n".join(warning_lines)

        embed = discord.Embed(title="✅ Verification Successful!", description=description, color=discord.Color.green())
        embed.set_footer(text="You may now remove the code from your Roblox About Me.")
        await interaction.followup.send(embed=embed, ephemeral=True)
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass


# ── Cog ───────────────────────────────────────────────────────────────────────

class RobloxCog(commands.Cog, name="Roblox"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── /info ────────────────────────────────────────────────────────────────

    @app_commands.command(name="info", description="Show detailed Roblox info for a user")
    @app_commands.describe(roblox_username="The Roblox username to look up")
    async def info(self, interaction: discord.Interaction, roblox_username: str):
        await interaction.response.defer()
        embed = await _build_roblox_embed(interaction, roblox_username)
        if embed is None:
            await interaction.followup.send(embed=discord.Embed(title="❌ User Not Found", color=discord.Color.red(), description=f"No account found for `{roblox_username}`."))
            return
        await interaction.followup.send(embed=embed)

    # ─── /whois ───────────────────────────────────────────────────────────────

    @app_commands.command(name="whois", description="Look up the Roblox account a Discord member is verified as")
    @app_commands.describe(member="The Discord member to look up")
    async def whois(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()

        entry = await get_verified_user(str(member.id))
        if not entry:
            embed = discord.Embed(
                title="Not Verified",
                description=f"{member.mention} has not linked a Roblox account.\nThey can use `/verify` to do so.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)
            return

        roblox_username = entry["roblox_username"]
        embed = await _build_roblox_embed(interaction, roblox_username, title_prefix="Whois")
        if embed is None:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Roblox Account Not Found",
                description=f"{member.mention} was verified as `{roblox_username}` but that account no longer exists on Roblox.",
                color=discord.Color.red(),
            ))
            return

        embed.set_author(name=f"{member.display_name} ({member})", icon_url=member.display_avatar.url)
        await interaction.followup.send(embed=embed)

    # ─── /bgcheck ─────────────────────────────────────────────────────────────

    @app_commands.command(name="bgcheck", description="Run a background check on a Roblox user")
    @app_commands.describe(roblox_username="The Roblox username to check")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bgcheck(self, interaction: discord.Interaction, roblox_username: str):
        await interaction.response.defer()

        user_data = await rapi.get_user_by_username(roblox_username)
        if not user_data:
            await interaction.followup.send(embed=discord.Embed(title="❌ User Not Found", description=f"No Roblox account found with username `{roblox_username}`.", color=discord.Color.red()))
            return

        user_id = user_data["id"]
        display_name = user_data.get("displayName", roblox_username)
        rblx_banned = user_data.get("isBanned", False)

        info = await rapi.get_user_info(user_id)
        created_at = info.get("created", "") if info else ""
        age_days = rapi.account_age_days(created_at) if created_at else 0

        badge_count, farming_suspicious, top_game = await rapi.get_badge_info(user_id)
        groups = await rapi.get_user_groups(user_id)
        group_map = {g["group"]["id"]: g for g in groups}

        in_main_group = MAIN_GROUP_ID in group_map
        main_rank = group_map[MAIN_GROUP_ID]["role"]["name"] if in_main_group else None

        ally_groups = await rapi.get_group_allies(MAIN_GROUP_ID)
        ally_id_set = {g["id"] for g in ally_groups}

        ally_memberships = []
        for g in groups:
            gid = g["group"]["id"]
            if gid in ally_id_set:
                ally_memberships.append({"name": g["group"]["name"], "rank": g["role"]["name"]})

        member_group_ids = {g["group"]["id"] for g in groups}
        non_member_allies = [g for g in ally_groups if g["id"] not in member_group_ids]
        pending_groups = await rapi.get_user_pending_in_groups(user_id, non_member_allies)

        main_guild_id_str = await get_config("main_guild_id")
        discord_banned = await _discord_banned(interaction, roblox_username, main_guild_id_str)
        game_banned = await is_game_banned(roblox_username)

        age_ok = age_days >= 350
        cookie_missing = badge_count == -1
        badges_ok = badge_count >= 175 if not cookie_missing else None
        is_alt = not age_ok or (badges_ok is False) or farming_suspicious

        if cookie_missing:
            color = discord.Color.yellow()
            verdict = "⚠️ Incomplete — badge check skipped (no Roblox cookie configured)"
        elif is_alt:
            color = discord.Color.red()
            verdict = "⚠️ Likely **Alternative Account**"
        else:
            color = discord.Color.green()
            verdict = "✅ Passes background check"

        embed = discord.Embed(
            title=f"BGCheck — {roblox_username}",
            url=f"https://www.roblox.com/users/{user_id}/profile",
            description=f"**Display Name:** {display_name}\n**Roblox Banned:** {'Yes ❌' if rblx_banned else 'No ✅'}",
            color=color,
        )

        embed.add_field(
            name="Account Age",
            value=f"{'✅' if age_ok else '❌'} **{age_days}** days {'(meets 350+ requirement)' if age_ok else '(needs 350+)'}",
            inline=False,
        )

        if cookie_missing:
            embed.add_field(name="Badges", value="⚙️ **Not checked** — add `ROBLOX_COOKIE` secret to enable.", inline=False)
        else:
            embed.add_field(
                name="Badges",
                value=(
                    f"{'✅' if badges_ok else '❌'} **{badge_count}** badges {'(meets 175+)' if badges_ok else '(needs 175+)'}\n"
                    + (f"⚠️ **Farming detected** — majority from `{top_game}`" if farming_suspicious else "No farming detected")
                ),
                inline=False,
            )

        embed.add_field(
            name="TGEAR Galactic Empire",
            value=f"{'✅ Member' if in_main_group else '❌ Not a member'}" + (f" — Rank: **{main_rank}**" if main_rank else ""),
            inline=False,
        )

        if ally_memberships:
            lines = [f"• **{m['name']}** — {m['rank']}" for m in ally_memberships]
            embed.add_field(name=f"Allied Divisions — Member ({len(ally_memberships)})", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Allied Divisions — Member", value="Not in any allied divisions", inline=False)

        if pending_groups:
            lines = [f"• **{g['name']}**" for g in pending_groups]
            embed.add_field(name=f"Allied Divisions — Pending ({len(pending_groups)})", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Allied Divisions — Pending", value="No pending requests", inline=False)

        embed.add_field(name="Discord Ban", value=("❌ Banned" if discord_banned else "✅ Not banned") if main_guild_id_str else "⚙️ Not configured", inline=True)
        embed.add_field(name="Game Ban", value="❌ Banned" if game_banned else "✅ Not banned", inline=True)
        embed.add_field(name="Verdict", value=verdict, inline=False)

        reasons = []
        if not age_ok:
            reasons.append(f"Account age {age_days} days < 350")
        if badges_ok is False:
            reasons.append(f"Only {badge_count} badges < 175")
        if farming_suspicious:
            reasons.append(f"Suspicious badge farming from `{top_game}`")
        if reasons:
            embed.add_field(name="Reasons", value="\n".join(f"• {r}" for r in reasons), inline=False)

        embed.set_footer(text=f"Roblox ID: {user_id}")
        await interaction.followup.send(embed=embed)

    # ─── /verify ──────────────────────────────────────────────────────────────

    @app_commands.command(name="verify", description="Start Roblox verification for yourself")
    @app_commands.describe(roblox_username="Your Roblox username")
    async def verify(self, interaction: discord.Interaction, roblox_username: str):
        existing = await get_verified_user(str(interaction.user.id))
        if existing:
            await interaction.response.send_message(embed=discord.Embed(title="Already Verified", description=f"You are already verified as **{existing['roblox_username']}**.\nUse `/unverify` first to re-verify.", color=discord.Color.orange()), ephemeral=True)
            return
        user_data = await rapi.get_user_by_username(roblox_username)
        if not user_data:
            await interaction.response.send_message(embed=discord.Embed(title="❌ User Not Found", description=f"No Roblox account found with username `{roblox_username}`.", color=discord.Color.red()), ephemeral=True)
            return
        code = _gen_code()
        await save_pending_verification(str(interaction.user.id), roblox_username, code)
        dm_embed = discord.Embed(
            title="Roblox Verification",
            description=(
                f"To verify as **{roblox_username}**, follow these steps:\n\n"
                f"**1.** Go to your [Roblox profile settings](https://www.roblox.com/my/account#!/info)\n"
                f"**2.** Paste the code below into your **About Me** and save\n\n"
                f"```\n{code}\n```\n"
                f"**3.** Come back here and click the button below\n\n"
                f"⏳ This code expires in **1 hour**."
            ),
            color=discord.Color.blurple(),
        )
        try:
            await interaction.user.send(embed=dm_embed, view=VerifyView())
            await interaction.response.send_message("📬 Check your DMs! Follow the steps to complete verification.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I couldn't DM you. Please enable DMs from server members and try again.", ephemeral=True)

    # ─── /unverify ────────────────────────────────────────────────────────────

    @app_commands.command(name="unverify", description="Remove a user's Roblox verification")
    @app_commands.describe(member="The Discord member to unverify")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unverify(self, interaction: discord.Interaction, member: discord.Member):
        entry = await get_verified_user(str(member.id))
        if not entry:
            await interaction.response.send_message(embed=discord.Embed(title="Not Verified", description=f"{member.mention} is not verified.", color=discord.Color.orange()), ephemeral=True)
            return
        roblox_username = entry["roblox_username"]
        await delete_verified_user(str(member.id))
        verified_role_id = await get_config("verified_role")
        unverified_role_id = await get_config("unverified_role")
        candidate_role_id = await get_config("candidate_role")
        to_add, to_remove = [], []
        if unverified_role_id:
            r = interaction.guild.get_role(int(unverified_role_id))
            if r:
                to_add.append(r)
        for rid in [verified_role_id, candidate_role_id]:
            if rid:
                r = interaction.guild.get_role(int(rid))
                if r:
                    to_remove.append(r)
        if to_add:
            await member.add_roles(*to_add)
        if to_remove:
            await member.remove_roles(*to_remove)
        try:
            await member.edit(nick=None)
        except discord.Forbidden:
            pass
        embed = discord.Embed(title="User Unverified", color=discord.Color.orange())
        embed.add_field(name="Discord User", value=member.mention, inline=True)
        embed.add_field(name="Roblox Account", value=roblox_username, inline=True)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ─── /gameban & /ungameban ────────────────────────────────────────────────

    @app_commands.command(name="gameban", description="Mark a Roblox user as banned from the main game")
    @app_commands.describe(roblox_username="Roblox username to ban", reason="Reason")
    @app_commands.checks.has_permissions(administrator=True)
    async def gameban(self, interaction: discord.Interaction, roblox_username: str, reason: str = "No reason provided"):
        await add_game_ban(roblox_username, str(interaction.user), reason)
        embed = discord.Embed(title="Game Ban Added", color=discord.Color.red())
        embed.add_field(name="User", value=roblox_username)
        embed.add_field(name="Reason", value=reason)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ungameban", description="Remove a game ban for a Roblox user")
    @app_commands.describe(roblox_username="Roblox username to unban")
    @app_commands.checks.has_permissions(administrator=True)
    async def ungameban(self, interaction: discord.Interaction, roblox_username: str):
        await remove_game_ban(roblox_username)
        embed = discord.Embed(title="Game Ban Removed", color=discord.Color.green(), description=f"`{roblox_username}` is no longer flagged as game-banned.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RobloxCog(bot))
