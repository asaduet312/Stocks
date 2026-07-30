"""PSX Stock Analysis — web interface (Streamlit).

Opens in your browser at http://localhost:8501
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

# Resolve local example modules and repo root on any OS / CWD (Railway, Linux, macOS, Windows).
_EXAMPLES_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLES_DIR.parent
for _path in (_EXAMPLES_DIR, _REPO_ROOT):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

import pandas as pd
import plotly.graph_objects as go
import psxdata
import requests
import streamlit as st
import streamlit.components.v1 as components
from plotly.subplots import make_subplots
from psxdata.constants import BASE_URL, REQUEST_HEADERS
from psxdata.scrapers.realtime import RealtimeScraper
from psxdata.scrapers.screener import ScreenerScraper

from form_template import FormTemplate
from stock_analysis import add_technicals, analyze_symbol

st.set_page_config(
    page_title="PSX Stock Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

INTRADAY_STATE_KEY = "intraday_snapshots"
MAX_INTRADAY_CANDLES = 20
CANDLE_CHART_SYMBOL_KEY = "candle_chart_symbol"
TRENDING_LIST_CATALOG: dict[str, str] = {
    "PRL": "Pakistan Refinery",
    "BIPL": "Biafo Industries",
    "POWER": "Power Cement",
    "LOADS": "Loads Limited",
}
TRENDING_LIST_SYMBOLS = list(TRENDING_LIST_CATALOG.keys())
STOCKS_LIST_FILE = _REPO_ROOT / "Stocks List.json"
STOCKS_LIST_KEY = "stocks_list"


def _default_stocks_list() -> list[dict]:
    return [
        {"symbol": sym, "name": name, "included": True}
        for sym, name in TRENDING_LIST_CATALOG.items()
    ]


def load_stocks_list_file() -> list[dict]:
    """Load watchlist from Stocks List.json, seeding defaults if missing."""
    if not STOCKS_LIST_FILE.exists():
        stocks = _default_stocks_list()
        save_stocks_list_file(stocks)
        return stocks

    try:
        payload = json.loads(STOCKS_LIST_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        stocks = _default_stocks_list()
        save_stocks_list_file(stocks)
        return stocks

    raw = payload.get("stocks") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        stocks = _default_stocks_list()
        save_stocks_list_file(stocks)
        return stocks

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

    if not stocks:
        stocks = _default_stocks_list()
        save_stocks_list_file(stocks)
    return stocks


def save_stocks_list_file(stocks: list[dict]) -> None:
    """Persist the current watchlist to Stocks List.json."""
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
    STOCKS_LIST_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def init_stocks_list() -> None:
    """Load Stocks List.json into session state once at app start."""
    if STOCKS_LIST_KEY not in st.session_state:
        st.session_state[STOCKS_LIST_KEY] = load_stocks_list_file()


init_stocks_list()


@st.cache_data(ttl=60, show_spinner=False)
def load_trading_board() -> pd.DataFrame:
    return RealtimeScraper().fetch("REG", "main")


@st.cache_data(ttl=900, show_spinner="Loading market data...")
def load_sectors() -> pd.DataFrame:
    return psxdata.sectors()


@st.cache_data(ttl=900, show_spinner="Loading KSE-100...")
def load_kse100() -> pd.DataFrame:
    return psxdata.indices("KSE100")


@st.cache_data(ttl=900, show_spinner="Loading screener...")
def load_screener() -> pd.DataFrame:
    return ScreenerScraper().fetch()


@st.cache_data(ttl=900, show_spinner="Fetching price history...")
def load_history(symbol: str) -> pd.DataFrame:
    raw = psxdata.stocks(symbol)
    if raw.empty:
        raw = psxdata.stocks(symbol, cache=False)
    if raw.empty:
        return raw
    return add_technicals(raw.sort_values("date").tail(365))


@st.cache_data(ttl=300, show_spinner="Fetching quote...")
def load_quote(symbol: str) -> pd.DataFrame:
    return psxdata.quote(symbol)


@st.cache_data(ttl=900, show_spinner=False)
def load_last_trading_day(symbol: str) -> pd.DataFrame:
    """Most recent daily OHLCV row for a symbol (last trading session)."""
    raw = psxdata.stocks(symbol, cache=True)
    if raw.empty:
        return raw
    return raw.sort_values("date").tail(1).copy()


def _board_price_map(board: pd.DataFrame) -> dict[str, float]:
    """Map symbol -> live price from one trading-board snapshot."""
    prices: dict[str, float] = {}
    if board.empty or "symbol" not in board.columns:
        return prices
    for _, row in board.iterrows():
        sym = str(row.get("symbol", "")).strip().upper()
        if not sym:
            continue
        current = pd.to_numeric(row.get("current"), errors="coerce")
        ldcp = pd.to_numeric(row.get("ldcp"), errors="coerce")
        change = pd.to_numeric(row.get("change"), errors="coerce")
        if pd.notna(current):
            prices[sym] = float(current)
        elif pd.notna(ldcp) and pd.notna(change):
            prices[sym] = float(ldcp + change)
        elif pd.notna(ldcp):
            prices[sym] = float(ldcp)
    return prices


def _last_day_ohlc(symbol: str) -> dict:
    """Fetch last-session OHLC using psxdata disk cache (safe for threads)."""
    raw = psxdata.stocks(symbol, cache=True)
    if raw.empty:
        return {"Symbol": symbol, "Low": None, "High": None, "Open of Day": None, "Close Of Day": None, "Date": None}
    bar = raw.sort_values("date").iloc[-1]
    return {
        "Symbol": symbol,
        "Low": float(bar["low"]) if pd.notna(bar.get("low")) else None,
        "High": float(bar["high"]) if pd.notna(bar.get("high")) else None,
        "Open of Day": float(bar["open"]) if pd.notna(bar.get("open")) else None,
        "Close Of Day": float(bar["close"]) if pd.notna(bar.get("close")) else None,
        "Date": bar["date"].strftime("%Y-%m-%d") if pd.notna(bar.get("date")) else None,
    }


@st.cache_data(ttl=60, show_spinner=False)
def load_trending_list(symbols: tuple[str, ...], refresh_token: int = 0) -> pd.DataFrame:
    """Last-session OHLC plus live price for watchlist symbols.

    Live prices come from one trading-board fetch. OHLC uses disk cache and
    parallel requests so the grid loads quickly after the first warm-up.
    """
    _ = refresh_token
    if not symbols:
        return pd.DataFrame(
            columns=["Symbol", "Low", "High", "Open of Day", "Close Of Day", "Current Price", "Date"]
        )

    board = load_trading_board()
    prices = _board_price_map(board)

    workers = min(8, max(1, len(symbols)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        ohlc_rows = list(pool.map(_last_day_ohlc, symbols))

    rows: list[dict] = []
    for row in ohlc_rows:
        sym = row["Symbol"]
        current = prices.get(sym)
        if current is None and row.get("Close Of Day") is not None:
            current = row["Close Of Day"]
        rows.append({**row, "Current Price": current})

    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def load_today_bar(symbol: str) -> pd.DataFrame:
    """Today's daily OHLC row when PSX has published it."""
    raw = psxdata.stocks(symbol, cache=False)
    if raw.empty:
        return raw
    today = pd.Timestamp.today().normalize()
    day = raw[raw["date"].dt.normalize() == today].copy()
    return day.sort_values("date")


