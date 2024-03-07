from datetime import datetime, timedelta
import pytest
from go.models import PfPlayer

from go.playfab_db import PfIgnHistory
from go.exceptions import PlayerNotFoundError

def test_create_and_read_player(pfdb, session, pf_p1):
    function_start = datetime.now()

    # Write Player to DB
    pfdb.create_player(player=pf_p1, session=session)
    assert 1 == pfdb.player_count(session=session)

    # # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)
    assert player.ign == pf_p1.ign
    assert player.account_created == pf_p1.account_created
    assert player.last_login == pf_p1.last_login
    assert player.avatar_url == pf_p1.avatar_url

    ign_hist = player.ign_history
    function_end = datetime.now()

    assert len(ign_hist) == 1
    assert ign_hist[0].ign == player.ign
    assert ign_hist[0].pf_player_id == player.id
    assert ign_hist[0].date >= function_start
    assert ign_hist[0].date <= function_end


def test_read_players_by_ign(pfdb, session, pf_p1, pf_p2):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)

    players = pfdb.read_players_by_ign(ign=pf_p1.ign, session=session)
    assert len(players) == 1
    player1 = players[0]
    assert player1.id == pf_p1.id

    players = pfdb.read_players_by_ign(ign=pf_p2.ign, session=session)
    assert len(players) == 1
    player2 = players[0]    
    assert player2.id == pf_p2.id

    players = pfdb.read_players_by_ign(ign="IGN NOT IN DB", session=session)
    assert players == []


def test_read_players_by_ign_duplicate(pfdb, session, pf_p1, pf_p2, pf_p1v2):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    pfdb.create_player(player=pf_p1v2, session=session)

    players = pfdb.read_players_by_ign(ign=pf_p1.ign, session=session)
    assert len(players) == 2
    ids = set([_.id for _ in players])
    assert pf_p1.id in ids
    assert pf_p1v2.id in ids

def test_player_exists(pfdb, session, pf_p1, pf_p2):
    assert pfdb.player_exists(pf_player_id=pf_p1.id, session=session) == False
    
    # Write Player to DB
    pfdb.create_player(player=pf_p1, session=session)
    assert 1 == pfdb.player_count(session=session)
    assert pfdb.player_exists(pf_player_id=pf_p1.id, session=session) == True
    assert pfdb.player_exists(pf_player_id=pf_p2.id, session=session) == False

    pfdb.delete_player(session=session, pf_player_id=pf_p1.id)
    assert pfdb.player_exists(pf_player_id=pf_p1.id, session=session) == False
    assert pfdb.player_exists(pf_player_id=pf_p2.id, session=session) == False


def test_delete_player(pfdb, session, pf_p1, pf_p2):
    # Write 2 Players to DB
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    assert 2 == pfdb.player_count(session=session)

    # Delete Player
    pfdb.delete_player(session=session, pf_player_id=pf_p2.id)

    # Ensure Player1 is still there
    assert 1 == pfdb.player_count(session=session)
    assert pfdb.player_exists(pf_player_id=pf_p1.id, session=session) == True
    assert pfdb.player_exists(pf_player_id=pf_p2.id, session=session) == False

    # Read Player from DB
    assert None == pfdb.read_player(pf_player_id=pf_p2.id, session=session)


def test_delete_player_with_stats(pfdb, session, pf_p1, pf_p2, stats_p1_1, stats_p1_2, stats_p2_1):
    # Write 2 Players to DB
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    assert 2 == pfdb.player_count(session=session)

    # add CareerStats to make sure those entries are deleted too
    pfdb.add_career_stats(stats=stats_p2_1, session=session)
    pfdb.add_career_stats(stats=stats_p1_1, session=session)
    pfdb.add_career_stats(stats=stats_p1_2, session=session)

    # Delete Player
    pfdb.delete_player(session=session, pf_player_id=pf_p2.id)

    # Ensure Player1 is still there
    assert 1 == pfdb.player_count(session=session)
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)
    assert player.ign == pf_p1.ign
    assert player.account_created == pf_p1.account_created
    assert player.last_login == pf_p1.last_login
    assert player.avatar_url == pf_p1.avatar_url

    # Read Player from DB
    assert None == pfdb.read_player(pf_player_id=pf_p2.id, session=session)


