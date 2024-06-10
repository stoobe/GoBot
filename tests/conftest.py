from datetime import datetime
from typing import Generator

import pytest
from discord.ext import commands
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

import _config
from go.bot.go_cog import DiscordUser, GoCog
from go.bot.go_db import GoDB
from go.bot.models import GoPlayer, GoTeam, PfCareerStats, PfPlayer
from go.bot.playfab_db import PlayfabDB


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
    gocog.set_rating_if_needed(pf_p1.id, session)
    gocog.set_rating_if_needed(pf_p2.id, session)
    gocog.set_rating_if_needed(pf_p3.id, session)
    session.refresh(pf_p1)
    session.refresh(pf_p2)
    session.refresh(pf_p3)
    session.refresh(go_p1)
    session.refresh(go_p2)
    session.refresh(go_p3)
    yield gocog


@pytest.fixture
def du1(go_p1, scope="function"):
    return DiscordUser(id=go_p1.discord_id, name=go_p1.discord_name)


@pytest.fixture
def du2(go_p2, scope="function"):
    return DiscordUser(id=go_p2.discord_id, name=go_p2.discord_name)


@pytest.fixture
def du3(go_p3, scope="function"):
    return DiscordUser(id=go_p3.discord_id, name=go_p3.discord_name)
