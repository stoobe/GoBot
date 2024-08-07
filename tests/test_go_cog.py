from datetime import date, datetime

import pytest
from sqlalchemy.exc import InvalidRequestError

from config import _config 
from go.bot.exceptions import DiscordUserError
from go.bot.go_cog import DiscordUser
from go.bot.logger import create_logger
from go.bot.models import GoRatings, PfCareerStats, PfPlayer
from go.bot.playfab_api import as_player_id

logger = create_logger(__name__)

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


def test_get_rating_default(godb, pfdb, gocog, session, pf_p1, stats_p1_1):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.add_career_stats(stats=stats_p1_1, session=session)

    go_rating = gocog.set_rating_if_needed(pf_player_id=pf_p1.id, session=session, season=_config.go_season)
    assert go_rating == stats_p1_1.calc_rating()

    go_rating2 = godb.get_official_rating(pf_player_id=pf_p1.id, session=session, season=_config.go_season)
    assert go_rating == go_rating2


def test_connect_go_and_pf_players(godb, pfdb, session, go_p1, go_p2, pf_p1, pf_p2):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)

    session.add(go_p1)
    session.add(go_p2)

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
    session.add(go_p1)

    assert go_p1.pf_player is None
    assert pf_p1.go_player is None

    gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)

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

    gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)

    go_p = godb.read_player(discord_id=du1.id, session=session)
    assert go_p is not None
    assert go_p.discord_id == 12345

    session.refresh(pf_p1)
    assert pf_p1.go_player.discord_id == go_p.discord_id

    session.refresh(go_p)
    assert go_p.pf_player_id == pf_p1.id


def test_set_ign_twice_error(gocog, godb, pfdb, session, go_p1, pf_p1, du1):
    pfdb.create_player(player=pf_p1, session=session)
    session.add(go_p1)

    gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)

    with pytest.raises(DiscordUserError):
        gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)


def test_set_ign_twice_error_second_user(gocog, godb, pfdb, session, go_p1, pf_p1, du1, du2):
    pfdb.create_player(player=pf_p1, session=session)
    session.add(go_p1)

    gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)

    with pytest.raises(DiscordUserError):
        gocog.do_set_ign(player=du2, ign=pf_p1.ign, session=session)


def test_set_ign_doesnt_exist(gocog, godb, pfdb, session, pf_p1, du1):
    pfdb.create_player(player=pf_p1, session=session)

    with pytest.raises(DiscordUserError):
        gocog.do_set_ign(player=du1, ign="IGN DOESNT EXIST", session=session)


def test_set_ign_duplicate_ign(gocog, godb, pfdb, session, pf_p1, du1, pf_p1v2):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p1v2, session=session)

    with pytest.raises(DiscordUserError):
        gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)


def test_do_set_ign_as_playfabid(gocog, godb, pfdb, session, go_p1, pf_p1, du1):
    playfab_str = "14E017AE65DFDD61"
    pf_p1.id = as_player_id(playfab_str)
    pfdb.create_player(player=pf_p1, session=session)
    session.add(go_p1)

    assert go_p1.pf_player is None
    assert pf_p1.go_player is None

    gocog.do_set_ign(player=du1, ign=playfab_str, session=session)

    session.refresh(pf_p1)
    assert pf_p1.go_player.discord_id == go_p1.discord_id

    session.refresh(go_p1)
    assert go_p1.pf_player_id == pf_p1.id


def test_signup_with_missing_rating_fail(gocog, godb, pfdb, session, du1, pf_p1, stats_p1_1):
    pfdb.create_player(player=pf_p1, session=session)

    assert 0 == godb.signup_count(session=session)
    gocog.do_set_ign(player=du1, ign="IGN1", session=session)

    pfdb.add_career_stats(stats=stats_p1_1, session=session)

    # without setting the rating do_signup will fail
    with pytest.raises(DiscordUserError):
        signup = gocog.do_signup(players=[du1], team_name="tname1", session_id=channel1, session=session)


