"""Candle Chart form — Stocks List picker and two-session 5-minute candles."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from data.market import prepare_last_and_current_day_bars
from data.watchlists import (
    CANDLE_CHART_SYMBOL_KEY,
    STOCK_NAME_HINTS,
    STOCKS_LIST_KEY,
    update_stocks_list,
)
from forms.chart_render import render_tradingview_intraday_chart


@st.fragment(run_every=timedelta(seconds=30))
def _auto_poll_candle_chart(symbol: str, enabled: bool) -> None:
    if not enabled:
        return
    st.session_state["candle_live_bars"] = prepare_last_and_current_day_bars(
        symbol, interval_minutes=5
    )


def render_candle_chart_page() -> None:
    """Candle Chart page with Stocks List picker and two-session 5-minute candles."""
    st.title("Candle Chart")

    stocks: list[dict] = [dict(s) for s in st.session_state[STOCKS_LIST_KEY]]

    chart_col, list_col = st.columns([6.0, 1.2])
    with list_col:
        st.markdown("**Stocks List**")
        new_sym = st.text_input(
            "Add ticker",
            value="",
            key="candle_new_symbol",
            placeholder="Ticker",
            label_visibility="collapsed",
        ).strip().upper()
        if st.button("Add", key="candle_add_stock", use_container_width=True):
            if not new_sym:
                st.warning("Enter a ticker.")
            elif any(s["symbol"] == new_sym for s in stocks):
                st.info(f"**{new_sym}** already listed.")
            else:
                update_stocks_list(
                    stocks + [{
                        "symbol": new_sym,
                        "name": STOCK_NAME_HINTS.get(new_sym, ""),
                        "included": True,
                    }]
                )
                st.session_state[CANDLE_CHART_SYMBOL_KEY] = new_sym
                st.session_state.pop("candle_live_bars", None)
                st.rerun()

        if not stocks:
            st.info("Add a ticker above to start charting.")
        else:
            symbols = [s["symbol"] for s in stocks]
            if st.session_state.get(CANDLE_CHART_SYMBOL_KEY) not in symbols:
                st.session_state[CANDLE_CHART_SYMBOL_KEY] = symbols[0]
            selected_symbol = st.session_state[CANDLE_CHART_SYMBOL_KEY]
            selected_idx = symbols.index(selected_symbol)

            labels = [f"{s['symbol']} — {s.get('name', '')}".rstrip(" —") for s in stocks]
            picked = st.radio(
                "Stocks List",
                options=symbols,
                index=selected_idx,
                format_func=lambda sym: labels[symbols.index(sym)],
                key="candle_stock_list",
                label_visibility="collapsed",
            )
            if picked != selected_symbol:
                st.session_state[CANDLE_CHART_SYMBOL_KEY] = picked
                st.session_state.pop("candle_live_bars", None)
                st.rerun()

            if st.button("Remove selected", key="candle_remove_stock", use_container_width=True):
                remaining = [s for s in stocks if s["symbol"] != picked]
                update_stocks_list(remaining)
                st.session_state.pop("candle_live_bars", None)
                if remaining:
                    st.session_state[CANDLE_CHART_SYMBOL_KEY] = remaining[0]["symbol"]
                else:
                    st.session_state.pop(CANDLE_CHART_SYMBOL_KEY, None)
                st.rerun()

    with chart_col:
        if not stocks:
            st.info("Add stocks in the Stocks List panel to view candles.")
            return

        symbol = st.session_state[CANDLE_CHART_SYMBOL_KEY]
        selected_stock = next(
            (s for s in stocks if s["symbol"] == symbol),
            {"symbol": symbol, "name": ""},
        )
        stock_name = selected_stock.get("name", "").strip()
        stock_title = f"{symbol} — {stock_name}" if stock_name else symbol
        st.markdown(f"**Selected Stock:** {stock_title}")

        _auto_poll_candle_chart(symbol, True)
        bars = st.session_state.get("candle_live_bars")
        if bars is None:
            bars = prepare_last_and_current_day_bars(symbol, interval_minutes=5)
            st.session_state["candle_live_bars"] = bars

        if not bars.empty:
            render_tradingview_intraday_chart(
                bars,
                symbol,
                5,
                bar_spacing=8,
                chart_height=520,
                max_candles=None,
            )
        else:
            st.warning(
                f"No intraday ticks for **{symbol}** right now. "
                "Try again during market hours (Mon–Fri, PSX session)."
            )