@st.cache_data(ttl=30, show_spinner=False)
def load_intraday_ticks(symbol: str) -> pd.DataFrame:
    """Fetch today's PSX intraday ticks: [unix_ts, price, volume]."""
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


def fetch_live_tick(symbol: str) -> dict:
    """Latest price snapshot from trading board, falling back to screener quote."""
    sym = symbol.upper()
    board = load_trading_board()
    if not board.empty and "symbol" in board.columns:
        match = board[board["symbol"] == sym]
        if not match.empty:
            row = match.iloc[0]
            ldcp = pd.to_numeric(row.get("ldcp"), errors="coerce")
            change = pd.to_numeric(row.get("change"), errors="coerce")
            price = ldcp + change if pd.notna(ldcp) and pd.notna(change) else ldcp
            return {
                "symbol": sym,
                "price": float(price) if pd.notna(price) else None,
                "ldcp": float(ldcp) if pd.notna(ldcp) else None,
                "change": float(change) if pd.notna(change) else None,
                "change_pct": (change / ldcp * 100) if pd.notna(ldcp) and ldcp else None,
                "volume": float(row.get("volume")) if pd.notna(row.get("volume")) else None,
                "bid_price": float(row.get("bid_price")) if pd.notna(row.get("bid_price")) else None,
                "offer_price": float(row.get("offer_price")) if pd.notna(row.get("offer_price")) else None,
                "source": "trading_board",
                "timestamp": datetime.now(),
            }

    quote = psxdata.quote(sym, cache=False)
    if not quote.empty:
        row = quote.iloc[0]
        price = pd.to_numeric(row.get("price"), errors="coerce")
        change_pct = pd.to_numeric(row.get("change_pct"), errors="coerce")
        return {
            "symbol": sym,
            "price": float(price) if pd.notna(price) else None,
            "ldcp": None,
            "change": None,
            "change_pct": float(change_pct) if pd.notna(change_pct) else None,
            "volume": float(row.get("volume_avg_30d")) if pd.notna(row.get("volume_avg_30d")) else None,
            "bid_price": None,
            "offer_price": None,
            "source": "screener",
            "timestamp": datetime.now(),
        }

    return {"symbol": sym, "price": None, "timestamp": datetime.now(), "source": "none"}


