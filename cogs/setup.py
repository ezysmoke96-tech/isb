import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_all_config, set_config


def make_setup_embed(config: dict) -> discord.Embed:
    def val(key: str) -> str:
        v = config.get(key)
        return f"`{v}`" if v else "*not set*"

    embed = discord.Embed(title="Bot Configuration", description="Click the buttons below to edit each section.", color=discord.Color.blurple())
    embed.add_field(name="Roles", value=(f"Verified: {val('verified_role')}\nUnverified: {val('unverified_role')}\nCandidate: {val('candidate_role')}\nLeaderboard: {val('leaderboard_role')}\nAcademy Pass: {val('academy_pass_role')}"), inline=False)
    embed.add_field(name="Phase Roles", value=(f"Phase 1: {val('phase1_role')}\nPhase 2: {val('phase2_role')}\nPhase 3: {val('phase3_role')}\nPhase 4: {val('phase4_role')}\nPhase 5: {val('phase5_role')}"), inline=False)
    embed.add_field(name="Channels", value=f"Phase Logs: {val('phase_logs_channel')}", inline=False)
    embed.add_field(name="Servers & Links", value=(f"Main Server ID: {val('main_guild_id')}\nAcademy Server ID: {val('academy_guild_id')}\nISB Discord Link: {val('isb_discord_link')}"), inline=False)
    embed.add_field(name="Roblox", value=(f"Game Universe ID: {val('game_universe_id')}\nISB Group ID: {val('isb_group_id')}"), inline=False)
    return embed


class RolesModal(discord.ui.Modal, title="Configure Roles"):
    verified_role = discord.ui.TextInput(label="Verified Role ID", required=False, placeholder="e.g. 123456789012345678")
    unverified_role = discord.ui.TextInput(label="Unverified Role ID", required=False, placeholder="e.g. 123456789012345678")
    candidate_role = discord.ui.TextInput(label="Candidate Role ID", required=False, placeholder="e.g. 123456789012345678")
    leaderboard_role = discord.ui.TextInput(label="Leaderboard Role ID", required=False, placeholder="e.g. 123456789012345678")
    academy_pass_role = discord.ui.TextInput(label="Academy Pass Role ID", required=False, placeholder="e.g. 123456789012345678")

    async def on_submit(self, interaction: discord.Interaction):
        for key, field in [("verified_role", self.verified_role), ("unverified_role", self.unverified_role), ("candidate_role", self.candidate_role), ("leaderboard_role", self.leaderboard_role), ("academy_pass_role", self.academy_pass_role)]:
            if field.value.strip():
                await set_config(key, field.value.strip())
        config = await get_all_config()
        await interaction.response.edit_message(embed=make_setup_embed(config))


class PhaseRolesModal(discord.ui.Modal, title="Configure Phase Roles"):
    phase1 = discord.ui.TextInput(label="Phase 1 Role ID", required=False)
    phase2 = discord.ui.TextInput(label="Phase 2 Role ID", required=False)
    phase3 = discord.ui.TextInput(label="Phase 3 Role ID", required=False)
    phase4 = discord.ui.TextInput(label="Phase 4 Role ID", required=False)
    phase5 = discord.ui.TextInput(label="Phase 5 Role ID", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        for key, field in [("phase1_role", self.phase1), ("phase2_role", self.phase2), ("phase3_role", self.phase3), ("phase4_role", self.phase4), ("phase5_role", self.phase5)]:
            if field.value.strip():
                await set_config(key, field.value.strip())
        config = await get_all_config()
        await interaction.response.edit_message(embed=make_setup_embed(config))


class ChannelsModal(discord.ui.Modal, title="Configure Channels"):
    phase_logs = discord.ui.TextInput(label="Phase Logs Channel ID", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if self.phase_logs.value.strip():
            await set_config("phase_logs_channel", self.phase_logs.value.strip())
        config = await get_all_config()
        await interaction.response.edit_message(embed=make_setup_embed(config))


class ServersModal(discord.ui.Modal, title="Configure Servers & Links"):
    main_guild = discord.ui.TextInput(label="Main Discord Server ID", required=False)
    academy_guild = discord.ui.TextInput(label="Academy Discord Server ID", required=False)
    isb_link = discord.ui.TextInput(label="ISB Discord Invite Link", required=False, placeholder="https://discord.gg/...")

    async def on_submit(self, interaction: discord.Interaction):
        for key, field in [("main_guild_id", self.main_guild), ("academy_guild_id", self.academy_guild), ("isb_discord_link", self.isb_link)]:
            if field.value.strip():
                await set_config(key, field.value.strip())
        config = await get_all_config()
        await interaction.response.edit_message(embed=make_setup_embed(config))


class RobloxConfigModal(discord.ui.Modal, title="Configure Roblox Settings"):
    game_id = discord.ui.TextInput(label="Roblox Game Universe ID", required=False)
    isb_group = discord.ui.TextInput(label="ISB Roblox Group ID", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if self.game_id.value.strip():
            await set_config("game_universe_id", self.game_id.value.strip())
        if self.isb_group.value.strip():
            await set_config("isb_group_id", self.isb_group.value.strip())
        config = await get_all_config()
        await interaction.response.edit_message(embed=make_setup_embed(config))


class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Roles", style=discord.ButtonStyle.primary, emoji="👥", row=0)
    async def roles_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(RolesModal())

    @discord.ui.button(label="Phase Roles", style=discord.ButtonStyle.primary, emoji="📋", row=0)
    async def phase_roles_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(PhaseRolesModal())

    @discord.ui.button(label="Channels", style=discord.ButtonStyle.secondary, emoji="📢", row=1)
    async def channels_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(ChannelsModal())

    @discord.ui.button(label="Servers & Links", style=discord.ButtonStyle.secondary, emoji="🔗", row=1)
    async def servers_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(ServersModal())

    @discord.ui.button(label="Roblox", style=discord.ButtonStyle.success, emoji="🎮", row=1)
    async def roblox_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(RobloxConfigModal())


class SetupCog(commands.Cog, name="Setup"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Configure the bot settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_cmd(self, interaction: discord.Interaction):
        config = await get_all_config()
        await interaction.response.send_message(embed=make_setup_embed(config), view=SetupView(), ephemeral=True)

    @app_commands.command(name="editsetup", description="Edit the current bot configuration")
    @app_commands.checks.has_permissions(administrator=True)
    async def editsetup(self, interaction: discord.Interaction):
        config = await get_all_config()
        await interaction.response.send_message(embed=make_setup_embed(config), view=SetupView(), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
