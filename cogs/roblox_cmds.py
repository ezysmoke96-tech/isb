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
SECURITY_BUREAU_GROUP_ID = 34100596


def _gen_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "VRF-" + "".join(secrets.choice(chars) for _ in range(10))


class VerifyView(discord.ui.View):
    """Persistent view used for the verify DM button."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅ I've added the code — Verify me!",
        style=discord.ButtonStyle.green,
        custom_id="verify_done_persistent",
    )
    async def verify_done(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        pending = await get_pending_verification(str(interaction.user.id))
        if not pending:
            await interaction.followup.send(
                "❌ No pending verification found. Please run `/verify` again.", ephemeral=True
            )
            return

        roblox_username = pending["roblox_username"]
        code = pending["code"]

        user_data = await rapi.get_user_by_username(roblox_username)
        if not user_data:
            await interaction.followup.send(
                f"❌ Could not find Roblox user `{roblox_username}`. Check the username and run `/verify` again.",
                ephemeral=True,
            )
            return

        found = await rapi.check_profile_for_code(user_data["id"], code)
        if not found:
            await interaction.followup.send(
                f"❌ The code `{code}` wasn't found in your Roblox **About Me**.\n"
                "Make sure you saved it on your profile, then try again.",
                ephemeral=True,
            )
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
                        warning_lines.append("⚠️ Could not set nickname — I cannot manage this member's nickname.")
                    except discord.HTTPException as e:
                        warning_lines.append(f"⚠️ Nickname update failed: {e}")
                else:
                    warning_lines.append("⚠️ You don't appear to be in the main server — roles and nickname were not applied.")
            else:
                warning_lines.append("⚠️ Main server not found in bot's cache — roles and nickname were not applied.")
        else:
            warning_lines.append("⚠️ Main server not configured (`/setup`) — roles and nickname were not applied.")

        applied_parts = []
        if roles_applied:
            applied_parts.append("✅ Roles updated")
        if nick_applied:
            applied_parts.append(f"✅ Nickname set to **{roblox_username}**")

        description = f"You are now verified as **[{roblox_username}](https://www.roblox.com/users/{user_data['id']}/profile)** on Roblox."
        if applied_parts:
            description += "\n" + " · ".join(applied_parts)
        if warning_lines:
            description += "\n\n" + "\n".join(warning_lines)

        embed = discord.Embed(
            title="✅ Verification Successful!",
            description=description,
            color=discord.Color.green(),
        )
        embed.set_footer(text="You may now remove the code from your Roblox About Me.")
        await interaction.followup.send(embed=embed, ephemeral=True)
        button.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass


class RobloxCog(commands.Cog, name="Roblox"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── /BGCheck ─────────────────────────────────────────────────────────────

    @app_commands.command(name="bgcheck", description="Run a background check on a Roblox user")
    @app_commands.describe(roblox_username="The Roblox username to check")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bgcheck(self, interaction: discord.Interaction, roblox_username: str):
        await interaction.response.defer()

        user_data = await rapi.get_user_by_username(roblox_username)
        if not user_data:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"No Roblox account found with username `{roblox_username}`.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
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
        in_sec_bureau = SECURITY_BUREAU_GROUP_ID in group_map

        isb_group_id_str = await get_config("isb_group_id")
        isb_group_id = int(isb_group_id_str) if isb_group_id_str else None

        ally_ids = await rapi.get_group_allies(MAIN_GROUP_ID)
        unauthorized_divs = []
        for g in groups:
            gid = g["group"]["id"]
            if gid == MAIN_GROUP_ID or gid == SECURITY_BUREAU_GROUP_ID:
                continue
            if isb_group_id and gid == isb_group_id:
                continue
            if gid in ally_ids:
                unauthorized_divs.append(g["group"]["name"])

        discord_banned = False
        main_guild_id_str = await get_config("main_guild_id")
        if main_guild_id_str:
            verified_entry = await get_verified_user_by_roblox(roblox_username)
            if verified_entry:
                main_guild = interaction.client.get_guild(int(main_guild_id_str))
                if main_guild:
                    try:
                        await main_guild.fetch_ban(discord.Object(id=int(verified_entry["discord_id"])))
                        discord_banned = True
                    except discord.NotFound:
                        discord_banned = False

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
            embed.add_field(
                name="Badges",
                value="⚙️ **Not checked** — add `ROBLOX_COOKIE` secret to enable badge verification.",
                inline=False,
            )
        else:
            embed.add_field(
                name="Badges",
                value=(
                    f"{'✅' if badges_ok else '❌'} **{badge_count}** badges "
                    f"{'(meets 175+ requirement)' if badges_ok else '(needs 175+)'}\n"
                    + (f"⚠️ **Farming detected** — majority of badges from `{top_game}`" if farming_suspicious else "No farming detected")
                ),
                inline=False,
            )
        embed.add_field(
            name="TGEAR Galactic Empire",
            value=f"{'✅ Member' if in_main_group else '❌ Not a member'}" + (f" — Rank: **{main_rank}**" if main_rank else ""),
            inline=False,
        )
        embed.add_field(
            name="Security Bureau (Requesting Group)",
            value="✅ Member" if in_sec_bureau else "❌ Not a member / no join request",
            inline=False,
        )
        embed.add_field(
            name="Unauthorized Divisions",
            value=("⚠️ In other TGEAR divisions:\n" + "\n".join(f"• {d}" for d in unauthorized_divs)) if unauthorized_divs else "✅ None",
            inline=False,
        )
        embed.add_field(
            name="Discord Ban",
            value=("❌ Banned from main server" if discord_banned else "✅ Not banned") if main_guild_id_str else "⚙️ Main server not configured",
            inline=True,
        )
        embed.add_field(
            name="Game Ban",
            value="❌ Banned from main game" if game_banned else "✅ Not banned",
            inline=True,
        )
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

    # ─── /Info ────────────────────────────────────────────────────────────────

    @app_commands.command(name="info", description="Show Roblox info for a user")
    @app_commands.describe(roblox_username="The Roblox username to look up")
    async def info(self, interaction: discord.Interaction, roblox_username: str):
        await interaction.response.defer()

        user_data = await rapi.get_user_by_username(roblox_username)
        if not user_data:
            embed = discord.Embed(title="❌ User Not Found", color=discord.Color.red(), description=f"No account found for `{roblox_username}`.")
            await interaction.followup.send(embed=embed)
            return

        user_id = user_data["id"]
        info = await rapi.get_user_info(user_id)
        created_at = info.get("created", "") if info else ""
        age_days = rapi.account_age_days(created_at) if created_at else 0
        rblx_banned = user_data.get("isBanned", False)

        badge_count, _, _ = await rapi.get_badge_info(user_id)
        groups = await rapi.get_user_groups(user_id)
        group_map = {g["group"]["id"]: g for g in groups}
        in_main = MAIN_GROUP_ID in group_map
        main_rank = group_map[MAIN_GROUP_ID]["role"]["name"] if in_main else "Not a member"

        game_banned = await is_game_banned(roblox_username)
        discord_banned = False
        main_guild_id_str = await get_config("main_guild_id")
        if main_guild_id_str:
            entry = await get_verified_user_by_roblox(roblox_username)
            if entry:
                guild = interaction.client.get_guild(int(main_guild_id_str))
                if guild:
                    try:
                        await guild.fetch_ban(discord.Object(id=int(entry["discord_id"])))
                        discord_banned = True
                    except discord.NotFound:
                        pass

        embed = discord.Embed(
            title=f"Roblox Info — {roblox_username}",
            url=f"https://www.roblox.com/users/{user_id}/profile",
            color=discord.Color.blurple(),
        )
        badge_display = "⚙️ Not configured" if badge_count == -1 else str(badge_count)
        embed.add_field(name="Account Age", value=f"{age_days} days", inline=True)
        embed.add_field(name="Badges", value=badge_display, inline=True)
        embed.add_field(name="Roblox Banned", value="Yes" if rblx_banned else "No", inline=True)
        embed.add_field(name="In TGEAR Main Group", value="Yes" if in_main else "No", inline=True)
        embed.add_field(name="Rank", value=main_rank, inline=True)
        embed.add_field(name="Discord Banned", value=("Yes" if discord_banned else "No") if main_guild_id_str else "N/A", inline=True)
        embed.add_field(name="Game Banned", value="Yes" if game_banned else "No", inline=True)
        embed.set_footer(text=f"Roblox ID: {user_id}")
        await interaction.followup.send(embed=embed)

    # ─── /verify ──────────────────────────────────────────────────────────────

    @app_commands.command(name="verify", description="Start Roblox verification for yourself")
    @app_commands.describe(roblox_username="Your Roblox username")
    async def verify(self, interaction: discord.Interaction, roblox_username: str):
        existing = await get_verified_user(str(interaction.user.id))
        if existing:
            embed = discord.Embed(
                title="Already Verified",
                description=f"You are already verified as **{existing['roblox_username']}**.\nUse `/unverify` first to re-verify.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_data = await rapi.get_user_by_username(roblox_username)
        if not user_data:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"No Roblox account found with username `{roblox_username}`. Check the spelling.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        code = _gen_code()
        await save_pending_verification(str(interaction.user.id), roblox_username, code)

        dm_embed = discord.Embed(
            title="Roblox Verification",
            description=(
                f"To verify as **{roblox_username}**, follow these steps:\n\n"
                f"**1.** Go to your [Roblox profile settings](https://www.roblox.com/my/account#!/info)\n"
                f"**2.** Open your profile and click **Edit**\n"
                f"**3.** Paste the code below into your **About Me** / description field and save\n\n"
                f"```\n{code}\n```\n"
                f"**4.** Come back here and click the button below\n\n"
                f"⏳ This code expires in **1 hour**. Once verified you can remove it."
            ),
            color=discord.Color.blurple(),
        )
        try:
            await interaction.user.send(embed=dm_embed, view=VerifyView())
            await interaction.response.send_message(
                "📬 Check your DMs! Follow the steps to complete verification.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I couldn't DM you. Please enable DMs from server members and try again.", ephemeral=True
            )

    # ─── /unverify ────────────────────────────────────────────────────────────

    @app_commands.command(name="unverify", description="Remove a user's Roblox verification")
    @app_commands.describe(member="The Discord member to unverify")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unverify(self, interaction: discord.Interaction, member: discord.Member):
        entry = await get_verified_user(str(member.id))
        if not entry:
            embed = discord.Embed(
                title="Not Verified",
                description=f"{member.mention} is not verified.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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

        embed = discord.Embed(
            title="User Unverified",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Discord User", value=member.mention, inline=True)
        embed.add_field(name="Roblox Account", value=roblox_username, inline=True)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ─── /gameban & /ungameban (admin utilities) ──────────────────────────────

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
