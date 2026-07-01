import streamlit as st

from core.models import Tournament
from core.tournament import (
    add_team,
    all_group_matches_played,
    compute_group_standings,
    create_groups_and_matches,
    create_tournament,
    generate_final_bracket,
    get_group_sizes_summary,
    get_match_by_id,
    get_qualified_per_group,
    get_team_name,
    get_tournament_setup_summary,
    get_unplayed_matches,
    record_match_result,
    remove_team,
)


# ------------------------------------------------------------
# CONFIGURAZIONE PAGINA
# ------------------------------------------------------------

st.set_page_config(
    page_title="Torneo di Briscola",
    page_icon="🃏",
    layout="wide",
)


# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------

if "tournament" not in st.session_state:
    st.session_state.tournament = None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# ------------------------------------------------------------
# FUNZIONI UI
# ------------------------------------------------------------

def is_admin() -> bool:
    return st.session_state.is_admin


def show_podium(tournament: Tournament) -> None:
    st.subheader("🏆 Podio")

    if tournament.champion_id:
        st.success(f"🥇 1° posto: {get_team_name(tournament, tournament.champion_id)}")

    if tournament.runner_up_id:
        st.info(f"🥈 2° posto: {get_team_name(tournament, tournament.runner_up_id)}")

    if tournament.third_place_id:
        st.warning(f"🥉 3° posto: {get_team_name(tournament, tournament.third_place_id)}")

    if tournament.fourth_place_id:
        st.write(f"4° posto: {get_team_name(tournament, tournament.fourth_place_id)}")


def show_match_label(tournament: Tournament, match) -> str:
    formato = "Best of 3" if match.best_of == 3 else "Partita secca"

    return (
        f"ID {match.id} — "
        f"{get_team_name(tournament, match.team1_id)} vs "
        f"{get_team_name(tournament, match.team2_id)} — "
        f"{match.round_name} — {formato}"
    )


def show_groups(tournament: Tournament) -> None:
    st.subheader("Gironi")

    if not tournament.groups:
        st.info("I gironi non sono ancora stati generati.")
        return

    for group in tournament.groups:
        with st.expander(f"Girone {group.name} — {len(group.team_ids)} squadre", expanded=True):
            for team_id in group.team_ids:
                st.write(f"- {get_team_name(tournament, team_id)}")


def show_group_standings(tournament: Tournament) -> None:
    st.subheader("Classifiche gironi")

    if not tournament.groups:
        st.info("I gironi non sono ancora stati generati.")
        return

    for group in tournament.groups:
        standings = compute_group_standings(tournament, group.name)

        st.markdown(f"### Girone {group.name}")

        if not standings:
            st.info("Nessuna classifica disponibile.")
            continue

        table_data = []
        for i, row in enumerate(standings, start=1):
            table_data.append(
                {
                    "Pos.": i,
                    "Squadra": row["team_name"],
                    "Giocate": row["played"],
                    "Vinte": row["wins"],
                    "Perse": row["losses"],
                    "Punti": row["points"],
                    "PF": row["points_for"],
                    "PS": row["points_against"],
                    "Diff.": row["point_difference"],
                }
            )

        st.dataframe(table_data, use_container_width=True)


def show_matches(tournament: Tournament) -> None:
    st.subheader("Partite")

    if not tournament.matches:
        st.info("Non ci sono ancora partite.")
        return

    rounds_order = [
        "Girone",
        "Sedicesimi",
        "Ottavi",
        "Quarti",
        "Semifinale",
        "Finale 3°/4° posto",
        "Finale",
    ]

    for round_name in rounds_order:
        round_matches = [
            match for match in tournament.matches
            if match.round_name == round_name
        ]

        if not round_matches:
            continue

        st.markdown(f"### {round_name}")

        table_data = []
        for match in round_matches:
            if match.is_played():
                result = f"Vince {get_team_name(tournament, match.winner_id)}"

                if match.best_of == 3:
                    result += f" ({match.team1_wins}-{match.team2_wins})"
                elif match.team1_score is not None and match.team2_score is not None:
                    result += f" ({match.team1_score}-{match.team2_score})"
            else:
                result = "Da giocare"

            table_data.append(
                {
                    "ID": match.id,
                    "Girone": match.group_name or "",
                    "Squadra 1": get_team_name(tournament, match.team1_id),
                    "Squadra 2": get_team_name(tournament, match.team2_id),
                    "Formato": "Best of 3" if match.best_of == 3 else "Secca",
                    "Risultato": result,
                }
            )

        st.dataframe(table_data, use_container_width=True)


