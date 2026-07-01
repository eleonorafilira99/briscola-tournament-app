import math
import random
from typing import Optional

from core.models import Group, Match, Team, Tournament


MAX_GROUP_SIZE = 4
HANDS_PER_MATCH = 3
POINTS_PER_HAND = 120


def create_teams(team_names: list[str]) -> list[Team]:
    return [
        Team(id=index, name=name.strip())
        for index, name in enumerate(team_names, start=1)
    ]


def get_team_name(tournament: Tournament, team_id: Optional[int]) -> str:
    if team_id is None:
        return "BYE"

    for team in tournament.teams:
        if team.id == team_id:
            return team.name

    return f"Squadra sconosciuta {team_id}"


def create_groups(tournament: Tournament) -> None:
    team_ids = [team.id for team in tournament.teams]
    random.shuffle(team_ids)

    number_of_groups = math.ceil(len(team_ids) / MAX_GROUP_SIZE)
    raw_groups: list[list[int]] = [[] for _ in range(number_of_groups)]

    for index, team_id in enumerate(team_ids):
        raw_groups[index % number_of_groups].append(team_id)

    tournament.groups = [
        Group(name=chr(ord("A") + index), team_ids=group_team_ids)
        for index, group_team_ids in enumerate(raw_groups)
    ]


def create_match(
    match_id: int,
    stage: str,
    round_name: str,
    team1_id: Optional[int],
    team2_id: Optional[int],
) -> Match:
    return Match(
        id=match_id,
        stage=stage,
        round_name=round_name,
        team1_id=team1_id,
        team2_id=team2_id,
    )


