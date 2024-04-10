from datetime import datetime
from datetime import date as datetype
from typing import List
from time import sleep
import pytest

from go.exceptions import GoDbError, PlayerNotFoundError
from go.go_db import GoTeamPlayerSignup
from go.models import GoPlayer, GoRatings

import _config

date1 = datetype(2023,1,1)
date2 = datetype(2023,1,2)
date3 = datetype(2023,1,3)
date4 = datetype(2023,1,4)
date5 = datetype(2023,1,5)
date6 = datetype(2023,1,6)

channel_id1 = 1111
channel_id2 = 2222
    
def test_create_and_read_player(godb, session, go_p1 : GoPlayer):
    function_start = datetime.now()

    # Write Player to DB
    godb.create_player(go_player=go_p1, session=session)
    assert 1 == godb.player_count(session=session)

    # # Read Player from DB
    go_p = godb.read_player(discord_id=go_p1.discord_id, session=session)
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


def test_player_exists(godb, session, go_p1, go_p2):
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == False
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False

    # Write Player to DB
    godb.create_player(go_player=go_p1, session=session)
    assert 1 == godb.player_count(session=session)
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == True
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False

    godb.delete_player(session=session, discord_id=go_p1.discord_id)
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == False
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False


def test_delete_player(godb, session, go_p1, go_p2):
    # Write 2 Players to DB
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)
    assert 2 == godb.player_count(session=session)

    # Delete Player
    godb.delete_player(session=session, discord_id=go_p2.discord_id)

    # Ensure Player1 is still there
    assert 1 == godb.player_count(session=session)
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == True
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False

    # Read Player from DB
    assert None == godb.read_player(discord_id=go_p2.discord_id, session=session)



def test_create_and_read_team_and_roster(godb, session, go_p1, go_p2):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)
    assert 2 == godb.player_count(session=session)
    assert 0 == godb.team_count(session=session)
    assert 0 == godb.roster_count(session=session)

    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    assert 2 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert team1.team_name == "tn1"
    assert team1.team_size == 2
    assert len(team1.rosters) == 2
    
    roster_ids = {r.discord_id for r in team1.rosters}
    assert len(roster_ids) == 2
    assert go_p1.discord_id in roster_ids
    assert go_p2.discord_id in roster_ids
    
    assert len(go_p1.rosters) == 1
    assert len(go_p2.rosters) == 1

    team2 = godb.create_team(team_name="tn2", go_players=[go_p1], session=session)
    assert 2 == godb.player_count(session=session)
    assert 2 == godb.team_count(session=session)
    assert 3 == godb.roster_count(session=session)
    assert team2.team_name == "tn2"
    assert team2.team_size == 1
    assert len(team2.rosters) == 1    
    assert team2.rosters[0].discord_id == go_p1.discord_id
    
    assert len(go_p1.rosters) == 2
    assert len(go_p2.rosters) == 1
    
    session.delete(team1)
    session.commit()
    assert 2 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 1 == godb.roster_count(session=session)
    assert len(go_p1.rosters) == 1
    assert len(go_p2.rosters) == 0

    with pytest.raises(GoDbError):
        godb.delete_player(discord_id=go_p1.discord_id, session=session)



def test_read_team_with_roster(godb, session, go_p1, go_p2):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)

    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb.create_team(team_name="tn2", go_players=[go_p1], session=session)

    teama = godb.read_team_with_roster(discord_ids={go_p1.discord_id, go_p2.discord_id}, session=session)
    assert teama.id == team1.id
    
    teamb = godb.read_team_with_roster(discord_ids={go_p1.discord_id}, session=session)
    assert teamb.id == team2.id
    
    teamc = godb.read_team_with_roster(discord_ids={go_p2.discord_id}, session=session)
    assert teamc == None

    teamd = godb.read_team_with_roster(discord_ids={}, session=session)
    assert teamd == None

def test_read_team_with_name(godb, session, go_p1, go_p2):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)

    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb.create_team(team_name="tn2", go_players=[go_p1], session=session)

    teama = godb.read_team_with_name(team_name="tn1", session=session)
    assert teama.id == team1.id
    
    teamb = godb.read_team_with_name(team_name="tn2", session=session)
    assert teamb.id == team2.id
    
    teamc = godb.read_team_with_name(team_name="tn3", session=session)
    assert teamc == None
    
    teamd = godb.read_team_with_name(team_name=None, session=session)
    assert teamd == None


