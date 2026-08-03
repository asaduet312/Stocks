"""Stocks Dashboard — Streamlit entry point.

Each report is an independent page under app_pages/.
Dashboard shows report buttons; report pages show Back to return home.

Run: streamlit run app.py
Open: http://localhost:8501
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from data.watchlists import init_stocks_list, init_ten_min_watchlist
from ui.styles import inject_app_styles

st.set_page_config(
    page_title="Stocks Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_stocks_list()
init_ten_min_watchlist()
inject_app_styles()

# Drop leftovers from the old session_state form switcher.
st.session_state.pop("current_page", None)
st.session_state.pop("reports_form_select", None)
st.session_state.pop("selected_form", None)
st.session_state.pop("form_dropdown", None)

pages = [
    st.Page(
        "app_pages/stocks_dashboard.py",
        title="Stocks Dashboard",
        default=True,
        url_path="stocks-dashboard",
    ),
    st.Page(
        "app_pages/ten_min_breakout.py",
        title="10-Minute Breakout Scanner",
        url_path="ten-min-breakout",
    ),
    st.Page(
        "app_pages/candle_chart.py",
        title="Candle Chart",
        url_path="candle-chart",
    ),
]

# Hidden built-in nav — dashboard/report pages own their own buttons.
current = st.navigation(pages, position="hidden")
current.run()
