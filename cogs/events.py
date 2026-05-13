import discord
from discord.ext import commands

from utils.db import get_autoroles


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print(f"{member} joined {member.guild.name} (bot={member.bot})")

        role_ids = await get_autoroles(str(member.guild.id))
        if not role_ids:
            return

        roles_to_add = []
        for rid in role_ids:
            role = member.guild.get_role(int(rid))
            if role:
                roles_to_add.append(role)

        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Autorole on join")
            except discord.Forbidden:
                print(f"Missing permissions to assign autoroles to {member}")
            except discord.HTTPException as e:
                print(f"Failed to assign autoroles to {member}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
