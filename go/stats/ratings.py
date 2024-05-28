from __future__ import annotations

import csv

from pydantic import BaseModel


class GoRating(BaseModel):
    ign: str
    pfid: str
    pfid2: str
    go_rating: float


def load_ratings(fname):
    pfid_to_rating = dict()
    pfid_to_rating[""] = None
    with open(fname, mode="r") as file:
        csv_reader = csv.DictReader(f=file)
        for i, row in enumerate(csv_reader):
            row["pfid2"] = row["mapfid"]
            row = GoRating(**row)  # type: ignore
            pfid_to_rating[row.pfid] = row.go_rating
    print(f"loaded {len(pfid_to_rating)} ratings")
    return pfid_to_rating