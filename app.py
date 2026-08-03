"""Stocks Dashboard — Streamlit entry point.

Main form: Stocks Dashboard
Other forms (top buttons, not a dropdown):
  - 10-Minute Breakout Scanner
  - Candle Chart

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
from forms.candle_chart import render_candle_chart_page
from forms.stocks_dashboard import render_stocks_dashboard
from forms.ten_min_breakout import render_ten_min_breakout_scanner
from ui.navigation import (
    PAGE_CANDLE_CHART,
    PAGE_STOCKS_DASHBOARD,
    PAGE_TEN_MIN_BREAKOUT,
    ensure_current_page,
    render_top_nav,
)
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

page = ensure_current_page()
render_top_nav(page)

if page == PAGE_STOCKS_DASHBOARD:
    render_stocks_dashboard()
elif page == PAGE_TEN_MIN_BREAKOUT:
    render_ten_min_breakout_scanner()
elif page == PAGE_CANDLE_CHART:
    render_candle_chart_page()
