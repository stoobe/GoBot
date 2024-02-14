from typing import Generator
import pytest
from sqlalchemy import Engine
from sqlmodel import SQLModel, Session, create_engine

from datetime import datetime
from go.playfab_db import PlayfabDB

from go.models import GoPlayer, GoTeam, PfPlayer, PfCareerStats, PfIgnHistory
from go.go_db import GoDB


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
    engine = create_engine(sqlite_url, echo=True)
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
def pfdb_empty(pfdb_instance, session, scope="function") -> Generator[PlayfabDB, None, None]:
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
def godb_empty(godb_instance, session, scope="function") -> Generator[GoDB, None, None]:
    # Clear DB before test function
    godb_instance.delete_all_players(session=session)
    yield godb_instance
    # Clear DB after test function
    godb_instance.delete_all_players(session=session)