"""Reusable Streamlit form shell: compact title, refresh, watchlist, and data grid.

``FormTemplate`` mirrors the Trending List layout so future forms can reuse the
same GUI (watchlist + report grid) with different load criteria and columns.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

ColumnConfig = Mapping[str, object]
LoadRecordsFn = Callable[[tuple[str, ...], int], pd.DataFrame]
RefreshFn = Callable[[], None]
ResolveNameFn = Callable[[str], str]
GetStocksFn = Callable[[], list[dict]]
SetStocksFn = Callable[[list[dict]], None]


def _inject_form_template_styles() -> None:
    """Compact page + watchlist styles shared by all FormTemplate forms."""
    st.markdown(
        """
        <style>
        /* --- Form page: remove top chrome / label gaps --- */
        /* Compact top padding only when no Reports menu sits above the form */
        .block-container:has(.form-page-marker):not(:has(.top-reports-nav-marker)) {
            padding-top: 0.35rem !important;
        }
        .block-container:has(.form-page-marker):has(.top-reports-nav-marker) {
            padding-top: 0.5rem !important;
        }
        .block-container:has(.form-page-marker) {
            padding-bottom: 0.5rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        .block-container:has(.form-page-marker) > div {
            gap: 0.25rem !important;
        }
        div:has(> .form-page-marker) {
            gap: 0.2rem !important;
        }
        .form-page-marker + div,
        .form-header {
            margin: 0 !important;
            padding: 0 !important;
        }
        .form-title {
            margin: 0 !important;
            padding: 0 !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            line-height: 1.2 !important;
        }
        .form-report-label {
            margin: 0 0 0.15rem 0 !important;
            padding: 0 !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            line-height: 1.2 !important;
        }

        /* --- Watchlist column --- */
        [data-testid="column"]:has(.compact-watchlist-marker) {
            flex: 0 0 7.75rem !important;
            width: 7.75rem !important;
            min-width: 7.75rem !important;
            max-width: 7.75rem !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            row-gap: 0 !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stElementContainer"],
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="element-container"],
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stVerticalBlockBorderWrapper"] {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 0 !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stHorizontalBlock"] {
            gap: 0.05rem !important;
            margin: 0 !important;
            margin-bottom: -0.72rem !important;
            padding: 0 !important;
            min-height: 0 !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stHorizontalBlock"] [data-testid="column"] {
            padding: 0 !important;
            min-height: 0 !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stHorizontalBlock"] [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 0 !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) button {
            padding: 0 !important;
            font-size: 0.58rem !important;
            min-height: 0.95rem !important;
            height: 0.95rem !important;
            line-height: 1 !important;
            border-radius: 0.15rem !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stTextInput"] {
            margin-bottom: 0 !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stTextInput"] input,
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stTextInput"] [data-baseweb="base-input"] {
            padding: 0.05rem 0.3rem !important;
            font-size: 0.65rem !important;
            min-height: 1.1rem !important;
            height: 1.1rem !important;
            line-height: 1 !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stTextInput"] [data-testid="stWidgetLabel"] {
            display: none !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stCheckbox"] {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 0.9rem !important;
            height: 0.9rem !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stCheckbox"] label {
            gap: 0.12rem !important;
            min-height: 0.9rem !important;
            height: 0.9rem !important;
            align-items: center !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stCheckbox"] label p,
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stCheckbox"] label span {
            font-size: 0.65rem !important;
            line-height: 0.9rem !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }
        [data-testid="column"]:has(.compact-watchlist-marker) [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] {
            margin: 0 !important;
            min-height: 0 !important;
        }
        .watchlist-items-start {
            display: block;
            height: 0;
            margin: 0;
            padding: 0;
        }

        @media (max-width: 768px) {
            .block-container:has(.form-page-marker):not(:has(.top-reports-nav-marker)) {
                padding-top: 0.25rem !important;
            }
            .block-container:has(.form-page-marker):has(.top-reports-nav-marker) {
                padding-top: 0.4rem !important;
            }
            .block-container:has(.form-page-marker) {
                padding-left: 0.4rem !important;
                padding-right: 0.4rem !important;
            }
            [data-testid="column"]:has(.compact-watchlist-marker) {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
                max-width: 100% !important;
            }
            .form-title {
                font-size: 1rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@dataclass
class FormTemplate:
    """Reusable watchlist + report-grid form shell.

    Example
    -------
    >>> FormTemplate(
    ...     form_id="trending",
    ...     title="List of Stocks",
    ...     load_records=my_loader,
    ...     get_stocks=lambda: st.session_state["stocks_list"],
    ...     set_stocks=save_fn,
    ...     display_columns=["Symbol", "Low", "High"],
    ...     column_config={...},
    ...     on_refresh=clear_caches,
    ... ).render()
    """

    form_id: str
    load_records: LoadRecordsFn = field(repr=False)
    get_stocks: GetStocksFn = field(repr=False)
    set_stocks: SetStocksFn = field(repr=False)

    title: str = "List of Stocks"
    watchlist_label: str = "Watchlist"
    report_label: str = "Report"
    refresh_label: str = "🔄 Refresh"
    empty_watchlist_message: str = "Select at least one stock in the watchlist to load the report."
    empty_data_message: str = "Could not load data for the selected symbols. Try refreshing."

    on_refresh: RefreshFn | None = field(default=None, repr=False)
    resolve_symbol_name: ResolveNameFn | None = field(default=None, repr=False)

    display_columns: Sequence[str] | None = None
    column_config: ColumnConfig | None = None
    row_px: int = 32
    header_px: int = 34
    report_ratio: float = 7.0
    watch_ratio: float = 0.9

    def _refresh_token_key(self) -> str:
        return f"{self.form_id}_refresh_token"

    def _key(self, name: str) -> str:
        return f"{self.form_id}_{name}"

    def render_watchlist(self) -> list[str]:
        """Render compact right-panel watchlist; return included symbols."""
        stocks: list[dict] = [dict(s) for s in self.get_stocks()]

        st.markdown('<span class="compact-watchlist-marker"></span>', unsafe_allow_html=True)
        st.markdown(
            f'<p style="margin:0;padding:0;font-size:0.72rem;font-weight:600;line-height:1.1;">'
            f"{self.watchlist_label}</p>",
            unsafe_allow_html=True,
        )

        new_sym = st.text_input(
            "Add ticker",
            value="",
            key=self._key("new_symbol"),
            placeholder="Ticker",
            label_visibility="collapsed",
        ).strip().upper()
        add_clicked = st.button("Add", key=self._key("add_stock"), use_container_width=True)

        if add_clicked:
            if not new_sym:
                st.warning("Enter a ticker.")
            elif any(s["symbol"] == new_sym for s in stocks):
                st.info(f"**{new_sym}** already listed.")
            else:
                name = ""
                if self.resolve_symbol_name is not None:
                    name = self.resolve_symbol_name(new_sym) or ""
                self.set_stocks(stocks + [{"symbol": new_sym, "name": name, "included": True}])
                st.rerun()

        st.markdown('<span class="watchlist-items-start"></span>', unsafe_allow_html=True)

        updated_stocks: list[dict] = []
        list_changed = False
        for stock in stocks:
            sym = stock["symbol"]
            cb_col, rm_col = st.columns([5, 1], gap="small")
            with cb_col:
                checked = st.checkbox(
                    sym,
                    value=bool(stock.get("included", True)),
                    key=self._key(f"include_{sym}"),
                )
            with rm_col:
                if st.button("✕", key=self._key(f"remove_{sym}"), help=f"Remove {sym}"):
                    self.set_stocks([s for s in stocks if s["symbol"] != sym])
                    st.rerun()

            if checked != bool(stock.get("included", True)):
                list_changed = True
            updated_stocks.append({**stock, "included": checked})

        if list_changed:
            self.set_stocks(updated_stocks)

        return [s["symbol"] for s in updated_stocks if s.get("included")]

    def render_grid(self, df: pd.DataFrame) -> None:
        """Render the report dataframe with FormTemplate formatting."""
        if df is None or df.empty:
            st.warning(self.empty_data_message)
            return

        cols = list(self.display_columns) if self.display_columns else list(df.columns)
        cols = [c for c in cols if c in df.columns]
        if not cols:
            st.warning(self.empty_data_message)
            return

        display = df[cols].copy()
        table_height = self.header_px + max(len(display), 1) * self.row_px
        kwargs: dict = {
            "use_container_width": True,
            "hide_index": True,
            "height": table_height,
        }
        if self.column_config:
            kwargs["column_config"] = dict(self.column_config)
        st.dataframe(display, **kwargs)

    def render(self) -> None:
        """Render the full form: title, refresh, watchlist, and report grid."""
        _inject_form_template_styles()
        st.markdown('<span class="form-page-marker"></span>', unsafe_allow_html=True)

        token_key = self._refresh_token_key()
        if token_key not in st.session_state:
            st.session_state[token_key] = 0

        title_col, refresh_col = st.columns([4.5, 1.2], gap="small")
        with title_col:
            st.markdown(f'<p class="form-title">{self.title}</p>', unsafe_allow_html=True)
        with refresh_col:
            if st.button(self.refresh_label, use_container_width=True, key=self._key("refresh")):
                st.session_state[token_key] = int(st.session_state[token_key]) + 1
                if self.on_refresh is not None:
                    self.on_refresh()
                st.rerun()

        report_col, watch_col = st.columns([self.report_ratio, self.watch_ratio], gap="small")

        with watch_col:
            active_symbols = self.render_watchlist()

        with report_col:
            if not active_symbols:
                st.info(self.empty_watchlist_message)
                return

            st.markdown(
                f'<p class="form-report-label">{self.report_label}</p>',
                unsafe_allow_html=True,
            )
            df = self.load_records(tuple(active_symbols), int(st.session_state[token_key]))
            self.render_grid(df)