def test_signup_solo(gocog, godb, pfdb, session, du1, pf_p1, stats_p1_1):
    pfdb.create_player(player=pf_p1, session=session)

    assert 0 == godb.signup_count(session=session)
    gocog.do_set_ign(player=du1, ign="IGN1", session=session)

    pfdb.add_career_stats(stats=stats_p1_1, session=session)
    gocog.set_rating_if_needed(pf_p1.id, session, season=_config.go_season)

    signup = gocog.do_signup(players=[du1], team_name="tname1", session_id=channel1, session=session)
    assert 1 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 1 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)

    team = signup.team
    # team = godb.read_team(team_id=team_id, session=session)
    assert team.team_name == "tname1"
    assert team.team_size == 1
    assert len(team.signups) == 1
    assert len(team.rosters) == 1

    signup2 = gocog.do_signup(players=[du1], team_name=None, session_id=channel2, session=session)
    assert signup2.team.team_name == "tname1"


def test_signup_duo(gocog, godb, pfdb, session, du1, pf_p1, du2, pf_p2, stats_p1_1, stats_p2_1):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)
    gocog.do_set_ign(player=du2, ign=pf_p2.ign, session=session)

    pfdb.add_career_stats(stats=stats_p1_1, session=session)
    pfdb.add_career_stats(stats=stats_p2_1, session=session)
    gocog.set_rating_if_needed(pf_p1.id, session, season=_config.go_season)
    gocog.set_rating_if_needed(pf_p2.id, session, season=_config.go_season)

    signup = gocog.do_signup(players=[du1, du2], team_name="tname2", session_id=channel1, session=session)
    assert 2 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)

    team = signup.team
    # team = godb.read_team(team_id=team_id, session=session)
    assert team.team_name == "tname2"
    assert team.team_size == 2
    assert len(team.signups) == 1
    assert len(team.rosters) == 2


def test_signup_trio(gocog_preload, session, du1, du2, du3):
    godb = gocog_preload.godb
    signup = gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname3", session_id=channel1, session=session)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 3 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)

    team = signup.team
    # team = godb.read_team(team_id=team_id, session=session)
    assert team.team_name == "tname3"
    assert team.team_size == 3
    assert len(team.signups) == 1
    assert len(team.rosters) == 3

    signup = gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname3", session_id=channel2, session=session)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 3 == godb.roster_count(session=session)
    assert 2 == godb.signup_count(session=session)

    session.refresh(team)
    assert team.team_name == "tname3"
    assert team.team_size == 3
    assert len(team.signups) == 2
    assert len(team.rosters) == 3


def test_signup_with_Nones(gocog_preload, session, du1, du2, du3):
    godb = gocog_preload.godb
    signup = gocog_preload.do_signup(
        players=[du1, None, None], team_name="tname3", session_id=channel1, session=session
    )


def test_signup_missing_ign_fail(gocog_preload, session, du1, du2, du3):
    godb = gocog_preload.godb
    du0 = DiscordUser(id=0, name="du0")
    with pytest.raises(DiscordUserError):
        signup = gocog_preload.do_signup(
            players=[du1, du2, du0], team_name="tname3", session_id=channel1, session=session
        )


def test_signup_missing_user_fails(gocog_preload, session, du1, du2, du3):
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1, None, du3], team_name="tname3", session_id=channel1, session=session)

    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[None, du2, du3], team_name="tname3", session_id=channel1, session=session)

    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[None, None], team_name="tname3", session_id=channel1, session=session)


def test_signup_missing_set_ign_fails(gocog, godb, pfdb, session, du1, pf_p1, du2, pf_p2, du3, pf_p3):
    pfdb.create_player(player=pf_p1, session=session)
    pfdb.create_player(player=pf_p2, session=session)
    pfdb.create_player(player=pf_p3, session=session)
    gocog.do_set_ign(player=du1, ign=pf_p1.ign, session=session)
    gocog.do_set_ign(player=du2, ign=pf_p2.ign, session=session)
    # gocog.do_set_ign(player=du3, ign=pf_p3.ign, session=session)

    with pytest.raises(DiscordUserError):
        gocog.do_signup(players=[du1, du2, du3], team_name="tname3", session_id=channel1, session=session)


def test_signup_dup_user_fails(gocog_preload, session, du1, du2, du3):
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1, du1, du3], team_name="tname3", session_id=channel1, session=session)


