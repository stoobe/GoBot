from datetime import datetime
from time import sleep
from typing import List

import pytest
from sqlmodel import delete

from config import _config 
from go.bot.exceptions import GoDbError, PlayerNotFoundError
from go.bot.go_db import GoTeamPlayerSignup
from go.bot.models import GoPlayer, GoRatings, GoTeam

date1 = datetime(2023, 1, 1)
date2 = datetime(2023, 1, 2)
date3 = datetime(2023, 1, 3)
date4 = datetime(2023, 1, 4)
date5 = datetime(2023, 1, 5)
date6 = datetime(2023, 1, 6)

channel1 = 1111
channel2 = 2222
channel3 = 3333
channel4 = 4444
channel5 = 5555
channel6 = 6666

seas = _config.go_season


def test_create_and_read_player(godb, session, go_p1: GoPlayer):
    # Write Player to DB
    session.add(go_p1)
    assert 1 == godb.player_count(session=session)

    # # Read Player from DB
    go_p = godb.read_player(discord_id=go_p1.discord_id, session=session)
    assert go_p.discord_id == go_p1.discord_id
    assert go_p.discord_name == go_p1.discord_name
    assert go_p.pf_player_id == go_p1.pf_player_id
    assert go_p.created_at == go_p1.created_at


def test_player_exists(godb, session, go_p1, go_p2):
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == False
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False

    # Write Player to DB
    session.add(go_p1)
    assert 1 == godb.player_count(session=session)
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == True
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False

    godb.delete_player(session=session, discord_id=go_p1.discord_id)
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == False
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False


def test_delete_player(godb, session, go_p1, go_p2):
    # Write 2 Players to DB
    session.add(go_p1)
    session.add(go_p2)
    assert 2 == godb.player_count(session=session)

    # Delete Player
    godb.delete_player(session=session, discord_id=go_p2.discord_id)

    # Ensure Player1 is still there
    assert 1 == godb.player_count(session=session)
    assert godb.player_exists(discord_id=go_p1.discord_id, session=session) == True
    assert godb.player_exists(discord_id=go_p2.discord_id, session=session) == False

    # Read Player from DB
    assert None == godb.read_player(discord_id=go_p2.discord_id, session=session)

    with pytest.raises(GoDbError):
        NONEXISTANT_DISCORD_ID = 978342
        godb.delete_player(session=session, discord_id=NONEXISTANT_DISCORD_ID)


def test_create_and_read_team_and_roster(gocog_preload, godb, session, go_p1, go_p2):
    assert 3 == godb.player_count(session=session)
    assert 0 == godb.team_count(session=session)
    assert 0 == godb.roster_count(session=session)

    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    assert 3 == godb.player_count(session=session)
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

    team2 = godb.create_team("tn2", [go_p1], session, None, seas)
    assert 3 == godb.player_count(session=session)
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
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 1 == godb.roster_count(session=session)
    assert len(go_p1.rosters) == 1
    assert len(go_p2.rosters) == 0

    with pytest.raises(GoDbError):
        godb.delete_player(discord_id=go_p1.discord_id, session=session)


def test_read_team_with_roster(gocog_preload, godb, session, go_p1, go_p2):

    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p1], session, None, seas)

    teama = godb.read_team_with_roster(discord_ids={go_p1.discord_id, go_p2.discord_id}, session=session)
    assert teama.id == team1.id

    teamb = godb.read_team_with_roster(discord_ids={go_p1.discord_id}, session=session)
    assert teamb.id == team2.id

    teamc = godb.read_team_with_roster(discord_ids={go_p2.discord_id}, session=session)
    assert teamc == None

    teamd = godb.read_team_with_roster(discord_ids={}, session=session)
    assert teamd == None


def test_read_team_with_name(gocog_preload, godb, session, go_p1, go_p2):
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p1], session, None, seas)

    teama = godb.read_team_with_name(team_name="tn1", session=session)
    assert teama.id == team1.id

    teamb = godb.read_team_with_name(team_name="tn2", session=session)
    assert teamb.id == team2.id

    teamc = godb.read_team_with_name(team_name="tn3", session=session)
    assert teamc == None

    teamd = godb.read_team_with_name(team_name=None, session=session)
    assert teamd == None


