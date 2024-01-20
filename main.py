import GoCog
import config

import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import sqlite3
import datetime
# import recordclass
import attrs

MY_GUILD = discord.Object(id=config.guild_id)

def adapt_date_iso(val):
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()

def convert_date(val):
    """Convert ISO 8601 date to datetime.date object."""
    return datetime.date.fromisoformat(val.decode())

sqlite3.register_adapter(datetime.date, adapt_date_iso)
sqlite3.register_converter("date", convert_date)

# def recordclass_factory(cursor, row):
#     fields = [column[0] for column in cursor.description]
#     Row = recordclass.make_dataclass("Row", fields)
#     r = Row(*row)
#     #print(f"r {r}")
#     return r

def attrs_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    Row = attrs.make_class("Row", fields)
    r = Row(*row)
    print(f"attrs_factory row {r}")
    return r
    
con = sqlite3.connect("gobot.db")
# con.row_factory = sqlite3.Row
# con.row_factory = recordclass_factory
con.row_factory = attrs_factory
cur = con.cursor()





class MyBot(commands.Bot):
    def __init__(self, *, command_prefix, intents: discord.Intents, cur):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.cur = cur
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.

        # already added by Bot
        # self.tree = app_commands.CommandTree(self)

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to your guild.
        print("setup hook)")
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        

intents = discord.Intents.all()
# client = MyClient(intents=intents)
print("1111")
bot = MyBot(command_prefix="!", intents=intents, cur=cur)


# @client.event
# async def on_ready():
#     print('------------------')
#     print(f'on_ready() -- Logged in as {client.user} (ID: {client.user.id})')



print("2222")
# GoCog.setup(bot)
# await bot.add_cog(GoCog.GoCog(bot))
# bot.load_extension("GoCog")
print("33333")


async def main():
    async with bot:
        await bot.load_extension("GoCog")
        await bot.start(config.bot_token)

asyncio.run(main())



# bot.run(DISCORD_TOKEN)

print("44444)")