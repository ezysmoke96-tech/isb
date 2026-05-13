import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

_8BALL = [
    "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes, definitely.",
    "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
    "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
    "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]


class FunCog(commands.Cog, name="Fun"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dice", description="Roll a dice")
    @app_commands.describe(sides="Number of sides (default 6)", rolls="Number of dice to roll (default 1)")
    async def dice(self, interaction: discord.Interaction, sides: app_commands.Range[int, 2, 1000] = 6, rolls: app_commands.Range[int, 1, 20] = 1):
        results = [random.randint(1, sides) for _ in range(rolls)]
        total = sum(results)
        embed = discord.Embed(title=f"🎲 {rolls}d{sides} Roll", color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Results", value=" + ".join(f"**{r}**" for r in results), inline=False)
        if rolls > 1:
            embed.add_field(name="Total", value=str(total), inline=True)
            embed.add_field(name="Average", value=f"{total/rolls:.1f}", inline=True)
        embed.set_footer(text=f"Rolled by {interaction.user}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads 🪙", "Tails 🪙"])
        embed = discord.Embed(title="🪙 Coin Flip", description=f"**{result}**", color=discord.Color.gold(), timestamp=datetime.now(timezone.utc))
        embed.set_footer(text=f"Flipped by {interaction.user}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your question")
    async def eightball(self, interaction: discord.Interaction, question: str):
        response = random.choice(_8BALL)
        positive = any(w in response.lower() for w in ["yes", "certain", "definitely", "good", "most likely"])
        color = discord.Color.green() if positive else discord.Color.red() if any(w in response.lower() for w in ["no", "don't", "doubtful"]) else discord.Color.yellow()
        embed = discord.Embed(title="🎱 Magic 8-Ball", color=color, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"**{response}**", inline=False)
        embed.set_footer(text=f"Asked by {interaction.user}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCog(bot))
