from __future__ import annotations

import csv
from datetime import date
from typing import Optional

from pydantic import BaseModel


class GameResult(BaseModel):
    date: date
    lobby: str
    match: int
    team: str
    ign: str
    ign2: Optional[str] = None
    playfabid: str
    playfabid2: str
    placement: int
    kills: int
    damage: int
    is_fun_match: bool
    team_size: Optional[int] = None
    roster: Optional[set] = None


def load_match_results(fname):
    results = []
    with open(fname, mode="r") as file:
        csv_reader = csv.DictReader(f=file)
        for i, row in enumerate(csv_reader):
            # row["date"] = row["datetime"].split()[0].replace("/", "-")
            row = GameResult(**row)  # type: ignore
            results.append(row)

    print(f"before filtering out fun games {len(results)}")
    results = [r for r in results if not r.is_fun_match]
    print(f"after filtering out fun games {len(results)}")
    return results
