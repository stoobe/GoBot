import asyncio
import sqlite3
import datetime
import logging

from sqlalchemy import Engine
from sqlmodel import SQLModel, Session, create_engine
import discord
from discord import app_commands
from discord.ext import commands

from go.exceptions import DiscordUserError
import go.logger
from go.logger import create_logger
from go.go_cog import GoCog, DiscordUser
import _config
from go.go_db import GoDB
from go.playfab_db import PlayfabDB


logger = create_logger(__name__)

MY_GUILD = discord.Object(id=_config.guild_id)


class MyBot:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.godb = GoDB(engine=self.engine)
        self.pfdb = PlayfabDB(engine=self.engine)

            
        


def main():

    engine = create_engine(_config.godb_url, echo=_config.godb_echo, pool_pre_ping=True)

    SQLModel.metadata.create_all(engine)
    
    discord.utils.setup_logging(level=_config.logging_level, root=False, formatter=go.logger.formatter)
    
    cog = GoCog(bot=MyBot(engine))

    player = DiscordUser(id=408731638223208448, name="GO_STOOOBE")
    print(cog.do_player_info(player=player))
    
    print('\n\n')
    
    try:
        player2 = DiscordUser(id=721590633579544607, name="KOTIC")
        with Session(engine) as session:
            go_p = cog.do_set_ign(player2, ign="o_", session=session)
    except DiscordUserError as err:
            print(f'{err.message}')             

if __name__ == "__main__":
    main()
