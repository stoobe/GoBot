import asyncio

import discord
from discord.ext import commands
from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine

import _config
import go.logger
from go.go_bot import GoBot
from go.go_db import GoDB
from go.logger import create_logger
from go.playfab_db import PlayfabDB

logger = create_logger(__name__)

MY_GUILD = discord.Object(id=_config.guild_id)


async def main():

    engine = create_engine(_config.godb_url, echo=_config.godb_echo, pool_pre_ping=True)

    SQLModel.metadata.create_all(engine)

    discord.utils.setup_logging(level=_config.logging_level, root=False, formatter=go.logger.formatter)  # type: ignore

    # You must have access to the message_content intent for the commands extension to function.
    # This must be set both in the developer portal and within your code.
    # Failure to do this will result in your bot not responding to any of your commands.
    intents = discord.Intents.all()
    bot = GoBot(command_prefix="!", intents=intents, engine=engine)

    async with bot:
        logger.info("before bot.load_extension")
        await bot.load_extension("go.go_cog")
        logger.info("bot.start")
        await bot.start(_config.bot_token)
        logger.info("end")


if __name__ == "__main__":
    asyncio.run(main())
