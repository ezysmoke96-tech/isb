import discord
from discord import app_commands
from discord.ext import commands

from utils.db import get_config

ISB_EMOJI = "<:ISB:1503058585997934714>"

PHASE_KEYS = {
    "1": "phase1_role",
    "2": "phase2_role",
    "3": "phase3_role",
    "4": "phase4_role",
    "5": "phase5_role",
    "pass": "academy_pass_role",
}


class AcademyCog(commands.Cog, name="Academy"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── /academykick ─────────────────────────────────────────────────────────

    @app_commands.command(name="academykick", description="Kick a member from the ISB Academy server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def academykick(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        academy_guild_id = await get_config("academy_guild_id")
        if not academy_guild_id:
            embed = discord.Embed(
                title="⚙️ Not Configured",
                description="The Academy server ID is not set. Use `/setup` to configure it.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        academy_guild = interaction.client.get_guild(int(academy_guild_id))
        if not academy_guild:
            embed = discord.Embed(
                title="❌ Academy Server Unreachable",
                description="The bot is not in the configured Academy server.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        academy_member = academy_guild.get_member(member.id)
        if not academy_member:
            embed = discord.Embed(
                title="Member Not Found",
                description=f"{member.mention} is not in the Academy server.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        kick_message = (
            f"{ISB_EMOJI} You have been kicked from the academy. "
            f"{reason} , By {interaction.user.mention}"
        )

        try:
            await member.send(kick_message)
        except discord.Forbidden:
            pass

        try:
            await academy_member.kick(reason=f"{reason} — by {interaction.user}")
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="The bot doesn't have kick permissions in the Academy server.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        confirm_embed = discord.Embed(
            title=f"{ISB_EMOJI} Member Kicked from Academy",
            color=discord.Color.red(),
        )
        confirm_embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        confirm_embed.add_field(name="Reason", value=reason, inline=False)
        confirm_embed.add_field(name="Actioned by", value=interaction.user.mention, inline=False)
        confirm_embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=confirm_embed)

    # ─── /academy ─────────────────────────────────────────────────────────────

    @app_commands.command(name="academy", description="Assign an academy phase role to a member")
    @app_commands.describe(phase="The academy phase", member="The member who passed")
    @app_commands.choices(
        phase=[
            app_commands.Choice(name="Phase 1", value="1"),
            app_commands.Choice(name="Phase 2", value="2"),
            app_commands.Choice(name="Phase 3", value="3"),
            app_commands.Choice(name="Phase 4", value="4"),
            app_commands.Choice(name="Phase 5", value="5"),
            app_commands.Choice(name="Pass", value="pass"),
        ]
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def academy(
        self,
        interaction: discord.Interaction,
        phase: app_commands.Choice[str],
        member: discord.Member,
    ):
        role_key = PHASE_KEYS[phase.value]
        role_id = await get_config(role_key)

        is_pass = phase.value == "pass"
        label = "Academy Pass" if is_pass else f"Phase {phase.value}"
        not_configured_hint = "Use `/setup` → **Roles** to configure it." if is_pass else "Use `/setup` → **Phase Roles** to configure it."

        if not role_id:
            embed = discord.Embed(
                title=f"⚙️ {label} Role Not Configured",
                description=f"The {label} role is not set. {not_configured_hint}",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        role = interaction.guild.get_role(int(role_id))
        if not role:
            embed = discord.Embed(
                title="❌ Role Not Found",
                description=f"Could not find the configured {label} role in this server.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Remove all other phase roles (including pass) from the member
        roles_to_remove = []
        for key, cfg_key in PHASE_KEYS.items():
            if key == phase.value:
                continue
            other_role_id = await get_config(cfg_key)
            if other_role_id:
                other_role = interaction.guild.get_role(int(other_role_id))
                if other_role and other_role in member.roles:
                    roles_to_remove.append(other_role)

        await member.add_roles(role, reason=f"Academy {label} — by {interaction.user}")
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason=f"Superseded by {label} — by {interaction.user}")

        embed = discord.Embed(
            title=f"{'🎓 Academy Pass Granted' if is_pass else f'Phase {phase.value} Assigned'}",
            color=discord.Color.gold() if is_pass else discord.Color.green(),
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Role Added", value=role.mention, inline=True)
        if roles_to_remove:
            embed.add_field(name="Roles Removed", value=" ".join(r.mention for r in roles_to_remove), inline=True)
        embed.add_field(name="Assigned by", value=interaction.user.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ─── /academylogs ─────────────────────────────────────────────────────────

    @app_commands.command(name="academylogs", description="View recent entries from the phase logs channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def academylogs(self, interaction: discord.Interaction):
        channel_id = await get_config("phase_logs_channel")
        if not channel_id:
            embed = discord.Embed(
                title="⚙️ Not Configured",
                description="The phase logs channel is not set. Use `/setup` to configure it.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        channel = interaction.client.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description="Could not find the configured phase logs channel.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        messages = [m async for m in channel.history(limit=10)]

        if not messages:
            embed = discord.Embed(
                title="Phase Logs",
                description="No recent messages found in the logs channel.",
                color=discord.Color.blurple(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Phase Logs — #{channel.name}",
            description=f"Last **{len(messages)}** messages:",
            color=discord.Color.blurple(),
        )
        for msg in reversed(messages):
            content = msg.content[:500] if msg.content else "*[embed or attachment]*"
            embed.add_field(
                name=f"{msg.author} — {discord.utils.format_dt(msg.created_at, style='R')}",
                value=content,
                inline=False,
            )
        embed.set_footer(text=f"Channel: #{channel.name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AcademyCog(bot))
