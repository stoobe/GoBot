import asyncio

import discord
from sqlmodel import SQLModel, create_engine

import _config
import go.bot.logger
from go.bot.go_bot import GoBot
from go.bot.logger import create_logger

logger = create_logger(__name__)


async def main():

    engine = create_engine(_config.godb_url, echo=_config.godb_echo, pool_pre_ping=True)

    SQLModel.metadata.create_all(engine)

    discord.utils.setup_logging(level=_config.logging_level, root=False, formatter=go.bot.logger.formatter)  # type: ignore

    # inents specify what kinds of things the bot can do
    intents = discord.Intents.all()
    bot = GoBot(command_prefix="!", intents=intents, engine=engine)

    async with bot:
        logger.info("before bot.load_extension")
        await bot.load_extension("go.bot.go_cog")
        logger.info("before bot.start")
        await bot.start(_config.bot_token)
        logger.info("end")


if __name__ == "__main__":
    asyncio.run(main())