def test_create_team_duplicate_roster(godb, session, go_p1, go_p2):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)

    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb.create_team(team_name="tn2", go_players=[go_p1], session=session)

    with pytest.raises(GoDbError):
        teamx = godb.create_team(team_name="anything", go_players=[go_p1, go_p2], session=session)

    with pytest.raises(GoDbError):
        teamx = godb.create_team(team_name="anything else", go_players=[go_p1], session=session)
    
    

def test_create_and_read_player_signups(godb, session, go_p1, go_p2):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)

    assert 0 == godb.team_count(session=session)
    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb.create_team(team_name="tn2", go_players=[go_p1], session=session)
    
    assert 0 == godb.signup_count(session=session)
    godb.add_signup(team=team1, date=date1, session=session)
    assert 1 == godb.signup_count(session=session)
    godb.add_signup(team=team2, date=date2, session=session)
    assert 2 == godb.signup_count(session=session)

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(date=date1, session=session)
    assert 2 == len(signups)
    assert team1.id == signups[0].team.id
    assert team1.id == signups[1].team.id
    assert go_p1.discord_id == signups[0].player.discord_id
    assert go_p2.discord_id == signups[1].player.discord_id
    
    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(date=date2, session=session)
    assert 1 == len(signups)
    assert team2.id == signups[0].team.id
    assert go_p1.discord_id == signups[0].player.discord_id
    
    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(date=date3, session=session)
    assert 0 == len(signups)


def test_read_player_signups_with_filters(godb, session, go_p1, go_p2, go_p3):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)
    godb.create_player(go_player=go_p3, session=session)

    team1 = godb.create_team(team_name="tn1", go_players=[go_p1], session=session)
    team12 = godb.create_team(team_name="tn12", go_players=[go_p1, go_p2], session=session)
    team123 = godb.create_team(team_name="tn123", go_players=[go_p1, go_p2, go_p3], session=session)
    team23 = godb.create_team(team_name="tn23", go_players=[go_p2, go_p3], session=session)
    team3 = godb.create_team(team_name="tn3", go_players=[go_p3], session=session)

    godb.add_signup(team=team1, date=date1, session=session)
    godb.add_signup(team=team23, date=date1, session=session)
    godb.add_signup(team=team12, date=date2, session=session)
    godb.add_signup(team=team123, date=date3, session=session)
    godb.add_signup(team=team1, date=date4, session=session)
    godb.add_signup(team=team3, date=date4, session=session)
    godb.add_signup(team=team23, date=date5, session=session)

    assert godb.signup_count(session=session) == 7
    
    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session)
    assert len(signups) == 12
    
    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, date=date1)
    assert len(signups) == 3

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, date=date1, team_id=team23.id)
    assert len(signups) == 2
    
    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, date=date6)
    assert len(signups) == 0

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, team_id=team23.id)
    assert len(signups) == 4
        
    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, discord_id=go_p1.discord_id)
    assert len(signups) == 4
    
    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, discord_id=0)
    assert len(signups) == 0

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, date=date1, discord_id=go_p1.discord_id)
    assert len(signups) == 1


def test_signups_cascading_delete(godb, session, go_p1, go_p2):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)

    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb.create_team(team_name="tn2", go_players=[go_p1], session=session)
    
    godb.add_signup(team=team1, date=date1, session=session)
    godb.add_signup(team=team2, date=date2, session=session)
    

    assert 2 == godb.signup_count(session=session)
    session.delete(team1)
    session.commit()
    assert 1 == godb.signup_count(session=session)
    session.delete(team2)
    session.commit()
    assert 0 == godb.signup_count(session=session)
    

def test_signups_same_day_twice(godb, session, go_p1, go_p2):
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)
    
    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    
    godb.add_signup(team=team1, date=date1, session=session)
    
    # with pytest.raises(IntegrityError):
    # used to raise IntegrityError from the DB but now we test for players signing
    # up more than once on the same day so it'll catch any team with a member 
    # already signed up
    
    with pytest.raises(GoDbError):
        # try adding the same signup twice
        godb.add_signup(team=team1, date=date1, session=session)



