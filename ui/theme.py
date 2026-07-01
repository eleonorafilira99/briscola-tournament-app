import streamlit as st


PRIMARY = "#7B1E3A"
SECONDARY = "#F4C542"
BACKGROUND = "#FFF8EF"
CARD_BACKGROUND = "#FFFFFF"
TEXT = "#2B2B2B"


def apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {BACKGROUND};
            color: {TEXT};
        }}

        .main-title {{
            font-size: 2.6rem;
            font-weight: 800;
            color: {PRIMARY};
            margin-bottom: 0.2rem;
        }}

        .subtitle {{
            font-size: 1.1rem;
            color: {TEXT};
            margin-bottom: 2rem;
        }}

        .custom-card {{
            background-color: {CARD_BACKGROUND};
            border-left: 8px solid {PRIMARY};
            padding: 1.2rem;
            border-radius: 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
        }}

        .badge {{
            display: inline-block;
            background-color: {SECONDARY};
            color: {TEXT};
            padding: 0.25rem 0.65rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.85rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    