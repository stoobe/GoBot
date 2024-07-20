from __future__ import annotations

import random
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional, Union

import discord
from dateutil import parser
from discord import app_commands
from discord.ext import commands
from pydantic import BaseModel
from sqlmodel import Session, delete, select
import pprint

import _config
from go.bot.exceptions import DiscordUserError, ErrorCode, GoDbError
from go.bot.go_bot import GoBot
from go.bot.go_db import GoDB, GoTeamPlayerSignup
from go.bot.logger import create_logger
from go.bot.models import (
    GoHost,
    GoLobby,
    GoPlayer,
    GoRatings,
    GoRoster,
    GoSession,
    GoSignup,
    GoTeam,
)
from go.bot.playfab_api import as_player_id, as_playfab_id, is_playfab_str
from go.bot.playfab_db import PlayfabDB

MY_GUILD = discord.Object(id=_config.guild_id)

logger = create_logger(__name__)


def time_str(dt: datetime) -> str:
    return dt.strftime("%a %b %-d at %-I:%M %p")


def get_name(member: Union[discord.Member, discord.User, None]) -> str:
    if member is None:
        return ""
    for attr in ["nick", "global_name", "display_name", "name"]:
        if hasattr(member, attr):
            val = getattr(member, attr)
            if val:
                return val
    else:
        raise Exception(f"in get_name no attributes had a value for {member}")


def escmd(text: str) -> str:
    """Escape markdown characters in text."""
    return text.replace("*", "\\*").replace("_", "\\_").replace("~", "\\~").replace("`", "\\`")


def increment_team_name(team_name: str) -> str:
    team_name_base = team_name.rstrip("0123456789")
    n = 1
    if team_name != team_name_base:
        n = int(team_name[len(team_name_base) :])
    team_name2 = f"{team_name_base.strip()} {n+1}"
    return team_name2


class DiscordUser(BaseModel):
    id: int
    name: str


def convert_user(user: Union[discord.Member, discord.User]):
    return DiscordUser(id=user.id, name=get_name(user))


