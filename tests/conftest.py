import re
from datetime import datetime
from types import SimpleNamespace
from typing import Generator, List

import discord
import discord.ext.commands as commands
import discord.ext.test as dpytest
import pytest
import pytest_asyncio
from discord.ext import commands
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from config import _config
from go.bot.go_bot import GoBot
from go.bot.go_cog import DiscordUser, GoCog
from go.bot.go_db import GoDB
from go.bot.models import GoPlayer, GoTeam, PfCareerStats, PfPlayer
from go.bot.playfab_db import PlayfabDB


@pytest.fixture
def dates() -> Generator[List[datetime], None, None]:
    yield [
        datetime(2023, 1, 1),
        datetime(2023, 1, 2),
        datetime(2023, 1, 3),
        datetime(2023, 1, 4),
        datetime(2023, 1, 5),
        datetime(2023, 1, 6),
    ]


@pytest.fixture
def channels() -> Generator[List[int], None, None]:
    yield [1111, 2222, 3333, 4444, 5555, 6666]


@pytest.fixture
def go_p1() -> Generator[GoPlayer, None, None]:
    player = GoPlayer(
        discord_id=101,
        discord_name="dn1",
        pf_player_id=None,
    )
    yield player


@pytest.fixture
def go_p2() -> Generator[GoPlayer, None, None]:
    player = GoPlayer(
        discord_id=102,
        discord_name="dn2",
        pf_player_id=None,
    )
    yield player


@pytest.fixture
def go_p3() -> Generator[GoPlayer, None, None]:
    player = GoPlayer(
        discord_id=103,
        discord_name="dn3",
        pf_player_id=None,
    )
    yield player


@pytest.fixture
def go_p_owner() -> Generator[GoPlayer, None, None]:
    player = GoPlayer(
        discord_id=_config.owner_id,
        discord_name="OWNER",
        pf_player_id=None,
    )
    yield player


@pytest.fixture
def go_team1() -> Generator[GoTeam, None, None]:
    t = GoTeam(
        team_name="tn1",
        team_size=1,
    )
    yield t


@pytest.fixture
def go_team2() -> Generator[GoTeam, None, None]:
    t = GoTeam(
        team_name="tn2",
        team_size=2,
    )
    yield t


@pytest.fixture
def pf_p1() -> Generator[PfPlayer, None, None]:
    player = PfPlayer(
        id=1,
        ign="IGN1",
        account_created=datetime(2022, 1, 1, 1, 0, 0),
        last_login=datetime(2022, 2, 1, 1, 0, 0),
    )
    yield player


@pytest.fixture
def pf_p2() -> Generator[PfPlayer, None, None]:
    player = PfPlayer(
        id=2,
        ign="IGN2",
        account_created=datetime(2022, 2, 2, 1, 0, 0),
        last_login=datetime(2022, 3, 1, 1, 0, 0),
    )
    yield player


@pytest.fixture
def pf_p3() -> Generator[PfPlayer, None, None]:
    player = PfPlayer(
        id=3,
        ign="IGN3",
        account_created=datetime(2022, 2, 2, 1, 0, 0),
        last_login=datetime(2022, 3, 1, 1, 0, 0),
    )
    yield player


@pytest.fixture
def pf_p1v2() -> Generator[PfPlayer, None, None]:
    player = PfPlayer(
        id=4,
        ign="IGN1",
        account_created=datetime(2022, 2, 2, 1, 0, 0),
        last_login=datetime(2022, 3, 1, 1, 0, 0),
    )
    yield player


@pytest.fixture
def stats_p1_1() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 1, 1),
        pf_player_id=1,
        games=10,
        wins=5,
        kills=7,
        damage=2000,
    )
    yield stats


@pytest.fixture
def stats_p1_2() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 2, 1),
        pf_player_id=1,
        games=30,
        wins=20,
        kills=25,
        damage=10000,
    )
    yield stats


@pytest.fixture
def stats_p1_3() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 4, 1),
        pf_player_id=1,
        games=530,
        wins=520,
        kills=525,
        damage=60000,
    )
    yield stats


@pytest.fixture
def stats_p1_4() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 4, 7),
        pf_player_id=1,
        games=540,
        wins=530,
        kills=545,
        damage=61000,
    )
    yield stats


@pytest.fixture
def stats_p1_zeros() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2022, 1, 1),
        pf_player_id=1,
        games=0,
        wins=0,
        kills=0,
        damage=0,
    )
    yield stats


@pytest.fixture
def stats_p2_1() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 1, 1),
        pf_player_id=2,
        games=100,
        wins=50,
        kills=70,
        damage=5000,
    )
    yield stats


@pytest.fixture
def stats_p2_2() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 2, 1),
        pf_player_id=2,
        games=300,
        wins=100,
        kills=140,
        damage=10000,
    )
    yield stats


@pytest.fixture
def stats_p2_3() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 6, 1),
        pf_player_id=2,
        games=450,
        wins=200,
        kills=300,
        damage=30000,
    )
    yield stats


@pytest.fixture
def stats_p3_1() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date=datetime(2023, 1, 3),
        pf_player_id=3,
        games=103,
        wins=53,
        kills=73,
        damage=5003,
    )
    yield stats


@pytest.fixture
def du1(go_p1, scope="function"):
    return DiscordUser(id=go_p1.discord_id, name=go_p1.discord_name)


@pytest.fixture
def du2(go_p2, scope="function"):
    return DiscordUser(id=go_p2.discord_id, name=go_p2.discord_name)


@pytest.fixture
def du3(go_p3, scope="function"):
    return DiscordUser(id=go_p3.discord_id, name=go_p3.discord_name)


@pytest.fixture
def du_owner(go_p_owner, scope="function"):
    return DiscordUser(id=go_p_owner.discord_id, name=go_p_owner.discord_name)