def test_signups_player_same_day_twice(godb, session, go_p1, go_p2):

    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)
    
    team1 = godb.create_team(team_name="tn1", go_players=[go_p1, go_p2], session=session)
    team2 = godb.create_team(team_name="tn2", go_players=[go_p1], session=session)
    
    godb.add_signup(team=team1, date=date1, session=session)
    godb.add_signup(team=team2, date=date2, session=session)
    
    with pytest.raises(GoDbError):
        # try signing up a player for the same day on a different team
        # p1 is on both team1 and team2, so cannot signup for date1 again
        godb.add_signup(team=team2, date=date1, session=session)
        



def test_set_session_date(godb, session):

    godb.set_session_date(session_id=channel_id1, session_date=date1, session=session)
    assert(godb.get_session_date(channel_id1, session=session) == date1)
    assert(godb.get_session_date(channel_id2, session=session) == None)
    
    godb.set_session_date(session_id=channel_id1, session_date=date1, session=session)
    assert(godb.get_session_date(channel_id1, session=session) == date1)
    assert(godb.get_session_date(channel_id2, session=session) == None)
    
    godb.set_session_date(session_id=channel_id1, session_date=date2, session=session)
    assert(godb.get_session_date(channel_id1, session=session) == date2)
        


def test_get_official_rating(godb, pfdb, session, pf_p1, go_p1):
    pfdb.create_player(player=pf_p1, session=session)
    go_p1.pf_player_id  = pf_p1.id
    godb.create_player(go_player=go_p1, session=session)

    session.refresh(go_p1)
    session.refresh(pf_p1)
    
    rating1 = GoRatings(pf_player_id = pf_p1.id,
                        season=_config.go_season,
                        rating_type='official',
                        go_rating=1234.5
                        )
    print('rating1',rating1)
    session.add(rating1)
    session.commit()
    
    go_rating = godb.get_official_rating(pf_player_id=pf_p1.id, session=session)
    assert go_rating == 1234.5
    
    

def test_get_teams_for_date(gocog_preload, godb, session, go_p1, go_p2, go_p3):
    team1 = godb.create_team(team_name="tn1", go_players=[go_p1], session=session)
    
    team12 = godb.create_team(team_name="tn12", go_players=[go_p1, go_p2], session=session)
    team2 = godb.create_team(team_name="tn2", go_players=[go_p2], session=session)
    team123 = godb.create_team(team_name="tn123", go_players=[go_p1, go_p2, go_p3], session=session)
    team23 = godb.create_team(team_name="tn23", go_players=[go_p2, go_p3], session=session)
    team3 = godb.create_team(team_name="tn3", go_players=[go_p3], session=session)

    godb.add_signup(team=team1, date=date1, session=session)
    godb.add_signup(team=team23, date=date1, session=session)
    godb.add_signup(team=team12, date=date2, session=session)
    godb.add_signup(team=team123, date=date3, session=session)
    godb.add_signup(team=team1, date=date4, session=session)
    godb.add_signup(team=team3, date=date4, session=session)
    godb.add_signup(team=team2, date=date4, session=session)
    
    teams1 = godb.get_teams_for_date(session_date=date1, session=session)
    assert len(teams1) == 2
    assert teams1[0].id == team1.id
    assert teams1[1].id == team23.id
    
    teams4 = godb.get_teams_for_date(session_date=date4, session=session)
    assert len(teams4) == 3
    assert teams4[0].id == team1.id
    assert teams4[1].id == team3.id
    assert teams4[2].id == team2.id
        
    teams5 = godb.get_teams_for_date(session_date=date5, session=session)
    assert len(teams5) == 0

    # # test code for go_cog
    # msg = ''
    # for team in teams1:
    #             session.refresh(team)
    #             players = [r.player for r in team.rosters]
    #             players_str = ''
    #             for p in players:
    #                 session.refresh(p.pf_player)
    #                 if players_str:
    #                     players_str += ', '
    #                 players_str += p.pf_player.ign
    #             msg += f'**{team.team_name}** (*{team.team_rating}*) -- {players_str}\n'
    # print(f'msg: \n{msg}')
    # assert(0)