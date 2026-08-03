"""10-Minute Breakout Scanner form."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from data.market import load_ten_min_breakout_list
from data.watchlists import (
    STOCK_NAME_HINTS,
    TEN_MIN_BREAKOUT_COLUMNS,
    TEN_MIN_WATCHLIST_KEY,
    init_ten_min_watchlist,
    update_ten_min_watchlist,
)
from ui.form_template import FormTemplate


def _apply_ten_min_settings() -> None:
    """Parse scanner settings text boxes into session numeric values."""
    def _parse(key_in: str, key_out: str, default: float) -> None:
        raw = str(st.session_state.get(key_in, default)).strip().replace(",", "")
        try:
            st.session_state[key_out] = float(raw)
        except (TypeError, ValueError):
            st.session_state[key_out] = default

    _parse("ten_min_breakout_min_change_input", "ten_min_breakout_min_change", 2.0)


def render_ten_min_breakout_scanner() -> None:
    """10-Minute Breakout Scanner — mobile stacked FormTemplate layout."""
    init_ten_min_watchlist()

    def _load_records(symbols: tuple[str, ...], refresh_token: int) -> pd.DataFrame:
        min_change = float(st.session_state.get("ten_min_breakout_min_change", 2.0))
        return load_ten_min_breakout_list(
            symbols,
            refresh_token=refresh_token,
            min_change_pct=min_change,
        )

    form = FormTemplate(
        form_id="ten_min_breakout",
        title="10-Minute Breakout Scanner",
        watchlist_label="Watchlist",
        report_label="Breakouts",
        refresh_label="🔄 Refresh",
        empty_data_message="No watchlist stocks currently meet the 10-minute breakout filters.",
        load_records=_load_records,
        get_stocks=lambda: list(st.session_state[TEN_MIN_WATCHLIST_KEY]),
        set_stocks=update_ten_min_watchlist,
        resolve_symbol_name=lambda sym: STOCK_NAME_HINTS.get(sym, ""),
        layout="stacked",
        display_columns=TEN_MIN_BREAKOUT_COLUMNS,
        column_config={
            "Symbol": st.column_config.TextColumn(
                "Symbol",
                width="small",
                alignment="center",
            ),
            "Current Price": st.column_config.NumberColumn(
                "Price",
                width="small",
                format="%.2f",
                alignment="center",
            ),
            "Breakout Time": st.column_config.TextColumn(
                "Breakout Time",
                width="small",
                alignment="center",
            ),
            "Price Distance": st.column_config.NumberColumn(
                "Dist",
                width="small",
                format="%.2f",
                alignment="center",
            ),
            "Change %": st.column_config.NumberColumn(
                "Chg%",
                width="small",
                format="%.2f",
                alignment="center",
            ),
            "Volume": st.column_config.NumberColumn(
                "Vol (M)",
                width="small",
                format="%.2f",
                alignment="center",
            ),
            "First 10-Minute High": st.column_config.NumberColumn(
                "10m High",
                width="small",
                format="%.2f",
                alignment="center",
            ),
        },
        row_px=36,
        header_px=38,
        max_table_height_px=560,
        report_ratio=5.2,
        watch_ratio=1.05,
    )

    def _render_controls() -> None:
        with st.container(border=True):
            top_c1, top_c2 = st.columns([2.0, 0.9], gap="small")
            with top_c1:
                st.markdown('<p class="form-settings-label">Minimum Change %</p>', unsafe_allow_html=True)
                st.text_input(
                    "Minimum Change %",
                    value=str(st.session_state.get("ten_min_breakout_min_change", "2.0")),
                    key="ten_min_breakout_min_change_input",
                    label_visibility="collapsed",
                )
            with top_c2:
                st.markdown('<p class="form-settings-label">&nbsp;</p>', unsafe_allow_html=True)
                if st.button(form.refresh_label, use_container_width=True, key=form._key("refresh")):
                    _apply_ten_min_settings()
                    form.bump_refresh()
                    st.rerun()

            st.caption(
                "On Refresh: Change % ≥ Minimum Change %, first 10-minute candle green, "
                "and live price above that candle's high (current breakout only)."
            )

        _apply_ten_min_settings()

    form.render_controls = _render_controls
    form.render()
