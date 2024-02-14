from datetime import datetime
import pytest
from icecream import ic

from go.exceptions import PlayerNotFoundError

def test_create_and_read_player(pfdb_empty, session, player1):
    function_start = datetime.now()

    # Write Player to DB
    pfdb_empty.create_player(player=player1, session=session)
    assert 1 == pfdb_empty.player_count(session=session)

    # # Read Player from DB
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)
    ic(player1)
    ic(player)
    print(player1)
    assert player.ign == player1.ign
    assert player.account_created == player1.account_created
    assert player.last_login == player1.last_login
    assert player.avatar_url == player1.avatar_url

    ign_hist = player.ign_history
    function_end = datetime.now()

    assert len(ign_hist) == 1
    assert ign_hist[0].ign == player.ign
    assert ign_hist[0].pf_player_id == player.id
    assert ign_hist[0].date >= function_start
    assert ign_hist[0].date <= function_end


def test_player_exists(pfdb_empty, session, player1, player2):
    assert pfdb_empty.player_exists(pf_player_id=player1.id, session=session) == False
    
    # Write Player to DB
    pfdb_empty.create_player(player=player1, session=session)
    assert 1 == pfdb_empty.player_count(session=session)
    assert pfdb_empty.player_exists(pf_player_id=player1.id, session=session) == True
    assert pfdb_empty.player_exists(pf_player_id=player2.id, session=session) == False

    pfdb_empty.delete_player(session=session, pf_player_id=player1.id)
    assert pfdb_empty.player_exists(pf_player_id=player1.id, session=session) == False
    assert pfdb_empty.player_exists(pf_player_id=player2.id, session=session) == False


def test_delete_player(pfdb_empty, session, player1, player2):
    # Write 2 Players to DB
    pfdb_empty.create_player(player=player1, session=session)
    pfdb_empty.create_player(player=player2, session=session)
    assert 2 == pfdb_empty.player_count(session=session)

    # Delete Player
    pfdb_empty.delete_player(session=session, pf_player_id=player2.id)

    # Ensure Player1 is still there
    assert 1 == pfdb_empty.player_count(session=session)
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)
    assert player.ign == player1.ign
    assert player.account_created == player1.account_created
    assert player.last_login == player1.last_login
    assert player.avatar_url == player1.avatar_url

    # Read Player from DB
    with pytest.raises(PlayerNotFoundError):
        pfdb_empty.read_player(pf_player_id=player2.id, session=session)


def test_delete_player_with_stats(pfdb_empty, session, player1, player2, stats_p1_1, stats_p1_2, stats_p2_1):
    # Write 2 Players to DB
    pfdb_empty.create_player(player=player1, session=session)
    pfdb_empty.create_player(player=player2, session=session)
    assert 2 == pfdb_empty.player_count(session=session)

    # add CareerStats to make sure those entries are deleted too
    pfdb_empty.add_career_stats(stats=stats_p2_1, session=session)
    pfdb_empty.add_career_stats(stats=stats_p1_1, session=session)
    pfdb_empty.add_career_stats(stats=stats_p1_2, session=session)

    # Delete Player
    pfdb_empty.delete_player(session=session, pf_player_id=player2.id)

    # Ensure Player1 is still there
    assert 1 == pfdb_empty.player_count(session=session)
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)
    assert player.ign == player1.ign
    assert player.account_created == player1.account_created
    assert player.last_login == player1.last_login
    assert player.avatar_url == player1.avatar_url

    # Read Player from DB
    with pytest.raises(PlayerNotFoundError):
        pfdb_empty.read_player(pf_player_id=player2.id, session=session)


def test_delete_all_players(pfdb_empty, session, player1, player2):
    # Write 2 Players to DB
    pfdb_empty.create_player(player=player1, session=session)
    pfdb_empty.create_player(player=player2, session=session)
    assert 2 == pfdb_empty.player_count(session=session)

    # Delete all Players from DB
    pfdb_empty.delete_all_players(session=session)

    # Read all Players from DB
    assert 0 == pfdb_empty.player_count(session=session)


@pytest.mark.parametrize("ign, last_login, avatar_url",
                         [
                             (None, None, None),
                             ("IGN111", None, None),
                             (None, datetime(2023,3,3,3,3,3), None),
                             (None, None, "av.url"),
                             ("IGN111", datetime(2023,3,3,3,3,3), None),
                             ("IGN111", None, "av.url"),
                             (None, datetime(2023,3,3,3,3,3), "av.url"),
                             ("IGN111", datetime(2023,3,3,3,3,3), "av.url"),
                         ])
def test_update_player(pfdb_empty, session, player1, ign, last_login, avatar_url):
    # Write Player to DB
    pfdb_empty.create_player(player=player1, session=session)

    # Update Player
    pfdb_empty.update_player(
        session=session,
        pf_player_id=player1.id,
        ign=ign, 
        last_login=last_login,
        avatar_url=avatar_url
    )

    # Read Player from DB
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)

    # Check fields
    assert player.id == player1.id
    assert player.account_created == player1.account_created

    if ign:
        assert player.ign == ign
    else:
        assert player.ign == player1.ign
    
    if last_login:
        assert player.last_login == last_login
    else:
        assert player.last_login == player1.last_login
    
    if avatar_url:
        assert player.avatar_url == avatar_url
    else:
        assert player.avatar_url == player1.avatar_url


