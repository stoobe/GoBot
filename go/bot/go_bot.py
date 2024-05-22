import discord
from discord.ext import commands
from sqlalchemy import Engine

from go.bot.go_db import GoDB
from go.bot.logger import create_logger
from go.bot.playfab_db import PlayfabDB

logger = create_logger(__name__)


class GoBot(commands.Bot):

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
