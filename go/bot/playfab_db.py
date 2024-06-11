from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import Session, delete, func, select

from go.bot.exceptions import DataNotDeletedError, PlayerNotFoundError
from go.bot.logger import create_logger
from go.bot.models import PfCareerStats, PfIgnHistory, PfPlayer

logger = create_logger(__name__)


class PlayfabDB:

    #
    def __init__(self):
        pass

    #
    def create_player(self, player: PfPlayer, session: Session) -> None:
        logger.info("Creating PfPlayer in DB")
        session.add(player)

        ign_hist = player.ign_history
        ign_hist.sort(key=lambda x: x.date)
        most_recent_ign = ign_hist and ign_hist[-1].ign or None

        if most_recent_ign != player.ign:
            ign_row = PfIgnHistory(pf_player_id=player.id, date=datetime.now(), ign=player.ign)
            session.add(ign_row)

        session.commit()
        print(player)

    #
    def player_exists(self, pf_player_id: int, session: Session) -> bool:
        statement = select(PfPlayer).where(PfPlayer.id == pf_player_id)
        result = session.exec(statement).first()
        return result is not None

    #
    def read_player(self, pf_player_id: int, session: Session) -> Optional[PfPlayer]:
        logger.info(f"Reading PfPlayer with Playfab ID {pf_player_id} from DB")
        statement = select(PfPlayer).where(PfPlayer.id == pf_player_id)
        result = session.exec(statement).first()
        return result

    #
    def read_players_by_ign(self, ign: str, session: Session, limit=None) -> List[PfPlayer]:
        logger.info(f"Reading PfPlayer with {ign = } from DB")
        statement = select(PfPlayer).where(PfPlayer.ign.contains(ign.lower()))  # type: ignore
        if limit:
            statement = statement.limit(limit)
        result = [_ for _ in session.exec(statement)]
        return result

    #
    def player_count(self, session):
        statement = select(func.count(PfPlayer.id))  # type: ignore
        return session.exec(statement).one()

    #
    def update_player(
        self,
        session: Session,
        pf_player_id: int,
        ign: Optional[str] = None,
        last_login: Optional[datetime] = None,
        avatar_url: Optional[str] = None,
    ) -> None:

        logger.info(f"Updating PfPlayer with ID {pf_player_id} in DB")

        # Get the player, can throw PlayerNotFoundError
        player = self.read_player(pf_player_id=pf_player_id, session=session)
        if player is None:
            raise PlayerNotFoundError(f"Player with {pf_player_id = } not found")

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

    #
    def delete_player(self, session: Session, pf_player_id: int) -> None:
        logger.info(f"Deleting PfPlayer with ID {pf_player_id} from DB")

        # Get the player, can throw PlayerNotFoundError
        player = self.read_player(pf_player_id=pf_player_id, session=session)

        session.delete(player)
        session.commit()
        logger.info(f"PfPlayer with {pf_player_id = } was deleted")

    #
    def delete_all_players(self, session: Session) -> None:
        logger.info("Deleting all PfPlayers from DB")

        statement = delete(PfPlayer)
        session.exec(statement)  # type: ignore
        session.commit()
        logger.info("All PfPlayers were deleted")

    #
    def add_career_stats(self, stats: PfCareerStats, session: Session) -> None:
        logger.info("Adding CareerStats in DB")
        session.add(stats)
        session.commit()

    #
    def delete_all_career_stats(self, session: Session) -> None:
        logger.info("Deleting all CareerStats from DB")
        statement = delete(PfCareerStats)
        session.exec(statement)  # type: ignore
        session.commit()
        logger.info("All PfCareerStats were deleted")

    #
    def check_update_ign_history(self, player: PfPlayer, session: Session) -> None:
        """
        Check if player.ign is new. If so create a new IgnHistory entry.
        """
        ign_hist = player.ign_history
        ign_hist.sort(key=lambda x: x.date)
        most_recent_ign = ign_hist and ign_hist[-1].ign or None

        if most_recent_ign != player.ign:
            ign_row = PfIgnHistory(pf_player_id=player.id, date=datetime.now(), ign=player.ign)
            session.add(ign_row)

        session.commit()

    #
    def ign_history_count(self, session):
        statement = select(func.count(PfIgnHistory.ign))  # type: ignore
        return session.exec(statement).one()

    #
    def calc_rating_from_stats(
        self, pf_player_id, session: Session, snapshot_date: Optional[datetime] = None
    ) -> Optional[float]:
        if snapshot_date is None:
            snapshot_date = datetime.now()
            #     snapshot_date = _config.go_rating_snapshot_date

        statement = select(PfCareerStats).where(PfCareerStats.pf_player_id == pf_player_id)
        statement = statement.where(PfCareerStats.date <= snapshot_date)
        statement = statement.order_by(PfCareerStats.date.desc())  # type: ignore

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
