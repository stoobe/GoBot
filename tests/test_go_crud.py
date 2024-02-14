from datetime import datetime
import pytest
from icecream import ic

from go.exceptions import GoDbError, PlayerNotFoundError
from go.models import GoPlayer

def test_create_and_read_player(godb_empty, session, go_p1 : GoPlayer):
    function_start = datetime.now()

    # Write Player to DB
    godb_empty.create_player(go_player=go_p1, session=session)
    assert 1 == godb_empty.player_count(session=session)

    # # Read Player from DB
    go_p = godb_empty.read_player(discord_id=go_p1.discord_id, session=session)
    ic(go_p1)
    ic(go_p)
    assert go_p.discord_id == go_p1.discord_id
    assert go_p.discord_name == go_p1.discord_name
    assert go_p.pf_player_id == go_p1.pf_player_id
    assert go_p.created_at == go_p1.created_at

    # ign_hist = go_player.ign_history
    # function_end = datetime.now()

    # assert len(ign_hist) == 1
    # assert ign_hist[0].ign == go_player.ign
    # assert ign_hist[0].discord_id == go_player.id
    # assert ign_hist[0].date >= function_start
    # assert ign_hist[0].date <= function_end


def test_player_exists(godb_empty, session, go_p1, go_p2):
    assert godb_empty.player_exists(discord_id=go_p1.discord_id, session=session) == False
    assert godb_empty.player_exists(discord_id=go_p2.discord_id, session=session) == False

    # Write Player to DB
    godb_empty.create_player(go_player=go_p1, session=session)
    assert 1 == godb_empty.player_count(session=session)
    assert godb_empty.player_exists(discord_id=go_p1.discord_id, session=session) == True
    assert godb_empty.player_exists(discord_id=go_p2.discord_id, session=session) == False

    godb_empty.delete_player(session=session, discord_id=go_p1.discord_id)
    assert godb_empty.player_exists(discord_id=go_p1.discord_id, session=session) == False
    assert godb_empty.player_exists(discord_id=go_p2.discord_id, session=session) == False


def test_delete_player(godb_empty, session, go_p1, go_p2):
    # Write 2 Players to DB
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)
    assert 2 == godb_empty.player_count(session=session)

    # Delete Player
    godb_empty.delete_player(session=session, discord_id=go_p2.discord_id)

    # Ensure Player1 is still there
    assert 1 == godb_empty.player_count(session=session)
    assert godb_empty.player_exists(discord_id=go_p1.discord_id, session=session) == True
    assert godb_empty.player_exists(discord_id=go_p2.discord_id, session=session) == False

    # Read Player from DB
    with pytest.raises(PlayerNotFoundError):
        godb_empty.read_player(discord_id=go_p2.discord_id, session=session)


# def test_delete_player_with_stats(godb_empty, session, go_p1, go_p2, stats_p1_1, stats_p1_2, stats_p2_1):
#     # Write 2 Players to DB
#     godb_empty.create_player(go_player=go_p1, session=session)
#     godb_empty.create_player(go_player=go_p2, session=session)
#     assert 2 == godb_empty.player_count(session=session)

#     # add CareerStats to make sure those entries are deleted too
#     godb_empty.add_career_stats(stats=stats_p2_1, session=session)
#     godb_empty.add_career_stats(stats=stats_p1_1, session=session)
#     godb_empty.add_career_stats(stats=stats_p1_2, session=session)

#     # Delete Player
#     godb_empty.delete_player(session=session, discord_id=go_p2.discord_id)

#     # Ensure Player1 is still there
#     assert 1 == godb_empty.player_count(session=session)
#     go_player = godb_empty.read_player(discord_id=go_p1.discord_id, session=session)
#     assert go_player.ign == go_p1.ign
#     assert go_player.account_created == go_p1.account_created
#     assert go_player.last_login == go_p1.last_login
#     assert go_player.avatar_url == go_p1.avatar_url

#     # Read Player from DB
#     with pytest.raises(PlayerNotFoundError):
#         godb_empty.read_player(discord_id=go_p2.discord_id, session=session)


# def test_delete_all_players(godb_empty, session, go_p1, go_p2):
#     # Write 2 Players to DB
#     godb_empty.create_player(go_player=go_p1, session=session)
#     godb_empty.create_player(go_player=go_p2, session=session)
#     assert 2 == godb_empty.player_count(session=session)

#     # Delete all Players from DB
#     godb_empty.delete_all_players(session=session)

#     # Read all Players from DB
#     assert 0 == godb_empty.player_count(session=session)


# @pytest.mark.parametrize("ign, last_login, avatar_url",
#                          [
#                              (None, None, None),
#                              ("IGN111", None, None),
#                              (None, datetime(2023,3,3,3,3,3), None),
#                              (None, None, "av.url"),
#                              ("IGN111", datetime(2023,3,3,3,3,3), None),
#                              ("IGN111", None, "av.url"),
#                              (None, datetime(2023,3,3,3,3,3), "av.url"),
#                              ("IGN111", datetime(2023,3,3,3,3,3), "av.url"),
#                          ])
# def test_update_player(godb_empty, session, go_p1, ign, last_login, avatar_url):
#     # Write Player to DB
#     godb_empty.create_player(go_player=go_p1, session=session)

#     # Update Player
#     godb_empty.update_player(
#         session=session,
#         discord_id=go_p1.discord_id,
#         ign=ign, 
#         last_login=last_login,
#         avatar_url=avatar_url
#     )

#     # Read Player from DB
#     go_player = godb_empty.read_player(discord_id=go_p1.discord_id, session=session)

#     # Check fields
#     assert go_player.id == go_p1.discord_id
#     assert go_player.account_created == go_p1.account_created

#     if ign:
#         assert go_player.ign == ign
#     else:
#         assert go_player.ign == go_p1.ign
    
#     if last_login:
#         assert go_player.last_login == last_login
#     else:
#         assert go_player.last_login == go_p1.last_login
    
#     if avatar_url:
#         assert go_player.avatar_url == avatar_url
#     else:
#         assert go_player.avatar_url == go_p1.avatar_url


def test_create_and_read_team_and_roster(godb_empty, session, go_p1, go_p2):
    # Write Player to DB
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)
    assert 2 == godb_empty.player_count(session=session)
    assert 0 == godb_empty.team_count(session=session)
    assert 0 == godb_empty.roster_count(session=session)

    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    assert 2 == godb_empty.player_count(session=session)
    assert 1 == godb_empty.team_count(session=session)
    assert 2 == godb_empty.roster_count(session=session)
    assert team1.team_name == "tn1"
    assert team1.team_size == 2
    assert len(team1.rosters) == 2
    
    roster_ids = {r.discord_id for r in team1.rosters}
    assert len(roster_ids) == 2
    assert go_p1.discord_id in roster_ids
    assert go_p2.discord_id in roster_ids
    
    assert len(go_p1.rosters) == 1
    assert len(go_p2.rosters) == 1

    team2 = godb_empty.create_team(team_name="tn2", go_players=[go_p1], session=session)
    assert 2 == godb_empty.player_count(session=session)
    assert 2 == godb_empty.team_count(session=session)
    assert 3 == godb_empty.roster_count(session=session)
    assert team2.team_name == "tn2"
    assert team2.team_size == 1
    assert len(team2.rosters) == 1    
    assert team2.rosters[0].discord_id == go_p1.discord_id
    
    assert len(go_p1.rosters) == 2
    assert len(go_p2.rosters) == 1
    
    session.delete(team1)
    session.commit()
    assert 2 == godb_empty.player_count(session=session)
    assert 1 == godb_empty.team_count(session=session)
    assert 1 == godb_empty.roster_count(session=session)
    assert len(go_p1.rosters) == 1
    assert len(go_p2.rosters) == 0

    with pytest.raises(GoDbError):
        godb_empty.delete_player(discord_id=go_p1.discord_id, session=session)




