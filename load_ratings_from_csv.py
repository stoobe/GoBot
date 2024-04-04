import argparse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

import csv
from go.models import GoRatings

import _config

from go.playfab_api import PlayfabApi, as_player_id
from go.playfab_db import PlayfabDB


class Row(BaseModel):
    pfid: str
    go_rating: float

def main ():
    
    parser = argparse.ArgumentParser(description="sample argument parser")
    parser.add_argument("--season", type=str, required=True, help='something like "GOP1 S10"')
    parser.add_argument("--rating_type", type=str, required=True, help='something like "combined"')
    parser.add_argument("--file", type=str, required=True, help='csv file, requires field pfid"')
    parser.add_argument("--max", type=int, default=None, required=False)
    args = parser.parse_args()

    engine = create_engine(_config.godb_url, echo=_config.godb_echo)
    SQLModel.metadata.create_all(engine)

    pfdb = PlayfabDB(engine=engine)
    
    pfapi = PlayfabApi()
    pfapi.login_to_playfab()

    success_count = 0
    fail_count = 0

    with open(args.file, mode='r') as file:

        csv_reader = csv.DictReader(f=file)
        
        with Session(engine) as session:
        
            for i,csv_row in enumerate(csv_reader):
                if args.max and i >= args.max:
                    break
                print()
                print(i, csv_row)
                row = Row(**csv_row)
                pf_player_id = as_player_id(row.pfid)
                
                if not pfdb.player_exists(pf_player_id=pf_player_id, session=session):
                    print(f"get_player_from_account_info for pfid: {row.pfid}")
                    pf_p = pfapi.get_player_from_account_info(player_id=pf_player_id)
                    if pf_p is None:
                        fail_count += 1
                        continue
                    session.add(pf_p)
                    session.commit()
                    
                
                rating = GoRatings(pf_player_id=pf_player_id, season=args.season, rating_type=args.rating_type, go_rating=row.go_rating)
                print(i, rating)
                session.add(rating)
                if i%100 == 0:
                    session.commit()
                success_count += 1
                
            print(f"Result {success_count = } {fail_count = }")
            session.commit()

if __name__ == '__main__':
    main()