def test_read_team(gocog_preload, godb, session, go_p1, go_p2):
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p1], session, None, seas)

    teama = godb.read_team(team_id=team1.id, session=session)
    assert team1 is teama

    teamb = godb.read_team(team_id=2341234, session=session)
    assert teamb is None


def test_create_team_duplicate_roster(gocog_preload, godb, session, go_p1, go_p2):
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p1], session, None, seas)

    with pytest.raises(GoDbError):
        teamx = godb.create_team("anything", [go_p1, go_p2], session, None, seas)

    with pytest.raises(GoDbError):
        teamx = godb.create_team("anything else", [go_p1], session, None, seas)


def test_create_team_duplicate_player(gocog_preload, godb, session, go_p1, go_p2):
    with pytest.raises(GoDbError):
        team1 = godb.create_team("tn1", [go_p1, go_p1], session, None, seas)


def test_create_team_missing_rating(gocog_preload, godb, session, go_p1, go_p2):
    # works when p1 has a rating
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)

    statement = delete(GoRatings).where(GoRatings.pf_player_id == go_p1.pf_player_id)
    session.execute(statement)

    # fails when ratings removed
    with pytest.raises(GoDbError):
        team1 = godb.create_team("tn2", [go_p1], session, None, seas)


def test_create_and_read_player_signups(gocog_preload, godb, session, go_p1, go_p2):
    assert 0 == godb.team_count(session=session)
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p1], session, None, seas)

    assert 0 == godb.signup_count(session=session)
    godb.add_signup(team=team1, session_id=channel1, session=session)
    assert 1 == godb.signup_count(session=session)
    godb.add_signup(team=team2, session_id=channel2, session=session)
    assert 2 == godb.signup_count(session=session)

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session_id=channel1, session=session)
    assert 2 == len(signups)
    assert team1.id == signups[0].team.id
    assert team1.id == signups[1].team.id
    assert go_p1.discord_id == signups[0].player.discord_id
    assert go_p2.discord_id == signups[1].player.discord_id

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session_id=channel2, session=session)
    assert 1 == len(signups)
    assert team2.id == signups[0].team.id
    assert go_p1.discord_id == signups[0].player.discord_id

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session_id=channel3, session=session)
    assert 0 == len(signups)


def test_read_player_signups_with_filters(gocog_preload, godb, session, go_p1, go_p2, go_p3):
    team1 = godb.create_team("tn1", [go_p1], session, None, seas)
    team12 = godb.create_team("tn12", [go_p1, go_p2], session, None, seas)
    team123 = godb.create_team("tn123", [go_p1, go_p2, go_p3], session, None, seas)
    team23 = godb.create_team("tn23", [go_p2, go_p3], session, None, seas)
    team3 = godb.create_team("tn3", [go_p3], session, None, seas)

    godb.add_signup(team=team1, session_id=channel1, session=session)
    godb.add_signup(team=team23, session_id=channel1, session=session)
    godb.add_signup(team=team12, session_id=channel2, session=session)
    godb.add_signup(team=team123, session_id=channel3, session=session)
    godb.add_signup(team=team1, session_id=channel4, session=session)
    godb.add_signup(team=team3, session_id=channel4, session=session)
    godb.add_signup(team=team23, session_id=channel5, session=session)

    assert godb.signup_count(session=session) == 7

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session)
    assert len(signups) == 12

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, session_id=channel1)
    assert len(signups) == 3

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(
        session=session, session_id=channel1, team_id=team23.id
    )
    assert len(signups) == 2

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, session_id=channel6)
    assert len(signups) == 0

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, team_id=team23.id)
    assert len(signups) == 4

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, discord_id=go_p1.discord_id)
    assert len(signups) == 4

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(session=session, discord_id=0)
    assert len(signups) == 0

    signups: List[GoTeamPlayerSignup] = godb.read_player_signups(
        session=session, session_id=channel1, discord_id=go_p1.discord_id
    )
    assert len(signups) == 1


def test_signups_cascading_delete(gocog_preload, godb, session, go_p1, go_p2):
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p1], session, None, seas)

    godb.add_signup(team=team1, session_id=channel1, session=session)
    godb.add_signup(team=team2, session_id=channel2, session=session)

    assert 2 == godb.signup_count(session=session)
    session.delete(team1)
    session.commit()
    assert 1 == godb.signup_count(session=session)
    session.delete(team2)
    session.commit()
    assert 0 == godb.signup_count(session=session)


