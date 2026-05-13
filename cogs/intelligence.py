import base64
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import utils.db as db


def _ts() -> datetime:
    return datetime.now(timezone.utc)


class IntelCreateModal(discord.ui.Modal, title="Create Intelligence Report"):
    report_title = discord.ui.TextInput(label="Report Title", max_length=100)
    classification = discord.ui.TextInput(label="Classification (CLASSIFIED / TOP SECRET / etc.)", default="CLASSIFIED", max_length=50)
    content = discord.ui.TextInput(label="Report Content", style=discord.TextStyle.paragraph, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        report_id = await db.save_intel(
            str(interaction.guild.id),
            self.report_title.value,
            self.content.value,
            self.classification.value.upper(),
            str(interaction.user),
        )
        embed = discord.Embed(title=f"📄 Intel Report Created — #{report_id}", color=discord.Color.dark_red(), timestamp=_ts())
        embed.add_field(name="Title", value=self.report_title.value, inline=True)
        embed.add_field(name="Classification", value=f"**{self.classification.value.upper()}**", inline=True)
        embed.add_field(name="Created By", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"Report ID: {report_id} — Use /intelview {report_id} to view")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class MissionModal(discord.ui.Modal, title="Create Mission Briefing"):
    name = discord.ui.TextInput(label="Operation Name", max_length=100)
    briefing = discord.ui.TextInput(label="Briefing", style=discord.TextStyle.paragraph, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        mid = await db.create_mission(str(interaction.guild.id), self.name.value, self.briefing.value, str(interaction.user))
        embed = discord.Embed(title=f"🎯 Mission Briefing Created — #{mid}", color=discord.Color.blurple(), timestamp=_ts())
        embed.add_field(name="Operation", value=self.name.value, inline=False)
        embed.add_field(name="Briefing", value=self.briefing.value[:500], inline=False)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"Mission ID: {mid}")
        await interaction.response.send_message(embed=embed)


class InvestigationModal(discord.ui.Modal, title="Open Investigation"):
    title_field = discord.ui.TextInput(label="Investigation Title", max_length=100)
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        inv_id = await db.open_investigation(str(interaction.guild.id), self.title_field.value, self.description.value, str(interaction.user))
        embed = discord.Embed(title=f"🔍 Investigation Opened — #{inv_id}", color=discord.Color.orange(), timestamp=_ts())
        embed.add_field(name="Title", value=self.title_field.value, inline=False)
        embed.add_field(name="Description", value=self.description.value, inline=False)
        embed.add_field(name="Opened By", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"Investigation ID: {inv_id}")
        await interaction.response.send_message(embed=embed)


class IntelligenceCog(commands.Cog, name="Intelligence"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /intel group (create/view/delete/archive) ──────────────────────────────
    intel = app_commands.Group(name="intel", description="Intelligence report management")

    @intel.command(name="create", description="Create an intelligence report")
    async def intelcreate(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Missing permission.", ephemeral=True)
            return
        await interaction.response.send_modal(IntelCreateModal())

    @intel.command(name="view", description="View a classified intelligence report")
    @app_commands.describe(report_id="The report ID")
    async def intelview(self, interaction: discord.Interaction, report_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Missing permission.", ephemeral=True)
            return
        report = await db.get_intel(report_id, str(interaction.guild.id))
        if not report:
            await interaction.response.send_message(f"❌ Report #{report_id} not found.", ephemeral=True)
            return
        status = "📦 ARCHIVED" if report["archived"] else "🟢 ACTIVE"
        embed = discord.Embed(title=f"📄 [{report['classification']}] {report['title']}", description=report["content"], color=discord.Color.dark_red(), timestamp=_ts())
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Created By", value=report["created_by"], inline=True)
        embed.add_field(name="Filed At", value=report["created_at"], inline=True)
        embed.set_footer(text=f"Report ID: {report_id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @intel.command(name="delete", description="Permanently delete an intelligence report")
    @app_commands.describe(report_id="The report ID to delete")
    async def inteldelete(self, interaction: discord.Interaction, report_id: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator only.", ephemeral=True)
            return
        report = await db.get_intel(report_id, str(interaction.guild.id))
        if not report:
            await interaction.response.send_message(f"❌ Report #{report_id} not found.", ephemeral=True)
            return
        await db.delete_intel(report_id, str(interaction.guild.id))
        await interaction.response.send_message(f"🗑️ Report **#{report_id} — {report['title']}** permanently deleted.", ephemeral=True)

    @intel.command(name="archive", description="Archive an intelligence report")
    @app_commands.describe(report_id="The report ID to archive")
    async def intelarchive(self, interaction: discord.Interaction, report_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Missing permission.", ephemeral=True)
            return
        report = await db.get_intel(report_id, str(interaction.guild.id))
        if not report:
            await interaction.response.send_message(f"❌ Report #{report_id} not found.", ephemeral=True)
            return
        await db.archive_intel(report_id, str(interaction.guild.id))
        await interaction.response.send_message(f"📦 Report **#{report_id}** has been archived.", ephemeral=True)

    # ── /investigation group (start/close/list) ────────────────────────────────
    investigation = app_commands.Group(name="investigation", description="Investigation management")

    @investigation.command(name="start", description="Open a new investigation")
    async def investigationstart(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Missing permission.", ephemeral=True)
            return
        await interaction.response.send_modal(InvestigationModal())

    @investigation.command(name="close", description="Close an investigation file")
    @app_commands.describe(investigation_id="The investigation ID to close")
    async def investigationclose(self, interaction: discord.Interaction, investigation_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Missing permission.", ephemeral=True)
            return
        inv = await db.get_investigation(investigation_id, str(interaction.guild.id))
        if not inv:
            await interaction.response.send_message(f"❌ Investigation #{investigation_id} not found.", ephemeral=True)
            return
        await db.close_investigation(investigation_id, str(interaction.guild.id))
        await interaction.response.send_message(f"🔒 Investigation **#{investigation_id} — {inv['title']}** closed.", ephemeral=True)

    @investigation.command(name="list", description="List active investigations")
    async def investigationlist(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Missing permission.", ephemeral=True)
            return
        invs = await db.list_investigations(str(interaction.guild.id))
        embed = discord.Embed(title="🔍 Active Investigations", color=discord.Color.orange(), timestamp=_ts())
        if not invs:
            embed.description = "No active investigations."
        else:
            for inv in invs:
                embed.add_field(name=f"#{inv['id']} — {inv['title']}", value=f"Opened by {inv['opened_by']} on {inv['opened_at'][:10]}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Suspects ───────────────────────────────────────────────────────────────

    @app_commands.command(name="suspectadd", description="Add a suspect to the database")
    @app_commands.describe(member="The member to flag as suspect", reason="Reason")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def suspectadd(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.add_suspect(str(interaction.guild.id), str(member.id), reason, str(interaction.user))
        embed = discord.Embed(title="🚨 Suspect Added", color=discord.Color.red(), timestamp=_ts())
        embed.add_field(name="Suspect", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Filed By", value=interaction.user.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="suspectremove", description="Remove a suspect entry")
    @app_commands.describe(member="The member to remove from suspects")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def suspectremove(self, interaction: discord.Interaction, member: discord.Member):
        await db.remove_suspect(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ {member.mention} removed from suspect database.", ephemeral=True)

    @app_commands.command(name="targetprofile", description="Display full target dossier")
    @app_commands.describe(member="The member to profile")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def targetprofile(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        gid = str(interaction.guild.id)
        uid = str(member.id)

        suspect = await db.get_suspect(gid, uid)
        surv = await db.get_surveillance(gid, uid)
        traitor = await db.get_traitor_flag(gid, uid)
        priority = await db.get_priority_target(gid, uid)
        threat = await db.get_threat_level(gid, uid)
        clearance = await db.get_clearance(gid, uid)
        warnings = await db.get_warnings(gid, uid)
        strikes = await db.get_strikes(gid, uid)
        informant = await db.is_informant(gid, uid)
        wanted = await db.is_wanted(gid, uid)
        blacklisted = await db.is_blacklisted(gid, uid)

        embed = discord.Embed(title=f"🗂️ Target Dossier — {member}", color=discord.Color.dark_red(), timestamp=_ts())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Clearance Level", value=f"Level {clearance}" if clearance else "None", inline=True)
        embed.add_field(name="Threat Level", value=threat or "Not assessed", inline=True)
        embed.add_field(name="Suspect", value=f"Yes — {suspect['reason']}" if suspect else "No", inline=False)
        embed.add_field(name="Under Surveillance", value=f"Yes — {surv['reason']}" if surv else "No", inline=True)
        embed.add_field(name="Traitor Flag", value=f"⚠️ Yes — {traitor['reason']}" if traitor else "No", inline=True)
        embed.add_field(name="Priority Target", value=f"🎯 Yes — {priority['reason']}" if priority else "No", inline=True)
        embed.add_field(name="Wanted", value="🔴 Yes" if wanted else "No", inline=True)
        embed.add_field(name="Blacklisted", value="🚫 Yes" if blacklisted else "No", inline=True)
        embed.add_field(name="Informant", value="✅ Yes" if informant else "No", inline=True)
        embed.add_field(name="Warnings", value=str(len(warnings)), inline=True)
        embed.add_field(name="Strikes", value=str(len(strikes)), inline=True)
        embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "Unknown", inline=False)
        embed.set_footer(text=f"User ID: {member.id}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── Missions ───────────────────────────────────────────────────────────────

    @app_commands.command(name="missionbrief", description="Create an operation briefing")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def missionbrief(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MissionModal())

    @app_commands.command(name="missionclose", description="Close an operation briefing")
    @app_commands.describe(mission_id="The mission ID to close")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def missionclose(self, interaction: discord.Interaction, mission_id: int):
        mission = await db.get_mission(mission_id, str(interaction.guild.id))
        if not mission:
            await interaction.response.send_message(f"❌ Mission #{mission_id} not found.", ephemeral=True)
            return
        await db.close_mission(mission_id, str(interaction.guild.id))
        await interaction.response.send_message(f"🔒 Mission **#{mission_id} — {mission['name']}** closed.", ephemeral=True)

    # ── Personnel flags ────────────────────────────────────────────────────────

    @app_commands.command(name="surveillance", description="Mark a user as under surveillance")
    @app_commands.describe(member="Target member", reason="Reason for surveillance")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def surveillance(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.set_surveillance(str(interaction.guild.id), str(member.id), reason, str(interaction.user))
        embed = discord.Embed(title="👁️ Surveillance Active", color=discord.Color.orange(), timestamp=_ts())
        embed.add_field(name="Target", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Ordered By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="endsurveillance", description="End surveillance on a user")
    @app_commands.describe(member="Member to release from surveillance")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def endsurveillance(self, interaction: discord.Interaction, member: discord.Member):
        await db.end_surveillance(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ Surveillance on {member.mention} has ended.", ephemeral=True)

    @app_commands.command(name="clearance", description="Set a user's clearance level (1–5)")
    @app_commands.describe(member="The member", level="Clearance level (1–5)")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearance(self, interaction: discord.Interaction, member: discord.Member, level: app_commands.Range[int, 1, 5]):
        await db.set_clearance(str(interaction.guild.id), str(member.id), level, str(interaction.user))
        embed = discord.Embed(title="🔐 Clearance Updated", color=discord.Color.blurple(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Clearance Level", value=f"Level {level}", inline=True)
        embed.add_field(name="Set By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clearanceview", description="View a user's clearance level")
    @app_commands.describe(member="The member to check")
    async def clearanceview(self, interaction: discord.Interaction, member: discord.Member):
        level = await db.get_clearance(str(interaction.guild.id), str(member.id))
        embed = discord.Embed(title="🔐 Clearance Status", color=discord.Color.blurple())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Clearance Level", value=f"Level {level}" if level else "No clearance assigned", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="threatlevel", description="Set the threat level of a target")
    @app_commands.describe(member="The target", level="Threat level (LOW / MEDIUM / HIGH / CRITICAL)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def threatlevel(self, interaction: discord.Interaction, member: discord.Member, level: str):
        level = level.upper()
        colors = {"LOW": discord.Color.green(), "MEDIUM": discord.Color.yellow(), "HIGH": discord.Color.orange(), "CRITICAL": discord.Color.red()}
        await db.set_threat_level(str(interaction.guild.id), str(member.id), level, str(interaction.user))
        embed = discord.Embed(title="⚠️ Threat Level Set", color=colors.get(level, discord.Color.blurple()), timestamp=_ts())
        embed.add_field(name="Target", value=member.mention, inline=True)
        embed.add_field(name="Threat Level", value=f"**{level}**", inline=True)
        embed.add_field(name="Set By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="informantadd", description="Register a member as an informant")
    @app_commands.describe(member="The member to register")
    @app_commands.checks.has_permissions(administrator=True)
    async def informantadd(self, interaction: discord.Interaction, member: discord.Member):
        await db.add_informant(str(interaction.guild.id), str(member.id), str(interaction.user))
        await interaction.response.send_message(f"✅ {member.mention} registered as an informant.", ephemeral=True)

    @app_commands.command(name="informantremove", description="Remove informant status from a member")
    @app_commands.describe(member="The member to de-register")
    @app_commands.checks.has_permissions(administrator=True)
    async def informantremove(self, interaction: discord.Interaction, member: discord.Member):
        await db.remove_informant(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ {member.mention}'s informant status removed.", ephemeral=True)

    @app_commands.command(name="traitorflag", description="Flag a member as a suspected traitor")
    @app_commands.describe(member="The member to flag", reason="Reason")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def traitorflag(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.add_traitor_flag(str(interaction.guild.id), str(member.id), reason, str(interaction.user))
        embed = discord.Embed(title="⚠️ Traitor Flag Raised", color=discord.Color.dark_red(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Flagged By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removeflag", description="Remove traitor suspicion flag from a member")
    @app_commands.describe(member="The member to clear")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def removeflag(self, interaction: discord.Interaction, member: discord.Member):
        await db.remove_traitor_flag(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ Traitor flag removed from {member.mention}.", ephemeral=True)

    @app_commands.command(name="prioritytarget", description="Mark a member as a high priority suspect")
    @app_commands.describe(member="The target", reason="Reason")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def prioritytarget(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.add_priority_target(str(interaction.guild.id), str(member.id), reason, str(interaction.user))
        embed = discord.Embed(title="🎯 Priority Target Designated", color=discord.Color.red(), timestamp=_ts())
        embed.add_field(name="Target", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Ordered By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="interrogate", description="Open an interrogation log for a member")
    @app_commands.describe(member="The member being interrogated", notes="Initial notes")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def interrogate(self, interaction: discord.Interaction, member: discord.Member, notes: str):
        iid = await db.open_interrogation(str(interaction.guild.id), str(member.id), notes, str(interaction.user))
        embed = discord.Embed(title=f"🔎 Interrogation Log #{iid}", color=discord.Color.dark_orange(), timestamp=_ts())
        embed.add_field(name="Subject", value=member.mention, inline=True)
        embed.add_field(name="Conducted By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Initial Notes", value=notes, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="confiscate", description="Log a simulated confiscation")
    @app_commands.describe(member="The member", item="Item or asset confiscated")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def confiscate(self, interaction: discord.Interaction, member: discord.Member, item: str):
        embed = discord.Embed(title="📦 Confiscation Logged", color=discord.Color.orange(), timestamp=_ts())
        embed.add_field(name="Subject", value=member.mention, inline=True)
        embed.add_field(name="Item Confiscated", value=item, inline=True)
        embed.add_field(name="Actioned By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ── Communications ─────────────────────────────────────────────────────────

    @app_commands.command(name="classifiedpost", description="Send a classified announcement")
    @app_commands.describe(message="The classified message to broadcast")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def classifiedpost(self, interaction: discord.Interaction, message: str):
        embed = discord.Embed(
            title="⛔ CLASSIFIED TRANSMISSION",
            description=f"```\n{message}\n```",
            color=discord.Color.dark_red(),
            timestamp=_ts(),
        )
        embed.set_footer(text=f"Issued by: {interaction.user} | ISB")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="encrypt", description="Encrypt an ISB message (ISB Protocol Alpha)")
    @app_commands.describe(message="The message to encrypt")
    async def encrypt(self, interaction: discord.Interaction, message: str):
        encoded = base64.b64encode(message.encode()).decode()
        embed = discord.Embed(title="🔒 ISB Encrypted Transmission", color=discord.Color.dark_green(), timestamp=_ts())
        embed.add_field(name="Encrypted Output", value=f"```{encoded}```", inline=False)
        embed.set_footer(text="Protocol: ISB-ALPHA-B64 | Use /decrypt to decode")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="decrypt", description="Decrypt an ISB encrypted message")
    @app_commands.describe(message="The encrypted message to decrypt")
    async def decrypt(self, interaction: discord.Interaction, message: str):
        try:
            decoded = base64.b64decode(message.encode()).decode()
        except Exception:
            await interaction.response.send_message("❌ Invalid encrypted string. Make sure you copied the full output from `/encrypt`.", ephemeral=True)
            return
        embed = discord.Embed(title="🔓 Decryption Complete", color=discord.Color.green(), timestamp=_ts())
        embed.add_field(name="Decrypted Message", value=f"```{decoded}```", inline=False)
        embed.set_footer(text="Protocol: ISB-ALPHA-B64")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="intelping", description="Alert intelligence personnel")
    @app_commands.describe(message="Alert message to send")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def intelping(self, interaction: discord.Interaction, message: str):
        embed = discord.Embed(title="🔔 INTEL ALERT", description=message, color=discord.Color.yellow(), timestamp=_ts())
        embed.set_footer(text=f"Issued by {interaction.user}")
        await interaction.response.send_message(content="@here", embed=embed)

    @app_commands.command(name="raidalert", description="Issue a raid or threat warning")
    @app_commands.describe(threat="Describe the raid or threat")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def raidalert(self, interaction: discord.Interaction, threat: str):
        embed = discord.Embed(title="🚨 RAID / THREAT ALERT", description=threat, color=discord.Color.red(), timestamp=_ts())
        embed.set_footer(text=f"Issued by {interaction.user}")
        await interaction.response.send_message(content="@everyone", embed=embed)

    @app_commands.command(name="codeblack", description="Activate emergency ISB protocol (Code Black)")
    @app_commands.checks.has_permissions(administrator=True)
    async def codeblack(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⬛ CODE BLACK — EMERGENCY PROTOCOL ACTIVATED",
            description="All ISB personnel are to report to their stations immediately.\nAll non-essential operations are suspended.\nSecurity level elevated to MAXIMUM.",
            color=discord.Color.from_rgb(20, 20, 20),
            timestamp=_ts(),
        )
        embed.set_footer(text=f"Activated by {interaction.user}")
        await interaction.response.send_message(content="@everyone", embed=embed)

    @app_commands.command(name="codegreen", description="Return to normal ISB operations (Code Green)")
    @app_commands.checks.has_permissions(administrator=True)
    async def codegreen(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🟢 CODE GREEN — NORMAL OPERATIONS RESUMED",
            description="The emergency protocol has been lifted.\nAll ISB personnel may return to standard duties.\nSecurity level returned to normal.",
            color=discord.Color.green(),
            timestamp=_ts(),
        )
        embed.set_footer(text=f"Deactivated by {interaction.user}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(IntelligenceCog(bot))
