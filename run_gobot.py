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
import _config
from go.go_db import GoDB
from go.playfab_db import PlayfabDB


logger = create_logger(__name__)

MY_GUILD = discord.Object(id=_config.guild_id)


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
        logger.info(f"setup_hook start commands {[c.qualified_name for c in self.tree.walk_commands()]}")

        # # emergency resync, otherwise use /zadmin sync from Discord
        # self.tree.copy_global_to(guild=MY_GUILD)
        # await self.tree.sync(guild=MY_GUILD)

        logger.info(f"setup_hook end commands:   {[c.qualified_name for c in self.tree.walk_commands()]}")
            
        


async def main():

    engine = create_engine(_config.godb_url, echo=_config.godb_echo, pool_pre_ping=True)

    SQLModel.metadata.create_all(engine)
    
    discord.utils.setup_logging(level=_config.logging_level, root=False, formatter=go.logger.formatter)
    
    # You must have access to the message_content intent for the commands extension to function. 
    # This must be set both in the developer portal and within your code.
    # Failure to do this will result in your bot not responding to any of your commands.
    intents = discord.Intents.all()
    bot = MyBot(command_prefix="!", intents=intents, engine=engine)

    async with bot:
        logger.info("before bot.load_extension")        
        await bot.load_extension("go.go_cog")
        logger.info("bot.start")        
        await bot.start(_config.bot_token)
        logger.info("end")        

if __name__ == "__main__":
    asyncio.run(main())