def show_final_bracket(tournament: Tournament) -> None:
    st.subheader("Tabellone finale")

    knockout_matches = [
        match for match in tournament.matches
        if match.round_name != "Girone"
    ]

    if not knockout_matches:
        st.info("Il tabellone finale non è ancora stato generato.")
        return

    rounds_order = [
        "Sedicesimi",
        "Ottavi",
        "Quarti",
        "Semifinale",
        "Finale 3°/4° posto",
        "Finale",
    ]

    for round_name in rounds_order:
        round_matches = [
            match for match in knockout_matches
            if match.round_name == round_name
        ]

        if not round_matches:
            continue

        st.markdown(f"### {round_name}")

        for match in round_matches:
            formato = "Best of 3" if match.best_of == 3 else "Partita secca"

            if match.is_played():
                st.write(
                    f"**ID {match.id}** — "
                    f"{get_team_name(tournament, match.team1_id)} vs "
                    f"{get_team_name(tournament, match.team2_id)} — "
                    f"{formato} — "
                    f"✅ Vince **{get_team_name(tournament, match.winner_id)}**"
                )
            else:
                st.write(
                    f"**ID {match.id}** — "
                    f"{get_team_name(tournament, match.team1_id)} vs "
                    f"{get_team_name(tournament, match.team2_id)} — "
                    f"{formato}"
                )


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------

st.sidebar.title("🃏 Torneo Briscola")

page = st.sidebar.radio(
    "Menu",
    [
        "Regolamento torneo",
        "Setup torneo",
        "Gironi",
        "Inserisci risultati",
        "Classifiche",
        "Fase finale",
        "Podio",
    ],
)

st.sidebar.divider()

if not st.session_state.is_admin:
    password = st.sidebar.text_input("Password admin", type="password")

    if st.sidebar.button("Login admin"):
        if password == st.secrets["ADMIN_PASSWORD"]:
            st.session_state.is_admin = True
            st.sidebar.success("Accesso admin effettuato.")
            st.rerun()
        else:
            st.sidebar.error("Password errata.")
else:
    st.sidebar.success("Admin attivo")

    if st.sidebar.button("Logout"):
        st.session_state.is_admin = False
        st.rerun()


# ------------------------------------------------------------
# TITOLO
# ------------------------------------------------------------

st.title("🃏 Torneo di Briscola")

# ------------------------------------------------------------
# REGOLAMENTO TORNEO
# ------------------------------------------------------------

if page == "Regolamento torneo":
    st.header("Benvenuti al Torneo di Briscola organizzato da Sanbe Burger 🍔")

    st.markdown("""
Di seguito trovate una breve spiegazione di come si svolgerà il torneo.

---

## 1️⃣ Fase a gironi

All’inizio del torneo, tutte le coppie iscritte verranno suddivise automaticamente in **gironi equilibrati**, cercando di distribuire le squadre nel modo più uniforme possibile.

In genere ogni girone sarà composto da **4–6 coppie**.

Durante questa fase, ogni coppia affronterà le altre coppie del proprio girone.

Tutte le partite dei gironi si giocano in:

➡️ **Partita secca**  
(chi vince la partita conquista il match)

---

## 2️⃣ Accesso alla fase finale

Al termine dei gironi, le migliori coppie di ciascun girone si qualificano alla fase finale.

Il numero di coppie qualificate dipende dal numero totale di gironi:

- con **2 gironi** → passano le **prime 2**
- con **4 gironi** → passano le **prime 2**
- con **8 gironi** → passano le **prime 2**
- con **16 gironi** → passa solo la **prima classificata**

---

## 3️⃣ Fase finale a eliminazione diretta

Da qui in avanti non si può più sbagliare:  
chi perde viene eliminato.

A seconda del numero di coppie qualificate, il tabellone finale può iniziare da:

- **Semifinali**
- **Quarti di finale**
- **Ottavi di finale**

---

## Come si giocano le finali?

### Ottavi e Quarti
➡️ **Partita secca**

### Semifinali
➡️ **Al meglio delle 3 partite**  
(vince chi arriva per primo a 2 vittorie)

### Finale 3°–4° posto
➡️ **Al meglio delle 3 partite**

### Finale 1°–2° posto
➡️ **Al meglio delle 3 partite**

---

## Come viene calcolata la classifica dei gironi?

In caso di parità, la classifica viene ordinata considerando:

1. Punti conquistati  
2. Numero di vittorie  
3. Differenza punti  
4. Punti totali realizzati  

---
                
## Premi

Le prime 3 coppie classificate riceveranno i seguenti premi:

🥇 **1° premio**  
Panino + bevanda + fritto gratis

🥈 **2° premio**  
Bevanda + fritto gratis

🥉 **3° premio**  
Fritto gratis

---

🏆 **Buon divertimento e buona fortuna a tutti!**
""")

