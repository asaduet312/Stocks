"""Shared Streamlit chrome + top navigation styles."""
from __future__ import annotations

import streamlit as st


def inject_app_styles() -> None:
    """Hide Streamlit chrome/sidebar and style the top form button row."""
    st.markdown(
        """
        <style>
        /* Hide Streamlit chrome + left sidebar only (do not hide main content) */
        [data-testid="stToolbar"],
        [data-testid="stToolbarActions"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stAppDeployButton"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"],
        #MainMenu,
        #stDecoration,
        .stDeployButton,
        .stAppDeployButton,
        div[data-testid="stAppDeployButton"],
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
            height: 0 !important;
            min-height: 0 !important;
        }
        footer,
        footer[data-testid="stFooter"],
        .stAppFooter {
            display: none !important;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .main {
            margin-left: 0 !important;
        }

        .block-container {
            padding-top: 0.5rem !important;
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
            max-width: 100% !important;
        }

        .stocks-dash-nav-marker {
            display: block;
            height: 0;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }

        /* Compact top button row */
        div[data-testid="stHorizontalBlock"]:has(.stocks-dash-nav-marker) {
            gap: 0.35rem !important;
            margin: 0 0 0.55rem 0 !important;
            align-items: center !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.stocks-dash-nav-marker) button {
            min-height: 1.7rem !important;
            height: 1.7rem !important;
            padding: 0.1rem 0.55rem !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            line-height: 1.1 !important;
            border-radius: 0.3rem !important;
            white-space: nowrap !important;
        }
        .form-title {
            margin: 0 0 0.35rem 0 !important;
            padding: 0 !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            line-height: 1.2 !important;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.35rem !important;
                padding-left: 0.55rem !important;
                padding-right: 0.55rem !important;
                padding-bottom: 0.75rem !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.stocks-dash-nav-marker) button {
                font-size: 0.72rem !important;
                padding: 0.1rem 0.4rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
