import argparse
from datetime import datetime, timedelta
from dateutil import parser
from sqlmodel import SQLModel, Session, create_engine, select

from go.playfab_api import PlayfabApi
from go.playfab_db import PlayfabDB
from go.models import PfCareerStats, PfIgnHistory, PfPlayer
from go.logger import create_logger

import _config
logger = create_logger(__name__)



def main():

    parser = argparse.ArgumentParser(description="sample argument parser")
    parser.add_argument("--start", default=0, type=int, required=False)
    parser.add_argument("--end", default=10, type=int, required=False)
    parser.add_argument("--batchsize", default=100, type=int, required=False)
    parser.add_argument("--statname", default='CareerWins', type=str, required=False, help="CareerWins, CareerKills, CareerDamage, WeeklyWinsTotal, WeeklyKillsTotal")
    parser.add_argument("--min", default=0, type=int, required=False, help="Stop running after statname value gets below min")
    parser.add_argument("--recent", default=1, type=float, required=False, help="Skip getting new stats if there are recent ones within x days")

    args = parser.parse_args()
        
    engine = create_engine(_config.godb_url, echo=_config.godb_echo)

    SQLModel.metadata.create_all(engine)

    pfapi = PlayfabApi()
    pfapi.login_to_playfab()
    
    pfdb = PlayfabDB(engine=engine)

    with Session(engine) as session:

        start = args.start
        batchsize = args.batchsize
        end = args.end
        while start<end:
            
            if start + batchsize > end:
                batchsize = end - start
            
            logger.info("======================================================")
            logger.info("======================================================")
            logger.info(f"Loading: {start = }, {end = }, {batchsize = }")
            logger.info("------------------------------------------------------")
            
            
            leaderboard = pfapi.get_leaderboard(start_rank=start, batchsize=batchsize, stat_name=args.statname)
            start += batchsize

            for lb_row in leaderboard:
                logger.info("")

                if args.min and lb_row.stat_value < args.min:
                    logger.info(f"Minimum stat value reached {lb_row.stat_value} < {args.min}")
                    start = end
                    break

                player = PfPlayer(
                    id = lb_row.player_id,
                    ign = lb_row.ign, 
                    account_created = lb_row.account_created,
                    last_login = lb_row.last_login,                                        
                )

                logger.info(f"Rank {lb_row.stat_rank}, Value {lb_row.stat_value} -- {player}")
                
                if pfdb.player_exists(pf_player_id=player.id, session=session):
                    logger.info("Player already in DB")
                    pfdb.update_player(
                        session=session,
                        pf_player_id=player.id,
                        ign=player.ign,
                        last_login=player.last_login
                    )
                else:
                    pfdb.create_player(player=player, session=session)
                
                player = pfdb.read_player(pf_player_id=player.id, session=session)
                
                career_stats = [_ for _ in player.career_stats]
                career_stats.sort(key=lambda x: x.date)
               
                now = datetime.now()
                if career_stats and (now - career_stats[-1].date) < timedelta(days=args.recent):
                    # we already have pretty recent stats
                    logger.info(f"Already have recent stats for: {player.ign} at {career_stats[-1].date}")
                    pass
                else:
                    logger.info(f"Getting stats for: {player.ign}")
                    stats = pfapi.get_player_career_stats(player_id=player.id)
                    session.add(stats)
                    session.commit()          


if __name__=='__main__':
    main()