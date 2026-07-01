import random
from itertools import combinations
from typing import Optional

from core.models import Tournament, Team, Group, Match


# ------------------------------------------------------------
# UTILITÀ BASE
# ------------------------------------------------------------

def get_team_name(tournament: Tournament, team_id: Optional[int]) -> str:
    if team_id is None:
        return "Da definire"

    for team in tournament.teams:
        if team.id == team_id:
            return team.name

    return "Squadra sconosciuta"


def get_match_by_id(tournament: Tournament, match_id: int) -> Optional[Match]:
    for match in tournament.matches:
        if match.id == match_id:
            return match
    return None


def get_group_by_name(tournament: Tournament, group_name: str) -> Optional[Group]:
    for group in tournament.groups:
        if group.name == group_name:
            return group
    return None


def get_unplayed_matches(tournament: Tournament) -> list[Match]:
    return [
        match for match in tournament.matches
        if match.team1_id is not None
        and match.team2_id is not None
        and not match.is_played()
    ]


# ------------------------------------------------------------
# CREAZIONE TORNEO / SQUADRE
# ------------------------------------------------------------

def create_tournament(name: str) -> Tournament:
    return Tournament(name=name)


def add_team(tournament: Tournament, player1: str, player2: str, team_name: str = "") -> None:
    team = Team(
        id=tournament.next_team_id,
        player1=player1.strip(),
        player2=player2.strip(),
        team_name=team_name.strip(),
    )
    tournament.teams.append(team)
    tournament.next_team_id += 1


def remove_team(tournament: Tournament, team_id: int) -> None:
    tournament.teams = [team for team in tournament.teams if team.id != team_id]


# ------------------------------------------------------------
# LOGICA GIRONE
# ------------------------------------------------------------

def choose_number_of_groups(num_teams: int) -> int:
    """
    Sceglie il numero di gironi secondo la versione finale.

    Regole:
    - numero gironi sempre potenza di 2;
    - fino a 7 squadre sono ammessi gironi da 3;
    - da 8 squadre in su si preferiscono gironi da almeno 4;
    - si accettano gironi da 3 nei casi di transizione
      per evitare gironi troppo grandi;
    - preferibilmente nessun girone oltre 6, ma nei casi limite
      si accettano 7/8 se necessario.

    Intervalli principali:
    6–7    -> 2 gironi
    8–12   -> 2 gironi
    13–15  -> 4 gironi
    16–24  -> 4 gironi
    25–31  -> 8 gironi
    32–48  -> 8 gironi
    49–63  -> 16 gironi
    64–96  -> 16 gironi
    """

    if num_teams < 6:
        return 1

    possible_groups = []

    g = 1
    while g <= num_teams:
        min_size = num_teams // g
        max_size = min_size + (1 if num_teams % g else 0)

        if g >= 2:
            if num_teams <= 7:
                valid = min_size >= 3
            else:
                # Regola elastica: preferiamo minimo 4,
                # ma accettiamo minimo 3 se così evitiamo gironi troppo grandi.
                valid = min_size >= 3

            if valid:
                avg_size = num_teams / g
                distance_from_4 = abs(avg_size - 4)
                penalty_large_groups = max(0, max_size - 6)
                penalty_small_groups = max(0, 4 - min_size)

                score = (
                    distance_from_4,
                    penalty_large_groups,
                    penalty_small_groups,
                    -g,
                )

                possible_groups.append((score, g))

        g *= 2

    if not possible_groups:
        return 1

    possible_groups.sort(key=lambda x: x[0])
    return possible_groups[0][1]


def distribute_teams_into_groups(team_ids: list[int], num_groups: int) -> list[Group]:
    shuffled = team_ids[:]
    random.shuffle(shuffled)

    groups = [
        Group(name=chr(ord("A") + i), team_ids=[])
        for i in range(num_groups)
    ]

    for index, team_id in enumerate(shuffled):
        groups[index % num_groups].team_ids.append(team_id)

    return groups


def generate_group_matches(tournament: Tournament) -> None:
    for group in tournament.groups:
        for team1_id, team2_id in combinations(group.team_ids, 2):
            match = Match(
                id=tournament.next_match_id,
                round_name="Girone",
                group_name=group.name,
                team1_id=team1_id,
                team2_id=team2_id,
                best_of=1,
            )
            tournament.matches.append(match)
            tournament.next_match_id += 1


def create_groups_and_matches(tournament: Tournament) -> None:
    tournament.groups.clear()
    tournament.matches.clear()

    tournament.champion_id = None
    tournament.runner_up_id = None
    tournament.third_place_id = None
    tournament.fourth_place_id = None
    tournament.next_match_id = 1

    num_teams = len(tournament.teams)
    num_groups = choose_number_of_groups(num_teams)

    team_ids = [team.id for team in tournament.teams]
    tournament.groups = distribute_teams_into_groups(team_ids, num_groups)

    generate_group_matches(tournament)


# ------------------------------------------------------------
# RISULTATI
# ------------------------------------------------------------