def test_delete_all_players(pfdb, session, pf_p1, pf_p2):
    # Write 2 Players to DB
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    assert 2 == pfdb.player_count(session=session)

    # Delete all Players from DB
    pfdb.delete_all_players(session=session)

    # Read all Players from DB
    assert 0 == pfdb.player_count(session=session)


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
def test_update_player(pfdb, session, pf_p1, ign, last_login, avatar_url):
    # Write Player to DB
    pfdb.create_player(player=pf_p1, session=session)

    # Update Player
    pfdb.update_player(
        session=session,
        pf_player_id=pf_p1.id,
        ign=ign, 
        last_login=last_login,
        avatar_url=avatar_url
    )

    # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)

    # Check fields
    assert player.id == pf_p1.id
    assert player.account_created == pf_p1.account_created

    if ign:
        assert player.ign == ign
    else:
        assert player.ign == pf_p1.ign
    
    if last_login:
        assert player.last_login == last_login
    else:
        assert player.last_login == pf_p1.last_login
    
    if avatar_url:
        assert player.avatar_url == avatar_url
    else:
        assert player.avatar_url == pf_p1.avatar_url


def test_career_stats_create_and_read(pfdb, session, 
                                      pf_p1, stats_p1_1, stats_p1_2,
                                      pf_p2, stats_p2_1, stats_p2_2):
    pfdb.create_player(player=pf_p1, session=session)
    assert 1 == pfdb.player_count(session=session)

    pfdb.add_career_stats(stats=stats_p1_1, session=session)
    p1stats = pf_p1.career_stats
    assert len(p1stats) == 1

    pfdb.add_career_stats(stats=stats_p1_2, session=session)
    p1stats = pf_p1.career_stats
    assert len(p1stats) == 2

    pfdb.create_player(player=pf_p2, session=session)
    assert 2 == pfdb.player_count(session=session)

    pfdb.add_career_stats(stats=stats_p2_1, session=session)
    p2stats = pf_p2.career_stats
    assert len(p1stats) == 2
    assert len(p2stats) == 1

    pfdb.add_career_stats(stats=stats_p2_2, session=session)
    p2stats = pf_p2.career_stats
    assert len(p1stats) == 2
    assert len(p2stats) == 2


def test_career_stats_deletes(pfdb, session, 
                                      pf_p1, stats_p1_1, stats_p1_2,
                                      pf_p2, stats_p2_1, stats_p2_2):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.add_career_stats(stats=stats_p1_1, session=session)
    pfdb.add_career_stats(stats=stats_p1_2, session=session)

    pfdb.create_player(player=pf_p2, session=session)
    pfdb.add_career_stats(stats=stats_p2_1, session=session)
    pfdb.add_career_stats(stats=stats_p2_2, session=session)

    p1stats = pf_p1.career_stats
    p2stats = pf_p2.career_stats
    assert len(p1stats) == 2
    assert len(p2stats) == 2

    session.delete(p1stats[1])
    session.commit()

    session.refresh(pf_p1)
    session.refresh(pf_p2)
    p1stats = pf_p1.career_stats
    p2stats = pf_p2.career_stats
    assert len(p1stats) == 1
    assert len(p2stats) == 2

    session.delete(p1stats[0])
    session.commit()

    session.refresh(pf_p1)
    session.refresh(pf_p2)
    p1stats = pf_p1.career_stats
    p2stats = pf_p2.career_stats
    assert len(p1stats) == 0
    assert len(p2stats) == 2

    pfdb.delete_all_career_stats(session=session)

    session.refresh(pf_p1)
    session.refresh(pf_p2)
    p1stats = pf_p1.career_stats
    p2stats = pf_p2.career_stats
    assert len(p1stats) == 0
    assert len(p2stats) == 0



@pytest.mark.parametrize("igns",
                         [
                             (["IGN2"]),
                             (["IGN2 IGN3 IGN4"]),
                             (["IGN2 IGN3 IGN2"]),
                         ])
