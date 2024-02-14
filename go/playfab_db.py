import os
from typing import List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Session, delete, func, select
from go.exceptions import DataNotDeletedError, PlayerNotFoundError
from go.logger import create_logger

from go.models import PfCareerStats, PfIgnHistory, PfPlayer


# filename = os.path.splitext(os.path.basename(__file__))[0]
# logger = create_logger(logger_name=filename)
logger = create_logger()


class PlayfabDB:
    

    def __init__(self, engine):
        self.engine = engine


    def create_player(self, player: PfPlayer, session: Session) -> None:
        logger.info("Creating Player in DB")
        session.add(player)

        ign_hist = player.ign_history
        ign_hist.sort(key=lambda x: x.date)
        most_recent_ign = ign_hist and ign_hist[-1].ign or None
        
        if most_recent_ign != player.ign:
            ign_row = PfIgnHistory(
                pf_player_id=player.id,
                date=datetime.now(),
                ign=player.ign
            )
            session.add(ign_row)

        session.commit()
        
        
    def player_exists(self, pf_player_id: int, session: Session) -> bool:
        statement = select(PfPlayer).where(PfPlayer.id == pf_player_id)
        result = session.exec(statement).first()
        return result is not None   


    def read_player(self, pf_player_id: int, session: Session) -> PfPlayer:
        logger.info(f"Reading Player with Playfab ID {pf_player_id} from DB")
        statement = select(PfPlayer).where(PfPlayer.id == pf_player_id)
        result: PfPlayer = session.exec(statement).first()
        if result:
            return result
        else:
            logger.error("Player not found")
            raise PlayerNotFoundError(f"Player with ID {pf_player_id} not found")


    def player_count(self, session):
        statement = select(func.count(PfPlayer.id))
        return session.exec(statement).one()


    def update_player(
        self,
        session: Session,
        pf_player_id: str,
        ign: str = None,
        last_login: datetime = None,
        avatar_url: str = None,
    ) -> None:

        logger.info(f"Updating Player with ID {pf_player_id} in DB")

        # Get the player, can throw PlayerNotFoundError
        player = self.read_player(pf_player_id=pf_player_id, session=session)

        if ign:
            player.ign = ign

        if last_login:
            player.last_login = last_login

        if avatar_url:
            player.avatar_url = avatar_url

        session.add(player)

        if ign:
            self.check_update_ign_history(player=player, session=session)

        session.commit()
        logger.info(f"Updated Player with ID {pf_player_id} in DB")


    def delete_player(self, session: Session, pf_player_id: int) -> None:
        logger.info(f"Deleting Player with ID {pf_player_id} from DB")

        # Get the player, can throw PlayerNotFoundError
        player = self.read_player(pf_player_id=pf_player_id, session=session)

        # dont need to run this b/c we're using cascading deletes in the DB
        # statement = delete(CareerStats).where(CareerStats.player_id == player_id)
        # session.exec(statement)

        session.delete(player)
        session.commit()

        # Confirm the deletion
        statement = select(PfPlayer).where(PfPlayer.id == pf_player_id)
        results_post_delete = session.exec(statement)
        player_post_delete = results_post_delete.first()

        if player_post_delete is None:
            logger.info(f"Player with ID {pf_player_id} was confirmed deleted")
        else:
            raise DataNotDeletedError(f"Player with ID {pf_player_id} was not deleted")
        
        
    def delete_all_players(self, session: Session) -> None:
        logger.info("Deleting all Players from DB")

        statement = delete(PfPlayer)
        session.exec(statement)

        # Confirm the deletion
        statement = select(PfPlayer)
        results_post_delete = session.exec(statement)
        players_post_delete = results_post_delete.all()

        if players_post_delete == []:
            logger.info("All Players were confirmed deleted")
        else:
            logger.error("All Players were not deleted")
            raise DataNotDeletedError("All Players were not deleted")
        
        
    def add_career_stats(self, stats: PfCareerStats, session: Session) -> None:
        logger.info("Adding CareerStats in DB")
        session.add(stats)
        session.commit()


    def delete_all_career_stats(self, session: Session) -> None:
        logger.info("Deleting all CareerStats from DB")
        statement = select(PfCareerStats)
        results = session.exec(statement)

        for stats in results:
            session.delete(stats)
            session.commit()

        # Confirm the deletion
        results_post_delete = session.exec(statement)
        stats_post_delete = results_post_delete.all()

        if stats_post_delete == []:
            logger.info("All Stats were confirmed deleted")
        else:
            logger.error("All Stats were not deleted")
            raise DataNotDeletedError("All Stats were not deleted")
        
           
    def check_update_ign_history(self, player: PfPlayer, session: Session) -> None:
        """ 
            Check if player.ign is new. If so create a new IgnHistory entry.
        """
        ign_hist = player.ign_history
        ign_hist.sort(key=lambda x: x.date)
        most_recent_ign = ign_hist and ign_hist[-1].ign or None
        
        if most_recent_ign != player.ign:
            ign_row = PfIgnHistory(
                pf_player_id=player.id,
                date=datetime.now(),
                ign=player.ign
            )
            session.add(ign_row)

        session.commit()
