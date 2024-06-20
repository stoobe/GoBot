from __future__ import annotations

from datetime import date as datetype
from datetime import datetime
from typing import List, Optional, Set

from pydantic import BaseModel
from sqlmodel import Session, delete, func, select

from go.bot.exceptions import GoDbError
from go.bot.logger import create_logger
from go.bot.models import (
    GoHost,
    GoPlayer,
    GoRatings,
    GoRoster,
    GoSession,
    GoSignup,
    GoTeam,
)

logger = create_logger(__name__)


class GoTeamPlayerSignup(BaseModel):
    team: GoTeam
    player: GoPlayer
    signup: GoSignup


class GoDB:

    #
    def __init__(self):
        pass

    #
    def player_exists(self, discord_id: int, session: Session) -> bool:
        statement = select(GoPlayer).where(GoPlayer.discord_id == discord_id)
        result = session.exec(statement).first()
        return result is not None

    #
    def read_player(self, discord_id: int, session: Session) -> GoPlayer | None:
        logger.info(f"Reading GoPlayer with {discord_id = } from DB")
        statement = select(GoPlayer).where(GoPlayer.discord_id == discord_id)
        return session.exec(statement).first()

    #
    def player_count(self, session):
        statement = select(func.count(GoPlayer.discord_id))  # type: ignore
        return session.exec(statement).one()

    #
    def delete_player(self, session: Session, discord_id: int) -> None:
        logger.info(f"Deleting GoPlayer with {discord_id = } from DB")

        # Get the go_player, can throw PlayerNotFoundError
        go_player = self.read_player(discord_id=discord_id, session=session)
        if go_player is None:
            raise GoDbError(f"Cannot dlete GoPlayer with {discord_id = } -- was not found in the DB.")

        if go_player.rosters:
            raise GoDbError(f"GoPlayer with {discord_id = } cannot be deleted before teams are deleted")

        session.delete(go_player)
        session.commit()

        logger.info(f"GoPlayer with {discord_id = } was  deleted")

    #
    def delete_all_players(self, session: Session) -> None:
        logger.info("Deleting all GoPlayers from DB")

        statement = delete(GoPlayer)
        session.exec(statement)  # type: ignore

        logger.info("All GoPlayers were deleted")

    #
    def create_team(
        self,
        team_name: str,
        go_players: List[GoPlayer],
        session: Session,
        rating_limit: Optional[float],
        season: str,
    ) -> GoTeam:
        logger.info(f"Creating GoTeam {team_name = } in DB")
        ids = {p.discord_id for p in go_players}
        team_size = len(go_players)
        if len(ids) != team_size:
            raise GoDbError(f"Cannot create team: contains duplicate players")

        # make sure team doesn't already exist
        existing_team = self.read_team_with_roster(discord_ids=ids, session=session)
        if existing_team is not None:
            raise GoDbError(f"Team with roster { {p.discord_name for p in go_players} } already exists.")

        team_rating = 0.0
        for go_p in go_players:
            player_rating = self.get_official_rating(go_p.pf_player_id, session, season)
            if player_rating is None:
                team_rating = None
                break
            team_rating += player_rating

        if team_rating is None:
            raise GoDbError(f"Cannot create team: One or more players do not have an official rating")

        if rating_limit is not None and team_rating > rating_limit:
            raise GoDbError(f"Team rating {team_rating:,.0f} exceeds the cap of {rating_limit:,.0f}")

        team = GoTeam(team_name=team_name, team_size=team_size, team_rating=team_rating)
        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.id is not None

        for go_p in go_players:
            r = GoRoster(team_id=team.id, discord_id=go_p.discord_id)
            session.add(r)
        session.commit()
        session.refresh(team)

        return team

    #
    def team_count(self, session):
        statement = select(func.count(GoTeam.id))  # type: ignore
        return session.exec(statement).one()

    #
    def roster_count(self, session):
        statement = select(func.count(GoRoster.discord_id))  # type: ignore
        return session.exec(statement).one()

    #
    def signup_count(self, session):
        statement = select(func.count(GoSignup.team_id))  # type: ignore
        return session.exec(statement).one()

    #
    def add_signup(
        self, team: GoTeam, session_id: int, session: Session, signup_time: Optional[datetime] = None
    ) -> GoSignup:
        logger.info("Adding new signup to DB")

        if team.id is None:
            raise GoDbError("Cannot add signup: team has no id")

        current_signups = self.read_player_signups(session_id=session_id, session=session)
        discord_ids = {r.discord_id for r in team.rosters}

        for tp in current_signups:
            if tp.player.discord_id in discord_ids:
                # player = self.read_player(discord_id=tp.player.discord_id, session=session)
                raise GoDbError(
                    f'Player {tp.player.discord_name} is already signed up in this session for team "{tp.team.team_name}".'
                )

        if signup_time is None:
            signup_time = datetime.now()

        signup = GoSignup(team_id=team.id, session_id=session_id, signup_time=signup_time)
        session.add(signup)
        session.commit()
        return signup

    #
    def read_player_signups(
        self,
        session: Session,
        session_id: Optional[int] = None,
        team_id: Optional[int] = None,
        discord_id: Optional[int] = None,
    ) -> List[GoTeamPlayerSignup]:
        """returns empty list if none found for that date"""

        logger.info(f"Reading Signups for {session_id = } from DB")
        statement = (
            select(GoTeam, GoPlayer, GoRoster, GoSignup)
            .where(GoSignup.team_id == GoRoster.team_id)
            .where(GoRoster.team_id == GoTeam.id)
            .where(GoRoster.discord_id == GoPlayer.discord_id)
        )

        if session_id is not None:
            statement = statement.where(GoSignup.session_id == session_id)

        if team_id is not None:
            statement = statement.where(GoTeam.id == team_id)

        if discord_id is not None:
            statement = statement.where(GoPlayer.discord_id == discord_id)

        statement = statement.order_by(GoTeam.team_name, GoPlayer.discord_id)  # type: ignore

        result = session.exec(statement)
        signups = [
            GoTeamPlayerSignup(team=team, player=player, signup=signup) for (team, player, _roster, signup) in result
        ]
        logger.info(f"Returning {len(signups)} signups")
        return signups

    #
    def get_signup_for_session(self, discord_id: int, session_id: int, session: Session) -> Optional[GoSignup]:
        tpsignups = self.read_player_signups(session=session, discord_id=discord_id, session_id=session_id)
        if len(tpsignups) == 0:
            return None
        assert len(tpsignups) == 1
        return tpsignups[0].signup

    #
    def read_team(self, team_id: int, session: Session) -> Optional[GoTeam]:
        logger.info(f"Reading GoTeam with {team_id = } from DB")
        statement = select(GoTeam).where(GoTeam.id == team_id)
        team = session.exec(statement).first()
        return team

    #
    def read_team_with_roster(self, discord_ids: Set[int], session: Session) -> Optional[GoTeam]:
        logger.info(f"Reading GoTeam with {discord_ids = } from DB")

        # get all teams with the correct number of players
        team_ids = set()
        statement = select(GoTeam).where(GoTeam.team_size == len(discord_ids))
        result = session.exec(statement)
        for r in result:
            team_ids.add(r.id)

        # for each teammate
        for discord_id in discord_ids:
            # get the teams that have this player
            statement = select(GoRoster).where(GoRoster.discord_id == discord_id)
            player_teams = {roster.team_id for roster in session.exec(statement)}
            # and intersect with the teams we already have
            team_ids.intersection_update(player_teams)

        if len(team_ids) > 1:
            logger.error(f"Error: More than one team found with with {discord_ids = }")
            raise GoDbError("Error: More than one team found with that roster")

        elif len(team_ids) == 0:
            logger.info(f"No team found with that roster")
            return None

        elif len(team_ids) == 1:
            team_id = team_ids.pop()
            statement = select(GoTeam).where(GoTeam.id == team_id)
            team = session.exec(statement).one()

            logger.info(f"Returning team with {team.id = }")
            return team

        # else:
        #     raise Exception("Unreachable")

    #
    def read_team_with_name(self, team_name: str, session: Session) -> Optional[GoTeam]:
        logger.info(f"Reading GoTeam with {team_name = } from DB")
        statement = select(GoTeam).where(GoTeam.team_name == team_name)
        team = session.exec(statement).first()
        return team

    #
    def get_teams_for_session(self, session_id, session: Session) -> List[GoTeam]:
        logger.info(f"Reading GoSignups with {session_id = } from DB")
        statement = (
            select(GoSignup).where(GoSignup.session_id == session_id).order_by(GoSignup.signup_time)  # type: ignore
        )
        results = session.exec(statement)
        teams = []
        for signup in results:
            teams.append(signup.team)
        return teams

    #
    def get_session(self, session_id: int | None, session: Session) -> Optional[GoSession]:
        if not session_id:
            return None
        statement = select(GoSession).where(GoSession.id == session_id)
        return session.exec(statement).first()

    #
    def get_session_time(self, session_id: int, session: Session) -> Optional[datetime]:
        gosession = self.get_session(session_id, session)
        if gosession is None:
            return None
        return gosession.session_time

    #
    def set_session_time(self, session_id: int, session_time: datetime, session: Session):
        if session_id is None:
            raise ValueError("session_id cannot be None")
        if session_time is None:
            raise ValueError("session_time cannot be None")

        statement = select(GoSession).where(GoSession.id == session_id)
        gosession = session.exec(statement).first()

        if gosession is not None:
            if gosession.session_time == session_time:
                return
            else:
                gosession.session_time = session_time
        else:
            gosession = GoSession(id=session_id, session_time=session_time, signup_state="open")

        session.add(gosession)
        session.commit()

    #
    def get_official_rating(self, pf_player_id, session: Session, season: str) -> Optional[float]:
        statement = select(GoRatings).where(GoRatings.rating_type == "official")
        statement = statement.where(GoRatings.season == season)
        statement = statement.where(GoRatings.pf_player_id == pf_player_id)
        rating = session.exec(statement).first()
        if rating is None:
            return None
        return rating.go_rating

    #
    def set_host(self, discord_id: int, session_id: int, status: str, session: Session):
        statement = select(GoHost).where(GoHost.host_did == discord_id).where(GoHost.session_id == session_id)
        host = session.exec(statement).first()

        if host is None:
            host = GoHost(host_did=discord_id, session_id=session_id, status=status)
            session.add(host)
            session.commit()
        else:
            host.status = status
            session.add(host)
            session.commit()

    #
    def remove_host(self, discord_id: int, session_id: int, session: Session):
        statement = select(GoHost).where(GoHost.host_did == discord_id).where(GoHost.session_id == session_id)
        host = session.exec(statement).first()

        if host is not None:
            session.delete(host)
            session.commit()