def test_signup_name_change_uses_old_name(gocog_preload, session, du1, du2, du3):
    signup = gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname3", session_id=channel1, session=session)
    signup = gocog_preload.do_signup(
        players=[du1, du2, du3], team_name="SAME TEAM DIFF NAME", session_id=channel2, session=session
    )
    assert signup.team.team_name == "tname3"


def test_signup_name_collision(gocog_preload, session, du1, du2, du3):
    signup1 = gocog_preload.do_signup(
        players=[du1], team_name="SAME NAME DIFF TEAM", session_id=channel1, session=session
    )
    signup2 = gocog_preload.do_signup(
        players=[du2], team_name="SAME NAME DIFF TEAM", session_id=channel2, session=session
    )

    assert signup2.team.team_name == "SAME NAME DIFF TEAM 2"


def test_signup_name_collision_detect_number(gocog_preload, session, du1, du2, du3):
    signup1 = gocog_preload.do_signup(
        players=[du1], team_name="SAME NAME DIFF TEAM 123", session_id=channel1, session=session
    )
    signup2 = gocog_preload.do_signup(
        players=[du2], team_name="SAME NAME DIFF TEAM 123", session_id=channel2, session=session
    )
    signup3 = gocog_preload.do_signup(
        players=[du3], team_name="SAME NAME DIFF TEAM 124", session_id=channel2, session=session
    )

    assert signup2.team.team_name == "SAME NAME DIFF TEAM 124"
    assert signup3.team.team_name == "SAME NAME DIFF TEAM 125"


def test_signup_same_day_fail(gocog_preload, session, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname1", session_id=channel1, session=session)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname1", session_id=channel1, session=session)


def test_signup_too_many_signups_fail(gocog_preload, session, du1, du2, du3):
    gocog_preload.do_signup(players=[du1], team_name="tname1", session_id=channel1, session=session)
    gocog_preload.do_signup(players=[du1], team_name="tname1", session_id=channel2, session=session)
    gocog_preload.do_signup(players=[du1], team_name="tname1", session_id=channel3, session=session)
    gocog_preload.do_signup(players=[du1], team_name="tname1", session_id=channel4, session=session)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du1], team_name="tname1", session_id=channel5, session=session)


def test_signup_player_on_diff_team_same_day_fail(gocog_preload, session, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2], team_name="tname1", session_id=channel1, session=session)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_signup(players=[du2], team_name="tname2", session_id=channel1, session=session)


def test_signup_over_rating_cap(gocog_preload, session, du1, du2, du3):
    orig = _config.go_rating_limits[3]
    try:
        _config.go_rating_limits[3] = 1
        with pytest.raises(DiscordUserError):
            gocog_preload.do_signup(players=[du1, du2, du3], team_name="tname1", session_id=channel1, session=session)
    finally:
        _config.go_rating_limits[3] = orig


def test_change_signup(gocog_preload, session, du1, du2, du3):
    godb = gocog_preload.godb
    signup = gocog_preload.do_signup(players=[du1, du3], team_name="tname3", session_id=channel1, session=session)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)

    team = signup.team
    assert team.team_name == "tname3"
    assert team.team_size == 2
    assert len(team.signups) == 1
    assert len(team.rosters) == 2

    with pytest.raises(DiscordUserError):
        # du2 not on the original roster
        gocog_preload.do_change_signup(
            player=du2, players=[du1, du2, du3], new_team_name=None, session_id=channel1, session=session
        )

    with pytest.raises(DiscordUserError):
        # date2 wrong date
        gocog_preload.do_change_signup(
            player=du1, players=[du1, du2, du3], new_team_name=None, session_id=channel2, session=session
        )

    gocog_preload.do_change_signup(
        player=du1, players=[du1, du2, du3], new_team_name=None, session_id=channel1, session=session
    )
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 3 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)

    team = godb.read_team_with_name(team_name="tname3", session=session)
    assert team.team_name == "tname3"
    assert team.team_size == 3
    assert len(team.signups) == 1
    assert len(team.rosters) == 3

    gocog_preload.do_change_signup(
        player=du2, players=[du2], new_team_name="team_solo", session_id=channel1, session=session
    )
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 1 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)

    team = godb.read_team_with_name(team_name="team_solo", session=session)
    assert team.team_name == "team_solo"
    assert team.team_size == 1
    assert len(team.signups) == 1
    assert len(team.rosters) == 1

    assert godb.read_team_with_name(team_name="tname3", session=session) is None


