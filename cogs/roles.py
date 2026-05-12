import discord
from discord import app_commands
from discord.ext import commands

from utils.db import get_config

DEFAULT_LEADERBOARD_ROLE_ID = 1499865429504430181


class RolesCog(commands.Cog, name="Roles"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── /promote ─────────────────────────────────────────────────────────────

    @app_commands.command(name="promote", description="Promote a member by assigning a new role and removing an old one")
    @app_commands.describe(
        member="The member to promote",
        new_role="Role to assign",
        removed_role="Role to remove",
        new_role_2="Additional role to assign (optional)",
        new_role_3="Additional role to assign (optional)",
        removed_role_2="Additional role to remove (optional)",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def promote(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        new_role: discord.Role,
        removed_role: discord.Role,
        new_role_2: discord.Role | None = None,
        new_role_3: discord.Role | None = None,
        removed_role_2: discord.Role | None = None,
    ):
        if member == interaction.user:
            embed = discord.Embed(
                title="Action Blocked",
                description="You cannot promote yourself.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        to_add = [r for r in [new_role, new_role_2, new_role_3] if r]
        to_remove = [r for r in [removed_role, removed_role_2] if r]

        await member.add_roles(*to_add, reason=f"Promoted by {interaction.user}")
        await member.remove_roles(*to_remove, reason=f"Promoted by {interaction.user}")

        embed = discord.Embed(title="Member Promoted", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Roles Added", value=" ".join(r.mention for r in to_add), inline=False)
        embed.add_field(name="Roles Removed", value=" ".join(r.mention for r in to_remove), inline=False)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ─── /demote ──────────────────────────────────────────────────────────────

    @app_commands.command(name="demote", description="Demote a member by removing a role and assigning a lower one")
    @app_commands.describe(
        member="The member to demote",
        new_role="Role to assign",
        removed_role="Role to remove",
        new_role_2="Additional role to assign (optional)",
        new_role_3="Additional role to assign (optional)",
        removed_role_2="Additional role to remove (optional)",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def demote(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        new_role: discord.Role,
        removed_role: discord.Role,
        new_role_2: discord.Role | None = None,
        new_role_3: discord.Role | None = None,
        removed_role_2: discord.Role | None = None,
    ):
        if member == interaction.user:
            embed = discord.Embed(
                title="Action Blocked",
                description="You cannot demote yourself.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        to_add = [r for r in [new_role, new_role_2, new_role_3] if r]
        to_remove = [r for r in [removed_role, removed_role_2] if r]

        await member.add_roles(*to_add, reason=f"Demoted by {interaction.user}")
        await member.remove_roles(*to_remove, reason=f"Demoted by {interaction.user}")

        embed = discord.Embed(title="Member Demoted", color=discord.Color.red())
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Roles Added", value=" ".join(r.mention for r in to_add), inline=False)
        embed.add_field(name="Roles Removed", value=" ".join(r.mention for r in to_remove), inline=False)
        embed.add_field(name="Actioned by", value=interaction.user.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ─── /leaderboard ─────────────────────────────────────────────────────────

    @app_commands.command(name="leaderboard", description="List all members with the leaderboard role")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()

        role_id_str = await get_config("leaderboard_role")
        role_id = int(role_id_str) if role_id_str else DEFAULT_LEADERBOARD_ROLE_ID

        role = interaction.guild.get_role(role_id)
        if not role:
            embed = discord.Embed(
                title="❌ Role Not Found",
                description=f"Could not find the leaderboard role (`{role_id}`). Configure it via `/setup`.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return

        members = [m for m in interaction.guild.members if role in m.roles]
        members.sort(key=lambda m: m.display_name.lower())

        embed = discord.Embed(
            title=f"Leaderboard — {role.name}",
            description=f"**{len(members)}** member(s) with this role.",
            color=role.color if role.color.value else discord.Color.gold(),
        )

        if members:
            chunks = [members[i:i + 20] for i in range(0, len(members), 20)]
            for i, chunk in enumerate(chunks[:5]):
                lines = [f"{idx + 1 + i * 20}. {m.mention}" for idx, m in enumerate(chunk)]
                embed.add_field(
                    name=f"Members {i * 20 + 1}–{i * 20 + len(chunk)}",
                    value="\n".join(lines),
                    inline=False,
                )
        else:
            embed.description = "No members have this role."

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))
