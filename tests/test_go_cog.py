from datetime import date 
from datetime import date as datetype
import pytest

from go.exceptions import DiscordUserError

date1 = datetype(year=2022, month=1, day=1)
date2 = datetype(year=2022, month=1, day=2)
date3 = datetype(year=2022, month=1, day=3)
date4 = datetype(year=2022, month=1, day=4)
date5 = datetype(year=2022, month=1, day=5)

def test_connect_go_and_pf_players(godb, pfdb, session, go_p1, go_p2, pf_p1, pf_p2):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    
    godb.create_player(go_player=go_p1, session=session)
    godb.create_player(go_player=go_p2, session=session)
    
    pf_p = pfdb.read_players_by_ign(ign=pf_p1.ign, session=session)[0]
    assert pf_p is not None
    
    assert go_p1.pf_player is None
    assert go_p1.pf_player_id is None
    assert pf_p.go_player is None
    
    go_p1.pf_player = pf_p
    
    # i think Relationship(backpropogate=) sets this property when .pf_player was set
    assert pf_p.go_player.discord_id == go_p1.discord_id
    
    # refresh or commit needed to sync go_p1.pf_player_id with go_p1.pf_player
    session.refresh(go_p1)
    assert go_p1.pf_player_id == pf_p1.id
    

def test_do_set_ign1(gocog, godb, pfdb, session, go_p1, pf_p1, du1):    
    pfdb.create_player(player=pf_p1, session=session)    
    godb.create_player(go_player=go_p1, session=session)
    
    assert go_p1.pf_player is None
    assert pf_p1.go_player is None

    gocog.do_set_ign(player=du1, ign=pf_p1.ign)

    session.refresh(pf_p1)    
    assert pf_p1.go_player.discord_id == go_p1.discord_id    

    session.refresh(go_p1)
    assert go_p1.pf_player_id == pf_p1.id


def test_do_set_ign_new_go_player(gocog, godb, pfdb, session, pf_p1, du1):    
     # update discord_id to something new
    du1.id = 12345
    
    # prove the id isn't in the go_player table
    go_p = godb.read_player(discord_id=du1.id, session=session)
    assert go_p is None
    
    # playfab ign info to point to
    pfdb.create_player(player=pf_p1, session=session)
    
    gocog.do_set_ign(player=du1, ign=pf_p1.ign)

    go_p = godb.read_player(discord_id=du1.id, session=session)
    assert go_p is not None
    assert go_p.discord_id == 12345

    session.refresh(pf_p1)    
    assert pf_p1.go_player.discord_id == go_p.discord_id    

    session.refresh(go_p)
    assert go_p.pf_player_id == pf_p1.id


def test_set_ign_twice_error(gocog, godb, pfdb, session, go_p1, pf_p1, du1):    
    pfdb.create_player(player=pf_p1, session=session)
    godb.create_player(go_player=go_p1, session=session)

    gocog.do_set_ign(player=du1, ign=pf_p1.ign)

    with pytest.raises(DiscordUserError):
        gocog.do_set_ign(player=du1, ign=pf_p1.ign)


def test_set_ign_doesnt_exist(gocog, godb, pfdb, session, pf_p1, du1):    
    pfdb.create_player(player=pf_p1, session=session)

    with pytest.raises(DiscordUserError):
        gocog.do_set_ign(player=du1, ign="IGN DOESNT EXIST")


def test_set_ign_duplicate_ign(gocog, godb, pfdb, session, pf_p1, du1, pf_p1v2):    
    pfdb.create_player(player=pf_p1, session=session) 
    pfdb.create_player(player=pf_p1v2, session=session)

    with pytest.raises(DiscordUserError):
        gocog.do_set_ign(player=du1, ign=pf_p1.ign)


