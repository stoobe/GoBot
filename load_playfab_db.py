import argparse
from datetime import datetime, timedelta
from dateutil import parser
from sqlmodel import SQLModel, Session, create_engine, select

from go.playfab_api import PlayfabApi
from go.playfab_db import PlayfabDB
from go.models import PfCareerStats, PfIgnHistory, PfPlayer

import _config



def main():

    parser = argparse.ArgumentParser(description="sample argument parser")
    parser.add_argument("--start", default=0, type=int, required=False)
    parser.add_argument("--end", default=10, type=int, required=False)
    parser.add_argument("--batchsize", default=100, type=int, required=False)
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
            
            print("\n\n\n")
            print("======================================================")
            print(f"start {start}, end {end}, batchsize {batchsize}")
            print("======================================================")
            
            
            leaderboard = pfapi.get_leaderboard(start_rank=start, batchsize=batchsize)
            start += batchsize

            for lb_row in leaderboard:
                print("\n")

                player = PfPlayer(
                    id = lb_row.player_id,
                    ign = lb_row.ign, 
                    account_created = lb_row.account_created,
                    last_login = lb_row.last_login,                                        
                )

                print(f"Rank {lb_row.stat_rank}, Value {lb_row.stat_value} -- {player}")
                
                if pfdb.player_exists(pf_player_id=player.id, session=session):
                    print("Player already in DB")
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
                if career_stats and (now - career_stats[-1].date) < timedelta(days=1):
                    # we already have pretty recent stats
                    print(f"Already have recent stats for: {player.ign}")
                    pass
                else:
                    print(f"Getting stats for: {player.ign}")
                    stats = pfapi.get_player_career_stats(player_id=player.id)
                    session.add(stats)
                    session.commit()          

        session.close()


if __name__=='__main__':
    main()