def test_signups_same_day_twice(gocog_preload, godb, session, go_p1, go_p2):
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)

    godb.add_signup(team=team1, session_id=channel1, session=session)

    with pytest.raises(GoDbError):
        # try adding the same signup twice
        godb.add_signup(team=team1, session_id=channel1, session=session)


def test_signups_with_missing_team_id(gocog_preload, godb, session):
    team1 = GoTeam(team_name="tn1", team_size=2)
    with pytest.raises(GoDbError):
        godb.add_signup(team=team1, session_id=channel1, session=session)


def test_signups_player_same_day_twice(gocog_preload, godb, session, go_p1, go_p2):
    team1 = godb.create_team("tn1", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p1], session, None, seas)

    godb.add_signup(team=team1, session_id=channel1, session=session)
    godb.add_signup(team=team2, session_id=channel2, session=session)

    with pytest.raises(GoDbError):
        # try signing up a player for the same day on a different team
        # p1 is on both team1 and team2, so cannot signup for date1 again
        godb.add_signup(team=team2, session_id=channel1, session=session)


def test_set_session_time(godb, session):

    godb.set_session_time(session_id=channel1, session_time=date1, session=session)
    assert godb.get_session_time(channel1, session=session) == date1
    assert godb.get_session_time(channel2, session=session) == None

    godb.set_session_time(session_id=channel1, session_time=date1, session=session)
    assert godb.get_session_time(channel1, session=session) == date1
    assert godb.get_session_time(channel2, session=session) == None

    godb.set_session_time(session_id=channel1, session_time=date2, session=session)
    assert godb.get_session_time(channel1, session=session) == date2

    with pytest.raises(ValueError):
        godb.set_session_time(session_id=None, session_time=date2, session=session)

    with pytest.raises(ValueError):
        godb.set_session_time(session_id=channel1, session_time=None, session=session)


def test_get_official_rating(godb, pfdb, session, pf_p1, go_p1):
    pfdb.create_player(player=pf_p1, session=session)
    go_p1.pf_player_id = pf_p1.id
    session.add(go_p1)
    session.commit()

    session.refresh(go_p1)
    session.refresh(pf_p1)

    rating1 = GoRatings(pf_player_id=pf_p1.id, season=seas, rating_type="official", go_rating=1234.5)
    print("rating1", rating1)
    session.add(rating1)
    session.commit()

    go_rating = godb.get_official_rating(pf_player_id=pf_p1.id, session=session, season=seas)
    assert go_rating == 1234.5


def test_get_teams_for_session(gocog_preload, godb, session, go_p1, go_p2, go_p3):
    team1 = godb.create_team("tn1", [go_p1], session, None, seas)
    team1.team_rating = 1234.56
    session.add(team1)

    team12 = godb.create_team("tn12", [go_p1, go_p2], session, None, seas)
    team2 = godb.create_team("tn2", [go_p2], session, None, seas)
    team123 = godb.create_team("tn123", [go_p1, go_p2, go_p3], session, None, seas)
    team23 = godb.create_team("tn23", [go_p2, go_p3], session, None, seas)
    team3 = godb.create_team("tn3", [go_p3], session, None, seas)

    godb.add_signup(team=team1, session_id=channel1, session=session)
    godb.add_signup(team=team23, session_id=channel1, session=session)
    godb.add_signup(team=team12, session_id=channel2, session=session)
    godb.add_signup(team=team123, session_id=channel3, session=session)
    godb.add_signup(team=team1, session_id=channel4, session=session)
    godb.add_signup(team=team3, session_id=channel4, session=session)
    godb.add_signup(team=team2, session_id=channel4, session=session)

    teams1 = godb.get_teams_for_session(session_id=channel1, session=session)
    assert len(teams1) == 2
    assert teams1[0].id == team1.id
    assert teams1[1].id == team23.id

    teams4 = godb.get_teams_for_session(session_id=channel4, session=session)
    assert len(teams4) == 3
    assert teams4[0].id == team1.id
    assert teams4[1].id == team3.id
    assert teams4[2].id == team2.id

    teams5 = godb.get_teams_for_session(session_id=channel5, session=session)
    assert len(teams5) == 0
