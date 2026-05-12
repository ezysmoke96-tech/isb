import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands

from utils.db import init_db

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    embed = discord.Embed(color=discord.Color.red())

    if isinstance(error, app_commands.MissingPermissions):
        embed.title = "Permission Denied"
        embed.description = "You don't have the required permissions to use this command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        embed.title = "Bot Missing Permissions"
        embed.description = "I don't have the necessary permissions to do that."
    elif isinstance(error, app_commands.CheckFailure):
        embed.title = "Permission Denied"
        embed.description = "You are not allowed to use this command."
    else:
        embed.title = "Something went wrong"
        embed.description = str(error)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    await bot.tree.sync()
    print("Slash commands synced globally.")


async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Loaded cog: {filename}")


async def main():
    async with bot:
        await init_db()
        print("Database initialised.")

        from cogs.roblox_cmds import VerifyView
        from cogs.giveaway import GiveawayView
        bot.add_view(VerifyView())
        bot.add_view(GiveawayView())

        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
