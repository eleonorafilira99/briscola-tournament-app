from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Team:
    id: int
    player1: str
    player2: str
    team_name: str = ""

    @property
    def name(self) -> str:
        if self.team_name.strip():
            return self.team_name
        return f"{self.player1} / {self.player2}"

    @property
    def players_label(self) -> str:
        return f"{self.player1} / {self.player2}"


@dataclass
class Match:
    id: int
    round_name: str
    team1_id: Optional[int]
    team2_id: Optional[int]

    # Gironi / fase finale
    group_name: Optional[str] = None

    # Risultato partita secca o risultato complessivo del match
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None

    # Punteggio tradizionale, utile per gironi e classifiche
    team1_score: Optional[int] = None
    team2_score: Optional[int] = None

    # Nuovo: formato match
    # best_of = 1 → partita secca
    # best_of = 3 → vince chi arriva a 2 vittorie
    best_of: int = 1
    team1_wins: int = 0
    team2_wins: int = 0

    # Collegamento tabellone
    next_match_id: Optional[int] = None
    next_match_slot: Optional[int] = None

    # Finale 3°/4° posto
    third_place_match_id: Optional[int] = None
    third_place_match_slot: Optional[int] = None

    def is_played(self) -> bool:
        return self.winner_id is not None

    def required_wins(self) -> int:
        return (self.best_of // 2) + 1

    def is_best_of_three(self) -> bool:
        return self.best_of == 3


@dataclass
class Group:
    name: str
    team_ids: list[int] = field(default_factory=list)


@dataclass
class Tournament:
    name: str
    teams: list[Team] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)

    champion_id: Optional[int] = None
    runner_up_id: Optional[int] = None
    third_place_id: Optional[int] = None
    fourth_place_id: Optional[int] = None

    next_team_id: int = 1
    next_match_id: int = 1