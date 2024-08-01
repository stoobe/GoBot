from datetime import datetime

import pytest
from sqlalchemy.exc import InvalidRequestError

from config import _config 
from go.bot.exceptions import DiscordUserError
from go.bot.go_cog import DiscordUser
from go.bot.playfab_api import as_player_id

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


@pytest.mark.asyncio
async def test_channel_without_date_set(interaction_owner, gocog, du1, dates):
    i = interaction_owner

    await gocog.rename_team.callback(gocog, i, "team_name")
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.signup.callback(gocog, i, "team_name", du1)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.change_signup.callback(gocog, i, "team_name", du1)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.cancel.callback(gocog, i)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.list_teams.callback(gocog, i)
    i.assert_msg_count("Error: no session set up on channel")

    ## ADMIN COMMANDS:

    await gocog.sort_lobbies.callback(gocog, i)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.admin_set_ign.callback(gocog, i, du1, "new_ign")

    await gocog.admin_cancel.callback(gocog, i, du1)
    i.assert_msg_count("Error: no session set up on channel")

    # This command is supposed tow ork without a session set up
    # await gocog.set_session_time.callback(gocog, i, str(dates[0]))

    await gocog.get_session_time.callback(gocog, i)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.session_set_open.callback(gocog, i)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.session_set_closed.callback(gocog, i)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.session_set_change_only.callback(gocog, i)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.set_host.callback(gocog, i, du1)
    i.assert_msg_count("Error: no session set up on channel")

    await gocog.remove_host.callback(gocog, i, du1)
    i.assert_msg_count("Error: no session set up on channel")


@pytest.mark.asyncio
async def test_admin_permissions(interaction1, gocog, du1, du2, dates):
    i = interaction1

    await gocog.rename_team.callback(gocog, i, "new_team_name", du2)
    i.assert_msg_count("You dont have permission to use this command for other players")

    await gocog.sync_commands.callback(gocog, i)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.sort_lobbies.callback(gocog, i)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.wipe_commands.callback(gocog, i)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.admin_set_ign.callback(gocog, i, du1, "new_ign")
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.admin_cancel.callback(gocog, i, du1)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.set_session_time.callback(gocog, i, str(dates[0]))
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.get_session_time.callback(gocog, i)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.session_set_open.callback(gocog, i)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.session_set_closed.callback(gocog, i)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.session_set_change_only.callback(gocog, i)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.set_host.callback(gocog, i, du1)
    i.assert_msg_count("You dont have permission to use this command.")

    await gocog.remove_host.callback(gocog, i, du1)
    i.assert_msg_count("You dont have permission to use this command.")


@pytest.mark.asyncio
async def test_set_ign(interaction1, gocog, pf_p1, stats_p1_1, du1, session):
    gocog.pfdb.create_player(player=pf_p1, session=session)
    gocog.pfdb.add_career_stats(stats=stats_p1_1, session=session)
    gocog.set_rating_if_needed(pf_p1.id, session, season=_config.go_season)
    await gocog.set_ign.callback(gocog, interaction1, pf_p1.ign)
    print(interaction1.response.last_message)
    interaction1.assert_msg_count(f'IGN for {interaction1.user.name} set to "{pf_p1.ign}"')
    session.rollback()


@pytest.mark.asyncio
async def test_player_info(interaction1, gocog_preload_teams, du1):
    i = interaction1
    gocog = gocog_preload_teams
    await gocog.player_info.callback(gocog, i, du1)
    i.assert_msg_count(f"- IGN: ")
    i.assert_msg_count(f"- Teams:")
    i.assert_msg_count(f"- Sessions:")


@pytest.mark.asyncio
async def test_rename_team(interaction1, interaction_owner, gocog_preload_teams, du1, du2):
    gocog = gocog_preload_teams
    gocog.dms_enabled = False
    await gocog.rename_team.callback(gocog, interaction1, "new_team_name")
    interaction1.assert_msg_regx("Team name changed to new_team_name")

    # this one shoul fail -- du1 (interaction1) trying to rename team for du2
    await gocog.rename_team.callback(gocog, interaction1, "new_team_name", du2)
    interaction1.assert_msg_regx("You dont have permission to use this command for other players")

    # interaction_owner is allowed to do this though
    await gocog.rename_team.callback(gocog, interaction_owner, "how many possible names are there", du1)
    interaction_owner.assert_msg_regx("Team name changed to how many possible names are there")


@pytest.mark.asyncio
async def test_signup(interaction1, gocog_preload_teams, du2):
    gocog = gocog_preload_teams
    i = interaction1
    gocog.dms_enabled = False
    await gocog.signup.callback(gocog, i, "team_name", du2)
    i.assert_msg_count(f'Signed up "team_name" for')
    i.assert_msg_count(f"\n- Players: ")
    i.assert_msg_count(f"\n- This is signup #")


@pytest.mark.asyncio
async def test_change_signup(interaction1, gocog_preload_teams, du2, du3):
    gocog = gocog_preload_teams
    i = interaction1
    gocog.dms_enabled = False
    await gocog.change_signup.callback(gocog, i, du2, du3, None, "another_name")
    i.assert_msg_count(f'Cancelled "')
    i.assert_msg_count(f'Signed up "another_name" for')
    i.assert_msg_count(f"\n- Players: ")
    i.assert_msg_count(f"\n- This is signup #")


@pytest.mark.asyncio
async def test_cancel(interaction1, gocog_preload_teams, du1):
    gocog = gocog_preload_teams
    gocog.dms_enabled = False
    await gocog.cancel.callback(gocog, interaction1)
    interaction1.assert_msg_regx('Cancelled ".*" for session on ')


@pytest.mark.asyncio
async def test_sub(interaction1, gocog, du1):
    await gocog.sub.callback(gocog, interaction1)
    interaction1.assert_msg_count(f"GO League doesn't have subs")


@pytest.mark.asyncio
async def test_list_teams(interaction1, gocog_preload_teams, du1):
    gocog = gocog_preload_teams
    await gocog.list_teams.callback(gocog, interaction1)
    interaction1.assert_msg_count(f"teams:")
    interaction1.assert_msg_count(f"players:")
    interaction1.assert_msg_count("\nA: ")


@pytest.mark.asyncio
async def test_list_schedule(interaction1, gocog_preload_teams, du1):
    gocog = gocog_preload_teams
    await gocog.list_schedule.callback(gocog, interaction1)
    interaction1.assert_msg_regx("^<.*> -- . teams  . players")


@pytest.mark.asyncio
async def test_coin_flip(interaction1, gocog):
    i = interaction1

    for _ in range(20):
        await gocog.flip_coin.callback(gocog, i, None)
        interaction1.assert_msg_regx("Coin flip: (Heads|Tails)")

    for _ in range(20):
        await gocog.flip_coin.callback(gocog, i, 3)
        interaction1.assert_msg_regx("Random number between 1 and 3: (1|2|3)")
