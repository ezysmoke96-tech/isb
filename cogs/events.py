import discord
from discord.ext import commands

from utils.db import get_autoroles


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        role_ids = await get_autoroles(str(member.guild.id))
        if role_ids:
            roles_to_add = [
                member.guild.get_role(int(rid))
                for rid in role_ids
                if member.guild.get_role(int(rid))
            ]
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Autorole on join")
                except (discord.Forbidden, discord.HTTPException):
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