# ------------------------------------------------------------
# SETUP TORNEO
# ------------------------------------------------------------

if page == "Setup torneo":
    st.header("Setup torneo")

    if st.session_state.tournament is None:
        tournament_name = st.text_input("Nome torneo", value="Torneo di Briscola")

        if st.button("Crea torneo"):
            st.session_state.tournament = create_tournament(tournament_name)
            st.success("Torneo creato.")
            st.rerun()

    else:
        tournament = st.session_state.tournament

        st.subheader(tournament.name)

        if not is_admin():
            st.warning("Solo l'admin può modificare il setup.")
        else:
            st.markdown("### Aggiungi coppia")

            with st.form("add_team_form"):
                team_name = st.text_input("Nome squadra")
                player1 = st.text_input("Giocatore 1")
                player2 = st.text_input("Giocatore 2")
                submitted = st.form_submit_button("Aggiungi coppia")

                if submitted:
                    if player1.strip() and player2.strip():
                        add_team(tournament, player1, player2, team_name)
                        st.success("Coppia aggiunta.")
                        st.rerun()
                    else:
                        st.error("Inserisci entrambi i nomi dei giocatori e della squadra.")

        st.markdown("### Coppie iscritte")

        if not tournament.teams:
            st.info("Nessuna coppia iscritta.")
        else:
            for team in tournament.teams:
                col1, col2 = st.columns([4, 1])
                if team.team_name.strip():
                    col1.write(f"**{team.id}** — {team.team_name} ({team.players_label})")
                else:
                    col1.write(f"**{team.id}** — {team.players_label}")

                if is_admin() and not tournament.groups:
                    if col2.button("Rimuovi", key=f"remove_team_{team.id}"):
                        remove_team(tournament, team.id)
                        st.rerun()

        st.divider()

        st.markdown("### Generazione gironi")

        num_teams = len(tournament.teams)

        if num_teams < 6:
            st.warning("Servono almeno 6 coppie per generare il torneo.")
        else:
            st.info(
                "Regola attiva: numero di gironi potenza di 2; "
                "gironi preferibilmente da 4–6 squadre; "
                "fino a 8 gironi passano le prime due; "
                "da 16 gironi passa solo la prima."
            )

            if is_admin():
                if st.button("Genera gironi e partite"):
                    create_groups_and_matches(tournament)
                    st.success("Gironi e partite generati.")
                    st.rerun()

        if tournament.groups:
            summary = get_tournament_setup_summary(tournament)

            st.success("Gironi già generati.")

            st.write(f"**Squadre:** {summary['num_teams']}")
            st.write(f"**Gironi:** {summary['num_groups']}")
            st.write(f"**Dimensione gironi:** {summary['group_sizes']}")
            st.write(f"**Qualificate per girone:** {summary['qualified_per_group']}")
            st.write(f"**Totale qualificate:** {summary['total_qualified']}")
            st.write(f"**Fase finale iniziale:** {summary['final_phase_start']}")

        st.divider()

        if is_admin():
            if st.button("Reset completo torneo"):
                st.session_state.tournament = None
                st.rerun()


# ------------------------------------------------------------
# GIRONI
# ------------------------------------------------------------

elif page == "Gironi":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        show_groups(tournament)
        st.divider()
        show_matches(tournament)


# ------------------------------------------------------------
# INSERISCI RISULTATI
# ------------------------------------------------------------