def record_snapshot(symbol: str, tick: dict) -> None:
    """Append a live price point to session history for intraday charts."""
    if tick.get("price") is None:
        return
    if INTRADAY_STATE_KEY not in st.session_state:
        st.session_state[INTRADAY_STATE_KEY] = {}

    sym = symbol.upper()
    snaps: list[dict] = st.session_state[INTRADAY_STATE_KEY].get(sym, [])
    now = pd.Timestamp(tick["timestamp"])
    point = {
        "timestamp": now,
        "price": float(tick["price"]),
        "volume": float(tick.get("volume") or 0),
    }

    if snaps and (now - snaps[-1]["timestamp"]).total_seconds() < 20:
        snaps[-1] = point
    else:
        snaps.append(point)

    cutoff = now - pd.Timedelta(hours=8)
    st.session_state[INTRADAY_STATE_KEY][sym] = [s for s in snaps if s["timestamp"] >= cutoff]


def _normalize_ohlc(open_: float, high: float, low: float, close: float) -> tuple[float, float, float, float]:
    """Ensure valid candlestick OHLC (high/low wrap open/close)."""
    o, h, l, c = float(open_), float(high), float(low), float(close)
    h = max(h, o, c)
    l = min(l, o, c)
    return o, h, l, c


def prepare_chart_bars(symbol: str, interval_minutes: int = 5, max_candles: int = MAX_INTRADAY_CANDLES) -> pd.DataFrame:
    """Build real 5-minute OHLCV candles from PSX intraday timeseries ticks."""
    interval_minutes = 5
    ticks = load_intraday_ticks(symbol)
    if ticks.empty:
        return pd.DataFrame()

    # Bucket in Asia/Karachi so bars align to PSX session clock (09:30, 09:35, …).
    idx = pd.to_datetime(ticks["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Karachi")
    tick_df = ticks.assign(dt=idx).set_index("dt").sort_index()

    rule = f"{interval_minutes}min"
    ohlc = tick_df["price"].resample(rule).ohlc().dropna(subset=["open"])
    vol = tick_df["volume"].resample(rule).sum()
    bars = ohlc.join(vol.rename("volume"))
    if bars.empty:
        return pd.DataFrame()

    bars = bars.tail(max_candles).copy()
    rows: list[dict] = []
    for ts_key, row in bars.iterrows():
        o, h, l, c = _normalize_ohlc(row["open"], row["high"], row["low"], row["close"])
        rows.append({
            "timestamp": int(pd.Timestamp(ts_key).timestamp()),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": float(row["volume"] or 0),
        })
    return pd.DataFrame(rows)


def prepare_last_and_current_day_bars(symbol: str, interval_minutes: int = 5) -> pd.DataFrame:
    """Build 5-minute candles for the latest two trading sessions from intraday ticks."""
    interval_minutes = 5
    ticks = load_intraday_ticks(symbol)
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
        o, h, l, c = _normalize_ohlc(row["open"], row["high"], row["low"], row["close"])
        rows.append({
            "timestamp": int(pd.Timestamp(ts_key).timestamp()),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": float(row["volume"] or 0),
        })
    return pd.DataFrame(rows)


def _session_value(key: str):
    """Return session value without treating empty DataFrames as falsy."""
    return st.session_state.get(key)


def _live_tick(symbol: str) -> dict:
    tick = _session_value("live_tick")
    if tick is None:
        tick = fetch_live_tick(symbol)
    return tick


def _live_bars(symbol: str, interval: int) -> pd.DataFrame:
    cached_interval = st.session_state.get("live_bars_interval")
    bars = _session_value("live_bars")
    if bars is None or cached_interval != interval:
        bars = prepare_chart_bars(symbol, interval_minutes=interval)
        st.session_state["live_bars"] = bars
        st.session_state["live_bars_interval"] = interval
    return bars


def _bars_to_tradingview_payload(bars: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Convert OHLCV bars to Lightweight Charts candle and volume payloads."""
    candles: list[dict] = []
    volumes: list[dict] = []

    for _, row in bars.iterrows():
        ts = int(row["timestamp"])
        open_, high, low, close = _normalize_ohlc(
            row["open"], row["high"], row["low"], row["close"]
        )
        vol = float(row.get("volume") or 0)
        up = close >= open_

        candles.append({"time": ts, "open": open_, "high": high, "low": low, "close": close})
        volumes.append({
            "time": ts,
            "value": vol,
            "color": "rgba(38, 166, 154, 0.55)" if up else "rgba(239, 83, 80, 0.55)",
        })

    return candles, volumes


def render_tradingview_intraday_chart(
    bars: pd.DataFrame,
    symbol: str,
    interval_minutes: int,
    bar_spacing: int = 8,
    chart_height: int = 520,
    max_candles: int | None = MAX_INTRADAY_CANDLES,
) -> None:
    """Render five-minute candles using TradingView Lightweight Charts."""
    if bars.empty:
        return

    bars = bars.sort_values("timestamp").copy()
    if max_candles is not None:
        bars = bars.tail(max_candles)
    candles, volumes = _bars_to_tradingview_payload(bars)

    candles_json = json.dumps(candles)
    volumes_json = json.dumps(volumes)
    title = f"{symbol} · last {len(candles)} × 5-min candles · PKR"
    wrap_height = chart_height + 72
    chart_area_height = chart_height - 8

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    html, body {{
      margin: 0;
      padding: 0;
      background: #ffffff;
      overflow: hidden;
      user-select: none;
    }}
    #wrap {{
      width: 100%;
      height: {wrap_height}px;
      background: #ffffff;
      display: flex;
      flex-direction: column;
    }}
    #header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 10px 4px;
      flex-shrink: 0;
    }}
    #title {{
      color: #131722;
      font: 600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    #toolbar {{
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
    }}
    .btn {{
      background: #f3f4f6;
      color: #374151;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      padding: 4px 8px;
      font: 600 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      cursor: pointer;
      line-height: 1;
    }}
    .btn:hover {{ background: #e5e7eb; }}
    .btn:active {{ background: #d1d5db; }}
    #hint {{
      color: #6b7280;
      font: 11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      padding: 0 10px 4px;
      flex-shrink: 0;
    }}
    #chart-shell {{
      position: relative;
      flex: 1;
      min-height: 220px;
    }}
    #chart {{
      width: 100%;
      height: 100%;
    }}
    #resize-handle {{
      height: 10px;
      cursor: ns-resize;
      background: linear-gradient(to bottom, #ffffff, #f3f4f6);
      border-top: 1px solid #e5e7eb;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    #resize-handle::after {{
      content: '';
      width: 36px;
      height: 3px;
      border-radius: 2px;
      background: #9ca3af;
    }}
  </style>
</head>
<body>
  <div id="wrap">
    <div id="header">
      <div id="title">{title}</div>
      <div id="toolbar">
        <button class="btn" id="zoom-out" title="Narrower candles">−</button>
        <button class="btn" id="zoom-in" title="Wider candles">+</button>
        <button class="btn" id="fit-btn" title="Fit all candles">Fit</button>
        <button class="btn" id="reset-btn" title="Reset zoom">Reset</button>
      </div>
    </div>
    <div id="hint">Scroll to zoom width · drag price scale for height · drag bottom edge to resize panel</div>
    <div id="chart-shell">
      <div id="chart"></div>
    </div>
    <div id="resize-handle" title="Drag to resize chart height"></div>
  </div>
  <script>
    const candles = {candles_json};
    const volumes = {volumes_json};
    const initialBarSpacing = {bar_spacing};
    const minBarSpacing = 2;
    const maxBarSpacing = 40;

    const wrap = document.getElementById('wrap');
    const shell = document.getElementById('chart-shell');
    const container = document.getElementById('chart');
    const handle = document.getElementById('resize-handle');

    let barSpacing = initialBarSpacing;
    let userAdjustedHeight = false;

    const formatKarachiTime = (time, withSeconds = false) => {{
      const d = new Date(time * 1000);
      const opts = {{
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: 'Asia/Karachi',
      }};
      if (withSeconds) opts.second = '2-digit';
      return d.toLocaleTimeString('en-GB', opts);
    }};

    const formatKarachiTick = (time, tickMarkType) => {{
      const d = new Date(time * 1000);
      const opts = {{ timeZone: 'Asia/Karachi' }};
      if (tickMarkType === LightweightCharts.TickMarkType.Year) {{
        return d.toLocaleDateString('en-GB', {{ ...opts, year: 'numeric' }});
      }}
      if (tickMarkType === LightweightCharts.TickMarkType.Month) {{
        return d.toLocaleDateString('en-GB', {{ ...opts, month: 'short' }});
      }}
      if (tickMarkType === LightweightCharts.TickMarkType.DayOfMonth) {{
        return d.toLocaleDateString('en-GB', {{ ...opts, day: '2-digit', month: 'short' }});
      }}
      if (tickMarkType === LightweightCharts.TickMarkType.TimeWithSeconds) {{
        return formatKarachiTime(time, true);
      }}
      return formatKarachiTime(time, false);
    }};

    const chart = LightweightCharts.createChart(container, {{
      layout: {{
        background: {{ type: 'solid', color: '#ffffff' }},
        textColor: '#374151',
        fontSize: 10,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }},
      grid: {{
        vertLines: {{ color: '#e5e7eb' }},
        horzLines: {{ color: '#e5e7eb' }},
      }},
      crosshair: {{
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: {{
          color: '#9ca3af',
          width: 1,
          style: LightweightCharts.LineStyle.Dashed,
          labelBackgroundColor: '#374151',
        }},
        horzLine: {{
          color: '#9ca3af',
          width: 1,
          style: LightweightCharts.LineStyle.Dashed,
          labelBackgroundColor: '#374151',
        }},
      }},
      rightPriceScale: {{
        borderColor: '#e5e7eb',
        scaleMargins: {{ top: 0.18, bottom: 0.22 }},
        autoScale: true,
      }},
      timeScale: {{
        borderColor: '#e5e7eb',
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: false,
        fixRightEdge: false,
        barSpacing: barSpacing,
        minBarSpacing: minBarSpacing,
        rightOffset: 6,
        tickMarkFormatter: (time, tickMarkType) => formatKarachiTick(time, tickMarkType),
      }},
      localization: {{
        locale: 'en-US',
        timeFormatter: (time) => formatKarachiTime(time, false),
      }},
      handleScroll: {{
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      }},
      handleScale: {{
        axisPressedMouseMove: {{
          time: true,
          price: true,
        }},
        axisDoubleClickReset: {{
          time: true,
          price: true,
        }},
        mouseWheel: true,
        pinch: true,
      }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    }});
    candleSeries.setData(candles);

    const volumeSeries = chart.addHistogramSeries({{
      priceFormat: {{ type: 'volume' }},
      priceScaleId: '',
    }});
    volumeSeries.priceScale().applyOptions({{
      scaleMargins: {{ top: 0.82, bottom: 0 }},
    }});
    volumeSeries.setData(volumes);

    const applyBarSpacing = (next) => {{
      barSpacing = Math.max(minBarSpacing, Math.min(maxBarSpacing, next));
      chart.timeScale().applyOptions({{ barSpacing }});
    }};

    const fitAll = () => {{
      chart.timeScale().fitContent();
      candleSeries.priceScale().applyOptions({{ autoScale: true }});
    }};

    const resetView = () => {{
      applyBarSpacing(initialBarSpacing);
      candleSeries.priceScale().applyOptions({{
        autoScale: true,
        scaleMargins: {{ top: 0.18, bottom: 0.22 }},
      }});
      fitAll();
    }};

    document.getElementById('zoom-in').addEventListener('click', () => applyBarSpacing(barSpacing + 2));
    document.getElementById('zoom-out').addEventListener('click', () => applyBarSpacing(barSpacing - 2));
    document.getElementById('fit-btn').addEventListener('click', fitAll);
    document.getElementById('reset-btn').addEventListener('click', resetView);

    const resizeChart = () => {{
      const w = shell.clientWidth || wrap.clientWidth || 800;
      const h = shell.clientHeight || {chart_area_height};
      chart.applyOptions({{ width: w, height: h }});
    }};

    fitAll();
    resizeChart();

    window.addEventListener('resize', resizeChart);

    let dragging = false;
    let startY = 0;
    let startHeight = 0;

    handle.addEventListener('mousedown', (e) => {{
      dragging = true;
      userAdjustedHeight = true;
      startY = e.clientY;
      startHeight = shell.clientHeight;
      e.preventDefault();
    }});

    window.addEventListener('mousemove', (e) => {{
      if (!dragging) return;
      const next = Math.max(220, Math.min(900, startHeight + (e.clientY - startY)));
      shell.style.height = next + 'px';
      wrap.style.height = (next + 72) + 'px';
      resizeChart();
    }});

    window.addEventListener('mouseup', () => {{
      dragging = false;
    }});
  </script>
</body>
</html>
"""
    components.html(html, height=wrap_height + 20, scrolling=False)


@st.fragment(run_every=timedelta(seconds=30))
def _auto_poll_live(symbol: str, interval: int, enabled: bool) -> None:
    if not enabled:
        return
    load_intraday_ticks.clear()
    load_trading_board.clear()
    tick = fetch_live_tick(symbol)
    record_snapshot(symbol, tick)
    st.session_state["live_tick"] = tick
    st.session_state["live_bars"] = prepare_chart_bars(symbol, interval_minutes=interval)
    st.session_state["live_bars_interval"] = interval


def render_live_intraday_section(symbol: str) -> None:
    """Main-dashboard live section with real PSX 5-minute candles."""
    st.subheader("⚡ Live intraday — latest data")
    st.caption(
        f"Real **5-minute** OHLCV candles from PSX timeseries for **{symbol}** "
        f"(last **{MAX_INTRADAY_CANDLES}** bars)."
    )

    ctrl1, ctrl2, ctrl3 = st.columns([1.2, 1.2, 2.6])
    interval = 5
    with ctrl1:
        st.markdown("**Bar size:** 5 min")
    with ctrl2:
        auto_refresh = st.toggle("Auto-refresh", value=True, key="auto_refresh")
    with ctrl3:
        if st.button("🔄 Fetch latest now", use_container_width=True):
            load_trading_board.clear()
            load_quote.clear()
            load_intraday_ticks.clear()
            st.session_state.pop("live_tick", None)
            st.session_state.pop("live_bars", None)
            st.session_state.pop("live_bars_interval", None)

    zoom1, zoom2 = st.columns(2)
    with zoom1:
        bar_spacing = st.slider(
            "Candle width",
            min_value=2,
            max_value=40,
            value=8,
            step=1,
            help="Default candle width. Use +/− on the chart or scroll wheel to adjust live.",
            key="intraday_bar_spacing",
        )
    with zoom2:
        chart_height = st.slider(
            "Chart height",
            min_value=320,
            max_value=900,
            value=520,
            step=20,
            help="Panel height in pixels. You can also drag the bottom edge of the chart.",
            key="intraday_chart_height",
        )

    _auto_poll_live(symbol, interval, auto_refresh)

    tick = _live_tick(symbol)
    if _session_value("live_tick") is None:
        record_snapshot(symbol, tick)

    today = load_today_bar(symbol)
    price = tick.get("price")
    bars = prepare_chart_bars(symbol, interval)
    st.session_state["live_bars"] = bars
    st.session_state["live_bars_interval"] = interval

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Last price", f"{price:,.2f}" if price is not None else "n/a")
    chg = tick.get("change_pct")
    m2.metric("Change %", f"{chg:+.2f}%" if chg is not None else "n/a")
    m3.metric("Volume", f"{tick.get('volume'):,.0f}" if tick.get("volume") else "n/a")
    m4.metric("Bid / Ask", f"{tick.get('bid_price') or '-'} / {tick.get('offer_price') or '-'}")
    m5.metric("5-min bars", f"{len(bars)}" if not bars.empty else "0")

    if not today.empty:
        t = today.iloc[-1]
        st.markdown(
            f"**Today's session (daily):** open **{t['open']:,.2f}** · high **{t['high']:,.2f}** · "
            f"low **{t['low']:,.2f}** · close **{t['close']:,.2f}** · vol **{t['volume']:,.0f}**"
        )

    if not bars.empty:
        render_tradingview_intraday_chart(
            bars,
            symbol,
            interval,
            bar_spacing=bar_spacing,
            chart_height=chart_height,
            max_candles=MAX_INTRADAY_CANDLES,
        )
    else:
        st.warning(
            f"No intraday ticks for **{symbol}** right now. "
            "Try again during market hours (Mon–Fri, PSX session)."
        )

    with st.expander("Latest trading-board row"):
        board = load_trading_board()
        if not board.empty:
            row = board[board["symbol"] == symbol.upper()]
            if not row.empty:
                st.dataframe(row.T, use_container_width=True)
            else:
                st.caption(f"{symbol} not on the REG/main board right now — using screener fallback.")
        st.caption(f"Data source: PSX timeseries + {tick.get('source', 'unknown')}")

    if auto_refresh:
        st.caption("Auto-refreshing every 30 seconds during this session.")


@st.fragment(run_every=timedelta(seconds=30))
def _auto_poll_candle_chart(symbol: str, enabled: bool) -> None:
    if not enabled:
        return
    load_intraday_ticks.clear()
    load_trading_board.clear()
    st.session_state["candle_live_tick"] = fetch_live_tick(symbol)
    st.session_state["candle_live_bars"] = prepare_last_and_current_day_bars(symbol, interval_minutes=5)


def render_candle_chart_page() -> None:
    """Candle Chart page with stock list picker and two-session 5-minute candles."""
    st.title("Candle Chart")

    stocks: list[dict] = [dict(s) for s in st.session_state[STOCKS_LIST_KEY]]
    if not stocks:
        st.info("No stocks found in Stocks List. Add stocks in Trending List first.")
        return

    symbols = [s["symbol"] for s in stocks]
    if st.session_state.get(CANDLE_CHART_SYMBOL_KEY) not in symbols:
        st.session_state[CANDLE_CHART_SYMBOL_KEY] = symbols[0]
    selected_symbol = st.session_state[CANDLE_CHART_SYMBOL_KEY]
    selected_idx = symbols.index(selected_symbol)

    chart_col, list_col = st.columns([6.0, 1.2])
    with list_col:
        st.markdown("**Stocks List**")
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
            st.session_state.pop("candle_live_tick", None)
            st.session_state.pop("candle_live_bars", None)
            st.rerun()

    with chart_col:
        symbol = st.session_state[CANDLE_CHART_SYMBOL_KEY]
        selected_stock = next((s for s in stocks if s["symbol"] == symbol), {"symbol": symbol, "name": ""})
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


def price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{symbol} — Price & Moving Averages", "Volume"),
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["close"], name="Close", line=dict(color="#2563eb", width=2)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["sma_20"], name="SMA 20", line=dict(color="#f59e0b", width=1.5)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["sma_50"], name="SMA 50", line=dict(color="#10b981", width=1.5)),
        row=1,
        col=1,
    )
    colors = ["#ef4444" if c < o else "#22c55e" for c, o in zip(df["close"], df["open"], strict=False)]
    fig.add_trace(
        go.Bar(x=df["date"], y=df["volume"], name="Volume", marker_color=colors, opacity=0.7),
        row=2,
        col=1,
    )
    fig.update_layout(
        height=520,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=60, b=40),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="PKR", row=1, col=1)
    fig.update_yaxes(title_text="Shares", row=2, col=1)
    return fig


