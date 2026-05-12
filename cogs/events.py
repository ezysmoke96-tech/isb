import discord
from discord.ext import commands

from utils.db import get_config


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print(f"{member} joined {member.guild.name}")

        unverified_role_id = await get_config("unverified_role")
        if not unverified_role_id:
            return

        role = member.guild.get_role(int(unverified_role_id))
        if role:
            try:
                await member.add_roles(role, reason="Auto-assigned on join")
            except discord.Forbidden:
                print(f"Missing permissions to assign Unverified role to {member}")


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
