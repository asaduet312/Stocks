"""Live PSX market helpers — no Streamlit cache; fresh fetch each call."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from psxdata.constants import BASE_URL, REQUEST_HEADERS
from psxdata.scrapers.realtime import RealtimeScraper

from data.watchlists import TEN_MIN_BREAKOUT_COLUMNS


def load_trading_board() -> pd.DataFrame:
    return RealtimeScraper().fetch("REG", "main")


def board_quote_map(board: pd.DataFrame) -> dict[str, dict]:
    """Map symbol -> {price, change_pct, volume} from one trading-board snapshot."""
    quotes: dict[str, dict] = {}
    if board.empty or "symbol" not in board.columns:
        return quotes

    for _, row in board.iterrows():
        sym = str(row.get("symbol", "")).strip().upper()
        if not sym:
            continue

        current = pd.to_numeric(row.get("current"), errors="coerce")
        ldcp = pd.to_numeric(row.get("ldcp"), errors="coerce")
        change = pd.to_numeric(row.get("change"), errors="coerce")
        change_pct = pd.to_numeric(row.get("change_pct"), errors="coerce")
        volume = pd.to_numeric(row.get("volume"), errors="coerce")

        if pd.notna(current):
            price = float(current)
        elif pd.notna(ldcp) and pd.notna(change):
            price = float(ldcp + change)
        elif pd.notna(ldcp):
            price = float(ldcp)
        else:
            price = None

        if pd.isna(change_pct) and pd.notna(ldcp) and ldcp and pd.notna(change):
            change_pct = change / ldcp * 100

        quotes[sym] = {
            "price": price,
            "change_pct": float(change_pct) if pd.notna(change_pct) else None,
            "volume": float(volume) if pd.notna(volume) else None,
        }
    return quotes


def fetch_intraday_ticks(symbol: str) -> pd.DataFrame:
    """Fetch PSX intraday ticks: [unix_ts, price, volume]."""
    sym = symbol.upper()
    url = f"{BASE_URL}/timeseries/int/{sym}"
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError, TypeError):
        return pd.DataFrame(columns=["timestamp", "price", "volume"])

    rows = payload.get("data") if isinstance(payload, dict) else None
    if not rows:
        return pd.DataFrame(columns=["timestamp", "price", "volume"])

    df = pd.DataFrame(rows, columns=["timestamp", "price", "volume"])
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["timestamp", "price"]).sort_values("timestamp")
    return df.reset_index(drop=True)


def _first_completed_10m_candle(symbol: str) -> dict | None:
    """Return today's first completed 10-minute OHLC candle, or None if unavailable."""
    ticks = fetch_intraday_ticks(symbol)
    if ticks.empty:
        return None

    idx = pd.to_datetime(ticks["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Karachi")
    tick_df = ticks.assign(dt=idx).set_index("dt").sort_index()
    if tick_df.empty:
        return None

    now = pd.Timestamp.now(tz="Asia/Karachi")
    today = now.normalize()
    today_ticks = tick_df[tick_df.index.normalize() == today]
    if today_ticks.empty:
        return None

    bars = today_ticks["price"].resample("10min").ohlc().dropna(subset=["open"])
    if bars.empty:
        return None

    first_ts = bars.index[0]
    if now < first_ts + pd.Timedelta(minutes=10):
        return None

    first = bars.iloc[0]
    open_ = pd.to_numeric(first.get("open"), errors="coerce")
    high = pd.to_numeric(first.get("high"), errors="coerce")
    close = pd.to_numeric(first.get("close"), errors="coerce")
    if pd.isna(open_) or pd.isna(high) or pd.isna(close):
        return None

    return {
        "open": float(open_),
        "high": float(high),
        "close": float(close),
        "start": first_ts,
    }


def _last_breakout_time_above_level(
    symbol: str,
    level: float,
    first_candle_start: pd.Timestamp,
) -> str | None:
    """Most recent Karachi-time when price crossed above level after the first 10m candle."""
    ticks = fetch_intraday_ticks(symbol)
    if ticks.empty:
        return None

    idx = pd.to_datetime(ticks["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Karachi")
    tick_df = ticks.assign(dt=idx).set_index("dt").sort_index()
    if tick_df.empty:
        return None

    today = pd.Timestamp.now(tz="Asia/Karachi").normalize()
    today_ticks = tick_df[tick_df.index.normalize() == today]
    if today_ticks.empty:
        return None

    after_first_10m = first_candle_start + pd.Timedelta(minutes=10)
    eligible = today_ticks[today_ticks.index >= after_first_10m].copy()
    if eligible.empty:
        return None

    eligible["price_num"] = pd.to_numeric(eligible["price"], errors="coerce")
    eligible = eligible.dropna(subset=["price_num"])
    if eligible.empty:
        return None

    above = eligible["price_num"] > float(level)
    if not bool(above.iloc[-1]):
        return None

    prev_above = above.shift(fill_value=False)
    cross_up = above & ~prev_above
    if not cross_up.any():
        return eligible.index[0].strftime("%H:%M:%S")
    return cross_up[cross_up].index[-1].strftime("%H:%M:%S")


def _ten_min_breakout_row(symbol: str, quote: dict) -> dict | None:
    """Return a result row when the stock meets current-time 10-minute breakout filters."""
    price = quote.get("price")
    change_pct = quote.get("change_pct")
    volume = quote.get("volume")
    if price is None or change_pct is None:
        return None

    candle = _first_completed_10m_candle(symbol)
    if candle is None:
        return None

    if candle["close"] <= candle["open"]:
        return None
    if float(price) <= candle["high"]:
        return None

    breakout_price = float(candle["high"])
    price_distance = float(price) - breakout_price
    breakout_time = _last_breakout_time_above_level(symbol, breakout_price, candle["start"])
    if breakout_time is None:
        return None

    return {
        "Symbol": symbol,
        "Current Price": float(price),
        "Breakout Time": breakout_time,
        "Price Distance": price_distance,
        "Change %": float(change_pct),
        "Volume": float(volume) / 1_000_000.0 if volume is not None else None,
        "First 10-Minute High": breakout_price,
    }


def load_ten_min_breakout_list(
    symbols: tuple[str, ...],
    refresh_token: int = 0,
    min_change_pct: float = 2.0,
) -> pd.DataFrame:
    """Scan watchlist for live breakouts above the first completed 10-minute high."""
    _ = refresh_token
    columns = list(TEN_MIN_BREAKOUT_COLUMNS)
    if not symbols:
        return pd.DataFrame(columns=columns)

    board = load_trading_board()
    quotes = board_quote_map(board)

    candidates: list[tuple[str, dict]] = []
    for sym in symbols:
        quote = quotes.get(sym)
        if not quote:
            continue
        change_pct = quote.get("change_pct")
        if change_pct is None or float(change_pct) < float(min_change_pct):
            continue
        candidates.append((sym, quote))

    if not candidates:
        return pd.DataFrame(columns=columns)

    uniq: dict[str, dict] = {sym: quote for sym, quote in candidates}
    syms = list(uniq.keys())
    quote_list = [uniq[s] for s in syms]
    workers = min(8, max(1, len(syms)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_ten_min_breakout_row, syms, quote_list))

    rows = [r for r in results if r is not None]
    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    df = df.drop_duplicates(subset=["Symbol"], keep="last")
    return df.sort_values(
        by=["Price Distance", "Change %"],
        ascending=[True, False],
        kind="mergesort",
    ).reset_index(drop=True)


def normalize_ohlc(open_: float, high: float, low: float, close: float) -> tuple[float, float, float, float]:
    """Ensure valid candlestick OHLC (high/low wrap open/close)."""
    o, h, l, c = float(open_), float(high), float(low), float(close)
    h = max(h, o, c)
    l = min(l, o, c)
    return o, h, l, c


def prepare_last_and_current_day_bars(symbol: str, interval_minutes: int = 5) -> pd.DataFrame:
    """Build 5-minute candles for the latest two trading sessions from intraday ticks."""
    interval_minutes = 5
    ticks = fetch_intraday_ticks(symbol)
    if ticks.empty:
        return pd.DataFrame()

    idx = pd.to_datetime(ticks["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Karachi")
    tick_df = ticks.assign(dt=idx).set_index("dt").sort_index()
    if tick_df.empty:
        return pd.DataFrame()

    sessions = sorted(pd.Series(tick_df.index.normalize()).drop_duplicates())
    if not sessions:
        return pd.DataFrame()
    selected_sessions = sessions[-2:]
    tick_df = tick_df[tick_df.index.normalize().isin(selected_sessions)]
    if tick_df.empty:
        return pd.DataFrame()

    rule = f"{interval_minutes}min"
    ohlc = tick_df["price"].resample(rule).ohlc().dropna(subset=["open"])
    vol = tick_df["volume"].resample(rule).sum()
    bars = ohlc.join(vol.rename("volume"))
    if bars.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for ts_key, row in bars.iterrows():
        o, h, l, c = normalize_ohlc(row["open"], row["high"], row["low"], row["close"])
        rows.append({
            "timestamp": int(pd.Timestamp(ts_key).timestamp()),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": float(row["volume"] or 0),
        })
    return pd.DataFrame(rows)