def test_career_stats_create_and_read(pfdb_empty, session, 
                                      player1, stats_p1_1, stats_p1_2,
                                      player2, stats_p2_1, stats_p2_2):
    pfdb_empty.create_player(player=player1, session=session)
    assert 1 == pfdb_empty.player_count(session=session)

    pfdb_empty.add_career_stats(stats=stats_p1_1, session=session)
    p1stats = player1.career_stats
    assert len(p1stats) == 1

    pfdb_empty.add_career_stats(stats=stats_p1_2, session=session)
    p1stats = player1.career_stats
    assert len(p1stats) == 2

    pfdb_empty.create_player(player=player2, session=session)
    assert 2 == pfdb_empty.player_count(session=session)

    pfdb_empty.add_career_stats(stats=stats_p2_1, session=session)
    p2stats = player2.career_stats
    assert len(p1stats) == 2
    assert len(p2stats) == 1

    pfdb_empty.add_career_stats(stats=stats_p2_2, session=session)
    p2stats = player2.career_stats
    assert len(p1stats) == 2
    assert len(p2stats) == 2


def test_career_stats_deletes(pfdb_empty, session, 
                                      player1, stats_p1_1, stats_p1_2,
                                      player2, stats_p2_1, stats_p2_2):
    pfdb_empty.create_player(player=player1, session=session)
    pfdb_empty.add_career_stats(stats=stats_p1_1, session=session)
    pfdb_empty.add_career_stats(stats=stats_p1_2, session=session)

    pfdb_empty.create_player(player=player2, session=session)
    pfdb_empty.add_career_stats(stats=stats_p2_1, session=session)
    pfdb_empty.add_career_stats(stats=stats_p2_2, session=session)

    p1stats = player1.career_stats
    p2stats = player2.career_stats
    assert len(p1stats) == 2
    assert len(p2stats) == 2

    session.delete(p1stats[1])
    session.commit()

    session.refresh(player1)
    session.refresh(player2)
    p1stats = player1.career_stats
    p2stats = player2.career_stats
    assert len(p1stats) == 1
    assert len(p2stats) == 2

    session.delete(p1stats[0])
    session.commit()

    session.refresh(player1)
    session.refresh(player2)
    p1stats = player1.career_stats
    p2stats = player2.career_stats
    assert len(p1stats) == 0
    assert len(p2stats) == 2

    pfdb_empty.delete_all_career_stats(session=session)

    session.refresh(player1)
    session.refresh(player2)
    p1stats = player1.career_stats
    p2stats = player2.career_stats
    assert len(p1stats) == 0
    assert len(p2stats) == 0



@pytest.mark.parametrize("igns",
                         [
                             (["IGN2"]),
                             (["IGN2 IGN3 IGN4"]),
                             (["IGN2 IGN3 IGN2"]),
                         ])
def test_ign_hist_updates(pfdb_empty, session, player1, igns):
    # Write Player to DB
    pfdb_empty.create_player(player=player1, session=session)
    orig_ign = player1.ign
    current_ign = player1.ign

    for ign in igns:
        # assuming they are different so new IgnHistory entries will be made
        assert current_ign != ign

        # Update Player
        pfdb_empty.update_player(
            session=session,
            pf_player_id=player1.id,
            ign=ign, 
        )

        current_ign = ign

    # Read Player from DB
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)

    # Check fields
    assert player.id == player1.id
    assert player.ign == current_ign
    assert player.account_created == player1.account_created
    assert player.last_login == player1.last_login
    assert player.avatar_url == player1.avatar_url

    assert len(player.ign_history) == len(igns) + 1

    igns_db = [_.ign for _ in player.ign_history]
    for ign_db, ign_param in zip(igns_db, [orig_ign] + igns):
        assert ign_db == ign_param


def test_ign_hist_no_change(pfdb_empty, session, player1):
    # Write Player to DB
    pfdb_empty.create_player(player=player1, session=session)
    orig_ign = player1.ign

    # Update Player
    pfdb_empty.update_player(
        session=session,
        pf_player_id=player1.id,
        ign=player1.ign, #set to the same as before (no change)
    )

    # Read Player from DB
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)

    assert len(player.ign_history) == 1
    assert player.ign_history[0].ign == orig_ign

    # Update Player
    pfdb_empty.update_player(
        session=session,
        pf_player_id=player1.id,
        ign="IGN2", #a new name
    )

    # Read Player from DB
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)

    assert len(player.ign_history) == 2
    assert player.ign_history[0].ign == orig_ign    
    assert player.ign_history[1].ign == "IGN2"        

    # Update Player
    pfdb_empty.update_player(
        session=session,
        pf_player_id=player1.id,
        ign="IGN2", #set to the same as before (no change)
    )

    # Read Player from DB
    player = pfdb_empty.read_player(pf_player_id=player1.id, session=session)

    assert len(player.ign_history) == 2
    assert player.ign_history[0].ign == orig_ign    
    assert player.ign_history[1].ign == "IGN2"            