def round_robin_pairings(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    ids: list[Optional[int]] = list(team_ids)

    if len(ids) % 2 == 1:
        ids.append(None)

    number_of_teams = len(ids)
    rounds: list[list[tuple[int, int]]] = []

    for _ in range(number_of_teams - 1):
        current_round: list[tuple[int, int]] = []

        for index in range(number_of_teams // 2):
            team1 = ids[index]
            team2 = ids[number_of_teams - 1 - index]

            if team1 is not None and team2 is not None:
                current_round.append((team1, team2))

        rounds.append(current_round)

        ids = [ids[0]] + [ids[-1]] + ids[1:-1]

    return rounds


def create_group_schedule(tournament: Tournament) -> None:
    matches: list[Match] = []
    next_match_id = 1

    for group in tournament.groups:
        group_rounds = round_robin_pairings(group.team_ids)

        for round_index, pairings in enumerate(group_rounds, start=1):
            round_name = f"Girone {group.name} - Turno {round_index}"

            for team1_id, team2_id in pairings:
                matches.append(
                    create_match(
                        match_id=next_match_id,
                        stage="group",
                        round_name=round_name,
                        team1_id=team1_id,
                        team2_id=team2_id,
                    )
                )
                next_match_id += 1

    tournament.matches = matches


def create_tournament_from_team_names(team_names: list[str]) -> Tournament:
    cleaned_names = [name.strip() for name in team_names if name.strip()]
    tournament = Tournament(teams=create_teams(cleaned_names))

    create_groups(tournament)
    create_group_schedule(tournament)

    return tournament


def determine_match_winner(match: Match) -> int:
    hands_team1 = 0
    hands_team2 = 0

    for score1, score2 in zip(match.scores_team1, match.scores_team2):
        if score1 > score2:
            hands_team1 += 1
        elif score2 > score1:
            hands_team2 += 1

    if hands_team1 > hands_team2:
        return match.team1_id

    if hands_team2 > hands_team1:
        return match.team2_id

    total1 = match.total_team1()
    total2 = match.total_team2()

    if total1 > total2:
        return match.team1_id

    if total2 > total1:
        return match.team2_id

    return match.team1_id


def register_match_result(match: Match, scores_team1: list[int]) -> Match:
    if match.team1_id is None or match.team2_id is None:
        raise ValueError("Non è possibile registrare il risultato di una partita con BYE.")

    if len(scores_team1) != HANDS_PER_MATCH:
        raise ValueError(f"Devono essere inseriti esattamente {HANDS_PER_MATCH} punteggi.")

    for score in scores_team1:
        if score < 0 or score > POINTS_PER_HAND:
            raise ValueError("Ogni punteggio deve essere compreso tra 0 e 120.")

    scores_team2 = [POINTS_PER_HAND - score for score in scores_team1]

    match.scores_team1 = scores_team1
    match.scores_team2 = scores_team2
    match.winner_id = determine_match_winner(match)
    match.played = True

    return match


def compute_group_standings(tournament: Tournament, group: Group) -> list[dict]:
    standings = []

    for team_id in group.team_ids:
        played = 0
        wins = 0
        losses = 0
        tournament_points = 0
        points_for = 0
        points_against = 0

        for match in tournament.matches:
            if match.stage != "group" or not match.played:
                continue

            if team_id not in [match.team1_id, match.team2_id]:
                continue

            played += 1

            if team_id == match.team1_id:
                pf = match.total_team1()
                pa = match.total_team2()
            else:
                pf = match.total_team2()
                pa = match.total_team1()

            points_for += pf
            points_against += pa

            if match.winner_id == team_id:
                wins += 1
                tournament_points += 2
            else:
                losses += 1

        standings.append(
            {
                "team_id": team_id,
                "team_name": get_team_name(tournament, team_id),
                "played": played,
                "wins": wins,
                "losses": losses,
                "tournament_points": tournament_points,
                "points_for": points_for,
                "points_against": points_against,
                "point_diff": points_for - points_against,
            }
        )

    standings.sort(
        key=lambda row: (
            row["tournament_points"],
            row["point_diff"],
            row["points_for"],
        ),
        reverse=True,
    )

    return standings


def all_group_matches_played(tournament: Tournament) -> bool:
    group_matches = [match for match in tournament.matches if match.stage == "group"]
    return bool(group_matches) and all(match.played for match in group_matches)


def get_group_qualified_teams(
    tournament: Tournament,
    teams_per_group: int = 2,
) -> list[int]:
    qualified: list[int] = []

    for group in tournament.groups:
        standings = compute_group_standings(tournament, group)
        qualified.extend(row["team_id"] for row in standings[:teams_per_group])

    return qualified


def final_stage_exists(tournament: Tournament) -> bool:
    return any(match.stage == "final" for match in tournament.matches)


def get_final_matches(tournament: Tournament) -> list[Match]:
    return [match for match in tournament.matches if match.stage == "final"]


def get_next_match_id(tournament: Tournament) -> int:
    if not tournament.matches:
        return 1

    return max(match.id for match in tournament.matches) + 1


def get_final_round_name(number_of_teams: int) -> str:
    if number_of_teams == 2:
        return "Finale"

    if number_of_teams <= 4:
        return "Semifinale"

    if number_of_teams <= 8:
        return "Quarto di finale"

    if number_of_teams <= 16:
        return "Ottavo di finale"

    return "Fase finale"


def get_round_order(round_name: str) -> int:
    order = {
        "Ottavo di finale": 1,
        "Quarto di finale": 2,
        "Semifinale": 3,
        "Finale": 4,
        "Finale 3° posto": 4,
    }

    return order.get(round_name, 0)


def get_current_final_round_matches(tournament: Tournament) -> list[Match]:
    final_matches = get_final_matches(tournament)

    if not final_matches or tournament.champion_id is not None:
        return []

    active_matches = []

    for match in final_matches:
        if match.round_name == "Finale 3° posto":
            continue

        if not match.played:
            active_matches.append(match)

    if active_matches:
        min_order = min(get_round_order(match.round_name) for match in active_matches)
        return [
            match for match in final_matches
            if get_round_order(match.round_name) == min_order
        ]

    unfinished_final_or_third = [
        match for match in final_matches
        if match.round_name in ["Finale", "Finale 3° posto"]
        and not match.played
    ]

    if unfinished_final_or_third:
        return [
            match for match in final_matches
            if match.round_name in ["Finale", "Finale 3° posto"]
        ]

    last_order = max(get_round_order(match.round_name) for match in final_matches)

    return [
        match for match in final_matches
        if get_round_order(match.round_name) == last_order
    ]


def create_final_stage(tournament: Tournament) -> None:
    if final_stage_exists(tournament):
        raise ValueError("La fase finale è già stata generata.")

    if not all_group_matches_played(tournament):
        raise ValueError("Prima devono essere giocate tutte le partite dei gironi.")

    qualified = get_group_qualified_teams(tournament, teams_per_group=2)

    if len(qualified) < 2:
        raise ValueError("Non ci sono abbastanza squadre qualificate.")

    random.shuffle(qualified)

    if len(qualified) % 2 == 1:
        qualified.append(None)

    real_teams_count = len([team_id for team_id in qualified if team_id is not None])
    round_name = get_final_round_name(real_teams_count)

    next_match_id = get_next_match_id(tournament)
    final_matches: list[Match] = []

    for index in range(0, len(qualified), 2):
        team1_id = qualified[index]
        team2_id = qualified[index + 1]

        match = create_match(
            match_id=next_match_id,
            stage="final",
            round_name=round_name,
            team1_id=team1_id,
            team2_id=team2_id,
        )

        if team1_id is not None and team2_id is None:
            match.winner_id = team1_id
            match.played = True

        final_matches.append(match)
        next_match_id += 1

    tournament.matches.extend(final_matches)


def current_final_round_is_complete(tournament: Tournament) -> bool:
    current_round_matches = get_current_final_round_matches(tournament)

    if not current_round_matches:
        return False

    return all(match.played for match in current_round_matches)


def get_next_round_name(current_round_name: str) -> str:
    if current_round_name == "Ottavo di finale":
        return "Quarto di finale"

    if current_round_name == "Quarto di finale":
        return "Semifinale"

    if current_round_name == "Semifinale":
        return "Finale"

    return "Campione"


def get_match_loser(match: Match) -> Optional[int]:
    if match.winner_id is None:
        return None

    if match.winner_id == match.team1_id:
        return match.team2_id

    return match.team1_id


def get_real_losers(matches: list[Match]) -> list[int]:
    losers = []

    for match in matches:
        loser = get_match_loser(match)
        if loser is not None:
            losers.append(loser)

    return losers


def create_final_and_third_place_from_semifinals(
    tournament: Tournament,
    semifinal_matches: list[Match],
) -> None:
    winners = [
        match.winner_id
        for match in semifinal_matches
        if match.winner_id is not None
    ]

    losers = get_real_losers(semifinal_matches)

    if len(winners) != 2:
        raise ValueError("Le semifinali non sono complete.")

    next_match_id = get_next_match_id(tournament)

    final_match = create_match(
        match_id=next_match_id,
        stage="final",
        round_name="Finale",
        team1_id=winners[0],
        team2_id=winners[1],
    )

    tournament.matches.append(final_match)

    if len(losers) == 2:
        third_place_match = create_match(
            match_id=next_match_id + 1,
            stage="final",
            round_name="Finale 3° posto",
            team1_id=losers[0],
            team2_id=losers[1],
        )

        tournament.matches.append(third_place_match)

    elif len(losers) == 1:
        tournament.third_place_id = losers[0]


def close_tournament_from_finals(tournament: Tournament, final_matches: list[Match]) -> None:
    final_match = next(
        (
            match for match in final_matches
            if match.round_name == "Finale"
        ),
        None,
    )

    if final_match is None or not final_match.played:
        raise ValueError("La finale 1°/2° posto non è completa.")

    tournament.champion_id = final_match.winner_id
    tournament.runner_up_id = get_match_loser(final_match)

    third_place_match = next(
        (
            match for match in final_matches
            if match.round_name == "Finale 3° posto"
        ),
        None,
    )

    if third_place_match is not None:
        if not third_place_match.played:
            raise ValueError("La finale 3°/4° posto non è completa.")

        tournament.third_place_id = third_place_match.winner_id
        tournament.fourth_place_id = get_match_loser(third_place_match)


def advance_final_stage(tournament: Tournament) -> None:
    if not final_stage_exists(tournament):
        raise ValueError("La fase finale non è ancora stata generata.")

    current_round_matches = get_current_final_round_matches(tournament)

    if not current_round_matches:
        raise ValueError("Non ci sono partite di fase finale.")

    if not all(match.played for match in current_round_matches):
        raise ValueError("Prima devono essere giocate tutte le partite del turno corrente.")

    current_round_name = current_round_matches[0].round_name

    if current_round_name == "Finale":
        close_tournament_from_finals(tournament, current_round_matches)
        return

    if current_round_name == "Semifinale":
        create_final_and_third_place_from_semifinals(tournament, current_round_matches)
        return

    winners = [
        match.winner_id
        for match in current_round_matches
        if match.winner_id is not None
    ]

    if len(winners) == 1:
        tournament.champion_id = winners[0]
        return

    if len(winners) % 2 == 1:
        winners.append(None)

    next_round_name = get_next_round_name(current_round_name)
    next_match_id = get_next_match_id(tournament)

    for index in range(0, len(winners), 2):
        team1_id = winners[index]
        team2_id = winners[index + 1]

        match = create_match(
            match_id=next_match_id,
            stage="final",
            round_name=next_round_name,
            team1_id=team1_id,
            team2_id=team2_id,
        )

        if team1_id is not None and team2_id is None:
            match.winner_id = team1_id
            match.played = True

        tournament.matches.append(match)
        next_match_id += 1


def can_advance_final_stage(tournament: Tournament) -> bool:
    if not final_stage_exists(tournament):
        return False

    if tournament.champion_id is not None:
        return False

    return current_final_round_is_complete(tournament)


def get_unplayed_matches(tournament: Tournament) -> list[Match]:
    return [
        match for match in tournament.matches
        if not match.played
        and match.team1_id is not None
        and match.team2_id is not None
    ]

def get_editable_played_matches(tournament: Tournament) -> list[Match]:
    editable_matches: list[Match] = []

    for match in tournament.matches:
        if not match.played:
            continue

        if match.team1_id is None or match.team2_id is None:
            continue

        if match.stage == "group":
            if not final_stage_exists(tournament):
                editable_matches.append(match)

        elif match.stage == "final":
            current_round_matches = get_current_final_round_matches(tournament)

            current_round_ids = {m.id for m in current_round_matches}

            if match.id in current_round_ids:
                editable_matches.append(match)

    return editable_matches