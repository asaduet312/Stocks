"""Top button navigation — Stocks Dashboard is the home form."""
from __future__ import annotations

import streamlit as st

PAGE_STOCKS_DASHBOARD = "stocks_dashboard"
PAGE_TEN_MIN_BREAKOUT = "ten_min_breakout"
PAGE_CANDLE_CHART = "candle_chart"

DEFAULT_PAGE = PAGE_STOCKS_DASHBOARD


def navigate_to(page: str) -> None:
    st.session_state.current_page = page
    st.rerun()


def ensure_current_page() -> str:
    """Initialize and return the active form id; default is Stocks Dashboard."""
    # Drop any leftover key from the old Reports dropdown selector.
    st.session_state.pop("reports_form_select", None)
    st.session_state.pop("selected_form", None)
    st.session_state.pop("form_dropdown", None)

    if "current_page" not in st.session_state:
        st.session_state.current_page = DEFAULT_PAGE

    page = st.session_state.current_page
    if page not in {PAGE_STOCKS_DASHBOARD, PAGE_TEN_MIN_BREAKOUT, PAGE_CANDLE_CHART}:
        st.session_state.current_page = DEFAULT_PAGE
        st.rerun()
    return st.session_state.current_page


def render_top_nav(page: str) -> None:
    """Render in-flow top buttons (no dropdown / no sidebar page picker)."""
    if page == PAGE_STOCKS_DASHBOARD:
        cols = st.columns([1.15, 1.55, 1.0, 4.0])
        with cols[0]:
            st.markdown('<span class="stocks-dash-nav-marker"></span>', unsafe_allow_html=True)
            if st.button("Stocks Dashboard", key="nav_stocks_dashboard", type="primary"):
                navigate_to(PAGE_STOCKS_DASHBOARD)
        with cols[1]:
            if st.button("10-Minute Breakout Scanner", key="nav_ten_min_breakout"):
                navigate_to(PAGE_TEN_MIN_BREAKOUT)
        with cols[2]:
            if st.button("Candle Chart", key="nav_candle_chart"):
                navigate_to(PAGE_CANDLE_CHART)
        return

    if page == PAGE_TEN_MIN_BREAKOUT:
        cols = st.columns([1.15, 1.55, 1.0, 4.0])
        with cols[0]:
            st.markdown('<span class="stocks-dash-nav-marker"></span>', unsafe_allow_html=True)
            if st.button("Stocks Dashboard", key="nav_stocks_dashboard"):
                navigate_to(PAGE_STOCKS_DASHBOARD)
        with cols[1]:
            if st.button(
                "10-Minute Breakout Scanner",
                key="nav_ten_min_breakout",
                type="primary",
            ):
                navigate_to(PAGE_TEN_MIN_BREAKOUT)
        with cols[2]:
            if st.button("Candle Chart", key="nav_candle_chart"):
                navigate_to(PAGE_CANDLE_CHART)
        return

    # candle_chart
    cols = st.columns([1.15, 1.55, 1.0, 4.0])
    with cols[0]:
        st.markdown('<span class="stocks-dash-nav-marker"></span>', unsafe_allow_html=True)
        if st.button("Stocks Dashboard", key="nav_stocks_dashboard"):
            navigate_to(PAGE_STOCKS_DASHBOARD)
    with cols[1]:
        if st.button("10-Minute Breakout Scanner", key="nav_ten_min_breakout"):
            navigate_to(PAGE_TEN_MIN_BREAKOUT)
    with cols[2]:
        if st.button("Candle Chart", key="nav_candle_chart", type="primary"):
            navigate_to(PAGE_CANDLE_CHART)
