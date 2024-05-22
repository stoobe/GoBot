from datetime import date as datetype
from typing import List, Optional, Union

import discord
from dateutil import parser
from discord import app_commands
from discord.ext import commands
from pydantic import BaseModel
from sqlmodel import Session

import _config
from go.exceptions import DiscordUserError, ErrorCode, GoDbError
from go.go_bot import GoBot
from go.go_db import GoDB, GoTeamPlayerSignup
from go.logger import create_logger
from go.models import GoPlayer, GoRatings, GoSignup, GoTeam
from go.playfab_api import as_player_id, as_playfab_id, is_playfab_str
from go.playfab_db import PlayfabDB

MY_GUILD = discord.Object(id=_config.guild_id)

logger = create_logger(__name__)


def get_name(member: Union[discord.Member, discord.User, None]) -> str:
    if member is None:
        return ""
    elif type(member) == discord.User:
        return member.global_name or member.display_name or member.name
    elif type(member) == discord.Member:
        return member.nick or member.global_name or member.display_name or member.name
    else:
        raise Exception(f"unreachable ")


class DiscordUser(BaseModel):
    id: int
    name: str


def convert_user(user: Union[discord.Member, discord.User]):
    return DiscordUser(id=user.id, name=get_name(user))


class GoCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        # if not isinstance(bot, GoBot):
        #     raise TypeError(f"GoCog must be initialized with a GoBot instance, not {type(bot)}")
        self.bot = bot
        self.engine = bot.engine  # type: ignore
        self.godb: GoDB = bot.godb  # type: ignore
        self.pfdb: PlayfabDB = bot.pfdb  # type: ignore

    go_group = app_commands.Group(name="go", description="GO League Commands")
    admin_group = app_commands.Group(name="goadmin", description="GO Admin Commands")

    # Above, we declare a command Group, in discord terms this is a parent command
    # We define it within the class scope (not an instance scope) so we can use it as a decorator.
    # This does have namespace caveats but i don't believe they're worth outlining in our needs.
    # @app_commands.command(name="top-command")
    # async def my_top_command(self, interaction: discord.Interaction) -> None:
    #   """ /top-command """
    #   await interaction.response.send_message("Hello from top level command!", ephemeral=True)

    def get_date_from_channel(self, channel_id: int, session: Session):
        date = self.godb.get_session_date(session_id=channel_id, session=session)
        if date is None:
            raise DiscordUserError("Signups not enabled on this channel.")
        return date

    def set_rating_if_needed(self, pf_player_id, session) -> Optional[float]:

        # make sure the player has a rating
        # if not pull one in from recent career stats
        go_rating = self.godb.get_official_rating(pf_player_id=pf_player_id, session=session)

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
                session.commit()

        return go_rating

    def do_set_ign(self, player: DiscordUser, ign: str, session: Session) -> GoPlayer:

        # if GoPlayer doesn't exist create it
        if not self.godb.player_exists(discord_id=player.id, session=session):
            go_p = GoPlayer(discord_id=player.id, discord_name=player.name)  # type: ignore
            self.godb.create_player(go_player=go_p, session=session)

        go_p = self.godb.read_player(discord_id=player.id, session=session)

        if go_p is None:
            msg = f"Could not create/read player from DB for user {player.name}"
            raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)

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

    @go_group.command(description="Set your In Game Name")
    async def set_ign(self, interaction: discord.Interaction, ign: str):  # type: ignore
        player = convert_user(interaction.user)
        logger.info(f"Running set_ign({player.name}, {ign})")

        try:
            with Session(self.engine) as session:

                go_p = self.do_set_ign(player=player, ign=ign, session=session)
                if go_p.pf_player_id is None or go_p.pf_player is None:
                    msg = f"Could not set the IGN for {player.name}."
                    raise DiscordUserError(msg, code=ErrorCode.MISC_ERROR)

                go_rating = self.set_rating_if_needed(go_p.pf_player_id, session)
                if go_rating is None:
                    msg = f"Could not find a go_rating for {ign}.  Reach out to @GO_STOOOBE to help fix this."
                    raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)

                go_rating = self.godb.get_official_rating(pf_player_id=go_p.pf_player_id, session=session)
                msg = f'IGN for {player.name} set to "{go_p.pf_player.ign}" with GO Rating {go_rating:,.0f}'

                stats = go_p.pf_player.career_stats[-1]
                msg += f"\n* Account created on {go_p.pf_player.account_created.date()}"
                msg += f"\n* Career Stats: games={stats.games}, win rate={100.0*stats.wins/stats.games:.0f}%, kpg={stats.kills/stats.games:.1f}"

                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warn(f"set_ign resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    def do_player_info(self, player: DiscordUser) -> str:
        with Session(self.engine) as session:
            go_p = self.godb.read_player(discord_id=player.id, session=session)
            if go_p is None or go_p.pf_player_id is None or go_p.pf_player is None:
                msg = f"{player.name} is not registered with GoBot"
            else:
                msg = f"- IGN: {go_p.pf_player.ign}\n"

                player_rating = self.godb.get_official_rating(pf_player_id=go_p.pf_player_id, session=session)
                msg += f"- GO Rating: {player_rating:,.0f}\n"

                msg += f"- Playfab ID: {as_playfab_id(go_p.pf_player_id)}\n"

                signups = []
                teams = [r.team for r in go_p.rosters]
                msg += f"- Teams:\n"
                for team in teams:
                    # incase it's missing from the DB for some reason
                    team_rating = team.team_rating or 0
                    igns = sorted([r.player.pf_player.ign for r in team.rosters])
                    msg += f'  - {team.team_name} *({team.team_rating:,.0f})* -- {len(team.signups)} signups -- {", ".join(igns)}\n'
                    for signup in team.signups:
                        signups.append(signup)

                msg += f"- Sessions:\n"
                for signup in signups:
                    msg += f"  - {signup.session_date} -- {signup.team.team_name}\n"

            return msg

    @go_group.command(description="Get info for a player")
    async def player_info(
        self,
        interaction: discord.Interaction,
        user: Union[discord.Member, discord.User, None] = None,
    ):

        if user is None:
            user = interaction.user

        player = convert_user(user)
        logger.info(f"Running player_info({player.name})")

        try:
            msg = self.do_player_info(player)
            logger.info(msg)
            await interaction.response.send_message(msg, ephemeral=True)
        except DiscordUserError as err:
            logger.warn(f"player_info resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message, ephemeral=True)

    def do_rename_team(self, new_team_name: str, player: DiscordUser, date: datetype, session: Session) -> GoTeam:
        tpsignups = self.godb.read_player_signups(session=session, discord_id=player.id, date=date)
        if len(tpsignups) == 0:
            msg = f"Player {player.name} is not signed up on {date}."
            raise DiscordUserError(msg)

        if len(tpsignups) > 1:
            msg = f"Somehow player {player.name} has signed up more than once on {date}"
            raise DiscordUserError(msg)

        team = tpsignups[0].team
        team.team_name = new_team_name
        session.add(team)
        session.commit()
        return team

    @go_group.command(description="Rename team for this channel's signup")
    async def rename_team(
        self,
        interaction: discord.Interaction,
        new_team_name: str,
        player: Optional[discord.Member] = None,
    ):

        if player is not None:
            if interaction.user.id != _config.owner_id:
                logger.warn(f"User {get_name(interaction.user)} tried to run rename_team for another player")
                await interaction.response.send_message(
                    "You dont have permission to use this command for other players"
                )
                return
        else:
            player = interaction.user  # type: ignore

        try:

            if interaction.channel is None or interaction.channel_id is None:
                logger.warn(f"Channel is None in rename_team")
                raise DiscordUserError("Error with discord -- cannot get channel info.", code=ErrorCode.MISC_ERROR)

            p = convert_user(player)  # type: ignore
            logger.info(f"Running rename_team({p.name}, {new_team_name}, {interaction.channel.name})")  # type: ignore

            with Session(self.engine) as session:
                date = self.get_date_from_channel(interaction.channel_id, session)
                team = self.do_rename_team(new_team_name, p, date, session)
                msg = f"Team name changed to {team.team_name}"
                logger.info(msg)
                await interaction.response.send_message(msg)
        except DiscordUserError as err:
            logger.warn(f"rename_team resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    def do_signup(
        self,
        players: List[Optional[DiscordUser]],
        team_name: str,
        date: datetype,
        session: Session,
    ) -> GoSignup:

        if not team_name:
            msg = f"Team name required."
            raise DiscordUserError(msg)

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

        for player in players:
            if player is None:
                continue
            discord_ids.add(player.id)
            go_player = self.godb.read_player(discord_id=player.id, session=session)
            go_players.append(go_player)
            if go_player is None or go_player.pf_player is None:
                msg = f"Player {player.name} needs run `/go set_ign`."
                raise DiscordUserError(msg)

            # make sure all players have ratings
            player_rating = self.godb.get_official_rating(pf_player_id=go_player.pf_player_id, session=session)
            if player_rating is None:
                msg = f"Player {player.name} does not have a GO Rating. Contact @GO_STOOOBE to help fix this."
                raise DiscordUserError(msg)

        if len(discord_ids) < len(players):
            msg = f"A player cannot be on the same team twice."
            raise DiscordUserError(msg)

        go_team_by_roster = self.godb.read_team_with_roster(discord_ids=discord_ids, session=session)

        # if the team name exists with a different name
        if go_team_by_roster and go_team_by_roster.team_name != team_name:
            # msg = f'Your team is already signed up with a different name: "{go_team_by_roster.team_name}".'
            # raise DiscordUserError(msg)
            team_name = go_team_by_roster.team_name
            logger.info(f'In do_signup: team already has name "{team_name}".  Using that name instead.')

        # read_team_with_name can handle team_name=None
        go_team_by_name = self.godb.read_team_with_name(team_name=team_name, session=session)

        # if the team_name already exists make sure it's for our team
        if go_team_by_name:
            if not go_team_by_roster or go_team_by_roster.id != go_team_by_name.id:
                igns = [r.player.pf_player.ign for r in go_team_by_name.rosters]
                msg = f'Team name "{go_team_by_name.team_name}" is already taken by team {", ".join(igns)}.'
                raise DiscordUserError(msg)

        # if it's an existing team
        if go_team_by_roster:
            # already signed up for today?
            signup_dates = [_.session_date for _ in go_team_by_roster.signups]
            if date in signup_dates:
                msg = f'Team "{team_name}" is already signed up for {date}.'
                raise DiscordUserError(msg)

            # signed up for too many dates?
            if len(signup_dates) >= 4:
                msg = f'Team "{team_name}" is already signed up for {len(signup_dates)} dates (max is 4).'
                raise DiscordUserError(msg)

        rating_limit = _config.go_rating_limits.get(len(go_players), None)

        try:
            # if it's a new team
            if go_team_by_roster is None:
                go_team_by_roster = self.godb.create_team(
                    team_name=team_name,
                    go_players=go_players,
                    session=session,
                    rating_limit=rating_limit,
                )

            if go_team_by_roster is None:
                msg = f"Could not create team in DB"
                raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)

            # rating_limit = _config.go_rating_limits.get(go_team_by_roster.team_size, None)
            # if rating_limit is not None and go_team_by_roster.team_rating > rating_limit:
            #         msg = f'Team "{team_name}" rating {go_team_by_roster.team_rating:,.0f} is over the cap {rating_limit:,.0f}.'
            #         raise DiscordUserError(msg)

            signup = self.godb.add_signup(team=go_team_by_roster, date=date, session=session)

        except GoDbError as err:
            # godb.add_signup checks that the players aren't on a different team that day
            # convert that error to this one we expect to throw
            raise DiscordUserError(err.args[0])

        session.refresh(go_team_by_roster)
        return signup

    @go_group.command(description="Sign up your team to play on a day")
    async def signup(
        self,
        interaction: discord.Interaction,
        team_name: str,
        player1: discord.Member,
        player2: Optional[discord.Member] = None,
        player3: Optional[discord.Member] = None,
    ):

        logger.info("")
        logger.info(
            f"GoCog.signup names ({interaction.channel}, {team_name}, {get_name(player1)}, {player2 and get_name(player2)}, {player3 and get_name(player3)})"
        )
        logger.info(
            f"GoCog.signup ids   ({interaction.channel_id}, {team_name}, {player1.id}, {player2 and player2.id}, {player3 and player3.id})"
        )

        try:

            with Session(self.engine) as session:

                if interaction.channel_id is None:
                    logger.warn(f"Channel is None in signup")
                    raise DiscordUserError("Error with discord -- cannot get channel info.", code=ErrorCode.MISC_ERROR)

                date = self.get_date_from_channel(interaction.channel_id, session)

                players: List[Optional[DiscordUser]] = [convert_user(player1)]
                players.append(convert_user(player2) if player2 else None)
                players.append(convert_user(player3) if player3 else None)

                if team_name:
                    team_name = team_name.strip()

                signup = self.do_signup(players=players, team_name=team_name, date=date, session=session)

                team = signup.team

                igns = [r.player.pf_player.ign for r in team.rosters]
                msg = f'Signed up "{team.team_name}" on {date} with players: {", ".join(igns)}.'
                msg += f"\nTeam GO Rating is {team.team_rating:,.0f}."
                msg += f"\nThis is signup #{len(team.signups)} for the team."
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warn(f"signup resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    def do_cancel(self, player: DiscordUser, date: datetype, session: Session) -> GoTeamPlayerSignup:
        tpsignups = self.godb.read_player_signups(session=session, discord_id=player.id, date=date)
        if len(tpsignups) == 0:
            msg = f"Player {player.name} is not signed up on {date}."
            raise DiscordUserError(msg)

        if len(tpsignups) > 1:
            logger.error(f"Somehow player {player.name} has signed up more than once on {date}")

        for tpsignup in tpsignups:
            logger.info(f"cancel row {tpsignup}")
            session.delete(tpsignup.signup)
        session.commit()

        tpsignup = tpsignups[0]
        session.refresh(tpsignup.team)
        session.refresh(tpsignup.player)

        if len(tpsignup.team.signups) == 0:
            session.delete(tpsignup.team)
            session.commit()

        return tpsignup

    @go_group.command(description="Cancel a signup for a day")
    async def cancel(self, interaction: discord.Interaction):

        player = convert_user(interaction.user)

        logger.info("")
        logger.info(f"GoCog.cancel names ({interaction.channel}, {player.name})")
        logger.info(f"GoCog.cancel ids   ({interaction.channel_id}, {player.id})")

        try:

            if interaction.channel_id is None:
                logger.warn(f"Channel is None in cancel")
                raise DiscordUserError("Error with discord -- cannot get channel info.", code=ErrorCode.MISC_ERROR)

            with Session(self.engine) as session:
                date = self.get_date_from_channel(interaction.channel_id, session)

                tpsignup = self.do_cancel(player=player, date=date, session=session)

                msg = f'Cancelled "{tpsignup.team.team_name}" for session on {date}.'
                msg += f"\nThere are {len(tpsignup.team.signups)} signups still active for the team."
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warn(f"do_cancel resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    @go_group.command(description="List the teams playing today")
    async def list_teams(self, interaction: discord.Interaction):
        try:

            if interaction.channel_id is None or interaction.channel is None:
                logger.warn(f"Channel is None in cancel")
                raise DiscordUserError("Error with discord -- cannot get channel info.", code=ErrorCode.MISC_ERROR)

            logger.info(
                f"Running list_teams on  channel_id: {interaction.channel_id}  channel.name: {interaction.channel.name}"  # type: ignore
            )

            with Session(self.engine) as session:
                msg = ""
                session_id = interaction.channel_id
                date = self.godb.get_session_date(session_id=session_id, session=session)

                if date is None:
                    msg = "This channel has no games to signup for."
                else:
                    teams = self.godb.get_teams_for_date(session_date=date, session=session)
                    msg = ""
                    player_count = 0
                    for team in teams:
                        session.refresh(team)
                        players = [r.player for r in team.rosters]
                        players_str = ""
                        for p in players:
                            player_count += 1
                            session.refresh(p.pf_player)
                            if players_str:
                                players_str += ", "
                            players_str += p.pf_player.ign
                        rating_str = f"{team.team_rating:,.0f}" if team.team_rating else "None"
                        msg += f"**{team.team_name}** (*{rating_str}*) -- {players_str}\n"
                    msg = f"**teams:** {len(teams)}\n**players:** {player_count}\n\n" + msg

                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warn(f"do_cancel resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    @admin_group.command(description="Syncs bot commands")
    async def sync_commands(self, interaction: discord.Interaction):
        logger.info(f"Command sync called by user {get_name(interaction.user)}.")
        if interaction.user.id != _config.owner_id:
            logger.warn(f"User {get_name(interaction.user)} tried to run sync")
            await interaction.response.send_message("You dont have permission to use this command!")
            return

        await interaction.response.send_message("Sync starting.")
        self.bot.tree.copy_global_to(guild=MY_GUILD)
        await self.bot.tree.sync(guild=MY_GUILD)

        await interaction.user.send("Command tree synced.")
        logger.info("Command tree synced.")

    @admin_group.command(description="Use with caution. Clears all the bot commands so they can be reloaded.")
    async def wipe_commands(self, interaction: discord.Interaction):
        logger.info(f"Command clear_commands alled by user {get_name(interaction.user)}.")
        if interaction.user.id != _config.owner_id:
            logger.warn(f"User {get_name(interaction.user)} tried to run clear_commands")
            await interaction.response.send_message("You dont have permission to use this command!")
            return

        await interaction.response.send_message("clear_commands starting.")
        await self.bot.tree.sync(guild=MY_GUILD)
        self.bot.tree.clear_commands(guild=MY_GUILD)
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()

        await interaction.user.send("clear_commands complete.")
        logger.info(f"clear_commands complete.")

    @admin_group.command(description="Admin tool to set a user's In Game Name")
    async def set_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        if interaction.user.id != _config.owner_id:
            logger.warn(f"User {get_name(interaction.user)} tried to run set_ign")
            await interaction.response.send_message("You dont have permission to use this command!")
            return

        player = convert_user(user)
        logger.info(f"Running go_admin.set_ign({player.name}, {ign})")

        try:
            with Session(self.engine) as session:

                go_p = self.do_set_ign(player=player, ign=ign, session=session)
                if go_p.pf_player_id is None or go_p.pf_player is None:
                    msg = f"Could not set the IGN for {player.name}."
                    raise DiscordUserError(msg, code=ErrorCode.MISC_ERROR)

                go_rating = self.set_rating_if_needed(go_p.pf_player_id, session)
                if go_rating is None:
                    msg = f"Could not find a go_rating for {ign}.  Reach out to @GO_STOOOBE to help fix this."
                    raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)

                msg = f'IGN for {player.name} set to "{go_p.pf_player.ign}" with GO Rating {go_rating:,.0f}'
                logger.info(msg)
                await interaction.response.send_message(msg)

        except DiscordUserError as err:
            logger.warn(f"set_ign resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message)

    @admin_group.command(description="Set the session date for this channel")
    async def set_session_date(self, interaction: discord.Interaction, date: str):
        if interaction.user.id != _config.owner_id:
            logger.warn(f"User {get_name(interaction.user)} tried to run set_session_date")
            await interaction.response.send_message("You dont have permission to use this command!")
            return

        logger.info(f"Running go_admin.set_session_date({date})")

        try:
            date2 = parser.parse(date).date()

            if interaction.channel is None or interaction.channel_id is None:
                msg = "Error with discord -- cannot get channel info."
                raise DiscordUserError(msg)

            with Session(self.engine) as session:
                session_id = interaction.channel_id
                self.godb.set_session_date(session_id=session_id, session_date=date2, session=session)
                msg = f'Session date for "{interaction.channel.name}" set to {date2}'  # type: ignore
                logger.info(msg)
                await interaction.response.send_message(msg)

        except parser.ParserError as err:
            msg = f"Error: Could not parse date string '{date}'"
            logger.warn(msg)
            await interaction.response.send_message(msg)

    @admin_group.command(description="Get the session date for this channel")
    async def get_session_date(self, interaction: discord.Interaction):
        if interaction.user.id != _config.owner_id:
            logger.warn(f"User {get_name(interaction.user)} tried to run get_session_date")
            await interaction.response.send_message("You dont have permission to use this command!")
            return

        logger.info(f"Running go_admin.get_session_date")

        if interaction.channel is None or interaction.channel_id is None:
            msg = "Error with discord -- cannot get channel info."
            raise DiscordUserError(msg)

        with Session(self.engine) as session:
            session_id = interaction.channel_id
            date = self.godb.get_session_date(session_id=session_id, session=session)
            msg = f'Session date for "{interaction.channel.name}" is {date}'  # type: ignore
            logger.info(msg)
            await interaction.response.send_message(msg)

    async def cog_load(self):
        logger.info(f"cog_load()")


async def setup(bot: commands.Bot) -> None:
    logger.info("setup cog start")
    await bot.add_cog(GoCog(bot))
    logger.info("setup cog end")