class GoCog(commands.Cog):

    go_group = app_commands.Group(name="go", description="GO League Commands")
    admin_group = app_commands.Group(name="goadmin", description="GO Admin Commands")

    #
    def __init__(self, bot: commands.Bot) -> None:
        # if not isinstance(bot, GoBot):
        #     raise TypeError(f"GoCog must be initialized with a GoBot instance, not {type(bot)}")
        self.bot = bot
        self.engine = bot.engine  # type: ignore
        self.godb: GoDB = bot.godb  # type: ignore
        self.pfdb: PlayfabDB = bot.pfdb  # type: ignore

        self.dms_enabled = True
        self.dm_queue = []

    #
    def set_rating_if_needed(self, pf_player_id, session, season: str) -> Optional[float]:
        # make sure the player has a rating
        # if not pull one in from recent career stats
        go_rating = self.godb.get_official_rating(pf_player_id, session, season)

        if go_rating is None:
            go_rating = self.pfdb.calc_rating_from_stats(pf_player_id=pf_player_id, session=session)

            if not go_rating:
                logger.error(f"In get_rating_default -- calc_rating_from_stats failed for id {pf_player_id}")
                return None
            else:
                official_rating = GoRatings(
                    pf_player_id=pf_player_id,
                    season=_config.go_season,
                    rating_type="official",
                    go_rating=go_rating,
                )
                logger.info(
                    f"In get_rating_default -- setting go_rating for {pf_player_id} to {go_rating:,.2f} from career stats"
                )
                session.add(official_rating)
                # session.commit()

        return go_rating

    #
    def do_set_ign(self, player: DiscordUser, ign: str, session: Session) -> GoPlayer:

        # if GoPlayer doesn't exist create it
        if not self.godb.player_exists(discord_id=player.id, session=session):
            go_p = GoPlayer(discord_id=player.id, discord_name=player.name)  # type: ignore
            session.add(go_p)

        go_p = self.godb.read_player(discord_id=player.id, session=session)
        assert go_p is not None

        # check if the ign has already been set (discord_id has associated playfab player_id)
        if go_p.pf_player_id is not None:
            pf_p = self.pfdb.read_player(pf_player_id=go_p.pf_player_id, session=session)
            msg = f"IGN for {player.name} already set to {pf_p.ign if pf_p else None}"
            raise DiscordUserError(msg)

        # lookup the playfab_player by ign
        # limit to one more than we'd return so we can tell the user if there are more
        pf_p = None
        pf_players = self.pfdb.read_players_by_ign(ign=ign, session=session, limit=11)

        if len(pf_players) > 1:
            msg = f'Found {len(pf_players)} players with IGN = "{ign}".  You can run `/go set_ign` with the playfab ID instead of the IGN to select your account.'
            if len(pf_players) > 10:
                pf_players = pf_players[:10]
                msg += "\nHere are the first 10:"
            for p in pf_players:
                if len(p.career_stats) == 0:
                    continue
                stats = p.career_stats[-1]
                # *(as of {stats.date.date()})*'
                msg += f"\n* **{p.ign}** -- playfab ID= **{as_playfab_id(p.id)}**  games={stats.games:,.0f}  wr={stats.calc_wr()*100:.0f}%  kpg={stats.calc_kpg():.1f}"
            raise DiscordUserError(msg, code=ErrorCode.MISC_ERROR)
        elif len(pf_players) == 1:
            pf_p = pf_players[0]
        elif is_playfab_str(ign):
            pf_player_id = as_player_id(ign)
            pf_p = self.pfdb.read_player(pf_player_id=pf_player_id, session=session)

        if pf_p is None:
            msg = f'Could not find a Population One account with IGN = "{ign}"'
            raise DiscordUserError(msg, code=ErrorCode.IGN_NOT_FOUND)

        if pf_p.go_player is not None:
            msg = f'This IGN is allready associated with Discord user = "{pf_p.go_player.discord_name}"'
            raise DiscordUserError(msg, code=ErrorCode.MISC_ERROR)

        go_p.pf_player_id = pf_p.id
        session.add(go_p)

        session.commit()
        return go_p

    #
    # Interact with user via Discord API
    # Calls do_set_ign and set_rating_if_needed
    # Put in it's own function so regular and admin set_ign can reuse it
    #
    async def handle_set_ign(self, func_name: str, interaction: discord.Interaction, player: DiscordUser, ign: str):
        logger.info(f"Running {func_name}({player.name}, {ign})")
        try:
            with Session(self.engine) as session:

                go_p = self.do_set_ign(player=player, ign=ign, session=session)
                if go_p.pf_player_id is None or go_p.pf_player is None:
                    msg = f"Could not set the IGN for {player.name}."
                    raise DiscordUserError(msg, code=ErrorCode.MISC_ERROR)

                go_rating = self.set_rating_if_needed(go_p.pf_player_id, session, season=_config.go_season)
                if go_rating is None:
                    msg = f"Could not find a go_rating for {ign}.  Reach out to @GO_STOOOBE to help fix this."
                    raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)

                session.commit()

                go_rating = self.godb.get_official_rating(go_p.pf_player_id, session, season=_config.go_season)
                msg = f'IGN for {player.name} set to "{go_p.pf_player.ign}" with GO Rating {go_rating:,.0f}'

                stats = go_p.pf_player.career_stats[-1]
                msg += f"\n* Account created on {go_p.pf_player.account_created.date()}"
                msg += f"\n* Career Stats: games={stats.games}, win rate={100.0*stats.wins/stats.games:.0f}%, kpg={stats.kills/stats.games:.1f}"

                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @go_group.command(name="set-ign", description="Set your In Game Name")
    async def set_ign(self, interaction: discord.Interaction, ign: str):
        player = convert_user(interaction.user)
        await self.handle_set_ign("set_ign", interaction, player, ign)

    #
    def do_player_info(self, player: DiscordUser) -> str:
        with Session(self.engine) as session:
            go_p = self.godb.read_player(discord_id=player.id, session=session)
            if go_p is None or go_p.pf_player_id is None or go_p.pf_player is None:
                msg = f"{player.name} is not registered with GoBot"
            else:
                msg = f"- IGN: {go_p.pf_player.ign}\n"

                player_rating = self.godb.get_official_rating(go_p.pf_player_id, session, season=_config.go_season)
                msg += f"- GO Rating: {player_rating if player_rating else 0.0:,.0f}\n"

                msg += f"- Playfab ID: {as_playfab_id(go_p.pf_player_id)}\n"

                signups: List[GoSignup] = []
                teams = [r.team for r in go_p.rosters]
                msg += f"- Teams:\n"
                for team in teams:
                    # incase it's missing from the DB for some reason
                    team_rating = team.team_rating or 0
                    igns = sorted([r.player.pf_player.ign for r in team.rosters])
                    msg += f'  - {escmd(team.team_name)} *({team.team_rating:,.0f})* -- {len(team.signups)} signups -- {", ".join([escmd(_) for _ in igns])}\n'
                    for signup in team.signups:
                        signups.append(signup)

                signups.sort(key=lambda su: su.session.session_time)
                msg += f"- Sessions:\n"
                for signup in signups:
                    msg += f"  - {time_str(signup.session.session_time)} -- {escmd(signup.team.team_name)}\n"

            return msg

    #
    @go_group.command(name="player-info", description="Get info for a player")
    async def player_info(
        self,
        interaction: discord.Interaction,
        user: Union[discord.Member, discord.User, None] = None,
    ):
        self.log_command(interaction)

        if user is None:
            user = interaction.user

        player = convert_user(user)

        try:
            msg = self.do_player_info(player)
            logger.info(msg)
            await interaction.response.send_message(msg, ephemeral=True)
        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message, ephemeral=True)

    #
    def do_rename_team(self, new_team_name: str, player: DiscordUser, session_id: int, session: Session) -> GoTeam:
        tpsignups = self.godb.read_player_signups(session=session, discord_id=player.id, session_id=session_id)
        if len(tpsignups) == 0:
            msg = f"Player {player.name} is not signed up on in this session."
            raise DiscordUserError(msg)

        assert len(tpsignups) == 1

        team = tpsignups[0].team
        team.team_name = new_team_name
        session.add(team)
        session.commit()
        return team

    #
    @go_group.command(name="rename-team", description="Rename your team in this session")
    async def rename_team(
        self,
        interaction: discord.Interaction,
        new_team_name: str,
        player: Optional[discord.Member] = None,
    ):
        self.log_command(interaction)

        if player is not None:
            if interaction.user.id != _config.owner_id:
                logger.warning(f"User {get_name(interaction.user)} tried to run rename_team for another player")
                await interaction.response.send_message(
                    "You dont have permission to use this command for other players"
                )
                return
        else:
            player = interaction.user  # type: ignore

        try:
            with Session(self.engine) as session:
                gosession = self.require_gosession(interaction, session)
                assert interaction.channel_id is not None

                p = convert_user(player)  # type: ignore
                logger.info(f"Running rename_team({p.name}, {new_team_name}, {interaction.channel})")  # type: ignore

                team = self.do_rename_team(new_team_name, p, session_id=interaction.channel_id, session=session)
                msg = f"Team name changed to {team.team_name}"
                logger.info(msg)
                await interaction.response.send_message(msg)
        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    def do_signup(
        self,
        players: List[Optional[DiscordUser]],
        team_name: str,
        session_id: int,
        session: Session,
        signup_time: Optional[datetime] = None,
    ) -> GoSignup:

        # make sure no players were skipped
        none_seen_at = None
        for i, p in enumerate(players):
            if p is not None and none_seen_at is not None:
                msg = f"Player{i+1} specified but Player{none_seen_at+1} was not."
                raise DiscordUserError(msg)
            if p is None:
                none_seen_at = i

        players = [p for p in players if p is not None]
        if len(players) == 0:
            msg = f"Must specify players for team."
            raise DiscordUserError(msg)

        go_players = []
        discord_ids = set()
        players_to_set_ign = []

        for player in players:
            if player is None:
                continue
            discord_ids.add(player.id)
            go_player = self.godb.read_player(discord_id=player.id, session=session)
            go_players.append(go_player)
            if go_player is None or go_player.pf_player is None:
                # store the players that need to set their IGN
                # so we can tell them all at once
                players_to_set_ign.append(player)
            else:
                # make sure all players have ratings
                player_rating = self.godb.get_official_rating(go_player.pf_player_id, session, season=_config.go_season)
                if player_rating is None:
                    msg = f"Player {player.name} does not have a GO Rating. Contact @GO_STOOOBE to help fix this."
                    raise DiscordUserError(msg)

        if players_to_set_ign:
            msg = ""
            for player in players_to_set_ign:
                msg += f"- Player {player.name} needs to run `/go set_ign`.\n"
            raise DiscordUserError(msg)

        if len(discord_ids) < len(players):
            msg = f"A player cannot be on the same team twice."
            raise DiscordUserError(msg)

        if team_name is None:
            team_name = f"team {random.randint(1000, 9999)}"

        team = self.godb.read_team_with_roster(discord_ids=discord_ids, session=session)

        # if the roster exists with a different team_name then use the previous name
        if team and team.team_name != team_name:
            team_name = team.team_name
            logger.info(f'In do_signup: team already has name "{team_name}".  Using that name instead.')

        # loop until we find a unique team name
        # or we've tried too many times
        team_name_orig = team_name
        n = 0
        while True:
            n += 1
            go_team_by_name = self.godb.read_team_with_name(team_name=team_name, session=session)

            if not go_team_by_name:
                # no team with team_name exists
                break
            elif go_team_by_name is team:
                # teams are the same
                break
            else:
                # go_team_by_name is not None and is not the same as go_team_by_roster
                # therefore increment the team name and try again
                team_name = increment_team_name(team_name)

            if n > 20:
                msg = f'Team name "{team_name_orig}" is already taken.'
                raise DiscordUserError(msg)

        # if it's an existing team
        if team:
            # already signed up for today?
            session_ids = [_.session_id for _ in team.signups]
            if session_id in session_ids:
                msg = f'Team "{team_name}" is already signed up for this session.'
                raise DiscordUserError(msg)

            # signed up for too many dates?
            if len(session_ids) >= 4:
                msg = f'Team "{team_name}" is already signed up for {len(session_ids)} dates (max is 4).'
                raise DiscordUserError(msg)

        rating_limit = _config.go_rating_limits.get(len(go_players), None)

        try:
            # if it's a new team
            if team is None:
                team = self.godb.create_team(
                    team_name=team_name,
                    go_players=go_players,
                    session=session,
                    rating_limit=rating_limit,
                    season=_config.go_season,
                )

            if team is None:
                msg = f"Could not create team in DB"
                raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)

            signup = self.godb.add_signup(team=team, session_id=session_id, session=session, signup_time=signup_time)

            # compose DM's for each signed up player
            date = self.godb.get_session_time(session_id, session)
            if date:
                ats = [f"<@{r.player.discord_id}>" for r in team.rosters]
                msg = f'✅ You\'ve been signed up for GO League on team "{team.team_name}".'
                msg += f"\n- Session Time: **{time_str(date)}**"
                msg += f"\n- Roster: {', '.join(ats)}"
                msg += f"\n- Team Signup #{len(team.signups)}"
                msg += f"\n- Make changes to your signup here: <#{session_id}>"
                for r in team.rosters:
                    self.dm_queue.append((r.player.discord_id, msg))

        except GoDbError as err:
            # godb.add_signup checks that the players aren't on a different team that day
            # convert that error to this one we expect to throw
            raise DiscordUserError(err.args[0])

        return signup

    #
    @go_group.command(description="Sign up a team for this session")
    async def signup(
        self,
        interaction: discord.Interaction,
        team_name: str,
        player1: discord.Member,
        player2: Optional[discord.Member] = None,
        player3: Optional[discord.Member] = None,
    ):
        self.log_command(interaction)

        try:

            with Session(self.engine) as session:
                self.dm_queue.clear()

                gosession = self.require_gosession(interaction, session)
                assert interaction.channel_id is not None

                gosession = self.godb.get_session(interaction.channel_id, session)
                assert gosession
                if gosession.signup_state != "open":
                    msg = "Signups are not open for this session."
                    raise DiscordUserError(msg)

                players: List[Optional[DiscordUser]] = [convert_user(player1)]
                players.append(None if not player2 else convert_user(player2))
                players.append(None if not player3 else convert_user(player3))

                if team_name:
                    team_name = team_name.strip()

                signup = self.do_signup(
                    players=players, team_name=team_name, session_id=interaction.channel_id, session=session
                )
                session.commit()
                session.refresh(signup.team)
                team = signup.team

                igns = [r.player.pf_player.ign for r in team.rosters]
                msg = f'Signed up "{team.team_name}" for {time_str(gosession.session_time)}'
                msg += f'\n- Players: {", ".join(igns)}.'
                msg += f"\n- This is signup #{len(team.signups)} for the team."
                logger.info(msg)
                await interaction.response.send_message(msg)

                await self.send_dms()

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    def do_change_signup(
        self,
        player,
        players: List[Optional[DiscordUser]],
        new_team_name: str | None,
        session_id: int,
        session: Session,
    ) -> str:
        # do_cancel will return the signup.team that the player is
        # signed up for on date.  If not signed up it will throw an error.
        signup = self.do_cancel(player=player, session_id=session_id, session=session)
        original_time = signup.signup_time
        old_team_name = signup.team.team_name

        if new_team_name:
            new_team_name = new_team_name.strip()
        else:
            new_team_name = signup.team.team_name

        if new_team_name is None:
            new_team_name = f"team {random.randint(1000, 9999)}"

        signup = self.do_signup(
            players=players, team_name=new_team_name, session_id=session_id, session=session, signup_time=original_time
        )

        team = signup.team
        session.commit()
        session.refresh(team)

        igns = [r.player.pf_player.ign for r in team.rosters]

        msg = f'Cancelled "{old_team_name}" for this session.'
        msg += "\n"
        msg += f'Signed up "{team.team_name}" for this session.'
        msg += f'\n- Players: {", ".join(igns)}.'
        msg += f"\n- This is signup #{len(team.signups)} for the team."
        logger.info(msg)
        return msg

    #
    @go_group.command(name="change-signup", description="Change the players in your signup and keep your spot in line")
    async def change_signup(
        self,
        interaction: discord.Interaction,
        player1: discord.Member,
        player2: Optional[discord.Member] = None,
        player3: Optional[discord.Member] = None,
        new_team_name: Optional[str] = None,
    ):
        try:
            self.log_command(interaction)

            with Session(self.engine) as session:
                session.begin()
                self.dm_queue.clear()

                gosession = self.require_gosession(interaction, session)
                assert interaction.channel_id is not None

                if gosession.signup_state == "closed":
                    msg = "Signups are closed for this session."
                    raise DiscordUserError(msg)

                # player may or may not be on the new team
                # but player (the user running the command) must
                # be on the team being cancelled
                player = convert_user(interaction.user)
                players: List[Optional[DiscordUser]] = [convert_user(player1)]
                players.append(convert_user(player2) if player2 else None)
                players.append(convert_user(player3) if player3 else None)

                msg = self.do_change_signup(player, players, new_team_name, interaction.channel_id, session)
                session.commit()

                logger.info(msg)
                await interaction.response.send_message(msg)
                await self.send_dms()

        except DiscordUserError as err:
            session.rollback()
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    # Does NOT commit or refresh
    #
    def do_cancel(self, player: DiscordUser, session_id: int, session: Session) -> GoSignup:
        signup = self.godb.get_signup_for_session(player.id, session_id, session)
        if signup is None:
            msg = f"Player {player.name} is not signed up for this session."
            raise DiscordUserError(msg)

        signup_count_before = len(signup.team.signups)

        discord_ids = [r.player.discord_id for r in signup.team.rosters]
        date = self.godb.get_session_time(session_id, session)
        datestr = "" if date is None else f" on **{time_str(date)}**"
        msg = f'❌ Your signup for team "{signup.team.team_name}"{datestr} has been **cancelled**. '
        msg += f"\n- {signup_count_before-1} signups still active for the team."

        logger.info(f"cancel signup {signup}")
        session.delete(signup)

        # if this was the last signup for the team
        # delete the team too
        if signup_count_before == 1:
            session.delete(signup.team)

        for did in discord_ids:
            self.dm_queue.append((did, msg))

        return signup

    #
    # interact with user via Discord API
    async def handle_cancel(self, func_name: str, interaction: discord.Interaction, player: DiscordUser):
        logger.info("")
        logger.info(f"{func_name} names ({interaction.channel}, {player.name})")
        logger.info(f"{func_name} ids   ({interaction.channel_id}, {player.id})")

        try:
            with Session(self.engine) as session:
                self.dm_queue.clear()

                gosession = self.require_gosession(interaction, session)
                assert interaction.channel_id is not None

                if gosession.signup_state == "closed" and func_name != "admin_cancel":
                    msg = "Signups are closed for this session."
                    raise DiscordUserError(msg)

                signup = self.do_cancel(player=player, session_id=interaction.channel_id, session=session)

                team_id = signup.team.id
                team_name = signup.team.team_name
                session.commit()

                team = self.godb.read_team(team_id=team_id, session=session)
                signups_remaining = 0
                if team:
                    signups_remaining = len(team.signups)

                msg = f'Cancelled "{team_name}" for session on {time_str(gosession.session_time)}.'
                msg += f"\nThere are {signups_remaining} signups still active for the team."
                logger.info(msg)
                await interaction.response.send_message(msg)
                await self.send_dms()

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @go_group.command(description="Cancel your signup for this session")
    async def cancel(self, interaction: discord.Interaction):
        self.log_command(interaction)
        player = convert_user(interaction.user)
        await self.handle_cancel("cancel", interaction, player)

    #
    @go_group.command(description="GO League doesn't have subs. Use /go change_signup")
    async def sub(self, interaction: discord.Interaction):
        self.log_command(interaction)
        msg = "GO League doesn't have subs\n"
        msg += "- Every new combo of players is a new team.\n"
        msg += "- Use `/go change_signup` to signup a different team for a session while keeping your orignial signup time."
        logger.info(msg)
        await interaction.response.send_message(msg)

    #
    @go_group.command(name="list-teams", description="List the teams signed up this session")
    async def list_teams(self, interaction: discord.Interaction):
        try:
            self.log_command(interaction)

            with Session(self.engine) as session:
                msg = ""
                gosession = self.require_gosession(interaction, session)
                assert interaction.channel_id is not None

                await interaction.response.defer()

                statement = select(GoHost).where(GoHost.session_id == gosession.id)
                statement = statement.where(GoHost.status == "confirmed")
                hosts = session.exec(statement).all()

                teams = self.godb.get_teams_for_session(session_id=interaction.channel_id, session=session)
                msg = ""
                player_count = 0
                for i, team in enumerate(teams):
                    session.refresh(team)
                    players = [r.player for r in team.rosters]
                    players_str = ""
                    for p in players:
                        player_count += 1
                        session.refresh(p.pf_player)
                        if players_str:
                            players_str += ", "
                        players_str += escmd(p.pf_player.ign)
                    rating_str = f"{team.team_rating:,.0f}" if team.team_rating else "None"
                    msg += f"{chr(ord('A')+i)}: **{escmd(team.team_name)}** (*{rating_str}*) -- {players_str}\n"

                header = f"**teams:** {len(teams)}"
                header += f"\n**players:** {player_count}"
                header += f"\n**hosts:** {', '.join([f'<@{h.host_did}>' for h in hosts])}"
                header += f"\n\n"
                msg = header + msg

                logger.info(msg)
                # await interaction.response.send_message(msg)
                await interaction.followup.send(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @go_group.command(name="list-schedule", description="List the schedule.")
    async def list_schedule(self, interaction: discord.Interaction):
        try:
            self.log_command(interaction)

            with Session(self.engine) as session:

                statement = select(GoSession).order_by(GoSession.session_time)  # type: ignore
                sessions: List[GoSession] = session.exec(statement).all()  # type: ignore
                msg = ""
                for s in sessions:
                    # skip the dev channel
                    if s.id == 1127111098290675864:
                        #unless we're in the dev channel
                        if interaction.channel_id != 1127111098290675864:
                            continue
                    player_count = 0
                    for signup in s.signups:
                        player_count += signup.team.team_size
                    state_str = ""
                    if s.signup_state != "closed":
                        state_str = f" (signups *{s.signup_state}*)"
                    msg += f"<#{s.id}> -- {len(s.signups)} teams  {player_count} players{state_str}\n"
                
                if not msg:
                    msg = "No sessions found."
                    
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @go_group.command(name="flip-coin", description="Flip a coin or random number generator between 1 and random_num.")
    async def flip_coin(self, interaction: discord.Interaction, random_num: Optional[int] = None):
        try:
            self.log_command(interaction)

            if random_num is not None:
                if random_num < 1:
                    msg = "Random number must be greater than 0."
                    raise DiscordUserError(msg)
                result = random.randint(1, random_num)
                msg = f"Random number between 1 and {random_num}: {result}"
            else:
                result = random.choice(["Heads", "Tails"])
                msg = f"Coin flip: {result}"

            logger.info(msg)
            await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @admin_group.command(name="sync-commands", description="Syncs bot commands")
    async def sync_commands(self, interaction: discord.Interaction):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            await interaction.response.send_message("Sync starting.")
            self.bot.tree.copy_global_to(guild=MY_GUILD)
            await self.bot.tree.sync(guild=MY_GUILD)

            await interaction.user.send("Command tree synced.")
            logger.info("Command tree synced.")
        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    def get_lobby_count(self, player_count):
        if player_count == 0:
            msg = "No players signed up for this session."
            raise DiscordUserError(msg)
        elif player_count < 30:
            lobbies_needed = 1
        elif player_count <= 48:
            lobbies_needed = 2
        else:
            lobbies_needed = 3
        return lobbies_needed

    #
    def snake_draft_inc(self, i: int, counting_up: bool, max_i: int) -> tuple[int, bool]:
        if counting_up:
            if i == max_i - 1:
                counting_up = False
            else:
                i += 1
        else:
            if i == 0:
                counting_up = True
            else:
                i -= 1
        return i, counting_up

    #
    # Accepts teams in signup order (lower index is earlier signup)
    def do_sort_lobbies(self, hosts: List[GoHost], teams: List[GoTeam]) -> Dict[int, List[GoTeam]]:

        player_count = sum([t.team_size for t in teams])
        lobby_count = self.get_lobby_count(player_count)
        host_dids = {h.host_did for h in hosts}

        print(f"{player_count = }")
        print(f"{host_dids = }")

        hosts_on_teams = set()
        team_to_host: Dict[int, int] = {}
        for team in teams:
            for r in team.rosters:
                if team.id and r.player.discord_id in host_dids:
                    team_to_host[team.id] = r.player.discord_id
                    hosts_on_teams.add(r.player.discord_id)
        
        hosts_not_on_teams = host_dids - hosts_on_teams
        possible_host_count = len(hosts_not_on_teams) + len(team_to_host)

        print(f'{hosts_on_teams = }')
        print(f'{hosts_not_on_teams = }')
        print(f'{possible_host_count = }')

        # check team_to_host b/c two hosts on the same team only count
        # as one host
        if possible_host_count < lobby_count:
            lobby_count = possible_host_count
            # msg = f"Error: Not enough hosts ({len(team_to_host)}) for the number of lobbies needed ({lobby_count})."
            # raise DiscordUserError(msg)
        
        max_players = lobby_count * 24
        print(f'{lobby_count = }')
        print(f'{max_players = }')

        # filter in/out which teams signed up early enough to play
        teams_in = []
        teams_out = []
        player_count_in = 0
        for team in teams:
            if player_count_in + team.team_size > max_players:
                teams_out.append(team)
            else:
                teams_in.append(team)
                player_count_in += team.team_size

        i = 0
        counting_up = True  # snake draft direction
        lobby_to_nplayers = defaultdict(int)
        lobby_to_teams = defaultdict(list)
        lobby_to_host: Dict[int, int] = {}

        # highest rating at end of queue
        teams_in_queue = sorted(teams_in, key=lambda t: t.team_rating, reverse=True)

        j = 0
        n_failed_to_fit = 0
        while len(teams_in_queue):

            if j == len(teams_in_queue):
                # if we cant fit any more teams into lobby i
                # then advance to the next lobby and start at j=0 again
                j = 0
                n_failed_to_fit += 1
                i, counting_up = self.snake_draft_inc(i, counting_up, max_i=lobby_count)

                if n_failed_to_fit >= lobby_count * 2:
                    # if we've tried out all the lobbies and still cant fit
                    # then break out of the loop
                    break
                continue

            team: GoTeam = teams_in_queue[j]
            assert team.id is not None

            if lobby_to_nplayers[i] + team.team_size > 24:
                # if the team wont fit, skip it for now
                # look at the next team for the same lobby[i]
                j += 1
                continue

            # if team has a host on the roster
            if team.id in team_to_host: 
                # if we already have a host for this lobby
                if i in lobby_to_host:
                    # then look at the next team for this lobby
                    j += 1
                    continue
                else:
                    lobby_to_host[i] = team_to_host[team.id]

            # if the team fits in the lobby
            # remove it from the queue and reset j to the beginning
            # of the queue (the highest rated team remainig to sort)
            teams_in_queue.pop(j)
            j = 0
            lobby_to_nplayers[i] += team.team_size
            lobby_to_teams[i].append(team)
            i, counting_up = self.snake_draft_inc(i, counting_up, max_i=lobby_count)

        print("lobby_to_nplayers")
        pprint.pp(lobby_to_nplayers)
        print("lobby_to_hosts")
        pprint.pp(lobby_to_host)
        print("lobby_to_teams")
        pprint.pp(lobby_to_teams)

        # assert len(lobby_to_hosts) == lobby_count
        # for i in range(lobby_count):
        #     assert i in lobby_to_hosts
        #     assert i in lobby_to_teams

        # if the lobby doesn't have a host assigned
        # then assign one from the list of hosts not on a team
        for lobby_i in lobby_to_teams:
            if lobby_i not in lobby_to_host:
                lobby_to_host[lobby_i] = hosts_not_on_teams.pop()

        # change to the map key from lobby index to host id
        host_to_teams = {host_did: lobby_to_teams[lobby_i] for lobby_i, host_did in lobby_to_host.items()}

        return host_to_teams

    #
    @admin_group.command(name="sort-lobbies", description="Sort the teams in the session into lobbies.")
    async def sort_lobbies(self, interaction: discord.Interaction):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            with Session(self.engine) as session:
                await interaction.response.defer(ephemeral=True)

                gosession = self.require_gosession(interaction, session)
                assert interaction.channel_id

                lobbies, hosts, teams, signups = self.load_session_data(interaction, session)

                host_to_teams = self.do_sort_lobbies(hosts, teams)

                for host_did, teams in sorted(host_to_teams.items()):
                    print(f"host {host_did}")
                    for t in teams:
                        print(f"  {t}")

                self.upload_sorted_lobbies(gosession, lobbies, signups, host_to_teams, session)

                # reload the session data from the DB since it becomes invalidated after commmit
                lobbies, hosts, teams, signups = self.load_session_data(interaction, session)

                print("")
                print(" INFO ")
                print("")
                for h in hosts:
                    print(f"Host: {h}")
                print("")
                for su in signups:
                    print(f"Signup: {su}")
                print("")
                lobby_player_count = defaultdict(int)
                for l in lobbies:
                    print(f"Lobby: {l}")
                    print(f"  {l.host}")
                    print(f"  {l.session}")
                    print(f"  n signups: {len(l.signups)}")
                    for su in l.signups:
                        lobby_player_count[l.id] += su.team.team_size

                team_ids_assigned = set()
                msg = ""
                for i, lobby in enumerate(lobbies):
                    msg += f"## Lobby {i+1} hosted by <@{lobby.host_did}>\n"
                    msg += f"{len(lobby.signups)} teams, {lobby_player_count[lobby.id]}  players\n"
                    for j, signup in enumerate(sorted(lobby.signups, key=lambda _:  -1*_.team.team_rating)):
                        team_ids_assigned.add(signup.team.id)
                        igns = [r.player.pf_player.ign for r in signup.team.rosters]
                        msg += f"{chr(ord('A')+j)}: **{escmd(signup.team.team_name)}** *({signup.team.team_rating:,.0f})* -- {', '.join(igns)}\n"


                teams_not_assigned = [t for t in teams if t.id not in team_ids_assigned]
                if teams_not_assigned:
                    msg += f"## Waitlist:\n"
                    for j,team in enumerate(teams_not_assigned):
                        if team.id not in team_ids_assigned:
                            igns = [r.player.pf_player.ign for r in team.rosters]
                            msg += f"{chr(ord('A')+j)}: **{escmd(team.team_name)}** *({team.team_rating:,.0f})* -- {', '.join(igns)}\n"
                            j += 1

                await interaction.followup.send(msg, ephemeral=True)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.followup.send(err.message, ephemeral=True)
            # await interaction.response.send_message(err.message, ephemeral=True)

    #
    def upload_sorted_lobbies(self, gosession: GoSession, lobbies, signups, host_to_teams, session):
        # clear out all past lobby assignments for all teams
        for su in signups:
            su.lobby = None

        # if we need more lobbies create them
        for i in range(len(lobbies), len(host_to_teams)):
            lobbies.append(GoLobby(session_id=gosession.id))

        # if we have too many lobbies delete the extras
        for lobby in lobbies[len(host_to_teams) :]:
            session.delete(lobby)
        lobbies = lobbies[: len(host_to_teams)]

        # host_map = {h.host_did: h for h in hosts}
        team_to_signup = {su.team_id: su for su in signups}

        for lobby, (host_did, teams) in zip(lobbies, sorted(host_to_teams.items())):
            # host = host_map[host_did]
            lobby.host_did = host_did
            lobby.session = gosession
            lobby.lobby_code = None
            lobby.signups.clear()
            session.add(lobby)

            for team in teams:
                signup = team_to_signup[team.id]
                lobby.signups.append(signup)

        session.commit()

    #
    def load_session_data(self, interaction, session):
        statement = select(GoLobby).where(GoLobby.session_id == interaction.channel_id)
        lobbies = session.exec(statement).all()

        for lobby in lobbies:
            if lobby.lobby_code is not None:
                msg = f"Error: Cannot sort lobbies after lobby code has been set."
                raise DiscordUserError(msg)

        statement = select(GoHost).where(GoHost.session_id == interaction.channel_id)
        statement = statement.where(GoHost.status == "confirmed")
        hosts = session.exec(statement).all()

        statement = select(GoTeam, GoSignup).where(GoSignup.session_id == interaction.channel_id)
        statement = statement.where(GoSignup.team_id == GoTeam.id)
        statement = statement.order_by(GoSignup.signup_time)  # type: ignore
        team_rows = session.exec(statement).all()

        # fetch all the players for this session so they're cached when
        # we later access team.roster
        statement = select(GoTeam, GoSignup, GoRoster, GoPlayer)
        statement = statement.where(GoSignup.session_id == interaction.channel_id)
        statement = statement.where(GoSignup.team_id == GoTeam.id)
        statement = statement.where(GoTeam.id == GoRoster.team_id)
        statement = statement.where(GoRoster.discord_id == GoPlayer.discord_id)
        statement = statement.order_by(GoSignup.signup_time)  # type: ignore
        player_rows = session.exec(statement).all()

        lobbies = [_ for _ in lobbies]
        hosts = [_ for _ in hosts]
        teams = [_[0] for _ in team_rows]
        signups = [_[1] for _ in team_rows]

        print("\nload_session_data lobbies:")
        pprint.pp(lobbies)
        print("\nload_session_data hosts:")
        pprint.pp(hosts)
        print("\nload_session_data teams:")
        pprint.pp(teams)
        print("\nload_session_data signups:")
        pprint.pp(signups)
        print('\n')

        return lobbies, hosts, teams, signups

    #
    def log_command(self, interaction):
        group_name = interaction.command.parent.name + "." if interaction.command.parent else ""
        command_name = interaction.command.name
        logger.info(f"Command {group_name}{command_name} called by user {get_name(interaction.user)}.")

    #
    def check_admin_permissions(self, interaction):
        if interaction.user.id != _config.owner_id:
            logger.warning(f"User {get_name(interaction.user)} tried to run an admin command")
            msg = f"You dont have permission to use this command."
            raise DiscordUserError(msg)

    #
    def require_gosession(self, interaction, session):
        gosession = self.godb.get_session(interaction.channel_id, session)
        if not gosession or not interaction.channel_id:
            msg = f"Error: no session set up on channel {interaction.channel}."
            raise DiscordUserError(msg)
        return gosession

    #
    @admin_group.command(
        name="wipe-commands", description="Use with caution. Clears all the bot commands so they can be reloaded."
    )
    async def wipe_commands(self, interaction: discord.Interaction):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            await interaction.response.send_message("clear_commands starting.")
            await self.bot.tree.sync(guild=MY_GUILD)
            self.bot.tree.clear_commands(guild=MY_GUILD)
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync()

            await interaction.user.send("clear_commands complete.")
            logger.info(f"clear_commands complete.")
        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @admin_group.command(name="set-ign", description="Admin tool to set a user's In Game Name")
    async def admin_set_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)
            player = convert_user(user)
            await self.handle_set_ign("admin_set_ign", interaction, player, ign)
        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @admin_group.command(name="cancel", description="Admin tool to cancel a signup")
    async def admin_cancel(self, interaction: discord.Interaction, player: discord.Member):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            converted_player = convert_user(player)
            await self.handle_cancel("admin_cancel", interaction, converted_player)
        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @admin_group.command(name="set-session-time", description="Set the session date & time for this channel")
    async def set_session_time(self, interaction: discord.Interaction, date_time: str):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)
            date = parser.parse(date_time)

            if interaction.channel is None or interaction.channel_id is None:
                msg = "Error with discord -- cannot get channel info."
                raise DiscordUserError(msg)

            with Session(self.engine) as session:
                session_id = interaction.channel_id
                self.godb.set_session_time(session_id=session_id, session_time=date, session=session)
                msg = f'Session date for "{interaction.channel}" set to {time_str(date)}'  # type: ignore
                logger.info(msg)
                await interaction.response.send_message(msg)

        except parser.ParserError as err:
            msg = f"Error: Could not parse date string '{date_time}'"
            logger.warning(msg)
            await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @admin_group.command(name="get-session-time", description="Get the session date for this channel")
    async def get_session_time(self, interaction: discord.Interaction):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            with Session(self.engine) as session:
                gosession = self.require_gosession(interaction, session)
                msg = f'Session time for "{interaction.channel}" is {time_str(gosession.session_time)}.'
                msg += f"\nSignups are {gosession.signup_state}."
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    async def set_session_state(self, interaction: discord.Interaction, state: str):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            with Session(self.engine) as session:
                gosession = self.require_gosession(interaction, session)
                gosession.signup_state = state
                session.add(gosession)
                session.commit()

                msg = f"Session signups set to {state} for {interaction.channel}"
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @admin_group.command(name="set-session-open", description="Set the signup state to open")
    async def session_set_open(self, interaction: discord.Interaction):
        await self.set_session_state(interaction, "open")

    #
    @admin_group.command(name="set-session-closed", description="Set the signup state to close")
    async def session_set_closed(self, interaction: discord.Interaction):
        await self.set_session_state(interaction, "closed")

    #
    @admin_group.command(name="set-session-frozen", description="Set the signup state to close")
    async def session_set_change_only(self, interaction: discord.Interaction):
        await self.set_session_state(interaction, "change_only")

    #
    @admin_group.command(name="set-host", description="Add a host to this session")
    async def set_host(self, interaction: discord.Interaction, player: discord.Member):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            with Session(self.engine) as session:
                gosession = self.require_gosession(interaction, session)

                goplayer = self.godb.read_player(player.id, session)
                if not goplayer:
                    raise DiscordUserError(f"{player.name} needs to run `/go set_ign`.")

                self.godb.set_host(goplayer.discord_id, gosession.id, "confirmed", session)

                msg = f"<@{goplayer.discord_id}> set as host for {interaction.channel}."
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    @admin_group.command(name="remove-host", description="Remove a host from this session")
    async def remove_host(self, interaction: discord.Interaction, player: discord.Member):
        try:
            self.log_command(interaction)
            self.check_admin_permissions(interaction)

            with Session(self.engine) as session:
                gosession = self.require_gosession(interaction, session)
                self.godb.remove_host(player.id, gosession.id, session)

                msg = f"<@{player.id}> removed as host for {interaction.channel}."
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warning(f"Caught error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    #
    async def send_dms(self):
        if self.dms_enabled:
            for discord_id, message in self.dm_queue:
                user = self.bot.get_user(discord_id)
                if user is None:
                    continue
                await user.send(message)

    #
    async def alert_users(self, discord_ids: List[int], message: str):
        if self.dms_enabled:
            for discord_id in discord_ids:
                user = self.bot.get_user(discord_id)
                if user is None:
                    continue
                await user.send(message)

    #
    async def cog_load(self):
        logger.info(f"cog_load()")


async def setup(bot: commands.Bot) -> None:
    logger.info("setup cog start")
    await bot.add_cog(GoCog(bot))
    logger.info("setup cog end")