def test_rename_team(gocog_preload, godb, session, du1, du2, du3):
    name1 = "tname1"
    gocog_preload.do_signup(players=[du1, du2], team_name=name1, session_id=channel1, session=session)
    team = godb.read_team_with_name(team_name=name1, session=session)
    assert team.team_name == name1

    p1 = DiscordUser(id=du1.id, name=du1.name)
    name2 = "tname222"
    gocog_preload.do_rename_team(player=p1, new_team_name=name2, session_id=channel1, session=session)
    assert team.team_name == name2

    # try to change the name for a date we're not signed up for
    with pytest.raises(DiscordUserError):
        gocog_preload.do_rename_team(player=p1, new_team_name=name2, session_id=channel2, session=session)


def test_cancel_signup(gocog_preload, godb, session, du1, du2, du3):

    assert 3 == godb.player_count(session=session)
    assert 0 == godb.team_count(session=session)
    assert 0 == godb.roster_count(session=session)
    assert 0 == godb.signup_count(session=session)

    # signup day 1
    gocog_preload.do_signup(players=[du1, du2], team_name="tname1", session_id=channel1, session=session)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)

    # signup day 2
    gocog_preload.do_signup(players=[du1, du2], team_name="tname1", session_id=channel2, session=session)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 2 == godb.signup_count(session=session)

    # cancel day 1
    signup = gocog_preload.do_cancel(player=du2, session_id=channel1, session=session)
    assert 3 == godb.player_count(session=session)
    assert 1 == godb.team_count(session=session)
    assert 2 == godb.roster_count(session=session)
    assert 1 == godb.signup_count(session=session)
    session.refresh(signup.team)
    assert signup.team.team_name == "tname1"
    assert len(signup.team.signups) == 1
    assert len(signup.team.rosters) == 2

    # cancel day 2
    # this will test that the team is deleted when the last session is cancelled
    signup = gocog_preload.do_cancel(player=du2, session_id=channel2, session=session)
    assert 3 == godb.player_count(session=session)
    assert 0 == godb.roster_count(session=session)
    assert 0 == godb.signup_count(session=session)
    assert 0 == godb.team_count(session=session)
    with pytest.raises(InvalidRequestError):
        session.refresh(signup.team)


def test_cancel_signup_fail(gocog_preload, godb, session, du1, du2, du3):
    gocog_preload.do_signup(players=[du1, du2], team_name="tname1", session_id=channel1, session=session)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_cancel(player=du3, session_id=channel1, session=session)
    with pytest.raises(DiscordUserError):
        gocog_preload.do_cancel(player=du1, session_id=channel2, session=session)


def test_cancel_return_values(gocog_preload, godb, session, du1, du2, du3):
    signup1 = gocog_preload.do_signup(players=[du1, du2], team_name="tname1", session_id=channel1, session=session)
    signup2 = gocog_preload.do_signup(players=[du1, du2], team_name="tname1", session_id=channel2, session=session)
    assert signup1.team is signup2.team

    team = signup1.team

    signup = gocog_preload.do_cancel(player=du2, session_id=channel1, session=session)
    assert signup.session_id == channel1
    assert team is signup.team

    signup = gocog_preload.do_cancel(player=du2, session_id=channel2, session=session)
    assert signup.session_id == channel2


def test_session_times(gocog, session):
    gocog.godb.set_session_time(session_id=channel1, session_time=date1, session=session)

    time1 = gocog.godb.get_session_time(session_id=channel1, session=session)
    assert time1 == date1

    time2 = gocog.godb.get_session_time(session_id=channel2, session=session)
    assert time2 is None


def tests_hosts(gocog, session, du1, du2):
    gocog.godb.set_session_time(session_id=channel1, session_time=date1, session=session)

    hosts = gocog.godb.get_hosts(session_id=channel1, session=session)
    assert len(hosts) == 0

    gocog.godb.set_host(du1.id, channel1, "confirmed", session)
    hosts = gocog.godb.get_hosts(session_id=channel1, session=session)
    assert len(hosts) == 1

    gocog.godb.set_host(du2.id, channel1, "confirmed", session)
    hosts = gocog.godb.get_hosts(session_id=channel1, session=session)
    assert len(hosts) == 2


def test_sort_lobbies(gocog_preload, godb, session, du1, du2, du3):
    gocog = gocog_preload
    gocog.godb.set_session_time(session_id=channel1, session_time=date1, session=session)
    gocog.godb.set_host(du1.id, channel1, "confirmed", session)

    signup1 = gocog.do_signup(players=[du1], team_name="tname1", session_id=channel1, session=session)
    signup2 = gocog.do_signup(players=[du2], team_name="tname2", session_id=channel1, session=session)

    hosts = gocog.godb.get_hosts(session_id=channel1, session=session)
    teams = gocog.godb.get_teams_for_session(session_id=channel1, session=session)

    host_to_teams = gocog.do_sort_lobbies(hosts, teams)
    print(host_to_teams)

    assert len(host_to_teams) == 1
    assert du1.id in host_to_teams
    assert len(host_to_teams[du1.id]) == 2


def test_sort_lobbies2(gocog_preload, session):
    gocog = gocog_preload
    gocog.godb.set_session_time(session_id=channel1, session_time=date1, session=session)

    for i in range(1000, 1036):
        du = DiscordUser(id=i, name=f"du{i}")
        pf_player = PfPlayer(id=i, ign=f"pf{i}", account_created=datetime.now(), last_login=datetime.now())
        gocog.pfdb.create_player(pf_player, session=session)
        gocog.do_set_ign(player=du, ign=pf_player.ign, session=session)

        pf_stats = PfCareerStats(date=datetime.now(), pf_player_id=i, games=1, wins=1, kills=1, damage=100)
        gocog.pfdb.add_career_stats(stats=pf_stats, session=session)
        gocog.set_rating_if_needed(pf_player.id, session, season=_config.go_season)

        gocog.do_signup(players=[du], team_name=f"tname{i}", session_id=channel1, session=session)

        if i < 1002:
            gocog.godb.set_host(i, channel1, "confirmed", session)

    session.commit()

    hosts = gocog.godb.get_hosts(session_id=channel1, session=session)
    assert len(hosts) == 2

    teams = gocog.godb.get_teams_for_session(session_id=channel1, session=session)
    assert len(teams) == 36

    host_to_teams = gocog.do_sort_lobbies(hosts, teams)
    logger.info(host_to_teams)

    assert len(host_to_teams) == 2
    assert 1000 in host_to_teams
    assert 1001 in host_to_teams
    assert len(host_to_teams[1000]) == 18
    assert len(host_to_teams[1001]) == 18


@pytest.mark.parametrize(
    "team_list",
    [
        #rating, team_size, host_on_team, lobby_host_id

        # small test, two solos, same lobby
        [
        (1000, 1, True, 1010),
        (1000, 1, False, 1010),
        ],

        # 27 players, one host, one team not in the lobby
        [
        (1000, 3, True, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, None),
        ],

        # 33 players, one host, 3 teams not in the lobby
        [
        (1000, 3, True, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, 1010),
        (1000, 3, False, None),
        (1000, 3, False, None),
        (1000, 3, False, None),
        ],        

        # 33 players, 2 hosts
        [
        (2000, 3, True, 1010),
        (1900, 3, True, 1020),
        (1800, 3, False, 1020),
        (1700, 3, False, 1010),
        (1600, 3, False, 1010),
        (1500, 3, False, 1020),
        (1400, 3, False, 1020),
        (1300, 3, False, 1010),
        (1200, 3, False, 1010),
        (1100, 3, False, 1020),
        (1000, 3, False, 1020),
        ],         


        # same as above but jumbled teams below hosts
        [
        (2000, 3, True, 1010),
        (1900, 3, True, 1020),
        (1100, 3, False, 1020),
        (1700, 3, False, 1010),
        (1800, 3, False, 1020),
        (1000, 3, False, 1020),
        (1500, 3, False, 1020),
        (1300, 3, False, 1010),
        (1600, 3, False, 1010),
        (1400, 3, False, 1020),
        (1200, 3, False, 1010),
        ],             


        # 51 players, 2 hosts, 1 team not in the lobby
        [
        (2000, 3, True, 1010),
        (1900, 3, True, 1020),
        (1800, 3, False, 1020),
        (1700, 3, False, 1010),
        (1600, 3, False, 1010),
        (1500, 3, False, 1020),
        (1400, 3, False, 1020),
        (1300, 3, False, 1010),
        (1200, 3, False, 1010),
        (1100, 3, False, 1020),
        (1000, 3, False, 1020),
        ( 900, 3, False, 1010),
        ( 800, 3, False, 1010),
        ( 700, 3, False, 1020),
        ( 600, 3, False, 1020),
        ( 500, 3, False, 1010),
        ( 400, 3, False, None),
        ],          

        # 51 players, 3 hosts
        [
        (2000, 3, True, 1010),
        (1900, 3, True, 1020),
        (1800, 3, True, 1030),
        (1700, 3, False, 1030),
        (1600, 3, False, 1020),
        (1500, 3, False, 1010),
        (1400, 3, False, 1010),
        (1300, 3, False, 1020),
        (1200, 3, False, 1030),
        (1100, 3, False, 1030),
        (1000, 3, False, 1020),
        ( 900, 3, False, 1010),
        ( 800, 3, False, 1010),
        ( 700, 3, False, 1020),
        ( 600, 3, False, 1030),
        ( 500, 3, False, 1030),
        ( 400, 3, False, 1020),
        ],        

        
        # 48 players, 2 hosts, many team sizes
        [
        (2000, 3, True, 1010),
        (1900, 3, True, 1020),
        (1800, 2, False, 1020),
        (1700, 3, False, 1010),
        (1600, 2, False, 1010),
        (1500, 3, False, 1020),
        (1400, 2, False, 1020),
        (1300, 3, False, 1010),
        (1200, 3, False, 1010),
        (1100, 2, False, 1020),
        (1000, 3, False, 1020),
        ( 900, 3, False, 1010),
        ( 800, 3, False, 1010),
        ( 700, 1, False, 1020),
        ( 600, 2, False, 1020),
        ( 500, 1, False, 1010), 
        ( 400, 3, False, 1010),
        ( 300, 1, False, 1020),
        ( 200, 2, False, 1020),
        ( 100, 1, False, 1020),
        (  50, 2, False, 1020),
        ],                    
    ],
)
def test_sort_lobbies3(gocog, session, team_list):
    godb = gocog.godb
    pfdb = gocog.pfdb
    gocog.godb.set_session_time(session_id=channel1, session_time=date1, session=session)
    
    teams = []
    exptected_lobby_host_id = {}
    for  team_id, (rating, team_size, host_on_team, lobby_host_id) in enumerate(team_list):
        
        # for whatever reason a 0th team is created somewhere
        team_id += 1

        exptected_lobby_host_id[team_id] = lobby_host_id
        du_list = []

        for i in range(team_size):
            player_id = 1000+team_id * 10 + i
            pf_player = PfPlayer(id=player_id, ign=f"ign{player_id}", \
                                 account_created=datetime.now(), last_login=datetime.now())
            pfdb.create_player(player=pf_player, session=session)
            
            official_rating = GoRatings(pf_player_id=pf_player.id, season=_config.go_season, rating_type="official", go_rating=rating/team_size)
            session.add(official_rating)
            
            du = DiscordUser(id=player_id, name=f"du{player_id}")
            du_list.append(du)

            go_player = gocog.do_set_ign(player=du, ign=pf_player.ign, session=session)

            if i==0 and host_on_team:
                godb.set_host(player_id, channel1, "confirmed", session)

        signup = gocog.do_signup(players=du_list, team_name=f"tname{team_id}", session_id=channel1, session=session)
        teams.append(signup.team)

    hosts = godb.get_hosts(session_id=channel1, session=session)

    print(f"{exptected_lobby_host_id =}")
    print(f"{hosts =}")
    print(f"{teams =}")

    host_to_teams = gocog.do_sort_lobbies(hosts, teams)

    team_ids = set()
    for host_id, teams in host_to_teams.items():
        for team in teams:
            assert team.id not in teams
            team_ids.add(team.id)
            assert exptected_lobby_host_id[team.id] == host_id     
    
    for team_id, host_id in exptected_lobby_host_id.items():
        if host_id is None:
            assert team_id not in team_ids
        else:
            assert team_id in team_ids
        