def record_match_result(
    tournament: Tournament,
    match_id: int,
    winner_id: int,
    team1_score: Optional[int] = None,
    team2_score: Optional[int] = None,
    team1_wins: int = 0,
    team2_wins: int = 0,
) -> None:
    match = get_match_by_id(tournament, match_id)

    if match is None:
        raise ValueError("Partita non trovata.")

    if match.team1_id is None or match.team2_id is None:
        raise ValueError("La partita non ha entrambe le squadre assegnate.")

    if winner_id not in [match.team1_id, match.team2_id]:
        raise ValueError("Il vincitore non partecipa a questa partita.")

    loser_id = match.team2_id if winner_id == match.team1_id else match.team1_id

    if match.best_of == 1:
        match.team1_score = team1_score
        match.team2_score = team2_score
        match.team1_wins = 1 if winner_id == match.team1_id else 0
        match.team2_wins = 1 if winner_id == match.team2_id else 0

    elif match.best_of == 3:
        required_wins = match.required_wins()

        if max(team1_wins, team2_wins) != required_wins:
            raise ValueError("In un Best of 3 una squadra deve arrivare a 2 vittorie.")

        if team1_wins == team2_wins:
            raise ValueError("Il risultato del Best of 3 non può essere in pareggio.")

        if team1_wins + team2_wins not in [2, 3]:
            raise ValueError("Un Best of 3 può finire solo 2-0 o 2-1.")

        computed_winner_id = match.team1_id if team1_wins > team2_wins else match.team2_id

        if computed_winner_id != winner_id:
            raise ValueError("Il vincitore non coincide con il risultato del Best of 3.")

        match.team1_wins = team1_wins
        match.team2_wins = team2_wins
        match.team1_score = team1_score
        match.team2_score = team2_score

    else:
        raise ValueError("Formato partita non supportato.")

    match.winner_id = winner_id
    match.loser_id = loser_id

    advance_winner_and_loser(tournament, match)


def advance_winner_and_loser(tournament: Tournament, match: Match) -> None:
    if match.winner_id is None:
        return

    if match.next_match_id is not None:
        next_match = get_match_by_id(tournament, match.next_match_id)

        if next_match is not None:
            if match.next_match_slot == 1:
                next_match.team1_id = match.winner_id
            elif match.next_match_slot == 2:
                next_match.team2_id = match.winner_id

    if match.loser_id is not None and match.third_place_match_id is not None:
        third_match = get_match_by_id(tournament, match.third_place_match_id)

        if third_match is not None:
            if match.third_place_match_slot == 1:
                third_match.team1_id = match.loser_id
            elif match.third_place_match_slot == 2:
                third_match.team2_id = match.loser_id

    update_podium_if_needed(tournament)


def update_podium_if_needed(tournament: Tournament) -> None:
    final_match = None
    third_place_match = None

    for match in tournament.matches:
        if match.round_name == "Finale":
            final_match = match
        elif match.round_name == "Finale 3°/4° posto":
            third_place_match = match

    if final_match and final_match.is_played():
        tournament.champion_id = final_match.winner_id
        tournament.runner_up_id = final_match.loser_id

    if third_place_match and third_place_match.is_played():
        tournament.third_place_id = third_place_match.winner_id
        tournament.fourth_place_id = third_place_match.loser_id


# ------------------------------------------------------------
# CLASSIFICHE GIRONI
# ------------------------------------------------------------

def compute_group_standings(tournament: Tournament, group_name: str) -> list[dict]:
    group = get_group_by_name(tournament, group_name)

    if group is None:
        return []

    standings = {
        team_id: {
            "team_id": team_id,
            "team_name": get_team_name(tournament, team_id),
            "played": 0,
            "wins": 0,
            "losses": 0,
            "points": 0,
            "points_for": 0,
            "points_against": 0,
            "point_difference": 0,
        }
        for team_id in group.team_ids
    }

    group_matches = [
        match for match in tournament.matches
        if match.round_name == "Girone"
        and match.group_name == group_name
        and match.is_played()
    ]

    for match in group_matches:
        if match.team1_id is None or match.team2_id is None:
            continue

        t1 = standings[match.team1_id]
        t2 = standings[match.team2_id]

        t1["played"] += 1
        t2["played"] += 1

        if match.winner_id == match.team1_id:
            t1["wins"] += 1
            t1["points"] += 3
            t2["losses"] += 1
        elif match.winner_id == match.team2_id:
            t2["wins"] += 1
            t2["points"] += 3
            t1["losses"] += 1

        if match.team1_score is not None and match.team2_score is not None:
            t1["points_for"] += match.team1_score
            t1["points_against"] += match.team2_score
            t2["points_for"] += match.team2_score
            t2["points_against"] += match.team1_score

    for row in standings.values():
        row["point_difference"] = row["points_for"] - row["points_against"]

    return sorted(
        standings.values(),
        key=lambda row: (
            row["points"],
            row["wins"],
            row["point_difference"],
            row["points_for"],
        ),
        reverse=True,
    )


def all_group_matches_played(tournament: Tournament) -> bool:
    group_matches = [
        match for match in tournament.matches
        if match.round_name == "Girone"
    ]

    return bool(group_matches) and all(match.is_played() for match in group_matches)


