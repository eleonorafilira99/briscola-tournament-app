import json
from dataclasses import asdict

import streamlit as st

from core.tournament import (
    advance_final_stage,
    all_group_matches_played,
    can_advance_final_stage,
    compute_group_standings,
    create_final_stage,
    create_tournament_from_team_names,
    final_stage_exists,
    get_editable_played_matches,
    get_final_matches,
    get_team_name,
    get_unplayed_matches,
    register_match_result,
)
from data.storage import (
    delete_saved_tournament,
    load_tournament,
    save_tournament,
    saved_tournament_exists,
)
from ui.theme import apply_theme


st.set_page_config(
    page_title="Torneo di Briscola",
    page_icon="🃏",
    layout="wide",
)

apply_theme()


def is_admin() -> bool:
    return st.session_state.get("admin_authenticated", False)


def show_podium(tournament) -> None:
    if tournament.champion_id is not None:
        st.success(f"🏆 1° posto: {get_team_name(tournament, tournament.champion_id)}")

    if tournament.runner_up_id is not None:
        st.info(f"🥈 2° posto: {get_team_name(tournament, tournament.runner_up_id)}")

    if tournament.third_place_id is not None:
        st.info(f"🥉 3° posto: {get_team_name(tournament, tournament.third_place_id)}")

    if tournament.fourth_place_id is not None:
        st.info(f"4° posto: {get_team_name(tournament, tournament.fourth_place_id)}")


def reset_tournament_session() -> None:
    delete_saved_tournament()

    if "tournament" in st.session_state:
        del st.session_state["tournament"]

    if "team_count" in st.session_state:
        del st.session_state["team_count"]

    st.rerun()


if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "tournament" not in st.session_state:
    st.session_state.tournament = load_tournament()

if "team_count" not in st.session_state:
    st.session_state.team_count = 8


st.markdown(
    '<div class="main-title">🃏 Torneo di Briscola a Coppie</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">Gestione gironi, calendario, risultati, classifiche e tabellone finale.</div>',
    unsafe_allow_html=True,
)


# SIDEBAR
st.sidebar.title("Menu")

st.sidebar.markdown("### Accesso admin")

admin_password = st.sidebar.text_input(
    "Password",
    type="password",
    placeholder="Inserisci password admin",
)

try:
    expected_password = st.secrets["ADMIN_PASSWORD"]
except Exception:
    st.sidebar.error("ADMIN_PASSWORD non configurata nei Secrets.")
    expected_password = None

if st.sidebar.button("Accedi come admin"):
    if expected_password is None:
        st.sidebar.error("Configura prima ADMIN_PASSWORD nei Secrets.")
    elif admin_password == expected_password:
        st.session_state.admin_authenticated = True
        st.sidebar.success("Accesso admin effettuato.")
        st.rerun()
    else:
        st.sidebar.error("Password non corretta.")

if is_admin():
    st.sidebar.success("Modalità admin attiva")

    if st.sidebar.button("Esci da admin"):
        st.session_state.admin_authenticated = False
        st.rerun()
else:
    st.sidebar.info("Modalità consultazione")


st.sidebar.divider()
st.sidebar.markdown("### Gestione torneo")

if saved_tournament_exists():
    st.sidebar.success("Torneo salvato presente")

    if st.sidebar.button("Ricarica torneo salvato"):
        st.session_state.tournament = load_tournament()
        st.rerun()
else:
    st.sidebar.info("Nessun torneo salvato")


if st.session_state.tournament is not None:
    tournament_json = json.dumps(
        asdict(st.session_state.tournament),
        ensure_ascii=False,
        indent=4,
    )

    st.sidebar.download_button(
        label="Esporta backup JSON",
        data=tournament_json,
        file_name="backup_torneo_briscola.json",
        mime="application/json",
        use_container_width=True,
    )


if is_admin():
    confirm_reset = st.sidebar.checkbox("Confermo reset totale")

    if confirm_reset and st.sidebar.button(
        "Reset completo torneo",
        type="primary",
        use_container_width=True,
    ):
        reset_tournament_session()