def test_create_and_read_signups(godb_empty, session, go_p1, go_p2):
    # Write Player to DB
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)
    assert 2 == godb_empty.player_count(session=session)
    assert 0 == godb_empty.team_count(session=session)
    assert 0 == godb_empty.roster_count(session=session)

    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    assert 2 == godb_empty.player_count(session=session)
    assert 1 == godb_empty.team_count(session=session)
    assert 2 == godb_empty.roster_count(session=session)
    assert team1.team_name == "tn1"
    assert team1.team_size == 2
    assert len(team1.rosters) == 2
    
    roster_ids = {r.discord_id for r in team1.rosters}
    assert len(roster_ids) == 2
    assert go_p1.discord_id in roster_ids
    assert go_p2.discord_id in roster_ids
    
    assert len(go_p1.rosters) == 1
    assert len(go_p2.rosters) == 1

    team2 = godb_empty.create_team(team_name="tn2", go_players=[go_p1], session=session)
    assert 2 == godb_empty.player_count(session=session)
    assert 2 == godb_empty.team_count(session=session)
    assert 3 == godb_empty.roster_count(session=session)
    assert team2.team_name == "tn2"
    assert team2.team_size == 1
    assert len(team2.rosters) == 1    
    assert team2.rosters[0].discord_id == go_p1.discord_id
    
    assert len(go_p1.rosters) == 2
    assert len(go_p2.rosters) == 1
    
    session.delete(team1)
    session.commit()
    assert 2 == godb_empty.player_count(session=session)
    assert 1 == godb_empty.team_count(session=session)
    assert 1 == godb_empty.roster_count(session=session)
    assert len(go_p1.rosters) == 1
    assert len(go_p2.rosters) == 0

    with pytest.raises(GoDbError):
        godb_empty.delete_player(discord_id=go_p1.discord_id, session=session)
        
        

# def test_career_stats_create_and_read(godb_empty, session, 
#                                       go_p1, stats_p1_1, stats_p1_2,
#                                       go_p2, stats_p2_1, stats_p2_2):
#     godb_empty.create_player(go_player=go_p1, session=session)
#     assert 1 == godb_empty.player_count(session=session)

#     godb_empty.add_career_stats(stats=stats_p1_1, session=session)
#     p1stats = go_p1.career_stats
#     assert len(p1stats) == 1

#     godb_empty.add_career_stats(stats=stats_p1_2, session=session)
#     p1stats = go_p1.career_stats
#     assert len(p1stats) == 2

#     godb_empty.create_player(go_player=go_p2, session=session)
#     assert 2 == godb_empty.player_count(session=session)

#     godb_empty.add_career_stats(stats=stats_p2_1, session=session)
#     p2stats = go_p2.career_stats
#     assert len(p1stats) == 2
#     assert len(p2stats) == 1

#     godb_empty.add_career_stats(stats=stats_p2_2, session=session)
#     p2stats = go_p2.career_stats
#     assert len(p1stats) == 2
#     assert len(p2stats) == 2


# def test_career_stats_deletes(godb_empty, session, 
#                                       go_p1, stats_p1_1, stats_p1_2,
#                                       go_p2, stats_p2_1, stats_p2_2):
#     godb_empty.create_player(go_player=go_p1, session=session)
#     godb_empty.add_career_stats(stats=stats_p1_1, session=session)
#     godb_empty.add_career_stats(stats=stats_p1_2, session=session)

#     godb_empty.create_player(go_player=go_p2, session=session)
#     godb_empty.add_career_stats(stats=stats_p2_1, session=session)
#     godb_empty.add_career_stats(stats=stats_p2_2, session=session)

#     p1stats = go_p1.career_stats
#     p2stats = go_p2.career_stats
#     assert len(p1stats) == 2
#     assert len(p2stats) == 2

