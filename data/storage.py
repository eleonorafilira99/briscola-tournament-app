import json
from dataclasses import asdict
from pathlib import Path

from core.models import Group, Match, Team, Tournament


DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "tournament.json"


def save_tournament(tournament: Tournament) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(asdict(tournament), file, ensure_ascii=False, indent=4)


def load_tournament() -> Tournament | None:
    if not DATA_FILE.exists():
        return None

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    teams = [Team(**team) for team in data.get("teams", [])]
    groups = [Group(**group) for group in data.get("groups", [])]
    matches = [Match(**match) for match in data.get("matches", [])]

    return Tournament(
        teams=teams,
        groups=groups,
        matches=matches,
        champion_id=data.get("champion_id"),
        runner_up_id=data.get("runner_up_id"),
        third_place_id=data.get("third_place_id"),
        fourth_place_id=data.get("fourth_place_id"),
    )


def delete_saved_tournament() -> None:
    if DATA_FILE.exists():
        DATA_FILE.unlink()


def saved_tournament_exists() -> bool:
    return DATA_FILE.exists()

