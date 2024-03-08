import argparse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

import csv
from go.models import GoRatings

import _config

from go.playfab_api import as_player_id


class Row(BaseModel):
    pfid: str
    go_rating: float

def main ():
    
    parser = argparse.ArgumentParser(description="sample argument parser")
    parser.add_argument("--season", type=str, required=True, help='something like "GOP1 S10"')
    parser.add_argument("--rating_type", type=str, required=True, help='something like "combined"')
    parser.add_argument("--file", type=str, required=True, help='csv file, requires fields pfid and go_rating"')    
    args = parser.parse_args()

    engine = create_engine(_config.godb_url, echo=_config.godb_echo)
    SQLModel.metadata.create_all(engine)

    with open(args.file, mode='r') as file:

        csv_reader = csv.DictReader(f=file)
        
        with Session(engine) as session:
        
            for i,row in enumerate(csv_reader):
                print()
                print(i, row)
                row = Row(**row)
                #print(i, row)
                pf_player_id = as_player_id(row.pfid)
                rating = GoRatings(pf_player_id=pf_player_id, season=args.season, rating_type=args.rating_type, go_rating=row.go_rating)
                print(i, rating)
                session.add(rating)
                if i%100 == 0:
                    session.commit()
                if i==101: break
            session.commit()

if __name__ == '__main__':
    main()