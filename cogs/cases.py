import asyncio
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import utils.db as db

_MANAGE = app_commands.checks.has_permissions(manage_guild=True)
_ADMIN  = app_commands.checks.has_permissions(administrator=True)


def _ts() -> datetime:
    return datetime.now(timezone.utc)


def _mention(client: discord.Client, user_id: str) -> str:
    try:
        user = client.get_user(int(user_id))
        return user.mention if user else f"<@{user_id}>"
    except Exception:
        return f"<@{user_id}>"


class CasesCog(commands.Cog, name="Cases"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Warnings ───────────────────────────────────────────────────────────────

    @app_commands.command(name="warn", description="Give a formal warning to a member")
    @app_commands.describe(member="The member to warn", reason="Reason for warning")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        gid = str(interaction.guild.id)
        wid = await db.add_warning(gid, str(member.id), reason, str(interaction.user))
        await db.log_case(gid, str(member.id), "WARN", reason, str(interaction.user))
        embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.yellow(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Warned By", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"Warning ID: {wid}")
        await interaction.response.send_message(embed=embed)
        try:
            await member.send(embed=discord.Embed(title="⚠️ You received a warning", description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason}\n**Issued By:** {interaction.user}", color=discord.Color.yellow()))
        except discord.Forbidden:
            pass

    @app_commands.command(name="warnings", description="View all warnings a member has received")
    @app_commands.describe(member="The member to check")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warns = await db.get_warnings(str(interaction.guild.id), str(member.id))
        embed = discord.Embed(title=f"⚠️ Warnings — {member}", color=discord.Color.yellow(), timestamp=_ts())
        if not warns:
            embed.description = "No warnings on record."
        else:
            for w in warns[:15]:
                embed.add_field(name=f"#{w['id']} — {w['warned_at'][:10]}", value=f"{w['reason']}\n*by {w['warned_by']}*", inline=False)
        embed.set_footer(text=f"Total: {len(warns)}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member")
    @app_commands.describe(member="The member to clear")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        await db.clear_warnings(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ All warnings cleared for {member.mention}.", ephemeral=True)

    # ── Strikes ────────────────────────────────────────────────────────────────

    @app_commands.command(name="strike", description="Give a disciplinary strike to a member")
    @app_commands.describe(member="The member to strike", reason="Reason for the strike")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def strike(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        gid = str(interaction.guild.id)
        sid = await db.add_strike(gid, str(member.id), reason, str(interaction.user))
        await db.log_case(gid, str(member.id), "STRIKE", reason, str(interaction.user))
        embed = discord.Embed(title="❌ Strike Issued", color=discord.Color.red(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"Strike ID: {sid}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="strikes", description="Show all strikes on a member")
    @app_commands.describe(member="The member to check")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def strikes(self, interaction: discord.Interaction, member: discord.Member):
        ss = await db.get_strikes(str(interaction.guild.id), str(member.id))
        embed = discord.Embed(title=f"❌ Strikes — {member}", color=discord.Color.red(), timestamp=_ts())
        if not ss:
            embed.description = "No strikes on record."
        else:
            for s in ss[:15]:
                embed.add_field(name=f"#{s['id']} — {s['struck_at'][:10]}", value=f"{s['reason']}\n*by {s['struck_by']}*", inline=False)
        embed.set_footer(text=f"Total: {len(ss)}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearstrikes", description="Remove all strikes from a member")
    @app_commands.describe(member="The member to clear")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearstrikes(self, interaction: discord.Interaction, member: discord.Member):
        await db.clear_strikes(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ All strikes cleared for {member.mention}.", ephemeral=True)

    # ── Cases ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="case", description="View a moderation case file")
    @app_commands.describe(case_id="The case ID")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def case(self, interaction: discord.Interaction, case_id: int):
        c = await db.get_case(case_id, str(interaction.guild.id))
        if not c:
            await interaction.response.send_message(f"❌ Case #{case_id} not found.", ephemeral=True)
            return
        embed = discord.Embed(title=f"📁 Case #{case_id}", color=discord.Color.blurple(), timestamp=_ts())
        embed.add_field(name="Member", value=_mention(self.bot, c["user_id"]), inline=True)
        embed.add_field(name="Action", value=c["action"], inline=True)
        embed.add_field(name="Reason", value=c["reason"], inline=False)
        embed.add_field(name="Actioned By", value=c["actioned_by"], inline=True)
        embed.add_field(name="Date", value=c["created_at"][:10], inline=True)
        embed.add_field(name="Status", value="Active" if c["active"] else "Closed", inline=True)
        # Evidence
        evidence = await db.get_evidence(case_id, str(interaction.guild.id))
        if evidence:
            embed.add_field(name=f"Evidence ({len(evidence)})", value="\n".join(f"• [{e['id']}] {e['content'][:80]}" for e in evidence[:5]), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="casesearch", description="Search moderation cases for a member")
    @app_commands.describe(member="The member to search")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def casesearch(self, interaction: discord.Interaction, member: discord.Member):
        cases = await db.search_cases(str(interaction.guild.id), str(member.id))
        embed = discord.Embed(title=f"📁 Cases — {member}", color=discord.Color.blurple(), timestamp=_ts())
        if not cases:
            embed.description = "No cases found."
        else:
            for c in cases:
                embed.add_field(name=f"#{c['id']} [{c['action']}] — {c['created_at'][:10]}", value=f"{c['reason']}\n*by {c['actioned_by']}*", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="terminatecase", description="Permanently close a case file")
    @app_commands.describe(case_id="The case ID to close")
    @app_commands.checks.has_permissions(administrator=True)
    async def terminatecase(self, interaction: discord.Interaction, case_id: int):
        await db.terminate_case(case_id, str(interaction.guild.id))
        await interaction.response.send_message(f"🔒 Case #{case_id} permanently closed.", ephemeral=True)

    @app_commands.command(name="auditlog", description="Display recent moderation actions")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def auditlog(self, interaction: discord.Interaction):
        cases = await db.list_recent_cases(str(interaction.guild.id), limit=15)
        embed = discord.Embed(title="📋 Moderation Audit Log", color=discord.Color.blurple(), timestamp=_ts())
        if not cases:
            embed.description = "No recent moderation actions."
        else:
            for c in cases:
                embed.add_field(
                    name=f"#{c['id']} [{c['action']}] — {c['created_at'][:10]}",
                    value=f"{_mention(self.bot, c['user_id'])} — {c['reason'][:80]}\n*by {c['actioned_by']}*",
                    inline=False,
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Reports ────────────────────────────────────────────────────────────────

    @app_commands.command(name="report", description="File a report against a member")
    @app_commands.describe(member="The member being reported", reason="Reason for the report")
    async def report(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        rid = await db.file_report(str(interaction.guild.id), str(interaction.user.id), str(member.id), reason)
        embed = discord.Embed(title="📋 Report Filed", color=discord.Color.orange(), timestamp=_ts())
        embed.add_field(name="Reported Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Filed By", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"Report ID: {rid}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reports", description="Display all active reports")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reports(self, interaction: discord.Interaction):
        reps = await db.list_reports(str(interaction.guild.id))
        embed = discord.Embed(title="📋 Active Reports", color=discord.Color.orange(), timestamp=_ts())
        if not reps:
            embed.description = "No active reports."
        else:
            for r in reps:
                embed.add_field(
                    name=f"#{r['id']} — {r['created_at'][:10]}",
                    value=f"**Target:** {_mention(self.bot, r['target_id'])}\n**Reporter:** {_mention(self.bot, r['reporter_id'])}\n{r['reason'][:80]}",
                    inline=False,
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="closereport", description="Close a report ticket")
    @app_commands.describe(report_id="The report ID to close")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def closereport(self, interaction: discord.Interaction, report_id: int):
        r = await db.get_report(report_id, str(interaction.guild.id))
        if not r:
            await interaction.response.send_message(f"❌ Report #{report_id} not found.", ephemeral=True)
            return
        await db.close_report(report_id, str(interaction.guild.id))
        await interaction.response.send_message(f"✅ Report #{report_id} closed.", ephemeral=True)

    @app_commands.command(name="evidence", description="Upload evidence to a case file")
    @app_commands.describe(case_id="The case ID", content="Evidence description or link")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def evidence(self, interaction: discord.Interaction, case_id: int, content: str):
        c = await db.get_case(case_id, str(interaction.guild.id))
        if not c:
            await interaction.response.send_message(f"❌ Case #{case_id} not found.", ephemeral=True)
            return
        eid = await db.add_evidence(case_id, str(interaction.guild.id), content, str(interaction.user))
        await interaction.response.send_message(f"✅ Evidence #{eid} added to case #{case_id}.", ephemeral=True)

    # ── Watchlist ──────────────────────────────────────────────────────────────

    @app_commands.command(name="watchlist", description="Add a user to the observation watchlist")
    @app_commands.describe(member="The member to watch", reason="Reason")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def watchlist(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.add_watchlist(str(interaction.guild.id), str(member.id), reason, str(interaction.user))
        embed = discord.Embed(title="👁️ Added to Watchlist", color=discord.Color.orange(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Added By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removewatchlist", description="Remove a user from the watchlist")
    @app_commands.describe(member="The member to remove")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def removewatchlist(self, interaction: discord.Interaction, member: discord.Member):
        await db.remove_watchlist(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ {member.mention} removed from watchlist.", ephemeral=True)

    # ── Blacklist ──────────────────────────────────────────────────────────────

    @app_commands.command(name="blacklist", description="Blacklist a user from ISB systems")
    @app_commands.describe(member="The member to blacklist", reason="Reason")
    @app_commands.checks.has_permissions(administrator=True)
    async def blacklist(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.add_blacklist(str(interaction.guild.id), str(member.id), reason, str(interaction.user))
        await db.log_case(str(interaction.guild.id), str(member.id), "BLACKLIST", reason, str(interaction.user))
        embed = discord.Embed(title="🚫 Member Blacklisted", color=discord.Color.dark_red(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Actioned By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unblacklist", description="Remove a user's blacklist")
    @app_commands.describe(member="The member to unblacklist")
    @app_commands.checks.has_permissions(administrator=True)
    async def unblacklist(self, interaction: discord.Interaction, member: discord.Member):
        await db.remove_blacklist(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ {member.mention} removed from blacklist.", ephemeral=True)

    # ── Suspend ────────────────────────────────────────────────────────────────

    @app_commands.command(name="suspend", description="Temporarily suspend a member from duties")
    @app_commands.describe(member="The member to suspend", reason="Reason for suspension")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def suspend(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        gid = str(interaction.guild.id)
        await db.add_suspension(gid, str(member.id), reason, str(interaction.user))
        await db.log_case(gid, str(member.id), "SUSPEND", reason, str(interaction.user))
        # Try to add suspended role if configured
        suspended_role_id = await db.get_config("suspended_role")
        if suspended_role_id:
            role = interaction.guild.get_role(int(suspended_role_id))
            if role:
                try:
                    await member.add_roles(role, reason=f"Suspended: {reason}")
                except (discord.Forbidden, discord.HTTPException):
                    pass
        embed = discord.Embed(title="⏸️ Member Suspended", color=discord.Color.orange(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Actioned By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unsuspend", description="Restore suspended member access")
    @app_commands.describe(member="The member to unsuspend")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unsuspend(self, interaction: discord.Interaction, member: discord.Member):
        await db.remove_suspension(str(interaction.guild.id), str(member.id))
        suspended_role_id = await db.get_config("suspended_role")
        if suspended_role_id:
            role = interaction.guild.get_role(int(suspended_role_id))
            if role and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Suspension lifted")
                except (discord.Forbidden, discord.HTTPException):
                    pass
        embed = discord.Embed(title="▶️ Suspension Lifted", color=discord.Color.green(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Restored By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ── Soft ban ───────────────────────────────────────────────────────────────

    @app_commands.command(name="softban", description="Ban and immediately unban a member to purge their messages")
    @app_commands.describe(member="The member to softban", reason="Reason")
    @app_commands.checks.has_permissions(ban_members=True)
    async def softban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Softban — message cleanup"):
        await interaction.response.defer()
        await db.log_case(str(interaction.guild.id), str(member.id), "SOFTBAN", reason, str(interaction.user))
        try:
            await member.ban(reason=reason, delete_message_days=7)
            await asyncio.sleep(1)
            await interaction.guild.unban(member, reason="Softban — auto-unban")
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions to softban.", ephemeral=True)
            return
        embed = discord.Embed(title="🔨 Soft Ban Applied", color=discord.Color.orange(), timestamp=_ts())
        embed.add_field(name="Member", value=str(member), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Actioned By", value=interaction.user.mention, inline=True)
        await interaction.followup.send(embed=embed)

    # ── Wanted ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="wanted", description="Mark a member as wanted")
    @app_commands.describe(member="The member to mark as wanted", reason="Reason")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def wanted(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.add_wanted(str(interaction.guild.id), str(member.id), reason, str(interaction.user))
        embed = discord.Embed(title="🔴 WANTED", color=discord.Color.red(), timestamp=_ts())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Subject", value=f"{member.mention} ({member})", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unwanted", description="Remove a member's wanted status")
    @app_commands.describe(member="The member to clear")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unwanted(self, interaction: discord.Interaction, member: discord.Member):
        await db.remove_wanted(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ Wanted status removed from {member.mention}.", ephemeral=True)

    # ── Mass DM ────────────────────────────────────────────────────────────────

    @app_commands.command(name="massdm", description="Send a DM to all members with a specific role (or all members)")
    @app_commands.describe(message="The message to send", role="Role to target (leave empty for all non-bot members)")
    @app_commands.checks.has_permissions(administrator=True)
    async def massdm(self, interaction: discord.Interaction, message: str, role: discord.Role | None = None):
        await interaction.response.defer(ephemeral=True)
        targets = [m for m in interaction.guild.members if not m.bot and (role is None or role in m.roles)]
        sent, failed = 0, 0
        for member in targets:
            try:
                await member.send(f"📢 **Message from {interaction.guild.name}:**\n\n{message}")
                sent += 1
                await asyncio.sleep(0.5)
            except (discord.Forbidden, discord.HTTPException):
                failed += 1
        await interaction.followup.send(f"✅ DMs sent: **{sent}** succeeded, **{failed}** failed.", ephemeral=True)

    # ── Reinforcements ─────────────────────────────────────────────────────────

    @app_commands.command(name="reinforcements", description="Request reinforcements")
    @app_commands.describe(message="Details of the request")
    async def reinforcements(self, interaction: discord.Interaction, message: str):
        embed = discord.Embed(title="🆘 REINFORCEMENTS REQUESTED", description=message, color=discord.Color.red(), timestamp=_ts())
        embed.set_footer(text=f"Requested by {interaction.user} in #{interaction.channel.name}")
        await interaction.response.send_message(content="@here", embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CasesCog(bot))
