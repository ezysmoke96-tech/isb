import asyncio
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.db import get_config

# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_ts() -> str:
    return discord.utils.format_dt(datetime.now(timezone.utc), style="F")


async def _get_log_channel(bot: commands.Bot, key: str) -> discord.TextChannel | None:
    val = await get_config(key)
    if not val:
        return None
    ch = bot.get_channel(int(val))
    if isinstance(ch, discord.TextChannel):
        return ch
    return None


async def _audit(guild: discord.Guild, action: discord.AuditLogAction, target_id: int | None = None):
    """Fetch the most recent audit log entry for an action, optionally matching a target."""
    await asyncio.sleep(0.6)
    try:
        async for entry in guild.audit_logs(limit=5, action=action):
            if target_id is None or getattr(entry.target, "id", None) == target_id:
                return entry
    except discord.Forbidden:
        pass
    return None


# ── Member join view ───────────────────────────────────────────────────────────

class MemberJoinView(discord.ui.View):
    """Persistent view attached to member-join log messages."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅ Approved Personnel",
        style=discord.ButtonStyle.green,
        custom_id="join_approve",
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need **Manage Server** permission.", ephemeral=True)
            return

        member_id = _extract_member_id(interaction.message)
        if not member_id:
            await interaction.response.send_message("❌ Could not identify the member.", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True

        embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Approved by {interaction.user} • {_now_ts()}")

        await interaction.response.edit_message(
            content=f"✅ **Approved** by {interaction.user.mention}",
            embed=embed,
            view=self,
        )

    @discord.ui.button(
        label="🚫 Unauthorized Personnel — Ban",
        style=discord.ButtonStyle.red,
        custom_id="join_ban",
    )
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ You need **Ban Members** permission.", ephemeral=True)
            return

        member_id = _extract_member_id(interaction.message)
        if not member_id:
            await interaction.response.send_message("❌ Could not identify the member.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            await interaction.guild.ban(
                discord.Object(id=member_id),
                reason=f"Marked as Unauthorized Personnel by {interaction.user}",
                delete_message_days=0,
            )
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing **Ban Members** permission.", ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Ban failed: {e}", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True

        embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
        embed.color = discord.Color.dark_red()
        embed.set_footer(text=f"Banned by {interaction.user} • {_now_ts()}")

        await interaction.message.edit(
            content=f"🚫 **Banned** by {interaction.user.mention}",
            embed=embed,
            view=self,
        )


def _extract_member_id(message: discord.Message | None) -> int | None:
    """Pull the member ID stored in the embed footer."""
    if not message or not message.embeds:
        return None
    footer = message.embeds[0].footer.text or ""
    for part in footer.split("•"):
        part = part.strip()
        if part.startswith("Member ID:"):
            try:
                return int(part.replace("Member ID:", "").strip())
            except ValueError:
                pass
    return None


# ── Logging Cog ────────────────────────────────────────────────────────────────

class LoggingCog(commands.Cog, name="Logging"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(MemberJoinView())

    # ── Startup update log ─────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        ch = await _get_log_channel(self.bot, "log_update_channel")
        if not ch:
            return
        embed = discord.Embed(
            title="🤖 Bot Online",
            description="The bot has connected successfully and all systems are operational.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Active Cogs", value=", ".join(c for c in self.bot.cogs), inline=False)
        embed.set_footer(text="Update Logs")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    # ── /botupdate command ─────────────────────────────────────────────────────

    @app_commands.command(name="botupdate", description="Post a bot update announcement to the update logs channel")
    @app_commands.describe(title="Update title", changes="What was added or changed")
    @app_commands.checks.has_permissions(administrator=True)
    async def botupdate(self, interaction: discord.Interaction, title: str, changes: str):
        ch = await _get_log_channel(self.bot, "log_update_channel")
        if not ch:
            await interaction.response.send_message("❌ Update logs channel not configured. Use `/setup` → **Log Channels**.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"📋 Bot Update — {title}",
            description=changes,
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Posted by {interaction.user}")
        await ch.send(embed=embed)
        await interaction.response.send_message(f"✅ Update posted to {ch.mention}.", ephemeral=True)

    # ── Member join log ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ch = await _get_log_channel(self.bot, "log_member_channel")
        if not ch or ch.guild.id != member.guild.id:
            return
        embed = discord.Embed(
            title="🔔 Unauthorized Personnel Has Joined",
            description=f"{member.mention} **{member}** joined the server.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        embed.set_footer(text=f"Member ID: {member.id}")
        try:
            await ch.send(
                content="[ISB] Unauthorized Personnel has joined",
                embed=embed,
                view=MemberJoinView(),
            )
        except discord.Forbidden:
            pass

    # ── Role moderation log ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if not added and not removed:
            return

        ch = await _get_log_channel(self.bot, "log_role_mod_channel")
        if not ch or ch.guild.id != after.guild.id:
            return

        entry = await _audit(after.guild, discord.AuditLogAction.member_role_update, after.id)
        actioned_by = entry.user.mention if entry else "*Unknown*"

        embed = discord.Embed(
            title="🎭 Manual Role Update",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.add_field(name="Member", value=f"{after.mention} ({after})", inline=False)
        if added:
            embed.add_field(name="Roles Added", value=" ".join(r.mention for r in added), inline=False)
        if removed:
            embed.add_field(name="Roles Removed", value=" ".join(r.mention for r in removed), inline=False)
        embed.add_field(name="Actioned By", value=actioned_by, inline=True)
        embed.set_footer(text=f"Member ID: {after.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    # ── Chat moderation log ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        ch = await _get_log_channel(self.bot, "log_chat_mod_channel")
        if not ch or ch.guild.id != message.guild.id:
            return
        if message.channel.id == ch.id:
            return

        embed = discord.Embed(
            description=message.content[:2000] if message.content else "*[no text content]*",
            color=discord.Color.light_grey(),
            timestamp=message.created_at,
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join(a.url for a in message.attachments), inline=False)
        embed.set_footer(text=f"User ID: {message.author.id} • Msg ID: {message.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    # ── Server moderation log (channels) ──────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        ch = await _get_log_channel(self.bot, "log_server_mod_channel")
        if not ch or ch.guild.id != channel.guild.id:
            return
        entry = await _audit(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        actioned_by = entry.user.mention if entry else "*Unknown*"
        embed = discord.Embed(
            title="📁 Channel Created",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Channel", value=f"{channel.mention} (`#{channel.name}`)", inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        embed.add_field(name="Created By", value=actioned_by, inline=False)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        ch = await _get_log_channel(self.bot, "log_server_mod_channel")
        if not ch or ch.guild.id != channel.guild.id:
            return
        entry = await _audit(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        actioned_by = entry.user.mention if entry else "*Unknown*"
        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Channel Name", value=f"`#{channel.name}`", inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        embed.add_field(name="Deleted By", value=actioned_by, inline=False)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        ch = await _get_log_channel(self.bot, "log_server_mod_channel")
        if not ch or ch.guild.id != after.guild.id:
            return

        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if hasattr(before, "topic") and hasattr(after, "topic") and before.topic != after.topic:
            changes.append(f"**Topic:** `{before.topic or 'none'}` → `{after.topic or 'none'}`")
        if hasattr(before, "position") and before.position != after.position:
            changes.append(f"**Position:** `{before.position}` → `{after.position}`")
        if hasattr(before, "nsfw") and before.nsfw != after.nsfw:
            changes.append(f"**NSFW:** `{before.nsfw}` → `{after.nsfw}`")
        if hasattr(before, "slowmode_delay") and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"**Slowmode:** `{before.slowmode_delay}s` → `{after.slowmode_delay}s`")

        before_overrides = {str(t.id): p for t, p in before.overwrites.items()}
        after_overrides = {str(t.id): p for t, p in after.overwrites.items()}
        perm_changes = []
        all_targets = set(before_overrides) | set(after_overrides)
        for tid in all_targets:
            b = before_overrides.get(tid)
            a = after_overrides.get(tid)
            if b != a:
                target = after.guild.get_role(int(tid)) or after.guild.get_member(int(tid))
                label = target.name if target else f"ID:{tid}"
                perm_changes.append(f"• Permissions changed for `{label}`")
        if perm_changes:
            changes.append("**Permission Overwrites:**\n" + "\n".join(perm_changes))

        if not changes:
            return

        entry = await _audit(after.guild, discord.AuditLogAction.channel_update, after.id)
        actioned_by = entry.user.mention if entry else "*Unknown*"

        embed = discord.Embed(
            title="✏️ Channel Updated",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Channel", value=after.mention, inline=True)
        embed.add_field(name="Updated By", value=actioned_by, inline=True)
        embed.add_field(name="Changes", value="\n".join(changes)[:1024], inline=False)
        embed.set_footer(text=f"Channel ID: {after.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    # ── Mod moderation log (roles) ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        ch = await _get_log_channel(self.bot, "log_mod_mod_channel")
        if not ch or ch.guild.id != role.guild.id:
            return
        entry = await _audit(role.guild, discord.AuditLogAction.role_create, role.id)
        actioned_by = entry.user.mention if entry else "*Unknown*"
        embed = discord.Embed(
            title="✨ Role Created",
            color=role.color if role.color.value else discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Created By", value=actioned_by, inline=False)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.set_footer(text=f"Role ID: {role.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        ch = await _get_log_channel(self.bot, "log_mod_mod_channel")
        if not ch or ch.guild.id != role.guild.id:
            return
        entry = await _audit(role.guild, discord.AuditLogAction.role_delete, role.id)
        actioned_by = entry.user.mention if entry else "*Unknown*"
        embed = discord.Embed(
            title="🗑️ Role Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Role Name", value=f"`{role.name}`", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Deleted By", value=actioned_by, inline=False)
        embed.set_footer(text=f"Role ID: {role.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        ch = await _get_log_channel(self.bot, "log_mod_mod_channel")
        if not ch or ch.guild.id != after.guild.id:
            return

        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if before.color != after.color:
            changes.append(f"**Color:** `{before.color}` → `{after.color}`")
        if before.hoist != after.hoist:
            changes.append(f"**Hoisted:** `{before.hoist}` → `{after.hoist}`")
        if before.mentionable != after.mentionable:
            changes.append(f"**Mentionable:** `{before.mentionable}` → `{after.mentionable}`")
        if before.permissions != after.permissions:
            gained = discord.Permissions((before.permissions.value ^ after.permissions.value) & after.permissions.value)
            lost = discord.Permissions((before.permissions.value ^ after.permissions.value) & before.permissions.value)
            if gained.value:
                granted = [name for name, val in gained if val]
                changes.append("**Permissions Granted:** `" + "`, `".join(granted) + "`")
            if lost.value:
                revoked = [name for name, val in lost if val]
                changes.append("**Permissions Revoked:** `" + "`, `".join(revoked) + "`")

        if not changes:
            return

        entry = await _audit(after.guild, discord.AuditLogAction.role_update, after.id)
        actioned_by = entry.user.mention if entry else "*Unknown*"

        embed = discord.Embed(
            title="✏️ Role Updated",
            color=after.color if after.color.value else discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Role", value=after.mention, inline=True)
        embed.add_field(name="Updated By", value=actioned_by, inline=True)
        embed.add_field(name="Changes", value="\n".join(changes)[:1024], inline=False)
        embed.set_footer(text=f"Role ID: {after.id}")
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot))
