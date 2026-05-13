import re
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

import utils.db as db

_MEDALS = [
    "DD's Negligence Medal",
    "Keh's Red Wine",
    "Director's Negligence Medal",
    "Medal of Honor",
    "Medal of Authority",
    "Imperial Security Bureau Intelligence Medal",
    "Medal of Braveness",
    "Medal of Activity I",
    "Medal of Activity II",
    "Medal of Activity III",
    "Operative Master Medal",
    "Operative Chef Medal",
]

_8BALL_RESPONSES = [
    "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes, definitely.",
    "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
    "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
    "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]


def _ts() -> datetime:
    return datetime.now(timezone.utc)


def _parse_duration(s: str) -> int | None:
    """Parse duration string like '7d', '2d12h', '1h30m' into seconds."""
    pattern = r"(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    m = re.fullmatch(pattern, s.strip().lower())
    if not m or not any(m.groups()):
        return None
    weeks, days, hours, minutes, secs = (int(x or 0) for x in m.groups())
    total = weeks * 604800 + days * 86400 + hours * 3600 + minutes * 60 + secs
    return total if total > 0 else None


class PersonnelCog(commands.Cog, name="Personnel"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loa_check_loop.start()

    def cog_unload(self):
        self.loa_check_loop.cancel()

    # ── LOA background task ────────────────────────────────────────────────────

    @tasks.loop(minutes=1)
    async def loa_check_loop(self):
        now = int(datetime.now(timezone.utc).timestamp())
        expired = await db.get_expired_loas(now)
        for entry in expired:
            await db.end_loa(entry["guild_id"], entry["user_id"])
            guild = self.bot.get_guild(int(entry["guild_id"]))
            if not guild:
                continue
            loa_role_id = await db.get_config("loa_role")
            if loa_role_id:
                role = guild.get_role(int(loa_role_id))
                if role:
                    member = guild.get_member(int(entry["user_id"]))
                    if member and role in member.roles:
                        try:
                            await member.remove_roles(role, reason="LOA expired")
                        except (discord.Forbidden, discord.HTTPException):
                            pass

    @loa_check_loop.before_loop
    async def before_loa_check(self):
        await self.bot.wait_until_ready()

    # ── LOA commands ───────────────────────────────────────────────────────────

    @app_commands.command(name="loa", description="Log a leave of absence for a member")
    @app_commands.describe(member="The member going on LOA", duration="Duration e.g. 7d, 2w, 3d12h", reason="Reason for LOA")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def loa(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str):
        secs = _parse_duration(duration)
        if not secs:
            await interaction.response.send_message("❌ Invalid duration. Use formats like `7d`, `2w`, `12h`, `3d6h`.", ephemeral=True)
            return

        now = int(_ts().timestamp())
        end = now + secs
        gid = str(interaction.guild.id)

        await db.add_loa(gid, str(member.id), reason, str(interaction.user), now, end)

        loa_role_id = await db.get_config("loa_role")
        if loa_role_id:
            role = interaction.guild.get_role(int(loa_role_id))
            if role:
                try:
                    await member.add_roles(role, reason="LOA granted")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        embed = discord.Embed(title="🏖️ Leave of Absence Logged", color=discord.Color.blurple(), timestamp=_ts())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Returns", value=discord.utils.format_dt(discord.utils.utcnow().__class__.fromtimestamp(end, tz=timezone.utc), style="R"), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Granted By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="returnloa", description="Mark a member's return from LOA")
    @app_commands.describe(member="The member returning")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def returnloa(self, interaction: discord.Interaction, member: discord.Member):
        loa = await db.get_active_loa(str(interaction.guild.id), str(member.id))
        if not loa:
            await interaction.response.send_message(f"❌ {member.mention} is not currently on LOA.", ephemeral=True)
            return
        await db.end_loa(str(interaction.guild.id), str(member.id))
        loa_role_id = await db.get_config("loa_role")
        if loa_role_id:
            role = interaction.guild.get_role(int(loa_role_id))
            if role and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Returned from LOA")
                except (discord.Forbidden, discord.HTTPException):
                    pass
        embed = discord.Embed(title="✅ Member Returned from LOA", color=discord.Color.green(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Confirmed By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ── Medals ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="medal", description="Award a medal or ribbon to a member")
    @app_commands.describe(member="The recipient", medal_name="Select the medal to award")
    @app_commands.choices(medal_name=[app_commands.Choice(name=m, value=m) for m in _MEDALS])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def medal(self, interaction: discord.Interaction, member: discord.Member, medal_name: str):
        mid = await db.award_medal(str(interaction.guild.id), str(member.id), medal_name, str(interaction.user))
        embed = discord.Embed(title="🏅 Medal Awarded", color=discord.Color.gold(), timestamp=_ts())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Recipient", value=member.mention, inline=True)
        embed.add_field(name="Medal", value=f"**{medal_name}**", inline=False)
        embed.add_field(name="Awarded By", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"Medal Record #{mid}")
        await interaction.response.send_message(embed=embed)

    # ── Roster ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="roster", description="Display all personnel")
    async def roster(self, interaction: discord.Interaction):
        await interaction.response.defer()
        members = sorted([m for m in interaction.guild.members if not m.bot], key=lambda m: (m.top_role.position, m.display_name.lower()), reverse=True)
        embed = discord.Embed(title=f"📋 Personnel Roster — {interaction.guild.name}", color=discord.Color.blurple(), timestamp=_ts())
        embed.set_footer(text=f"Total members: {len(members)}")
        chunks = [members[i:i+20] for i in range(0, min(len(members), 60), 20)]
        for i, chunk in enumerate(chunks):
            lines = [f"{m.mention} — **{m.top_role.name}**" for m in chunk]
            embed.add_field(name=f"Personnel {i*20+1}–{i*20+len(chunk)}", value="\n".join(lines), inline=False)
        await interaction.followup.send(embed=embed)

    # ── Transfer ───────────────────────────────────────────────────────────────

    @app_commands.command(name="transfer", description="Transfer a member to a division")
    @app_commands.describe(member="The member to transfer", division="Target division name", new_role="Role to assign", old_role="Role to remove")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def transfer(self, interaction: discord.Interaction, member: discord.Member, division: str, new_role: discord.Role, old_role: discord.Role | None = None):
        await member.add_roles(new_role, reason=f"Transferred to {division}")
        if old_role and old_role in member.roles:
            await member.remove_roles(old_role, reason=f"Transferred from previous division")
        embed = discord.Embed(title="🔄 Member Transferred", color=discord.Color.blurple(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Division", value=division, inline=True)
        embed.add_field(name="New Role", value=new_role.mention, inline=True)
        if old_role:
            embed.add_field(name="Previous Role Removed", value=old_role.mention, inline=True)
        embed.add_field(name="Transferred By", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ── Tickets ────────────────────────────────────────────────────────────────

    @app_commands.command(name="ticket", description="Open a support ticket")
    async def ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        staff_role_id = await db.get_config("staff_role")
        if staff_role_id:
            role = guild.get_role(int(staff_role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        username_clean = interaction.user.name.replace(" ", "-")
        ticket_count = await db.create_ticket(str(guild.id), "0", str(interaction.user.id))
        channel_name = f"ticket-{username_clean}-{ticket_count}"
        try:
            channel = await guild.create_text_channel(channel_name, overwrites=overwrites, reason="Support ticket")
            await db.close_ticket_db("0")
            await db.create_ticket(str(guild.id), str(channel.id), str(interaction.user.id))
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to create channels.", ephemeral=True)
            return

        embed = discord.Embed(title="🎫 Ticket Opened", description=f"Hello {interaction.user.mention}! Support will be with you shortly.\nUse `/closeticket` when your issue is resolved.", color=discord.Color.green(), timestamp=_ts())
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

    @app_commands.command(name="closeticket", description="Close a support ticket")
    async def closeticket(self, interaction: discord.Interaction):
        ticket = await db.get_ticket_by_channel(str(interaction.channel.id))
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return
        if ticket["status"] == "CLOSED":
            await interaction.response.send_message("❌ This ticket is already closed.", ephemeral=True)
            return
        await db.close_ticket_db(str(interaction.channel.id))
        embed = discord.Embed(title="🔒 Ticket Closed", description=f"Closed by {interaction.user.mention}. Channel will be deleted in 5 seconds.", color=discord.Color.red(), timestamp=_ts())
        await interaction.response.send_message(embed=embed)
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket closed")
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ── Countdown ──────────────────────────────────────────────────────────────

    @app_commands.command(name="countdown", description="Start a countdown timer")
    @app_commands.describe(duration="Duration e.g. 10m, 1h, 30s", label="What the countdown is for")
    async def countdown(self, interaction: discord.Interaction, duration: str, label: str = "Countdown"):
        secs = _parse_duration(duration)
        if not secs:
            await interaction.response.send_message("❌ Invalid duration. Use formats like `10m`, `1h`, `30s`.", ephemeral=True)
            return
        import time
        end_time = int(time.time()) + secs
        embed = discord.Embed(title=f"⏱️ {label}", color=discord.Color.blurple(), timestamp=_ts())
        embed.add_field(name="Ends", value=discord.utils.format_dt(datetime.fromtimestamp(end_time, tz=timezone.utc), style="R"), inline=True)
        embed.add_field(name="At", value=discord.utils.format_dt(datetime.fromtimestamp(end_time, tz=timezone.utc), style="F"), inline=True)
        embed.set_footer(text=f"Started by {interaction.user}")
        await interaction.response.send_message(embed=embed)

    # ── Activity ───────────────────────────────────────────────────────────────

    @app_commands.command(name="activitycheck", description="Check a member's server activity")
    @app_commands.describe(member="The member to check")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def activitycheck(self, interaction: discord.Interaction, member: discord.Member):
        embed = discord.Embed(title=f"📊 Activity Check — {member}", color=discord.Color.blurple(), timestamp=_ts())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="Status", value=str(member.status).title(), inline=True)
        embed.add_field(name="Roles", value=str(len(member.roles) - 1), inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        warns = await db.get_warnings(str(interaction.guild.id), str(member.id))
        strikes = await db.get_strikes(str(interaction.guild.id), str(member.id))
        embed.add_field(name="Warnings", value=str(len(warns)), inline=True)
        embed.add_field(name="Strikes", value=str(len(strikes)), inline=True)
        loa = await db.get_active_loa(str(interaction.guild.id), str(member.id))
        embed.add_field(name="On LOA", value="Yes" if loa else "No", inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="inactivitystrike", description="Issue a strike for inactivity")
    @app_commands.describe(member="The inactive member", reason="Additional context")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def inactivitystrike(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Inactivity"):
        full_reason = f"Inactivity: {reason}"
        gid = str(interaction.guild.id)
        sid = await db.add_strike(gid, str(member.id), full_reason, str(interaction.user))
        await db.log_case(gid, str(member.id), "INACTIVITY_STRIKE", full_reason, str(interaction.user))
        embed = discord.Embed(title="📉 Inactivity Strike", color=discord.Color.red(), timestamp=_ts())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=full_reason, inline=False)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"Strike ID: {sid}")
        await interaction.response.send_message(embed=embed)

    # ── Chain of Command ───────────────────────────────────────────────────────

    @app_commands.command(name="chainofcommand", description="Display the leadership hierarchy")
    async def chainofcommand(self, interaction: discord.Interaction):
        await interaction.response.defer()
        roles_with_members = []
        for role in sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True):
            if role.is_default() or not role.members:
                continue
            roles_with_members.append(role)
            if len(roles_with_members) >= 10:
                break
        embed = discord.Embed(title=f"🏛️ Chain of Command — {interaction.guild.name}", color=discord.Color.gold(), timestamp=_ts())
        for role in roles_with_members:
            names = ", ".join(m.display_name for m in role.members[:5])
            if len(role.members) > 5:
                names += f" (+{len(role.members)-5} more)"
            embed.add_field(name=role.name, value=names, inline=False)
        await interaction.followup.send(embed=embed)

    # ── Protocol ───────────────────────────────────────────────────────────────

    @app_commands.command(name="protocol", description="Display ISB protocols")
    async def protocol(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📜 ISB Standard Protocols", color=discord.Color.dark_red(), timestamp=_ts())
        embed.add_field(name="Protocol 1 — Chain of Command", value="All orders must follow the established chain of command. Direct superiors are to be obeyed unless orders violate ISB directives.", inline=False)
        embed.add_field(name="Protocol 2 — Intel Handling", value="All classified intel is to be handled at or above the required clearance level. Unauthorized distribution is punishable by immediate suspension.", inline=False)
        embed.add_field(name="Protocol 3 — Suspect Detention", value="Suspects are to be logged in the database before detention. All interrogations must be documented.", inline=False)
        embed.add_field(name="Protocol 4 — Code Black", value="Upon Code Black activation, all personnel report to their stations. Non-essential access is revoked until Code Green is issued.", inline=False)
        embed.add_field(name="Protocol 5 — LOA Policy", value="LOA must be approved by a superior officer. Unapproved absence will result in inactivity strikes.", inline=False)
        embed.add_field(name="Protocol 6 — Traitor Response", value="Any suspected traitor must be immediately flagged, placed under surveillance, and reported to Command.", inline=False)
        embed.set_footer(text="ISB — Imperial Security Bureau")
        await interaction.response.send_message(embed=embed)

    # ── Rank Card ──────────────────────────────────────────────────────────────

    @app_commands.command(name="rankcard", description="Display a member's progression card")
    @app_commands.describe(member="The member to view (leave empty for yourself)")
    async def rankcard(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await interaction.response.defer(ephemeral=True)
        target = member or interaction.user
        gid = str(interaction.guild.id)
        uid = str(target.id)

        clearance = await db.get_clearance(gid, uid)
        medals = await db.get_medals(gid, uid)
        warnings = await db.get_warnings(gid, uid)
        strikes = await db.get_strikes(gid, uid)
        loa = await db.get_active_loa(gid, uid)
        surveillance = await db.get_surveillance(gid, uid)
        traitor = await db.get_traitor_flag(gid, uid)
        priority = await db.get_priority_target(gid, uid)
        wanted = await db.is_wanted(gid, uid)
        informant = await db.is_informant(gid, uid)
        blacklisted = await db.is_blacklisted(gid, uid)

        embed = discord.Embed(title=f"🪪 Rank Card — {target.display_name}", color=target.color if target.color.value else discord.Color.blurple(), timestamp=_ts())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Rank", value=target.top_role.mention, inline=True)
        embed.add_field(name="Clearance", value=f"Level {clearance}" if clearance else "None", inline=True)
        embed.add_field(name="Joined", value=discord.utils.format_dt(target.joined_at, style="R") if target.joined_at else "Unknown", inline=True)
        embed.add_field(name="Medals", value=str(len(medals)), inline=True)
        embed.add_field(name="Warnings", value=str(len(warnings)), inline=True)
        embed.add_field(name="Strikes", value=str(len(strikes)), inline=True)
        if medals:
            embed.add_field(name="Awards", value="\n".join(f"🏅 {m['medal_name']}" for m in medals[:5]), inline=False)
        flags = []
        if loa:
            flags.append("🏖️ On LOA")
        if surveillance:
            flags.append("👁️ Under Surveillance")
        if traitor:
            flags.append("⚠️ Traitor Flag")
        if priority:
            flags.append("🎯 Priority Target")
        if wanted:
            flags.append("🔴 Wanted")
        if informant:
            flags.append("✅ Informant")
        if blacklisted:
            flags.append("🚫 Blacklisted")
        if flags:
            embed.add_field(name="Flags", value="\n".join(flags), inline=False)
        embed.set_footer(text=f"User ID: {target.id}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── Help ───────────────────────────────────────────────────────────────────

    @app_commands.command(name="help", description="Display all available commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📖 ISB Bot — Command Reference", color=discord.Color.blurple(), timestamp=_ts())
        embed.add_field(name="🔒 Verification", value="`/verify` `/unverify` `/whois`", inline=False)
        embed.add_field(name="🎮 Roblox", value="`/info` `/bgcheck` `/gameban` `/ungameban`", inline=False)
        embed.add_field(name="🛡️ Moderation", value="`/kick` `/ban` `/unban` `/mute` `/purge` `/softban`", inline=False)
        embed.add_field(name="⚠️ Discipline", value="`/warn` `/warnings` `/clearwarnings` `/strike` `/strikes` `/clearstrikes`", inline=False)
        embed.add_field(name="📁 Cases", value="`/case` `/casesearch` `/terminatecase` `/auditlog` `/evidence`", inline=False)
        embed.add_field(name="📋 Reports", value="`/report` `/reports` `/closereport`", inline=False)
        embed.add_field(name="🚨 Status", value="`/suspend` `/unsuspend` `/blacklist` `/unblacklist` `/wanted` `/unwanted` `/watchlist` `/removewatchlist`", inline=False)
        embed.add_field(name="🎭 Roles", value="`/promote` `/demote` `/leaderboard` `/transfer` `/autorole`", inline=False)
        embed.add_field(name="🏅 Personnel", value="`/loa` `/returnloa` `/medal` `/roster` `/activitycheck` `/inactivitystrike` `/rankcard`", inline=False)
        embed.add_field(name="🎫 Tickets", value="`/ticket` `/closeticket`", inline=False)
        embed.add_field(name="📄 Intelligence", value="`/intelcreate` `/intelview` `/inteldelete` `/intelarchive` `/investigationstart` `/investigationclose` `/investigationlist`", inline=False)
        embed.add_field(name="🎯 Targets", value="`/targetprofile` `/suspectadd` `/suspectremove` `/traitorflag` `/removeflag` `/prioritytarget` `/surveillance` `/endsurveillance` `/threatlevel` `/interrogate` `/confiscate`", inline=False)
        embed.add_field(name="🔐 Clearance & Informants", value="`/clearance` `/clearanceview` `/informantadd` `/informantremove`", inline=False)
        embed.add_field(name="🎯 Missions", value="`/missionbrief` `/missionclose`", inline=False)
        embed.add_field(name="📡 Communications", value="`/classifiedpost` `/encrypt` `/decrypt` `/intelping` `/raidalert` `/codeblack` `/codegreen` `/massdm` `/reinforcements`", inline=False)
        embed.add_field(name="🎓 Academy", value="`/academy` `/academykick` `/academylogs`", inline=False)
        embed.add_field(name="🎁 Giveaways", value="`/giveaway` `/gend` `/greroll`", inline=False)
        embed.add_field(name="🏛️ Server Info", value="`/chainofcommand` `/protocol` `/countdown` `/botupdate` `/logignore`", inline=False)
        embed.add_field(name="⚙️ Config", value="`/setup` `/editsetup`", inline=False)
        embed.add_field(name="🎲 Fun", value="`/dice` `/coinflip` `/8ball`", inline=False)
        embed.add_field(name="📊 General", value="`/ping` `/hello` `/serverinfo` `/help`", inline=False)
        embed.set_footer(text="ISB Bot — Imperial Security Bureau")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PersonnelCog(bot))
