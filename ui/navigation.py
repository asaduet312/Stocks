"""Page navigation helpers — open reports from dashboard; Back returns home."""
from __future__ import annotations

import streamlit as st

DASHBOARD_PAGE = "app_pages/stocks_dashboard.py"
TEN_MIN_BREAKOUT_PAGE = "app_pages/ten_min_breakout.py"
CANDLE_CHART_PAGE = "app_pages/candle_chart.py"


def render_dashboard_report_buttons() -> None:
    """Dashboard-only launchers. Opens each report as its own page."""
    cols = st.columns([1.55, 1.0, 5.0])
    with cols[0]:
        st.markdown('<span class="stocks-dash-nav-marker"></span>', unsafe_allow_html=True)
        if st.button("10-Minute Breakout Scanner", key="nav_ten_min_breakout"):
            st.switch_page(TEN_MIN_BREAKOUT_PAGE)
    with cols[1]:
        if st.button("Candle Chart", key="nav_candle_chart"):
            st.switch_page(CANDLE_CHART_PAGE)


def render_back_to_dashboard() -> None:
    """Report-page Back control — returns to dashboard and leaves this report."""
    cols = st.columns([1.0, 6.0])
    with cols[0]:
        st.markdown('<span class="stocks-dash-nav-marker"></span>', unsafe_allow_html=True)
        if st.button("← Back", key="nav_back_dashboard"):
            st.switch_page(DASHBOARD_PAGE)