elif page == "Inserisci risultati":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        st.subheader("Inserisci risultati")

        if not is_admin():
            st.warning("Solo l'admin può inserire i risultati.")
            st.stop()

        unplayed_matches = get_unplayed_matches(tournament)

        if not unplayed_matches:
            if tournament.champion_id is not None:
                st.success("Torneo concluso.")
                show_podium(tournament)
            else:
                st.success("Non ci sono partite da giocare al momento.")
                st.info("Vai nella sezione Fase finale per generare il turno successivo, se disponibile.")
        else:
            match_options = {
                show_match_label(tournament, match): match.id
                for match in unplayed_matches
            }

            selected_label = st.selectbox(
                "Seleziona partita",
                list(match_options.keys()),
            )

            selected_match_id = match_options[selected_label]
            match = get_match_by_id(tournament, selected_match_id)

            if match is None:
                st.error("Partita non trovata.")
                st.stop()

            st.markdown("### Dettaglio partita")
            st.write(f"**Fase:** {match.round_name}")
            st.write(f"**Formato:** {'Best of 3' if match.best_of == 3 else 'Partita secca'}")
            st.write(f"**Squadra 1:** {get_team_name(tournament, match.team1_id)}")
            st.write(f"**Squadra 2:** {get_team_name(tournament, match.team2_id)}")

            if match.best_of == 1:
                winner_id = st.radio(
                    "Vincitore",
                    [match.team1_id, match.team2_id],
                    format_func=lambda team_id: get_team_name(tournament, team_id),
                )

                col1, col2 = st.columns(2)
                with col1:
                    team1_score = st.number_input(
                        f"Punti {get_team_name(tournament, match.team1_id)}",
                        min_value=0,
                        step=1,
                        value=0,
                    )

                with col2:
                    team2_score = st.number_input(
                        f"Punti {get_team_name(tournament, match.team2_id)}",
                        min_value=0,
                        step=1,
                        value=0,
                    )

                if st.button("Salva risultato"):
                    try:
                        record_match_result(
                            tournament=tournament,
                            match_id=match.id,
                            winner_id=winner_id,
                            team1_score=team1_score,
                            team2_score=team2_score,
                        )
                        st.success("Risultato salvato.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            elif match.best_of == 3:
                st.info("Inserisci il numero di partite vinte nella serie. Il risultato deve essere 2-0 oppure 2-1.")

                col1, col2 = st.columns(2)

                with col1:
                    team1_wins = st.number_input(
                        f"Vittorie {get_team_name(tournament, match.team1_id)}",
                        min_value=0,
                        max_value=2,
                        step=1,
                        value=0,
                    )

                with col2:
                    team2_wins = st.number_input(
                        f"Vittorie {get_team_name(tournament, match.team2_id)}",
                        min_value=0,
                        max_value=2,
                        step=1,
                        value=0,
                    )

                if team1_wins > team2_wins:
                    winner_id = match.team1_id
                elif team2_wins > team1_wins:
                    winner_id = match.team2_id
                else:
                    winner_id = None

                if winner_id is not None:
                    st.write(f"Vincitore: **{get_team_name(tournament, winner_id)}**")

                if st.button("Salva risultato Best of 3"):
                    if winner_id is None:
                        st.error("Il risultato non può essere in pareggio.")
                    else:
                        try:
                            record_match_result(
                                tournament=tournament,
                                match_id=match.id,
                                winner_id=winner_id,
                                team1_wins=team1_wins,
                                team2_wins=team2_wins,
                            )
                            st.success("Risultato salvato.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))


# ------------------------------------------------------------
# CLASSIFICHE
# ------------------------------------------------------------

elif page == "Classifiche":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        show_group_standings(tournament)


# ------------------------------------------------------------
# FASE FINALE
# ------------------------------------------------------------

elif page == "Fase finale":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        st.subheader("Fase finale")

        if not tournament.groups:
            st.info("Prima genera i gironi.")
            st.stop()

        if not all_group_matches_played(tournament):
            st.warning("La fase finale può essere generata solo dopo aver completato tutte le partite dei gironi.")
            show_group_standings(tournament)
            st.stop()

        knockout_matches = [
            match for match in tournament.matches
            if match.round_name != "Girone"
        ]

        if not knockout_matches:
            num_groups = len(tournament.groups)
            qualified_per_group = get_qualified_per_group(num_groups)
            total_qualified = num_groups * qualified_per_group

            st.info(
                f"Passano {qualified_per_group} squadra/e per girone. "
                f"Totale qualificate: {total_qualified}."
            )

            if is_admin():
                if st.button("Genera tabellone finale"):
                    try:
                        generate_final_bracket(tournament)
                        st.success("Tabellone finale generato.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            else:
                st.warning("Solo l'admin può generare il tabellone finale.")
        else:
            show_final_bracket(tournament)


# ------------------------------------------------------------
# PODIO
# ------------------------------------------------------------

elif page == "Podio":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        if tournament.champion_id is None:
            st.info("Il torneo non è ancora concluso.")
        else:
            show_podium(tournament)