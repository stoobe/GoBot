import pytest
from sqlmodel import SQLModel, Session, create_engine

from datetime import datetime
from go.playfab_db import PlayfabDB

from go.models import PfPlayer, PfCareerStats, PfIgnHistory


@pytest.fixture
def player1():
    player = PfPlayer(
        id=1,
        ign="IGN1",
        account_created=datetime(2022, 1, 1, 1, 0, 0),
        last_login=datetime(2022, 2, 1, 1, 0, 0),
    )
    yield player


@pytest.fixture
def player2():
    player = PfPlayer(
        id=2,
        ign="IGN2",
        account_created=datetime(2022, 2, 2, 1, 0, 0),
        last_login=datetime(2022, 3, 1, 1, 0, 0),
    )
    yield player


@pytest.fixture
def stats_p1_1():
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
def stats_p1_1():
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
def stats_p1_2():
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
def stats_p2_1():
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
def stats_p2_2():
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
def pfdb_instance(scope="session"):
    sqlite_url = f"sqlite://" # in mem
    engine = create_engine(sqlite_url, echo=True)
    SQLModel.metadata.create_all(engine)
    pfdb = PlayfabDB(engine=engine)
    yield pfdb


@pytest.fixture
def session(pfdb_instance, scope="session"):

    session = Session(pfdb_instance.engine)
    yield session
    session.close()


@pytest.fixture
def pfdb_empty(pfdb_instance, session, scope="function"):
    # Clear DB before test function
    pfdb_instance.delete_all_players(session=session)
    yield pfdb_instance

    # Clear DB after test function
    pfdb_instance.delete_all_players(session=session)