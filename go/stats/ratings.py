from __future__ import annotations

import csv

from pydantic import BaseModel


class GoRating(BaseModel):
    ign: str
    pfid: str
    pfid2: str
    go_rating: float


def load_ratings(fname) -> dict[str, float]:
    rows = load_ratings_rows(fname)
    pfid_to_rating = dict()
    pfid_to_rating[""] = None

    for i, row in enumerate(rows):
        pfid_to_rating[row.pfid] = row.go_rating

    return pfid_to_rating



def load_ratings_rows(fname) -> list[GoRating]:
    rows = []
    with open(fname, mode="r") as file:
        csv_reader = csv.DictReader(f=file, escapechar="\\")
        for i, row in enumerate(csv_reader):
            row["pfid2"] = row.get("mapfid", row["pfid"])
            row = GoRating(**row)  # type: ignore
            rows.append(row)
    print(f"loaded {len(rows)} rating rows")
    return rows