import asyncio
import sqlite3
import datetime
from sqlmodel import SQLModel, create_engine, Engine

import discord
from discord import app_commands
from discord.ext import commands

import go.GoCog as GoCog
import config
from go.go_db import GoDB
from go.playfab_db import PlayfabDB


MY_GUILD = discord.Object(id=config.guild_id)


class MyBot(commands.Bot):
    def __init__(self, *, command_prefix, intents: discord.Intents, engine: Engine):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.engine = engine
        self.godb = GoDB(engine=self.engine)
        self.pfdb = PlayfabDB(engine=self.engine)

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to your guild.
        print("setup_hook start")
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        
        # self.tree.clear_commands(guild=self.get_guild(config.guild_id))
        # self.tree.copy_global_to(guild=MY_GUILD)
        # await self.tree.sync(guild=MY_GUILD)

        # print(f"remove say {self.remove_command('say')}")
        # print(f"remove say {self.remove_command('what')}")
        # await self.tree.sync(guild=MY_GUILD)

        print("setup_hook end")


async def main():

    sqlite_file_name = "gobot.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    engine = create_engine(sqlite_url, echo=False)

    SQLModel.metadata.create_all(engine)
    
    intents = discord.Intents.all()
    bot = MyBot(command_prefix="!", intents=intents, engine=engine)

    async with bot:
        await bot.load_extension("GoCog")
        await bot.start(config.bot_token)


    
    
if __name__ == "__main__":
    asyncio.run(main())
