from datetime import datetime
from datetime import date as datetype
from typing import List
import pytest
from icecream import ic
from sqlalchemy.exc import IntegrityError

from go.exceptions import GoDbError, PlayerNotFoundError
from go.go_db import GoTeamPlayer
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



def test_create_and_read_team_and_roster(godb_empty, session, go_p1, go_p2):
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



def test_read_team_with_roster(godb_empty, session, go_p1, go_p2):
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)

    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb_empty.create_team(team_name="tn2", go_players=[go_p1], session=session)

    teama = godb_empty.read_team_with_roster(discord_ids={go_p1.discord_id, go_p2.discord_id}, session=session)
    assert teama.id == team1.id
    
    teamb = godb_empty.read_team_with_roster(discord_ids={go_p1.discord_id}, session=session)
    assert teamb.id == team2.id
    
    teamc = godb_empty.read_team_with_roster(discord_ids={go_p2.discord_id}, session=session)
    assert teamc == None



def test_create_team_duplicate_roster(godb_empty, session, go_p1, go_p2):
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)

    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb_empty.create_team(team_name="tn2", go_players=[go_p1], session=session)

    with pytest.raises(GoDbError):
        teamx = godb_empty.create_team(team_name="anything", go_players=[go_p1, go_p2], session=session)

    with pytest.raises(GoDbError):
        teamx = godb_empty.create_team(team_name="anything else", go_players=[go_p1], session=session)
    
    

def test_create_and_read_signups(godb_empty, session, go_p1, go_p2):
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)

    assert 0 == godb_empty.team_count(session=session)
    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb_empty.create_team(team_name="tn2", go_players=[go_p1], session=session)

    date1 = datetype(2023,1,1)
    date2 = datetype(2023,1,2)
    date3 = datetype(2023,1,3)
    
    assert 0 == godb_empty.signup_count(session=session)
    godb_empty.add_signup(team=team1, date=date1, session=session)
    assert 1 == godb_empty.signup_count(session=session)
    godb_empty.add_signup(team=team2, date=date2, session=session)
    assert 2 == godb_empty.signup_count(session=session)

    signups: List[GoTeamPlayer] = godb_empty.read_signups(date=date1, session=session)
    assert 2 == len(signups)
    assert team1.id == signups[0].team.id
    assert team1.id == signups[1].team.id
    assert go_p1.discord_id == signups[0].player.discord_id
    assert go_p2.discord_id == signups[1].player.discord_id
    
    signups: List[GoTeamPlayer] = godb_empty.read_signups(date=date2, session=session)
    assert 1 == len(signups)
    assert team2.id == signups[0].team.id
    assert go_p1.discord_id == signups[0].player.discord_id
    
    signups: List[GoTeamPlayer] = godb_empty.read_signups(date=date3, session=session)
    assert 0 == len(signups)



def test_signups_cascading_delete(godb_empty, session, go_p1, go_p2):
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)

    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb_empty.create_team(team_name="tn2", go_players=[go_p1], session=session)

    date1 = datetype(2023,1,1)
    date2 = datetype(2023,1,2)
    
    godb_empty.add_signup(team=team1, date=date1, session=session)
    godb_empty.add_signup(team=team2, date=date2, session=session)
    

    assert 2 == godb_empty.signup_count(session=session)
    session.delete(team1)
    session.commit()
    assert 1 == godb_empty.signup_count(session=session)
    session.delete(team2)
    session.commit()
    assert 0 == godb_empty.signup_count(session=session)
    

def test_signups_same_day_twice(godb_empty, session, go_p1, go_p2):
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)

    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)

    date1 = datetype(2023,1,1)
    
    godb_empty.add_signup(team=team1, date=date1, session=session)
    
    # with pytest.raises(IntegrityError):
    # used to raise IntegrityError from the DB but now we test for players signing
    # up more than once on the same day so it'll catch any team with a member 
    # already signed up
    
    with pytest.raises(GoDbError):
        # try adding the same signup twice
        godb_empty.add_signup(team=team1, date=date1, session=session)



def test_signups_player_same_day_twice(godb_empty, session, go_p1, go_p2):
    godb_empty.create_player(go_player=go_p1, session=session)
    godb_empty.create_player(go_player=go_p2, session=session)

    team1 = godb_empty.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb_empty.create_team(team_name="tn2", go_players=[go_p1], session=session)

    date1 = datetype(2023,1,1)
    date2 = datetype(2023,1,2)
    
    godb_empty.add_signup(team=team1, date=date1, session=session)
    godb_empty.add_signup(team=team2, date=date2, session=session)
    
    with pytest.raises(GoDbError):
        # try signing up a player for the same day on a different team
        # p1 is on both team1 and team2, so cannot signup for date1 again
        godb_empty.add_signup(team=team2, date=date1, session=session)
        
