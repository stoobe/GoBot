from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel


class GoPlayer(SQLModel, table=True):
    __tablename__ = "go_player"  # type: ignore

    discord_id: int = Field(sa_column=Column(BigInteger(), primary_key=True, unique=True))
    discord_name: str
    pf_player_id: Optional[int] = Field(
        sa_column=Column(BigInteger(), ForeignKey("pf_player.id"), default=None, unique=True)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    rosters: List["GoRoster"] = Relationship(back_populates="player", sa_relationship_kwargs={"cascade": "delete"})
    pf_player: Optional["PfPlayer"] = Relationship(back_populates="go_player")


class GoTeam(SQLModel, table=True):
    __tablename__ = "go_team"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    team_name: str = Field(unique=True, index=True)
    team_size: int
    team_rating: Optional[float] = Field(default=None)

    rosters: List["GoRoster"] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "delete"})
    signups: List["GoSignup"] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "delete"})


class GoRoster(SQLModel, table=True):
    __tablename__ = "go_roster"  # type: ignore

    team_id: int = Field(primary_key=True, foreign_key="go_team.id")
    discord_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("go_player.discord_id"), primary_key=True))

    player: GoPlayer = Relationship(back_populates="rosters")
    team: GoTeam = Relationship(back_populates="rosters")


class GoSignup(SQLModel, table=True):
    __tablename__ = "go_signup"  # type: ignore

    team_id: int = Field(primary_key=True, foreign_key="go_team.id")
    session_date: date = Field(primary_key=True)
    lobby_id: Optional[int] = Field(default=None, foreign_key="go_lobby.id")
    signup_time: datetime = Field(default_factory=lambda: datetime.now())

    team: GoTeam = Relationship(back_populates="signups")
    lobby: "GoLobby" = Relationship(back_populates="signups")


class GoRatings(SQLModel, table=True):
    __tablename__ = "go_ratings"  # type: ignore

    pf_player_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("pf_player.id"), primary_key=True))
    season: str = Field(primary_key=True)
    rating_type: str = Field(primary_key=True)
    go_rating: float


class GoSchedule(SQLModel, table=True):
    __tablename__ = "go_schedule"  # type: ignore

    session_id: int = Field(sa_column=Column(BigInteger(), primary_key=True))
    session_date: date = Field(unique=True)


class GoLobby(SQLModel, table=True):
    __tablename__ = "go_lobby"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    session_date: date = Field(unique=True)
    host_did: Optional[int] = Field(sa_column=Column(BigInteger(), ForeignKey("go_player.discord_id"), default=None))
    lobby_code: Optional[str] = Field(default=None)

    signups: List["GoSignup"] = Relationship(back_populates="lobby")
    host: GoPlayer = Relationship()


class PfPlayer(SQLModel, table=True):
    __tablename__ = "pf_player"  # type: ignore

    id: int = Field(sa_column=Column(BigInteger(), primary_key=True))
    ign: str = Field(index=True)
    account_created: datetime
    last_login: datetime
    avatar_url: Optional[str] = Field(nullable=True, default=None)
    # discord_id: Optional[int] = Field(default=None, foreign_key="go_player.discord_id")

    career_stats: List["PfCareerStats"] = Relationship(
        back_populates="player", sa_relationship_kwargs={"cascade": "delete"}
    )
    ign_history: List["PfIgnHistory"] = Relationship(
        back_populates="player", sa_relationship_kwargs={"cascade": "delete"}
    )
    go_player: Optional["GoPlayer"] = Relationship(back_populates="pf_player")

    def __str__(self):
        return f"Player[{self.ign}, id {self.id}, created {self.account_created.date()}, last_login {self.last_login.strftime('%Y-%m-%d %H:%M')}]"


class PfCareerStats(SQLModel, table=True):
    __tablename__ = "pf_career_stats"  # type: ignore

    date: datetime = Field(primary_key=True)
    pf_player_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("pf_player.id"), primary_key=True))
    games: int
    wins: int
    kills: int
    damage: int
    mmr: Optional[int] = Field(nullable=True, default=None)
    skill: Optional[int] = Field(nullable=True, default=None)

    player: PfPlayer = Relationship(back_populates="career_stats")

    def calc_wr(self) -> float:
        if self.games == 0:
            return 0.0
        return self.wins / self.games

    def calc_kpg(self) -> float:
        if self.games == 0:
            return 0.0
        return 1.0 * self.kills / self.games

    def calc_dpg(self) -> float:
        if self.games == 0:
            return 0.0
        return 1.0 * self.damage / self.games

    def calc_rating(self) -> float:
        if self.games == 0:
            return 0.0
        return 100.0 * (self.kills + self.damage / 210.0 + 3.1 * self.wins) / self.games

    def calc_difference(self, previous):
        if (
            previous.games > self.games
            or previous.wins > self.wins
            or previous.kills > self.kills
            or previous.damage > self.damage
        ):
            raise Exception("Subtracting stats with more games will end up with negative values")
        if self.pf_player_id != previous.pf_player_id:
            raise Exception(f"Subtracting stats from different players {self.pf_player_id} and {previous.pf_player_id}")

        diff = PfCareerStats(
            date=self.date,
            pf_player_id=self.pf_player_id,
            games=self.games - previous.games,
            wins=self.wins - previous.wins,
            kills=self.kills - previous.kills,
            damage=self.damage - previous.damage,
            mmr=self.mmr,
            skill=self.skill,
        )
        return diff


class PfIgnHistory(SQLModel, table=True):
    __tablename__ = "pf_ign_history"  # type: ignore

    pf_player_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("pf_player.id"), primary_key=True))
    date: datetime = Field(primary_key=True)
    ign: str

    player: PfPlayer = Relationship(back_populates="ign_history")

    def __repr__(self):
        return f"IgnHistory[{self.date.date()}, ign {self.ign}, id {self.pf_player_id}]"
