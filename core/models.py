from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Team:
    id: int
    name: str


@dataclass
class Match:
    id: int
    stage: str
    round_name: str
    team1_id: Optional[int]
    team2_id: Optional[int]
    scores_team1: list[int] = field(default_factory=list)
    scores_team2: list[int] = field(default_factory=list)
    winner_id: Optional[int] = None
    played: bool = False

    def total_team1(self) -> int:
        return sum(self.scores_team1)

    def total_team2(self) -> int:
        return sum(self.scores_team2)


@dataclass
class Group:
    name: str
    team_ids: list[int]


@dataclass
class Tournament:
    teams: list[Team] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)

    champion_id: Optional[int] = None
    runner_up_id: Optional[int] = None
    third_place_id: Optional[int] = None
    fourth_place_id: Optional[int] = None
    