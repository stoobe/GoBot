import discord
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from config import _config 
import go.bot.logger
from go.bot.exceptions import DiscordUserError
from go.bot.go_cog import DiscordUser, GoCog
from go.bot.go_db import GoDB
from go.bot.logger import create_logger
from go.bot.playfab_db import PlayfabDB

logger = create_logger(__name__)


class MyBot:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.godb = GoDB()
        self.pfdb = PlayfabDB()


def main():

    engine = create_engine(_config.godb_url, echo=_config.godb_echo, pool_pre_ping=True)

    SQLModel.metadata.create_all(engine)

    discord.utils.setup_logging(level=_config.logging_level, root=False, formatter=go.bot.logger.formatter)  # type: ignore

    cog = GoCog(bot=MyBot(engine))  # type: ignore

    player = DiscordUser(id=408731638223208448, name="GO_STOOOBE")
    print(cog.do_player_info(player=player))

    print("\n\n")

    try:
        player2 = DiscordUser(id=721590633579544607, name="KOTIC")
        with Session(engine) as session:
            go_p = cog.do_set_ign(player2, ign="o_", session=session)
    except DiscordUserError as err:
        print(f"{err.message}")


if __name__ == "__main__":
    main()
