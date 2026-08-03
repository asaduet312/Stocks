"""Watchlist load/save helpers for Stocks List and 10-Minute scanner."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent

STOCK_NAME_HINTS: dict[str, str] = {
    "PRL": "Pakistan Refinery",
    "BIPL": "Biafo Industries",
    "POWER": "Power Cement",
    "LOADS": "Loads Limited",
}

STOCKS_LIST_FILE = REPO_ROOT / "Stocks List.json"
STOCKS_LIST_KEY = "stocks_list"
TEN_MIN_WATCHLIST_FILE = REPO_ROOT / "10MinutesWatchlist.json"
TEN_MIN_WATCHLIST_KEY = "ten_min_watchlist"
CANDLE_CHART_SYMBOL_KEY = "candle_chart_symbol"

TEN_MIN_BREAKOUT_COLUMNS = [
    "Symbol",
    "First 10-Minute High",
    "Current Price",
    "Breakout Time",
    "Price Distance",
    "Change %",
    "Volume",
]


def _default_stocks_list() -> list[dict]:
    return [
        {"symbol": sym, "name": name, "included": True}
        for sym, name in STOCK_NAME_HINTS.items()
    ]


def _normalize_watchlist_stocks(raw: list) -> list[dict]:
    """Normalize raw watchlist JSON entries to {symbol, name, included}."""
    stocks: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("symbol", "")).strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        stocks.append({
            "symbol": sym,
            "name": str(item.get("name", "")).strip(),
            "included": bool(item.get("included", True)),
        })
    return stocks


def _write_watchlist(path: Path, stocks: list[dict]) -> None:
    payload = {
        "stocks": [
            {
                "symbol": s["symbol"],
                "name": s.get("name", ""),
                "included": bool(s.get("included", True)),
            }
            for s in stocks
        ]
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _read_watchlist(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    raw = payload.get("stocks") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return None
    stocks = _normalize_watchlist_stocks(raw)
    return stocks or None


def load_stocks_list_file() -> list[dict]:
    """Load watchlist from Stocks List.json, seeding defaults if missing."""
    stocks = _read_watchlist(STOCKS_LIST_FILE)
    if stocks is None:
        stocks = _default_stocks_list()
        save_stocks_list_file(stocks)
    return stocks


def save_stocks_list_file(stocks: list[dict]) -> None:
    """Persist the Candle Chart watchlist to Stocks List.json."""
    _write_watchlist(STOCKS_LIST_FILE, stocks)


def load_ten_min_watchlist_file() -> list[dict]:
    """Load breakout watchlist; seed from Stocks List on first run."""
    stocks = _read_watchlist(TEN_MIN_WATCHLIST_FILE)
    if stocks is None:
        seed = load_stocks_list_file()
        save_ten_min_watchlist_file(seed)
        return [dict(s) for s in seed]
    return stocks


def save_ten_min_watchlist_file(stocks: list[dict]) -> None:
    """Persist the 10-Minute Breakout Scanner watchlist only."""
    _write_watchlist(TEN_MIN_WATCHLIST_FILE, stocks)


def init_stocks_list() -> None:
    """Load Stocks List.json into session state once at app start."""
    if STOCKS_LIST_KEY not in st.session_state:
        st.session_state[STOCKS_LIST_KEY] = load_stocks_list_file()


def init_ten_min_watchlist() -> None:
    """Load 10MinutesWatchlist.json into session state once."""
    if TEN_MIN_WATCHLIST_KEY not in st.session_state:
        st.session_state[TEN_MIN_WATCHLIST_KEY] = load_ten_min_watchlist_file()


def update_ten_min_watchlist(stocks: list[dict]) -> None:
    st.session_state[TEN_MIN_WATCHLIST_KEY] = stocks
    save_ten_min_watchlist_file(stocks)


def update_stocks_list(stocks: list[dict]) -> None:
    st.session_state[STOCKS_LIST_KEY] = stocks
    save_stocks_list_file(stocks)
