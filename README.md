# Discord Bot

A Python Discord bot built with discord.py.

## Structure

```
discord-bot/
├── bot.py          # Entry point — sets up intents, loads cogs, starts bot
└── cogs/
    ├── general.py      # Ping, hello, server info
    └── moderation.py   # Kick, ban, purge (requires permissions)
```

## Commands

### Prefix commands (default prefix: `!`)
| Command | Description |
|---------|-------------|
| `!ping` | Show bot latency |
| `!hello` | Bot greets you |
| `!info` | Show server info embed |
| `!kick @user [reason]` | Kick a member (requires Kick Members) |
| `!ban @user [reason]` | Ban a member (requires Ban Members) |
| `!purge [amount]` | Delete messages (requires Manage Messages) |

### Slash commands
All of the above are also available as `/ping`, `/hello`, `/info`, `/kick`, `/ban`.

## Adding New Cogs

Create a new file in `cogs/` and add a `setup` function:

```python
from discord.ext import commands

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def mycommand(self, ctx):
        await ctx.send("Hello!")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

The bot auto-discovers and loads all `.py` files in the `cogs/` folder on startup.

## Running

The bot is started via the **Discord Bot** workflow in this workspace.
