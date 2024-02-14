import os
from typing import List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Session, delete, func, select

from go.exceptions import DataNotDeletedError, GoDbError, PlayerNotFoundError
from go.logger import create_logger
from go.models import GoPlayer, GoRoster, GoSignup, GoTeam



# filename = os.path.splitext(os.path.basename(__file__))[0]
# logger = create_logger(logger_name=filename)
logger = create_logger()


class GoDB:
    

    def __init__(self, engine):
        self.engine = engine


    def create_player(self, go_player: GoPlayer, session: Session) -> None:
        logger.info("Creating GoPlayer in DB")
        session.add(go_player)

        # ign_hist = go_player.ign_history
        # ign_hist.sort(key=lambda x: x.date)
        # most_recent_ign = ign_hist and ign_hist[-1].ign or None
        
        # if most_recent_ign != go_player.ign:
        #     ign_row = PfIgnHistory(
        #         discord_id=go_player.discord_id,
        #         date=datetime.now(),
        #         ign=go_player.ign
        #     )
        #     session.add(ign_row)

        session.commit()
        
        
    def player_exists(self, discord_id: int, session: Session) -> bool:
        statement = select(GoPlayer).where(GoPlayer.discord_id == discord_id)
        result = session.exec(statement).first()
        return result is not None   


    def read_player(self, discord_id: int, session: Session) -> GoPlayer:
        logger.info(f"Reading GoPlayer with {discord_id = } from DB")
        statement = select(GoPlayer).where(GoPlayer.discord_id == discord_id)
        result: GoPlayer = session.exec(statement).first()
        if result:
            return result
        else:
            logger.error("GoPlayer not found")
            raise PlayerNotFoundError(f"GoPlayer with {discord_id = } not found")


    def player_count(self, session):
        statement = select(func.count(GoPlayer.discord_id))
        return session.exec(statement).one()


#     def update_player(
#         self,
#         session: Session,
#         discord_id: str,
#         ign: str = None,
#         last_login: datetime = None,
#         avatar_url: str = None,
#     ) -> None:

#         logger.info(f"Updating GoPlayer with ID {discord_id} in DB")

#         # Get the go_player, can throw PlayerNotFoundError
#         go_player = self.read_player(discord_id=discord_id, session=session)

#         if ign:
#             go_player.ign = ign

#         if last_login:
#             go_player.last_login = last_login

#         if avatar_url:
#             go_player.avatar_url = avatar_url

#         session.add(go_player)

#         if ign:
#             self.check_update_ign_history(go_player=go_player, session=session)

#         session.commit()
#         logger.info(f"Updated GoPlayer with ID {discord_id} in DB")


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
        logger.info("Creating GoTeam in DB")
        ids = {p.discord_id for p in go_players}
        team_size = len(go_players)
        if len(ids) != team_size:
            raise GoDbError(f"Cannot team: contains duplicate players")
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
        statement = select(func.count(GoSignup.discord_id))
        return session.exec(statement).one()
        
#     def add_career_stats(self, stats: PfCareerStats, session: Session) -> None:
#         logger.info("Adding CareerStats in DB")
#         session.add(stats)
#         session.commit()


#     def delete_all_career_stats(self, session: Session) -> None:
#         logger.info("Deleting all CareerStats from DB")
#         statement = select(PfCareerStats)
#         results = session.exec(statement)

#         for stats in results:
#             session.delete(stats)
#             session.commit()

#         # Confirm the deletion
#         results_post_delete = session.exec(statement)
#         stats_post_delete = results_post_delete.all()

#         if stats_post_delete == []:
#             logger.info("All Stats were confirmed deleted")
#         else:
#             logger.error("All Stats were not deleted")
#             raise DataNotDeletedError("All Stats were not deleted")
        
           
#     def check_update_ign_history(self, go_player: GoPlayer, session: Session) -> None:
#         """ 
#             Check if go_player.ign is new. If so create a new IgnHistory entry.
#         """
#         ign_hist = go_player.ign_history
#         ign_hist.sort(key=lambda x: x.date)
#         most_recent_ign = ign_hist and ign_hist[-1].ign or None
        
#         if most_recent_ign != go_player.ign:
#             ign_row = PfIgnHistory(
#                 discord_id=go_player.discord_id,
#                 date=datetime.now(),
#                 ign=go_player.ign
#             )
#             session.add(ign_row)

#         session.commit()