def test_ign_hist_updates(pfdb, session, pf_p1, igns):
    # Write Player to DB
    pfdb.create_player(player=pf_p1, session=session)
    orig_ign = pf_p1.ign
    current_ign = pf_p1.ign

    for ign in igns:
        # assuming they are different so new IgnHistory entries will be made
        assert current_ign != ign

        # Update Player
        pfdb.update_player(
            session=session,
            pf_player_id=pf_p1.id,
            ign=ign, 
        )

        current_ign = ign

    # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)

    # Check fields
    assert player.id == pf_p1.id
    assert player.ign == current_ign
    assert player.account_created == pf_p1.account_created
    assert player.last_login == pf_p1.last_login
    assert player.avatar_url == pf_p1.avatar_url

    assert len(player.ign_history) == len(igns) + 1

    igns_db = [_.ign for _ in player.ign_history]
    for ign_db, ign_param in zip(igns_db, [orig_ign] + igns):
        assert ign_db == ign_param


def test_ign_hist_no_change_and_ordering(pfdb, session, pf_p1):
    # Write Player to DB
    pfdb.create_player(player=pf_p1, session=session)
    orig_ign = pf_p1.ign
    assert 1 == pfdb.ign_history_count(session=session)

    # Update Player
    pfdb.update_player(
        session=session,
        pf_player_id=pf_p1.id,
        ign=pf_p1.ign, #set to the same as before (no change)
    )
    assert 1 == pfdb.ign_history_count(session=session)

    # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)

    assert len(player.ign_history) == 1
    assert player.ign_history[0].ign == orig_ign

    # Update Player
    pfdb.update_player(
        session=session,
        pf_player_id=pf_p1.id,
        ign="IGN2", #a new name
    )
    assert 2 == pfdb.ign_history_count(session=session)

    # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)

    assert len(player.ign_history) == 2
    assert player.ign_history[0].ign == orig_ign    
    assert player.ign_history[1].ign == "IGN2"        

    # Update Player
    pfdb.update_player(
        session=session,
        pf_player_id=pf_p1.id,
        ign="IGN2", #set to the same as before (no change)
    )
    assert 2 == pfdb.ign_history_count(session=session)

    # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)

    # make sure updating the player with the same IGN as before
    # doesn't add an entry to ign_history
    assert len(player.ign_history) == 2
    assert player.ign_history[0].ign == orig_ign    
    assert player.ign_history[1].ign == "IGN2"
    assert 2 == pfdb.ign_history_count(session=session)

    # Update Player
    pfdb.update_player(
        session=session,
        pf_player_id=pf_p1.id,
        ign="IGN3", #a new name
    )
    assert 3 == pfdb.ign_history_count(session=session)

    # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)

    assert len(player.ign_history) == 3
    assert player.ign_history[0].ign == orig_ign    
    assert player.ign_history[1].ign == "IGN2"
    assert player.ign_history[2].ign == "IGN3"
    
    # Update Player
    pfdb.update_player(
        session=session,
        pf_player_id=pf_p1.id,
        ign=orig_ign, #a new name
    )
    assert 4 == pfdb.ign_history_count(session=session)

    # Read Player from DB
    player = pfdb.read_player(pf_player_id=pf_p1.id, session=session)

    assert len(player.ign_history) == 4
    assert player.ign_history[0].ign == orig_ign    
    assert player.ign_history[1].ign == "IGN2"
    assert player.ign_history[2].ign == "IGN3"         
    assert player.ign_history[3].ign == orig_ign    
    
    one_hour_ago = datetime.now() - timedelta(hours=1)
    # try adding an older ign and see if sorting still works:
    ign_row = PfIgnHistory(
        pf_player_id=pf_p1.id,
        date=one_hour_ago,
        ign="IGNOLD"
    )
    session.add(ign_row)
    session.commit()
    session.refresh(player)

    assert 5 == pfdb.ign_history_count(session=session)
    assert len(player.ign_history) == 5
    assert player.ign_history[0].ign == "IGNOLD"    
    assert player.ign_history[1].ign == orig_ign    
    assert player.ign_history[2].ign == "IGN2"
    assert player.ign_history[3].ign == "IGN3"         
    assert player.ign_history[4].ign == orig_ign    