def test_signup_solo(gocog, godb, pfdb, session, du1, pf_p1):
    pfdb.create_player(player=pf_p1, session=session)

    assert 0 == godb.signup_count(session=session)
    gocog.do_set_ign(player=du1, ign="IGN1")
    
    team_id = gocog.do_signup(players=[du1], team_name="tname1", date=date1)
    assert 1 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 1 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)
    
    team = godb.read_team(team_id=team_id, session=session)
    assert team.team_name == "tname1"
    assert team.team_size == 1
    assert len(team.signups) == 1
    assert len(team.rosters) == 1
    
    
def test_signup_duo(gocog, godb, pfdb, session, du1, pf_p1, du2, pf_p2):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    gocog.do_set_ign(player=du1, ign=pf_p1.ign)
    gocog.do_set_ign(player=du2, ign=pf_p2.ign)
    
    team_id = gocog.do_signup(players=[du1, du2], team_name="tname2", date=date1)
    assert 2 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)
    
    team = godb.read_team(team_id=team_id, session=session)
    assert team.team_name == "tname2"
    assert team.team_size == 2
    assert len(team.signups) == 1
    assert len(team.rosters) == 2
    
    
def test_signup_trio(gocog_preload, session, du1, du2, du3):
    godb = gocog_preload.godb
    team_id = gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname3", date=date1)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 3 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)
    
    team = godb.read_team(team_id=team_id, session=session)
    assert team.team_name == "tname3"
    assert team.team_size == 3
    assert len(team.signups) == 1
    assert len(team.rosters) == 3

    team_id = gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname3", date=date2)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 3 == godb.roster_count(session=session)
    assert 2 == godb.signup_count(session=session)
    
    session.refresh(team)
    assert team.team_name == "tname3"
    assert team.team_size == 3
    assert len(team.signups) == 2
    assert len(team.rosters) == 3    


def test_signup_missing_user_fails(gocog_preload, du1, du2, du3):
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1, None, du3], team_name="tname3", date=date1)
        
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[None, du2, du3], team_name="tname3", date=date1)

    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[None, None], team_name="tname3", date=date1)


def test_signup_missing_set_ign_fails(gocog, godb, pfdb, session, du1, pf_p1, du2, pf_p2, du3, pf_p3):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    pfdb.create_player(player=pf_p3, session=session)
    gocog.do_set_ign(player=du1, ign=pf_p1.ign)
    gocog.do_set_ign(player=du2, ign=pf_p2.ign)
    # gocog.do_set_ign(player=du3, ign=pf_p3.ign)
    
    with pytest.raises(DiscordUserError):
        team_id = gocog.do_signup(players=[du1, du2, du3], team_name="tname3", date=date1)
        

def test_signup_dup_user_fails(gocog_preload, du1, du2, du3):
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1, du1, du3], team_name="tname3", date=date1)


def test_signup_name_change_fail(gocog_preload, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname3", date=date1)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1, du2, du3], team_name="SAME TEAM DIFF NAME", date=date2)


def test_signup_name_collision_fail(gocog_preload, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2], team_name="SAME NAME DIFF TEAM", date=date1)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du3], team_name="SAME NAME DIFF TEAM", date=date2)        


def test_signup_same_day_fail(gocog_preload, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname1", date=date1)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname1", date=date1)        


def test_signup_too_many_signups_fail(gocog_preload, du1, du2, du3):
    gocog_preload.do_signup(players=[du1], team_name="tname1", date=date1)
    gocog_preload.do_signup(players=[du1], team_name="tname1", date=date2)
    gocog_preload.do_signup(players=[du1], team_name="tname1", date=date3)
    gocog_preload.do_signup(players=[du1], team_name="tname1", date=date4)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1], team_name="tname1", date=date5) 


def test_signup_player_on_diff_team_same_day_fail(gocog_preload, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2], team_name="tname1", date=date1)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du2], team_name="tname2", date=date1)        


def test_cancel_signup(gocog_preload, godb, session, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2], team_name="tname1", date=date1)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)
    
    gocog_preload.do_cancel(player=du2, date=date1)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 0 == godb.signup_count(session=session)


def test_cancel_signup_fail(gocog_preload, godb, session, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2], team_name="tname1", date=date1)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_cancel(player=du3, date=date1)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_cancel(player=du1, date=date2)