#     session.delete(p1stats[1])
#     session.commit()

#     session.refresh(go_p1)
#     session.refresh(go_p2)
#     p1stats = go_p1.career_stats
#     p2stats = go_p2.career_stats
#     assert len(p1stats) == 1
#     assert len(p2stats) == 2

#     session.delete(p1stats[0])
#     session.commit()

#     session.refresh(go_p1)
#     session.refresh(go_p2)
#     p1stats = go_p1.career_stats
#     p2stats = go_p2.career_stats
#     assert len(p1stats) == 0
#     assert len(p2stats) == 2

#     godb_empty.delete_all_career_stats(session=session)

#     session.refresh(go_p1)
#     session.refresh(go_p2)
#     p1stats = go_p1.career_stats
#     p2stats = go_p2.career_stats
#     assert len(p1stats) == 0
#     assert len(p2stats) == 0



# @pytest.mark.parametrize("igns",
#                          [
#                              (["IGN2"]),
#                              (["IGN2 IGN3 IGN4"]),
#                              (["IGN2 IGN3 IGN2"]),
#                          ])
# def test_ign_hist_updates(godb_empty, session, go_p1, igns):
#     # Write Player to DB
#     godb_empty.create_player(go_player=go_p1, session=session)
#     orig_ign = go_p1.ign
#     current_ign = go_p1.ign

#     for ign in igns:
#         # assuming they are different so new IgnHistory entries will be made
#         assert current_ign != ign

#         # Update Player
#         godb_empty.update_player(
#             session=session,
#             discord_id=go_p1.discord_id,
#             ign=ign, 
#         )

#         current_ign = ign

#     # Read Player from DB
#     go_player = godb_empty.read_player(discord_id=go_p1.discord_id, session=session)

#     # Check fields
#     assert go_player.id == go_p1.discord_id
#     assert go_player.ign == current_ign
#     assert go_player.account_created == go_p1.account_created
#     assert go_player.last_login == go_p1.last_login
#     assert go_player.avatar_url == go_p1.avatar_url

#     assert len(go_player.ign_history) == len(igns) + 1

#     igns_db = [_.ign for _ in go_player.ign_history]
#     for ign_db, ign_param in zip(igns_db, [orig_ign] + igns):
#         assert ign_db == ign_param


# def test_ign_hist_no_change(godb_empty, session, go_p1):
#     # Write Player to DB
#     godb_empty.create_player(go_player=go_p1, session=session)
#     orig_ign = go_p1.ign

#     # Update Player
#     godb_empty.update_player(
#         session=session,
#         discord_id=go_p1.discord_id,
#         ign=go_p1.ign, #set to the same as before (no change)
#     )

#     # Read Player from DB
#     go_player = godb_empty.read_player(discord_id=go_p1.discord_id, session=session)

#     assert len(go_player.ign_history) == 1
#     assert go_player.ign_history[0].ign == orig_ign

#     # Update Player
#     godb_empty.update_player(
#         session=session,
#         discord_id=go_p1.discord_id,
#         ign="IGN2", #a new name
#     )

#     # Read Player from DB
#     go_player = godb_empty.read_player(discord_id=go_p1.discord_id, session=session)

#     assert len(go_player.ign_history) == 2
#     assert go_player.ign_history[0].ign == orig_ign    
#     assert go_player.ign_history[1].ign == "IGN2"        

#     # Update Player
#     godb_empty.update_player(
#         session=session,
#         discord_id=go_p1.discord_id,
#         ign="IGN2", #set to the same as before (no change)
#     )

#     # Read Player from DB
#     go_player = godb_empty.read_player(discord_id=go_p1.discord_id, session=session)

#     assert len(go_player.ign_history) == 2
#     assert go_player.ign_history[0].ign == orig_ign    
#     assert go_player.ign_history[1].ign == "IGN2"            