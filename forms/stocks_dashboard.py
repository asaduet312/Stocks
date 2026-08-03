"""Stocks Dashboard — main / home form."""
from __future__ import annotations

import streamlit as st


def render_stocks_dashboard() -> None:
    """Default landing form: title; report launchers sit in the top button row."""
    st.markdown('<span class="form-page-marker"></span>', unsafe_allow_html=True)
    st.markdown(
        '<p class="form-title">Stocks Dashboard</p>',
        unsafe_allow_html=True,
    )
