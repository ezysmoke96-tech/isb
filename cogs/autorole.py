import discord
from discord import app_commands
from discord.ext import commands

from utils.db import get_autoroles, add_autorole, remove_autorole, clear_autoroles


class AutoroleCog(commands.Cog, name="Autorole"):
    """Manage roles automatically assigned to every member (and bot) that joins."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    autorole_group = app_commands.Group(
        name="autorole",
        description="Manage roles automatically given to everyone who joins",
        default_permissions=discord.Permissions(manage_roles=True),
    )

    @autorole_group.command(name="add", description="Add a role to the autorole list")
    @app_commands.describe(
        role="The role to give automatically on join",
        role2="Additional role (optional)",
        role3="Additional role (optional)",
        role4="Additional role (optional)",
        role5="Additional role (optional)",
    )
    async def autorole_add(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        role2: discord.Role | None = None,
        role3: discord.Role | None = None,
        role4: discord.Role | None = None,
        role5: discord.Role | None = None,
    ):
        roles = [r for r in [role, role2, role3, role4, role5] if r is not None]

        bot_top_role = interaction.guild.me.top_role
        skipped = []
        added = []

        for r in roles:
            if r >= bot_top_role:
                skipped.append(r)
                continue
            await add_autorole(str(interaction.guild.id), str(r.id))
            added.append(r)

        embed = discord.Embed(title="Autorole Updated", color=discord.Color.green())
        if added:
            embed.add_field(
                name="Added",
                value="\n".join(r.mention for r in added),
                inline=False,
            )
        if skipped:
            embed.add_field(
                name="Skipped (role is above me)",
                value="\n".join(r.mention for r in skipped),
                inline=False,
            )
        if not added and not skipped:
            embed.description = "No roles were provided."
            embed.color = discord.Color.orange()

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @autorole_group.command(name="remove", description="Remove a role from the autorole list")
    @app_commands.describe(role="The role to remove from autorole")
    async def autorole_remove(self, interaction: discord.Interaction, role: discord.Role):
        await remove_autorole(str(interaction.guild.id), str(role.id))
        embed = discord.Embed(
            title="Autorole Updated",
            description=f"Removed {role.mention} from the autorole list.",
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @autorole_group.command(name="list", description="Show all current autoroles")
    async def autorole_list(self, interaction: discord.Interaction):
        role_ids = await get_autoroles(str(interaction.guild.id))

        if not role_ids:
            embed = discord.Embed(
                title="Autoroles",
                description="No autoroles configured. Use `/autorole add` to add one.",
                color=discord.Color.blurple(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        lines = []
        for rid in role_ids:
            role = interaction.guild.get_role(int(rid))
            lines.append(role.mention if role else f"*Unknown role `{rid}`*")

        embed = discord.Embed(
            title="Autoroles",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="These roles are given to every member and bot that joins.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @autorole_group.command(name="clear", description="Remove all autoroles")
    async def autorole_clear(self, interaction: discord.Interaction):
        await clear_autoroles(str(interaction.guild.id))
        embed = discord.Embed(
            title="Autoroles Cleared",
            description="All autoroles have been removed.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoroleCog(bot))