def trend_badge(trend: str) -> str:
    if trend.startswith("bullish"):
        return "🟢 Bullish"
    return "🔴 Bearish"


def _active_trending_symbols() -> list[str]:
    return [s["symbol"] for s in st.session_state[STOCKS_LIST_KEY] if s.get("included")]


def _update_stocks_list(stocks: list[dict]) -> None:
    st.session_state[STOCKS_LIST_KEY] = stocks
    save_stocks_list_file(stocks)


def render_trending_list_report() -> None:
    """Trending List — uses FormTemplate (watchlist + OHLC/live-price grid)."""

    def _on_refresh() -> None:
        load_trading_board.clear()
        load_trending_list.clear()

    FormTemplate(
        form_id="trending",
        title="List of Stocks",
        watchlist_label="Watchlist",
        report_label="Report",
        refresh_label="🔄 Refresh",
        load_records=load_trending_list,
        get_stocks=lambda: list(st.session_state[STOCKS_LIST_KEY]),
        set_stocks=_update_stocks_list,
        on_refresh=_on_refresh,
        resolve_symbol_name=lambda sym: TRENDING_LIST_CATALOG.get(sym, ""),
        display_columns=["Symbol", "Low", "High", "Open of Day", "Close Of Day", "Current Price"],
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Low": st.column_config.NumberColumn("Low", format="%.2f"),
            "High": st.column_config.NumberColumn("High", format="%.2f"),
            "Open of Day": st.column_config.NumberColumn("Open", format="%.2f"),
            "Close Of Day": st.column_config.NumberColumn("Close", format="%.2f"),
            "Current Price": st.column_config.NumberColumn("Current", format="%.2f"),
        },
    ).render()


