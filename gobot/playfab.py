from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, ForeignKey, Relationship, SQLModel, create_engine


class Players(SQLModel, table=True):
    playfab_id: int = Field(primary_key=True)
    ign: str
    account_created: datetime
    last_login: datetime 
    avatar_url: str = Field(nullable=True)

    careerstats : List["CareerStats"] = Relationship(back_populates="player")

    def __str__(self):
        return f"Player[{self.ign}, playfab_id {self.playfab_id}, created {self.account_created}, last_login {self.last_login}]"


class CareerStats(SQLModel, table=True):
    date: datetime = Field(primary_key=True)
    playfab_id: int = Field(primary_key=True, \
                            foreign_key="players.playfab_id")
    games: int
    wins: int
    kills: int
    damage: int
    mmr: int = Field(nullable=True)
    skill: int = Field(nullable=True)

    player: Players = Relationship(back_populates="careerstats")


class IgnHistory(SQLModel, table=True):
    playfab_id: int = Field(primary_key=True)
    date_observed: datetime = Field(primary_key=True)
    ign: str


if __name__ == "__main__":
    sqlite_file_name = "test.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    # sqlite_url = f"sqlite://" # in mem
    engine = create_engine(sqlite_url, echo=True)

    SQLModel.metadata.create_all(engine)