@pytest.fixture
def engine(scope="session") -> Generator[Engine, None, None]:
    sqlite_url = f"sqlite://"  # in mem
    engine = create_engine(sqlite_url, echo=_config.godb_echo)
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture
def session(engine, scope="session") -> Generator[Session, None, None]:
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def pfdb_instance(engine, scope="session") -> Generator[PlayfabDB, None, None]:
    pfdb = PlayfabDB()
    yield pfdb


@pytest.fixture
def pfdb(pfdb_instance, session, scope="function") -> Generator[PlayfabDB, None, None]:
    # Clear DB before test function
    pfdb_instance.delete_all_players(session=session)
    yield pfdb_instance
    # Clear DB after test function
    pfdb_instance.delete_all_players(session=session)


@pytest.fixture
def godb_instance(engine, scope="session") -> Generator[GoDB, None, None]:
    godb = GoDB()
    yield godb


@pytest.fixture
def godb(godb_instance, session, scope="function") -> Generator[GoDB, None, None]:
    # Clear DB before test function
    godb_instance.delete_all_players(session=session)
    yield godb_instance
    # Clear DB after test function
    godb_instance.delete_all_players(session=session)


class TestBotStub(commands.Bot):
    def __init__(self, engine):
        self.engine = engine
        self.godb = None
        self.pfdb = None


@pytest.fixture
def gocog(godb, pfdb, engine, scope="function"):
    _config.go_rating_limits = {1: 1000, 2: 2000, 3: 3000, 4: 4000}
    _config.go_rating_default = None

    bot = TestBotStub(engine=engine)
    bot.godb = godb
    bot.pfdb = pfdb

    cog = GoCog(bot)
    yield cog


@pytest.fixture
def gocog_preload(
    gocog,
    session,
    du1,
    du2,
    du3,
    pf_p1,
    pf_p2,
    pf_p3,
    go_p1,
    go_p2,
    go_p3,
    stats_p1_1,
    stats_p2_1,
    stats_p3_1,
    scope="function",
):
    gocog.pfdb.create_player(player=pf_p1, session=session)
    gocog.pfdb.create_player(player=pf_p2, session=session)
    gocog.pfdb.create_player(player=pf_p3, session=session)
    session.add(go_p1)
    session.add(go_p2)
    session.add(go_p3)
    gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)
    gocog.do_set_ign(player=du2, ign=pf_p2.ign, session=session)
    gocog.do_set_ign(player=du3, ign=pf_p3.ign, session=session)
    gocog.pfdb.add_career_stats(stats=stats_p1_1, session=session)
    gocog.pfdb.add_career_stats(stats=stats_p2_1, session=session)
    gocog.pfdb.add_career_stats(stats=stats_p3_1, session=session)
    gocog.set_rating_if_needed(pf_p1.id, session, season=_config.go_season)
    gocog.set_rating_if_needed(pf_p2.id, session, season=_config.go_season)
    gocog.set_rating_if_needed(pf_p3.id, session, season=_config.go_season)
    session.refresh(pf_p1)
    session.refresh(pf_p2)
    session.refresh(pf_p3)
    session.refresh(go_p1)
    session.refresh(go_p2)
    session.refresh(go_p3)
    yield gocog


@pytest.fixture
def gocog_preload_teams(gocog_preload, du1, du2, du3, channels, dates, session, scope="function"):

    gocog_preload.godb.set_session_time(session_id=channels[0], session_time=dates[0], session=session)
    gocog_preload.do_signup(players=[du1], team_name="tname1", session_id=channels[0], session=session)
    session.commit()
    yield gocog_preload


class UserStub:
    def __init__(self, du):
        self.id = du.id
        self.name = du.name
        self.last_message = None

    def send(self, message):
        self.last_message = message


class ResponseStub:
    def __init__(self):
        self.last_message = None

    async def send_message(self, message, ephemeral=False):
        self.last_message = message

    async def send(self, message, ephemeral=False):
        self.last_message = message

    async def defer(self, ephemeral=False):
        pass


class InteractionStub:
    def __init__(self, du, channel_id):
        self.user = UserStub(du)

        self.command = SimpleNamespace()
        self.command.parent = SimpleNamespace()
        self.command.parent.name = "go"
        self.command.name = "command_name"

        self.response = ResponseStub()
        self.followup = self.response

        self.channel_id = channel_id
        self.channel = f"channel {self.channel_id}"

    def assert_msg_count(self, msg, n=1):
        print(self.response.last_message)
        assert self.response.last_message is not None
        assert self.response.last_message.count(msg) == n

    def assert_msg_regx(self, pattern):
        print(self.response.last_message)
        assert self.response.last_message is not None
        match = re.search(pattern, self.response.last_message)
        assert match


@pytest.fixture
def interaction1(du1, channels, scope="function"):
    return InteractionStub(du1, channels[0])


@pytest.fixture
def interaction_owner(du_owner, channels, scope="function"):
    return InteractionStub(du_owner, channels[0])


# @pytest_asyncio.fixture
# async def bot(engine, godb, pfdb):
#     # Setup
#     intents = discord.Intents.default()
#     intents.members = True
#     intents.message_content = True
#     b = GoBot(command_prefix="!", intents=intents, engine=engine)
#     b.godb = godb
#     b.pfdb = pfdb
#     # b = commands.Bot(command_prefix="!", intents=intents)
#     await b._async_setup_hook()
#     dpytest.configure(b)

#     yield b

#     # Teardown
#     await dpytest.empty_queue()  # empty the global message queue as test teardown


# @pytest_asyncio.fixture
# async def cog2(bot):
#     cog = GoCog(bot)
#     yield cog
