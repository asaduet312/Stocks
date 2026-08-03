"""Independent page: Stocks Dashboard (home) — report launch buttons live here."""
from __future__ import annotations

import streamlit as st

from ui.navigation import render_dashboard_report_buttons

render_dashboard_report_buttons()

st.markdown('<span class="form-page-marker"></span>', unsafe_allow_html=True)
st.markdown(
    '<p class="form-title">Stocks Dashboard</p>',
    unsafe_allow_html=True,
)
