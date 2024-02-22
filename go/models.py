from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import BigInteger, Column, ForeignKey

from sqlmodel import Field, Relationship, SQLModel, create_engine


class GoPlayer(SQLModel, table=True):
    __tablename__ = "go_player"
    
    discord_id: int = Field(sa_column=Column(BigInteger(), primary_key=True, unique=True))
    discord_name: str
    pf_player_id: Optional[int] = Field(sa_column=Column(BigInteger(), ForeignKey("pf_player.id"), default=None, unique=True))
    created_at: datetime = Field(default=datetime.now())

    rosters : List["GoRoster"] = Relationship(back_populates="player", sa_relationship_kwargs={"cascade": "delete"})
    pf_player : Optional["PfPlayer"] = Relationship(back_populates="go_player")


class GoTeam(SQLModel, table=True):
    __tablename__ = "go_team"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_name: str = Field(unique=True, index=True)
    team_size: int

    rosters : List["GoRoster"] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "delete"})
    signups : List["GoSignup"] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "delete"})
    
    
class GoRoster(SQLModel, table=True):
    __tablename__ = "go_roster"
    
    team_id: int = Field(primary_key=True, foreign_key="go_team.id")
    discord_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("go_player.discord_id"), primary_key=True))
    
    player: GoPlayer = Relationship(back_populates="rosters")
    team: GoTeam = Relationship(back_populates="rosters")


class GoSignup(SQLModel, table=True):
    __tablename__ = "go_signup"
    
    team_id: int = Field(primary_key=True, foreign_key="go_team.id")
    session_date: date = Field(primary_key=True)

    team: GoTeam = Relationship(back_populates="signups")


class GoRatings(SQLModel, table=True):
    __tablename__ = "go_ratings"
    
    discord_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("go_player.discord_id"), primary_key=True))
    go_rating: float




class PfPlayer(SQLModel, table=True):
    __tablename__ = "pf_player"

    id: int = Field(sa_column=Column(BigInteger(), primary_key=True))
    ign: str = Field(index=True)
    account_created: datetime
    last_login: datetime 
    avatar_url: Optional[str] = Field(nullable=True)
    # discord_id: Optional[int] = Field(default=None, foreign_key="go_player.discord_id")

    career_stats : List["PfCareerStats"] = Relationship(back_populates="player", sa_relationship_kwargs={"cascade": "delete"})
    ign_history : List["PfIgnHistory"] = Relationship(back_populates="player", sa_relationship_kwargs={"cascade": "delete"})
    go_player : Optional["GoPlayer"] = Relationship(back_populates="pf_player")

    def __str__(self):
        return f"Player[{self.ign}, id {self.id}, created {self.account_created.date()}, last_login {self.last_login.strftime('%Y-%m-%d %H:%M')}]"
    

class PfCareerStats(SQLModel, table=True):
    __tablename__ = "pf_career_stats"

    date: datetime = Field(primary_key=True)
    pf_player_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("pf_player.id"), primary_key=True))
    games: int
    wins: int
    kills: int
    damage: int
    mmr: Optional[int] = Field(nullable=True)
    skill: Optional[int] = Field(nullable=True)

    player: PfPlayer = Relationship(back_populates="career_stats")


class PfIgnHistory(SQLModel, table=True):
    __tablename__ = "pf_ign_history"

    pf_player_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("pf_player.id"), primary_key=True))
    date: datetime = Field(primary_key=True)
    ign: str

    player: PfPlayer = Relationship(back_populates="ign_history")

    def __repr__(self):
        return f"IgnHistory[{self.date.date()}, ign {self.ign}, id {self.pf_player_id}]"