def render_dashboard(symbol: str) -> None:
    """Main stock analysis dashboard."""
    st.title("PSX Stock Analysis Dashboard")
    st.markdown("Live Pakistan Stock Exchange data — sectors, movers, charts & technicals.")

    quote_df = load_quote(symbol)
    summary = analyze_symbol(symbol)

    if "error" not in summary:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Price (PKR)", f"{summary['price']:,.2f}")
        c2.metric("SMA 20", f"{summary['sma_20']:,.2f}")
        c3.metric("SMA 50", f"{summary['sma_50']:,.2f}")
        c4.metric("52W Range", f"{summary['low_52w']:,.0f} – {summary['high_52w']:,.0f}")
        vol = summary["volatility_20d"]
        c5.metric("20D Volatility", f"{vol:+.2f}%" if vol is not None else "n/a")
        st.info(f"**{symbol}** trend: {trend_badge(summary['trend'])} · {summary['trend'].split('(')[-1].rstrip(')') if '(' in summary['trend'] else ''}")
    else:
        st.warning(f"No price history found for **{symbol}**. Try another ticker.")

    st.markdown("---")
    render_live_intraday_section(symbol)
    st.markdown("---")

    tab_chart, tab_movers, tab_sectors, tab_index = st.tabs(
        ["📊 Chart & Analysis", "🔥 Top Movers", "🏭 Sectors", "📋 KSE-100"]
    )

    with tab_chart:
        hist = load_history(symbol)
        if not hist.empty:
            st.plotly_chart(price_chart(hist, symbol), use_container_width=True)

            left, right = st.columns(2)
            with left:
                st.subheader("Live quote")
                if not quote_df.empty:
                    display_cols = [c for c in quote_df.columns if c in quote_df.columns]
                    st.dataframe(quote_df[display_cols].T, use_container_width=True)
                else:
                    st.caption("Quote not available in screener.")
            with right:
                st.subheader("Recent prices")
                show = hist[["date", "open", "high", "low", "close", "volume"]].sort_values("date", ascending=False).head(15)
                st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.error("Could not load chart data for this symbol.")

    with tab_movers:
        screener = load_screener()
        if screener.empty or "change_pct" not in screener.columns:
            st.warning("Screener data unavailable.")
        else:
            valid = screener.dropna(subset=["change_pct"])
            n = st.slider("Number of movers", 5, 25, 10)
            g1, g2 = st.columns(2)
            cols = [c for c in ["symbol", "price", "change_pct", "change_1y_pct", "pe_ratio", "volume_avg_30d"] if c in valid.columns]
            with g1:
                st.subheader("Top gainers")
                st.dataframe(valid.nlargest(n, "change_pct")[cols], use_container_width=True, hide_index=True)
            with g2:
                st.subheader("Top losers")
                st.dataframe(valid.nsmallest(n, "change_pct")[cols], use_container_width=True, hide_index=True)

    with tab_sectors:
        sectors = load_sectors()
        if sectors.empty:
            st.warning("Sector data unavailable.")
        else:
            top = sectors.sort_values("market_cap_b", ascending=False)
            fig = go.Figure(
                go.Bar(
                    x=top.head(15)["market_cap_b"],
                    y=top.head(15)["sector_name"],
                    orientation="h",
                    marker_color="#2563eb",
                )
            )
            fig.update_layout(
                title="Top 15 sectors by market cap (PKR billions)",
                height=500,
                template="plotly_white",
                yaxis=dict(autorange="reversed"),
                xaxis_title="Market cap (B PKR)",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                top[["sector_name", "market_cap_b", "advance", "decline", "unchanged", "turnover"]],
                use_container_width=True,
                hide_index=True,
            )

    with tab_index:
        kse100 = load_kse100()
        if kse100.empty:
            st.warning("KSE-100 data unavailable.")
        else:
            st.subheader(f"KSE-100 — {len(kse100)} stocks")
            top_idx = kse100.nlargest(15, "idx_weight")
            fig = go.Figure(go.Pie(labels=top_idx["symbol"], values=top_idx["idx_weight"], hole=0.4))
            fig.update_layout(title="Top 15 index weights (%)", height=450, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            show_cols = [c for c in ["symbol", "idx_weight", "current_index", "market_cap_m"] if c in kse100.columns]
            st.dataframe(kse100.sort_values("idx_weight", ascending=False)[show_cols], use_container_width=True, hide_index=True)


# --- Top navigation (in-flow at top of form; reliable on mobile browsers) ---
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
        padding-top: 0.75rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        max-width: 100% !important;
    }
    /* Keep room for the in-flow Reports menu above form content */
    .block-container:has(.top-reports-nav-marker),
    .block-container:has(.top-reports-nav-marker):has(.form-page-marker) {
        padding-top: 0.5rem !important;
    }

    .top-reports-nav-marker {
        display: block;
        height: 0;
        margin: 0;
        padding: 0;
        overflow: hidden;
    }

    /* Reports menu — first item at top of form (document flow, not fixed) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) {
        position: relative !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 0 0.65rem 0 !important;
        border: 1px solid rgba(15, 23, 42, 0.14) !important;
        border-radius: 0.4rem !important;
        background: #ffffff !important;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08) !important;
        padding: 0.55rem 0.75rem 0.6rem !important;
        z-index: 5 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) label {
        display: block !important;
        visibility: visible !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        margin-bottom: 0.15rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) [data-testid="stSelectbox"] {
        display: block !important;
        visibility: visible !important;
        width: 100% !important;
        max-width: 28rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) div[data-baseweb="select"] > div {
        min-height: 2.4rem !important;
    }

    @media (max-width: 768px) {
        .block-container,
        .block-container:has(.top-reports-nav-marker),
        .block-container:has(.top-reports-nav-marker):has(.form-page-marker) {
            padding-top: 0.4rem !important;
            padding-left: 0.55rem !important;
            padding-right: 0.55rem !important;
            padding-bottom: 0.75rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            margin-bottom: 0.55rem !important;
            padding: 0.65rem 0.6rem 0.7rem !important;
            background: #ffffff !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) [data-testid="stSelectbox"] {
            max-width: 100% !important;
            width: 100% !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) label {
            font-size: 1.05rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-reports-menu-marker) div[data-baseweb="select"] > div {
            min-height: 2.75rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

REPORT_MENU: dict[str, str] = {
    "Trending List": "trending_list",
    "Candle Chart": "candle_chart",
    "Dashboard": "dashboard",
}
REPORT_MENU_LABELS = list(REPORT_MENU.keys())
REPORT_PAGE_TO_LABEL = {page: label for label, page in REPORT_MENU.items()}

if "current_page" not in st.session_state:
    st.session_state.current_page = "trending_list"

st.markdown('<div class="top-reports-nav-marker"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown('<div class="top-reports-menu-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _default_label = REPORT_PAGE_TO_LABEL.get(st.session_state.current_page, REPORT_MENU_LABELS[0])
    selected_report = st.selectbox(
        "Reports",
        options=REPORT_MENU_LABELS,
        index=REPORT_MENU_LABELS.index(_default_label),
        key="reports_menu",
        help="Open a report form",
    )
    st.session_state.current_page = REPORT_MENU[selected_report]

symbol = "ENGRO"

if st.session_state.current_page == "trending_list":
    render_trending_list_report()
elif st.session_state.current_page == "candle_chart":
    render_candle_chart_page()
else:
    render_dashboard(symbol)
