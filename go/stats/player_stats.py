from __future__ import annotations

from pydantic import BaseModel


class Stats(BaseModel):
    ign: str | None = None
    playfab: str | None = None
    team_size: int | None = None
    games: int = 0
    wr: float = 0.0
    kpg: float = 0.0
    dpg: float = 0.0
    orig_rating: float | None = None

    def add_game(self, place, kills, damage):
        win = 1.0 if place == 1 else 0.0
        self.wr = (self.wr * self.games + win) / (self.games + 1)
        self.kpg = (self.kpg * self.games + kills) / (self.games + 1)
        self.dpg = (self.dpg * self.games + damage) / (self.games + 1)
        self.games += 1

    def go_rating(self):
        return 100.0 * (self.kpg + self.dpg / 210.0 + 3.1 * self.wr)

    def __str__(self):
        return f"g={self.games}  wr={self.wr :.2f}  kpg={self.kpg :.2f}  dpg={self.dpg :.0f}  rating={self.go_rating() :.2f}"