page = st.sidebar.radio(
    "Sezione",
    [
        "Setup torneo",
        "Gironi",
        "Calendario",
        "Inserisci risultati",
        "Classifiche",
        "Fase finale",
    ],
)


# SETUP TORNEO
if page == "Setup torneo":
    st.markdown(
        """
        <div class="custom-card">
            <span class="badge">Step 1</span>
            <h3>Configurazione iniziale</h3>
            <p>Inserisci il numero di squadre e assegna un nome a ciascuna coppia.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not is_admin():
        st.info("Sei in modalità consultazione. Solo l'admin può creare o modificare il torneo.")

    st.session_state.team_count = st.number_input(
        "Numero di squadre",
        min_value=2,
        max_value=64,
        value=st.session_state.team_count,
        step=1,
        disabled=not is_admin(),
    )

    st.divider()

    team_names = []
    cols = st.columns(2)

    for index in range(st.session_state.team_count):
        with cols[index % 2]:
            name = st.text_input(
                f"Nome squadra {index + 1}",
                value=f"Squadra {index + 1}",
                key=f"team_name_{index}",
                disabled=not is_admin(),
            )
            team_names.append(name)

    st.divider()

    if is_admin():
        if st.button("Crea torneo", type="primary", use_container_width=True):
            cleaned_names = [name.strip() for name in team_names if name.strip()]

            if len(cleaned_names) < 2:
                st.error("Inserisci almeno 2 squadre.")
            elif len(set(name.lower() for name in cleaned_names)) != len(cleaned_names):
                st.error("Ci sono nomi squadra duplicati. Correggili prima di creare il torneo.")
            else:
                st.session_state.tournament = create_tournament_from_team_names(cleaned_names)
                save_tournament(st.session_state.tournament)
                st.success("Torneo creato correttamente e salvato.")
                st.rerun()

    if st.session_state.tournament is not None:
        tournament = st.session_state.tournament

        st.subheader("Riepilogo torneo")

        group_matches_count = len([m for m in tournament.matches if m.stage == "group"])
        final_matches_count = len([m for m in tournament.matches if m.stage == "final"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Squadre", len(tournament.teams))
        col2.metric("Gironi", len(tournament.groups))
        col3.metric("Partite gironi", group_matches_count)
        col4.metric("Partite fase finale", final_matches_count)

        show_podium(tournament)


# GIRONI
elif page == "Gironi":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        st.subheader("Gironi")

        for group in tournament.groups:
            st.markdown(
                f"""
                <div class="custom-card">
                    <span class="badge">Girone {group.name}</span>
                    <h3>Squadre</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for team_id in group.team_ids:
                st.write(f"• {get_team_name(tournament, team_id)}")


# CALENDARIO
elif page == "Calendario":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        st.subheader("Calendario")

        group_matches = [match for match in tournament.matches if match.stage == "group"]
        final_matches = [match for match in tournament.matches if match.stage == "final"]

        st.markdown("### Fase a gironi")

        for match in group_matches:
            st.markdown(
                f"""
                <div class="custom-card">
                    <span class="badge">{match.round_name}</span>
                    <h3>{get_team_name(tournament, match.team1_id)} vs {get_team_name(tournament, match.team2_id)}</h3>
                    <p><strong>ID partita:</strong> {match.id}</p>
                    <p><strong>Stato:</strong> {"Giocata" if match.played else "Da giocare"}</p>
                    <p><strong>Vincitrice:</strong> {get_team_name(tournament, match.winner_id) if match.winner_id else "-"}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if final_matches:
            st.markdown("### Fase finale")

            round_order = {
                "Ottavo di finale": 1,
                "Quarto di finale": 2,
                "Semifinale": 3,
                "Finale": 4,
                "Finale 3° posto": 4,
            }

            final_matches.sort(
                key=lambda match: (
                    round_order.get(match.round_name, 99),
                    match.id,
                )
            )

            current_round = None

            for match in final_matches:
                if match.round_name != current_round:
                    current_round = match.round_name
                    st.markdown(f"#### {current_round}")

                st.markdown(
                    f"""
                    <div class="custom-card">
                        <span class="badge">{match.round_name}</span>
                        <h3>{get_team_name(tournament, match.team1_id)} vs {get_team_name(tournament, match.team2_id)}</h3>
                        <p><strong>ID partita:</strong> {match.id}</p>
                        <p><strong>Stato:</strong> {"Giocata" if match.played else "Da giocare"}</p>
                        <p><strong>Vincitrice:</strong> {get_team_name(tournament, match.winner_id) if match.winner_id else "-"}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        show_podium(tournament)

# INSERISCI RISULTATI
elif page == "Inserisci risultati":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        st.subheader("Inserisci risultati")

        if not is_admin():
            st.warning("Solo l'admin può inserire i risultati.")
            st.stop()

        # MODIFICA RISULTATI GIÀ INSERITI
        editable_matches = get_editable_played_matches(tournament)

        if editable_matches:
            st.markdown("### Modifica risultato già inserito")

            edit_options = {
                f"ID {match.id} — {get_team_name(tournament, match.team1_id)} vs {get_team_name(tournament, match.team2_id)} — {match.round_name}": match
                for match in editable_matches
            }

            selected_edit_label = st.selectbox(
                "Seleziona partita da modificare",
                options=list(edit_options.keys()),
                key="edit_match_selectbox",
            )

            selected_edit_match = edit_options[selected_edit_label]

            st.markdown(
                f"""
                <div class="custom-card">
                    <span class="badge">{selected_edit_match.round_name}</span>
                    <h3>{get_team_name(tournament, selected_edit_match.team1_id)} vs {get_team_name(tournament, selected_edit_match.team2_id)}</h3>
                    <p>Puoi modificare questa partita perché non è ancora stata generata la fase successiva.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("edit_result_form"):
                edited_scores_team1 = []

                for hand in range(1, 4):
                    current_value = 60

                    if len(selected_edit_match.scores_team1) >= hand:
                        current_value = selected_edit_match.scores_team1[hand - 1]

                    score = st.number_input(
                        f"Modifica mano {hand} — punti {get_team_name(tournament, selected_edit_match.team1_id)}",
                        min_value=0,
                        max_value=120,
                        value=current_value,
                        step=1,
                        key=f"edit_score_{selected_edit_match.id}_{hand}",
                    )

                    st.caption(
                        f"Punti {get_team_name(tournament, selected_edit_match.team2_id)}: {120 - score}"
                    )

                    edited_scores_team1.append(score)

                submitted_edit = st.form_submit_button(
                    "Salva modifica risultato",
                    type="secondary",
                    use_container_width=True,
                )

            if submitted_edit:
                try:
                    register_match_result(selected_edit_match, edited_scores_team1)
                    save_tournament(tournament)
                    st.success(
                        f"Risultato modificato. Vincitrice: {get_team_name(tournament, selected_edit_match.winner_id)}"
                    )
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

            st.divider()

        # INSERIMENTO NUOVI RISULTATI
        unplayed_matches = get_unplayed_matches(tournament)

        if not unplayed_matches:
            if tournament.champion_id is not None:
                st.success("Torneo concluso.")
                show_podium(tournament)
            else:
                st.success("Non ci sono partite da giocare al momento.")
                st.info("Vai nella sezione Fase finale per generare il turno successivo, se disponibile.")
        else:
            st.markdown("### Inserisci nuovo risultato")

            match_options = {
                f"ID {match.id} — {get_team_name(tournament, match.team1_id)} vs {get_team_name(tournament, match.team2_id)} — {match.round_name}": match
                for match in unplayed_matches
            }

            selected_label = st.selectbox(
                "Seleziona partita",
                options=list(match_options.keys()),
            )

            selected_match = match_options[selected_label]

            st.markdown(
                f"""
                <div class="custom-card">
                    <span class="badge">{selected_match.round_name}</span>
                    <h3>{get_team_name(tournament, selected_match.team1_id)} vs {get_team_name(tournament, selected_match.team2_id)}</h3>
                    <p>Inserisci solo il punteggio della prima squadra. Il punteggio dell'altra viene calcolato automaticamente.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("result_form"):
                scores_team1 = []

                for hand in range(1, 4):
                    score = st.number_input(
                        f"Mano {hand} — punti {get_team_name(tournament, selected_match.team1_id)}",
                        min_value=0,
                        max_value=120,
                        value=60,
                        step=1,
                        key=f"score_{selected_match.id}_{hand}",
                    )

                    st.caption(
                        f"Punti {get_team_name(tournament, selected_match.team2_id)}: {120 - score}"
                    )

                    scores_team1.append(score)

                submitted = st.form_submit_button(
                    "Registra risultato",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                try:
                    register_match_result(selected_match, scores_team1)
                    save_tournament(tournament)
                    st.success(
                        f"Risultato registrato. Vincitrice: {get_team_name(tournament, selected_match.winner_id)}"
                    )
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
                    
# CLASSIFICHE
elif page == "Classifiche":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        st.subheader("Classifiche Gironi")

        for group in tournament.groups:
            standings = compute_group_standings(tournament, group)

            st.markdown(
                f"""
                <div class="custom-card">
                    <span class="badge">Girone {group.name}</span>
                    <h3>Classifica</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            rows = []

            for position, row in enumerate(standings, start=1):
                rows.append(
                    {
                        "Pos": position,
                        "Squadra": row["team_name"],
                        "G": row["played"],
                        "V": row["wins"],
                        "S": row["losses"],
                        "PT": row["tournament_points"],
                        "PF": row["points_for"],
                        "PS": row["points_against"],
                        "Diff": row["point_diff"],
                    }
                )

            st.table(rows)


# FASE FINALE
elif page == "Fase finale":
    tournament = st.session_state.tournament

    if tournament is None:
        st.warning("Prima crea un torneo nella sezione Setup torneo.")
    else:
        st.subheader("Fase finale")

        if not all_group_matches_played(tournament):
            st.warning("Prima devono essere completate tutte le partite dei gironi.")
        else:
            if not final_stage_exists(tournament):
                st.markdown(
                    """
                    <div class="custom-card">
                        <span class="badge">Knockout</span>
                        <h3>Genera tabellone finale</h3>
                        <p>Verranno qualificate automaticamente le prime due squadre di ogni girone.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not is_admin():
                    st.info("Solo l'admin può generare la fase finale.")
                elif st.button("Genera fase finale", type="primary", use_container_width=True):
                    try:
                        create_final_stage(tournament)
                        save_tournament(tournament)
                        st.success("Fase finale generata correttamente.")
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))

            else:
                show_podium(tournament)

                if tournament.champion_id is None and can_advance_final_stage(tournament):
                    st.info("Tutte le partite del turno corrente sono state giocate.")

                    if not is_admin():
                        st.info("Solo l'admin può generare il turno successivo.")
                    elif st.button("Genera turno successivo", type="primary", use_container_width=True):
                        try:
                            advance_final_stage(tournament)
                            save_tournament(tournament)

                            if tournament.champion_id is not None:
                                st.success("Torneo concluso.")
                            else:
                                st.success("Turno successivo generato correttamente.")

                            st.rerun()
                        except ValueError as error:
                            st.error(str(error))

                final_matches = get_final_matches(tournament)

                st.markdown(
                    """
                    <div class="custom-card">
                        <span class="badge">Tabellone</span>
                        <h3>Partite fase finale</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                round_order = {
                    "Ottavo di finale": 1,
                    "Quarto di finale": 2,
                    "Semifinale": 3,
                    "Finale": 4,
                    "Finale 3° posto": 4,
                }

                final_matches.sort(
                    key=lambda match: (
                        round_order.get(match.round_name, 99),
                        match.id,
                    )
                )

                current_round = None

                for match in final_matches:
                    if match.round_name != current_round:
                        current_round = match.round_name
                        st.markdown(f"### {current_round}")

                    st.markdown(
                        f"""
                        <div class="custom-card">
                            <span class="badge">{match.round_name}</span>
                            <h3>{get_team_name(tournament, match.team1_id)} vs {get_team_name(tournament, match.team2_id)}</h3>
                            <p><strong>ID partita:</strong> {match.id}</p>
                            <p><strong>Stato:</strong> {"Giocata" if match.played else "Da giocare"}</p>
                            <p><strong>Vincitrice:</strong> {get_team_name(tournament, match.winner_id) if match.winner_id else "-"}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )