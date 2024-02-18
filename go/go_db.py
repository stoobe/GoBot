import os
from typing import List, Set
from datetime import datetime, timezone
from datetime import date as datetype
from pydantic import BaseModel
from sqlmodel import SQLModel, Session, delete, func, select

from go.exceptions import DataNotDeletedError, GoDbError, PlayerNotFoundError
from go.logger import create_logger
from go.models import GoPlayer, GoRoster, GoSignup, GoTeam



# filename = os.path.splitext(os.path.basename(__file__))[0]
# logger = create_logger(logger_name=filename)
logger = create_logger()


class GoTeamPlayerSignup(BaseModel):
    team: GoTeam
    player: GoPlayer
    signup: GoSignup

class GoDB:
    

    def __init__(self, engine):
        self.engine = engine


    def create_player(self, go_player: GoPlayer, session: Session) -> None:
        logger.info("Creating GoPlayer in DB")
        session.add(go_player)
        session.commit()
        
        
    def player_exists(self, discord_id: int, session: Session) -> bool:
        statement = select(GoPlayer).where(GoPlayer.discord_id == discord_id)
        result = session.exec(statement).first()
        return result is not None   


    def read_player(self, discord_id: int, session: Session) -> GoPlayer:
        logger.info(f"Reading GoPlayer with {discord_id = } from DB")
        statement = select(GoPlayer).where(GoPlayer.discord_id == discord_id)
        result: GoPlayer = session.exec(statement).first()
        return result
    

    def player_count(self, session):
        statement = select(func.count(GoPlayer.discord_id))
        return session.exec(statement).one()


    def delete_player(self, session: Session, discord_id: int) -> None:
        logger.info(f"Deleting GoPlayer with {discord_id = } from DB")

        # Get the go_player, can throw PlayerNotFoundError
        go_player = self.read_player(discord_id=discord_id, session=session)

        if go_player.rosters:
            raise GoDbError(f"GoPlayer with {discord_id = } cannot be deleted before teams are deleted")
            
        session.delete(go_player)
        session.commit()

        # Confirm the deletion
        if not self.player_exists(discord_id=discord_id, session=session):
            logger.info(f"GoPlayer with {discord_id = } was confirmed deleted")
        else:
            raise DataNotDeletedError(f"GoPlayer with {discord_id = } was not deleted")
        
        
    def delete_all_players(self, session: Session) -> None:
        logger.info("Deleting all GoPlayers from DB")

        statement = delete(GoPlayer)
        session.exec(statement)

        # Confirm the deletion
        statement = select(GoPlayer)
        results_post_delete = session.exec(statement)
        players_post_delete = results_post_delete.all()

        if players_post_delete == []:
            logger.info("All GoPlayers were confirmed deleted")
        else:
            logger.error("All GoPlayers were not deleted")
            raise DataNotDeletedError("All GoPlayers were not deleted")
        
        
    def create_team(self, team_name:str, go_players:List[GoPlayer], session: Session) -> GoTeam:
        logger.info(f"Creating GoTeam {team_name = } in DB")
        ids = {p.discord_id for p in go_players}
        team_size = len(go_players)
        if len(ids) != team_size:
            raise GoDbError(f"Cannot create team: contains duplicate players")
        
        # make sure team doesn't already exist
        existing_team = self.read_team_with_roster(discord_ids=ids, session=session)
        if existing_team is not None:
            raise GoDbError(f"Team with roster { {p.discord_name for p in go_players} } already exists.")
        
        team = GoTeam(team_name=team_name, team_size=team_size)
        session.add(team)
        session.commit()
        session.refresh(team)
        
        for go_p in go_players:
            r = GoRoster(team_id=team.id, discord_id=go_p.discord_id)
            session.add(r)
        session.commit()
        session.refresh(team)
                
        return team


    def team_count(self, session):
        statement = select(func.count(GoTeam.id))
        return session.exec(statement).one()
    

    def roster_count(self, session):
        statement = select(func.count(GoRoster.discord_id))
        return session.exec(statement).one()
        

    def signup_count(self, session):
        statement = select(func.count(GoSignup.team_id))
        return session.exec(statement).one()
        
        
    def add_signup(self, team: GoTeam, date: datetype, session: Session):
        logger.info("Adding new signup to DB")
        
        current_signups = self.read_player_signups(date=date, session=session)
        discord_ids = {r.discord_id for r in team.rosters}
        
        for tp in current_signups:
            if tp.player.discord_id in discord_ids:
                player = self.read_player(discord_id=tp.player.discord_id, session=session)
                raise GoDbError(f'Player {player.discord_name} is already signed up for {date} for team "{tp.team.team_name}".')
        
        signup = GoSignup(team_id=team.id, session_date=date)
        session.add(signup)
        session.commit()        

   
    def read_player_signups(self,
                     session: Session, 
                     date: datetype = None, 
                     team_id: int = None, 
                     discord_id: int = None
                     ) -> List[GoTeamPlayerSignup]:
           
        """ returns empty list if none found for that date """
        
        logger.info(f"Reading Signups for {date = } from DB")
        statement = (
            select(GoTeam, GoPlayer, GoRoster, GoSignup)
            .where(GoSignup.team_id == GoRoster.team_id)
            .where(GoRoster.team_id == GoTeam.id)
            .where(GoRoster.discord_id == GoPlayer.discord_id)
        )
        
        if date is not None:
            statement = statement.where(GoSignup.session_date == date)
        
        if team_id is not None:
            statement = statement.where(GoTeam.id == team_id)
            
        if discord_id is not None:
            statement = statement.where(GoPlayer.discord_id == discord_id)
            
        statement = statement.order_by(GoTeam.team_name, GoPlayer.discord_id)
        
        result = session.exec(statement)
        signups = [GoTeamPlayerSignup(team=team, player=player, signup=signup) for (team, player, _roster, signup) in result]
        logger.info(f"Returning {len(signups)} signups")
        return signups
   
   
    def read_team(self, team_id:id, session: Session) -> GoTeam:
        logger.info(f"Reading GoTeam with {team_id = } from DB")
        statement = select(GoTeam).where(GoTeam.id == team_id)
        team = session.exec(statement).first()
        return team
    
    
    def read_team_with_roster(self, discord_ids: Set[int], session: Session) -> GoTeam:
        logger.info(f"Reading GoTeam with {discord_ids = } from DB")
        
        # get all teams with the correct number of players
        team_ids = set()
        statement = select(GoTeam).where(GoTeam.team_size == len(discord_ids))
        result = session.exec(statement)
        for r in result:
            team_ids.add(r.id)
        
        for discord_id in discord_ids:
            statement = select(GoRoster).where(GoRoster.discord_id == discord_id)
            player_teams = {roster.team_id for roster in session.exec(statement)}
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
            team = session.exec(statement).first()
            
            logger.info(f"Returning team with {team.id = }")
            return team
        
        else:
            raise Exception("Unreachable")

    
    
    def read_team_with_name(self, team_name:str, session: Session) -> GoTeam:
        logger.info(f"Reading GoTeam with {team_name = } from DB")
        statement = select(GoTeam).where(GoTeam.team_name == team_name)
        team = session.exec(statement).first()
        return team
        