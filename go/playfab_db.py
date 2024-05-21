import os
from typing import List
from datetime import datetime, timedelta, timezone
from sqlmodel import SQLModel, Session, delete, func, select
from go.exceptions import DataNotDeletedError, PlayerNotFoundError
from go.logger import create_logger

from go.models import PfCareerStats, PfIgnHistory, PfPlayer
import _config

logger = create_logger(__name__)


class PlayfabDB:

    def __init__(self, engine):
        self.engine = engine

    def create_player(self, player: PfPlayer, session: Session) -> None:
        logger.info("Creating PfPlayer in DB")
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
        logger.info(f"Reading PfPlayer with Playfab ID {pf_player_id} from DB")
        statement = select(PfPlayer).where(PfPlayer.id == pf_player_id)
        result: PfPlayer = session.exec(statement).first()
        return result
        # if result:
        #     return result
        # else:
        #     logger.error("PfPlayer not found")
        #     raise PlayerNotFoundError(f"PfPlayer with ID {pf_player_id} not found")

    def read_players_by_ign(self, ign: str, session: Session, limit=None) -> List[PfPlayer]:
        logger.info(f"Reading PfPlayer with {ign = } from DB")
        statement = select(PfPlayer).where(PfPlayer.ign.contains(ign.lower()))
        if limit:
            statement = statement.limit(limit)
        result = [_ for _ in session.exec(statement)]
        return result

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

        logger.info(f"Updating PfPlayer with ID {pf_player_id} in DB")

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
        logger.info(f"Updated PfPlayer with ID {pf_player_id} in DB")

    def delete_player(self, session: Session, pf_player_id: int) -> None:
        logger.info(f"Deleting PfPlayer with ID {pf_player_id} from DB")

        # Get the player, can throw PlayerNotFoundError
        player = self.read_player(pf_player_id=pf_player_id, session=session)

        session.delete(player)
        session.commit()

        # Confirm the deletion
        if not self.player_exists(pf_player_id=pf_player_id, session=session):
            logger.info(
                f"PfPlayer with {pf_player_id = } was confirmed deleted")
        else:
            raise DataNotDeletedError(
                f"PfPlayer with {pf_player_id = } was not deleted")

    def delete_all_players(self, session: Session) -> None:
        logger.info("Deleting all PfPlayers from DB")

        statement = delete(PfPlayer)
        session.exec(statement)

        # Confirm the deletion
        if self.player_count(session=session) == 0:
            logger.info("All PfPlayers were confirmed deleted")
        else:
            logger.error("All PfPlayers were not deleted")
            raise DataNotDeletedError("All PfPlayers were not deleted")

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

    def ign_history_count(self, session):
        statement = select(func.count(PfIgnHistory.ign))
        return session.exec(statement).one()

    def calc_rating_from_stats(self, pf_player_id, session: Session, snapshot_date: datetime = None) -> float:
        if snapshot_date is None:
            snapshot_date = _config.go_rating_snapshot_date

        statement = select(PfCareerStats).where(
            PfCareerStats.pf_player_id == pf_player_id)
        statement = statement.where(PfCareerStats.date <= snapshot_date).order_by(
            PfCareerStats.date.desc())
        most_recent = None
        previous_snapshop = None
        for rating in session.exec(statement):
            if most_recent is None:
                most_recent = rating
            else:
                # if there have been at least 100 games played between rating and most_recenet
                # then we can use this rating
                if most_recent.games - rating.games >= 100:
                    previous_snapshop = rating

                # if we've accumulated over 500 games that's enough
                if most_recent.games - rating.games >= 500:
                    break
                # if we've gone back over 3 months we don't want to go back farther
                if snapshot_date - rating.date >= timedelta(days=96):
                    break

        if most_recent is None:
            return None

        if previous_snapshop is None:
            return most_recent.calc_rating()

        assert most_recent.games >= 100 + previous_snapshop.games
        diff = most_recent.calc_difference(previous_snapshop)
        return diff.calc_rating()
