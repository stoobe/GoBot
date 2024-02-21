import asyncio
import sqlite3
import datetime
import logging

from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine
import discord
from discord import app_commands
from discord.ext import commands

import go.logger
from go.logger import create_logger
from go.go_cog import GoCog
import config
from go.go_db import GoDB
from go.playfab_db import PlayfabDB


logger = create_logger(__name__)

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
        logger.info(f"setup_hook start {[c.qualified_name for c in self.tree.walk_commands()]}")

        # # emergency resync, otherwise use /zadmin sync from Discord
        # await self.tree.sync(guild=MY_GUILD)        
        # self.tree.copy_global_to(guild=MY_GUILD)
        # await self.tree.sync(guild=MY_GUILD)

        # # how to remove commands
        # print(f"mybot1 {[c.qualified_name for c in self.tree.walk_commands()]}")
        # await self.tree.sync()                
        # self.tree.remove_command("admin sync")
        # self.tree.remove_command("z sync")
        # self.tree.remove_command("sync")
        # self.tree.clear_commands(guild=None)
        # await self.tree.sync()
        # await self.tree.sync(guild=MY_GUILD)                
        # print(f"mybot2 {[c.qualified_name for c in self.tree.walk_commands()]}")

        logger.info(f"setup_hook end   {[c.qualified_name for c in self.tree.walk_commands()]}")
            
        


async def main():

    sqlite_file_name = "gobot.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    engine = create_engine(sqlite_url, echo=False)

    SQLModel.metadata.create_all(engine)
    
    discord.utils.setup_logging(level=logging.INFO, root=False, formatter=go.logger.formatter)
    
    # You must have access to the message_content intent for the commands extension to function. 
    # This must be set both in the developer portal and within your code.
    # Failure to do this will result in your bot not responding to any of your commands.
    intents = discord.Intents.all()
    bot = MyBot(command_prefix="!", intents=intents, engine=engine)

    async with bot:
        logger.info("before bot.load_extension")        
        await bot.load_extension("go.go_cog")
        logger.info("bot.start")        
        await bot.start(config.bot_token)
        logger.info("end")        

if __name__ == "__main__":
    asyncio.run(main())