def get_qualified_per_group(num_groups: int) -> int:
    """
    Regola finale:
    - 2 gironi  -> passano prime 2 -> semifinali
    - 4 gironi  -> passano prime 2 -> quarti
    - 8 gironi  -> passano prime 2 -> ottavi
    - 16+ gironi -> passa solo prima -> ottavi o oltre
    """
    if num_groups <= 8:
        return 2
    return 1


def get_qualified_teams(tournament: Tournament) -> list[int]:
    qualified = []
    num_groups = len(tournament.groups)
    qualified_per_group = get_qualified_per_group(num_groups)

    for group in tournament.groups:
        standings = compute_group_standings(tournament, group.name)
        top_teams = standings[:qualified_per_group]
        qualified.extend(row["team_id"] for row in top_teams)

    return qualified


# ------------------------------------------------------------
# FASE FINALE
# ------------------------------------------------------------

def get_round_name(num_teams_in_round: int) -> str:
    if num_teams_in_round == 32:
        return "Sedicesimi"
    if num_teams_in_round == 16:
        return "Ottavi"
    if num_teams_in_round == 8:
        return "Quarti"
    if num_teams_in_round == 4:
        return "Semifinale"
    if num_teams_in_round == 2:
        return "Finale"
    return f"Turno da {num_teams_in_round}"


def get_best_of_for_round(round_name: str) -> int:
    if round_name in ["Semifinale", "Finale", "Finale 3°/4° posto"]:
        return 3
    return 1


def generate_final_bracket(tournament: Tournament) -> None:
    if not all_group_matches_played(tournament):
        raise ValueError("Prima di generare la fase finale bisogna completare tutti i gironi.")

    if any(match.round_name != "Girone" for match in tournament.matches):
        raise ValueError("La fase finale è già stata generata.")

    qualified = get_qualified_teams(tournament)
    random.shuffle(qualified)

    num_qualified = len(qualified)

    if num_qualified < 4:
        raise ValueError("Servono almeno 4 squadre qualificate per generare la fase finale.")

    if num_qualified & (num_qualified - 1) != 0:
        raise ValueError("Il numero di qualificate deve essere una potenza di 2.")

    round_sizes = []
    size = num_qualified

    while size >= 2:
        round_sizes.append(size)
        size //= 2

    rounds: dict[int, list[Match]] = {}

    for round_size in round_sizes:
        round_name = get_round_name(round_size)
        num_matches = round_size // 2

        rounds[round_size] = []

        for _ in range(num_matches):
            match = Match(
                id=tournament.next_match_id,
                round_name=round_name,
                team1_id=None,
                team2_id=None,
                best_of=get_best_of_for_round(round_name),
            )
            tournament.matches.append(match)
            rounds[round_size].append(match)
            tournament.next_match_id += 1

    first_round = rounds[num_qualified]

    for i, team_id in enumerate(qualified):
        match_index = i // 2
        slot = 1 if i % 2 == 0 else 2

        if slot == 1:
            first_round[match_index].team1_id = team_id
        else:
            first_round[match_index].team2_id = team_id

    for round_size in round_sizes:
        if round_size == 2:
            continue

        current_round = rounds[round_size]
        next_round = rounds[round_size // 2]

        for i, match in enumerate(current_round):
            next_match = next_round[i // 2]
            match.next_match_id = next_match.id
            match.next_match_slot = 1 if i % 2 == 0 else 2

    semifinals = rounds.get(4, [])

    if len(semifinals) == 2:
        third_place_match = Match(
            id=tournament.next_match_id,
            round_name="Finale 3°/4° posto",
            team1_id=None,
            team2_id=None,
            best_of=3,
        )
        tournament.matches.append(third_place_match)
        tournament.next_match_id += 1

        semifinals[0].third_place_match_id = third_place_match.id
        semifinals[0].third_place_match_slot = 1

        semifinals[1].third_place_match_id = third_place_match.id
        semifinals[1].third_place_match_slot = 2


# ------------------------------------------------------------
# RIEPILOGHI
# ------------------------------------------------------------

def get_group_sizes_summary(tournament: Tournament) -> str:
    sizes = [len(group.team_ids) for group in tournament.groups]
    return " + ".join(str(size) for size in sorted(sizes, reverse=True))


def get_final_phase_start_name(tournament: Tournament) -> str:
    num_groups = len(tournament.groups)
    qualified_per_group = get_qualified_per_group(num_groups)
    total_qualified = num_groups * qualified_per_group
    return get_round_name(total_qualified)


def get_tournament_setup_summary(tournament: Tournament) -> dict:
    num_groups = len(tournament.groups)
    qualified_per_group = get_qualified_per_group(num_groups) if num_groups > 0 else 0

    return {
        "num_teams": len(tournament.teams),
        "num_groups": num_groups,
        "group_sizes": get_group_sizes_summary(tournament),
        "qualified_per_group": qualified_per_group,
        "total_qualified": num_groups * qualified_per_group,
        "final_phase_start": get_final_phase_start_name(tournament) if num_groups > 0 else "Non definita",
    }