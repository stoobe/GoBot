from typing import Generator
from datetime import datetime

import pytest
from sqlalchemy import Engine
from sqlmodel import SQLModel, Session, create_engine
from discord.ext import commands
from go.go_cog import DiscordUser, GoCog

from go.playfab_db import PlayfabDB
from go.go_db import GoDB
from go.models import GoPlayer, GoTeam, PfPlayer, PfCareerStats, PfIgnHistory


@pytest.fixture
def go_p1() -> Generator[GoPlayer, None, None]:
    player = GoPlayer(
        discord_id=101,
        discord_name="dn1",
    )
    yield player

@pytest.fixture
def go_p2() -> Generator[GoPlayer, None, None]:
    player = GoPlayer(
        discord_id=102,
        discord_name="dn2",
    )
    yield player

@pytest.fixture
def go_p3() -> Generator[GoPlayer, None, None]:
    player = GoPlayer(
        discord_id=103,
        discord_name="dn3",
    )
    yield player
    
@pytest.fixture
def go_team1() -> Generator[GoTeam, None, None]:
    player = GoTeam(
        team_name="tn1",
        player_count=1,
    )
    yield player

@pytest.fixture
def go_team2() -> Generator[GoTeam, None, None]:
    player = GoTeam(
        team_name="tn2",
        player_count=2,
    )
    yield player

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
        date = datetime(2023, 1, 1),
        pf_player_id=1,
        games=10,
        wins=5,
        kills=7,
        damage=500
    )
    yield stats


@pytest.fixture
def stats_p1_1() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date = datetime(2023, 1, 1),
        pf_player_id=1,
        games=10,
        wins=5,
        kills=7,
        damage=500,
    )
    yield stats


@pytest.fixture
def stats_p1_2() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date = datetime(2023, 2, 1),
        pf_player_id=1,
        games=30,
        wins=10,
        kills=14,
        damage=1000,
    )
    yield stats


@pytest.fixture
def stats_p2_1() -> Generator[PfCareerStats, None, None]:
    stats = PfCareerStats(
        date = datetime(2023, 1, 1),
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
        date = datetime(2023, 2, 1),
        pf_player_id=2,
        games=300,
        wins=100,
        kills=140,
        damage=10000,
    )
    yield stats


@pytest.fixture
def engine(scope="session") -> Generator[Engine, None, None]:
    sqlite_url = f"sqlite://" # in mem
    engine = create_engine(sqlite_url, echo=False)
    SQLModel.metadata.create_all(engine)    
    yield engine



@pytest.fixture
def session(engine, scope="session") -> Generator[Session, None, None]:
    session = Session(engine)
    yield session
    session.close()

@pytest.fixture
def pfdb_instance(engine, scope="session") -> Generator[PlayfabDB, None, None]:
    pfdb = PlayfabDB(engine=engine)
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
    godb = GoDB(engine=engine)
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
    bot = TestBotStub(engine=engine)
    bot.godb = godb
    bot.pfdb = pfdb
    
    cog = GoCog(bot)
    yield cog
    
@pytest.fixture
def gocog_preload(gocog, session, du1, du2, du3, pf_p1, pf_p2, pf_p3, scope="function"):
    gocog.pfdb.create_player(player=pf_p1, session=session)
    gocog.pfdb.create_player(player=pf_p2, session=session)
    gocog.pfdb.create_player(player=pf_p3, session=session)
    gocog.do_set_ign(player=du1, ign=pf_p1.ign)
    gocog.do_set_ign(player=du2, ign=pf_p2.ign)
    gocog.do_set_ign(player=du3, ign=pf_p3.ign)
    yield gocog



@pytest.fixture
def du1(go_p1, scope="function"):
    return DiscordUser(id=go_p1.discord_id, name="user_name_1")   

@pytest.fixture
def du2(go_p2, scope="function"):
    return DiscordUser(id=go_p2.discord_id, name="user_name_2")   

@pytest.fixture
def du3(go_p3, scope="function"):
    return DiscordUser(id=go_p3.discord_id, name="user_name_3")   