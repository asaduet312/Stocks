"""PSX Stock Analysis — terminal dashboard powered by psxdata.

Run:
    python examples/stock_analysis.py
    python examples/stock_analysis.py --symbols ENGRO LUCK UBL
"""
from __future__ import annotations

import argparse
from datetime import date

import pandas as pd
import psxdata
from psxdata.scrapers.screener import ScreenerScraper


def _fmt_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:+.2f}%"


def _fmt_num(value: float | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:,.{decimals}f}"


def add_technicals(df: pd.DataFrame) -> pd.DataFrame:
    """Add SMA-20, SMA-50, daily return, and 20-day volatility."""
    out = df.sort_values("date").copy()
    out["sma_20"] = out["close"].rolling(20, min_periods=1).mean()
    out["sma_50"] = out["close"].rolling(50, min_periods=1).mean()
    out["daily_return_pct"] = out["close"].pct_change() * 100
    out["volatility_20d"] = out["daily_return_pct"].rolling(20, min_periods=5).std()
    return out


def analyze_symbol(symbol: str, lookback_days: int = 365) -> dict:
    """Fetch history and compute technical summary for one ticker."""
    raw = psxdata.stocks(symbol)
    if raw.empty:
        raw = psxdata.stocks(symbol, cache=False)
    if raw.empty:
        return {"symbol": symbol.upper(), "error": "no data"}

    # Use the most recent rows available (PSX may lag for some symbols).
    df = add_technicals(raw.sort_values("date").tail(lookback_days))
    latest = df.iloc[-1]
    quote = psxdata.quote(symbol)
    live_price = quote["price"].iloc[0] if not quote.empty else latest["close"]

    trend = "bullish" if latest["close"] >= latest["sma_50"] else "bearish"
    if latest["sma_20"] >= latest["sma_50"]:
        trend += " (SMA20 > SMA50)"
    else:
        trend += " (SMA20 < SMA50)"

    return {
        "symbol": symbol.upper(),
        "price": float(live_price),
        "sma_20": float(latest["sma_20"]),
        "sma_50": float(latest["sma_50"]),
        "high_52w": float(df["high"].max()),
        "low_52w": float(df["low"].min()),
        "volatility_20d": float(latest["volatility_20d"]) if pd.notna(latest["volatility_20d"]) else None,
        "trend": trend,
        "rows": len(df),
    }


def print_market_overview() -> None:
    print("\n" + "=" * 60)
    print("MARKET OVERVIEW")
    print("=" * 60)

    sectors = psxdata.sectors()
    if not sectors.empty:
        top = sectors.sort_values("market_cap_b", ascending=False).head(5)
        print("\nTop 5 sectors by market cap (PKR billions):")
        for _, row in top.iterrows():
            breadth = f"+{int(row['advance'])} / -{int(row['decline'])} / ={int(row['unchanged'])}"
            print(
                f"  {row['sector_name']:<42} "
                f"cap={_fmt_num(row['market_cap_b'])}  breadth={breadth}"
            )

    kse100 = psxdata.indices("KSE100")
    if not kse100.empty:
        print(f"\nKSE-100: {len(kse100)} constituents")
        print("Top 5 by index weight:")
        for _, row in kse100.nlargest(5, "idx_weight").iterrows():
            print(f"  {row['symbol']:<8} weight={row['idx_weight']:.2f}%")


def print_movers(limit: int = 10) -> None:
    print("\n" + "=" * 60)
    print("TOP MOVERS (full market screener)")
    print("=" * 60)

    screener = ScreenerScraper().fetch()
    if screener.empty or "change_pct" not in screener.columns:
        print("  Screener data unavailable.")
        return

    cols = ["symbol", "price", "change_pct", "change_1y_pct", "pe_ratio", "volume_avg_30d"]
    cols = [c for c in cols if c in screener.columns]
    valid = screener.dropna(subset=["change_pct"]).copy()

    print(f"\nTop {limit} gainers today:")
    gainers = valid.nlargest(limit, "change_pct")[cols]
    for _, row in gainers.iterrows():
        print(
            f"  {row['symbol']:<10} {_fmt_num(row['price']):>10}  "
            f"day={_fmt_pct(row['change_pct']):>8}  1y={_fmt_pct(row.get('change_1y_pct')):>8}"
        )

    print(f"\nTop {limit} losers today:")
    losers = valid.nsmallest(limit, "change_pct")[cols]
    for _, row in losers.iterrows():
        print(
            f"  {row['symbol']:<10} {_fmt_num(row['price']):>10}  "
            f"day={_fmt_pct(row['change_pct']):>8}  1y={_fmt_pct(row.get('change_1y_pct')):>8}"
        )


def print_symbol_analysis(symbols: list[str]) -> None:
    print("\n" + "=" * 60)
    print("TECHNICAL ANALYSIS")
    print("=" * 60)

    for symbol in symbols:
        result = analyze_symbol(symbol)
        print(f"\n{result['symbol']}")
        if "error" in result:
            print(f"  Error: {result['error']}")
            continue
        print(f"  Price:          {_fmt_num(result['price'])}")
        print(f"  SMA-20:         {_fmt_num(result['sma_20'])}")
        print(f"  SMA-50:         {_fmt_num(result['sma_50'])}")
        print(f"  52-week range:  {_fmt_num(result['low_52w'])} – {_fmt_num(result['high_52w'])}")
        print(f"  20d volatility: {_fmt_pct(result['volatility_20d'])}")
        print(f"  Trend:          {result['trend']}")
        print(f"  History rows:   {result['rows']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PSX stock analysis dashboard")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["ENGRO", "LUCK", "UBL", "HBL", "FFC"],
        help="Tickers for technical analysis (default: ENGRO LUCK UBL HBL FFC)",
    )
    parser.add_argument("--movers", type=int, default=10, help="Top gainers/losers to show")
    args = parser.parse_args()

    print("=" * 60)
    print("PSX STOCK ANALYSIS")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)

    print_market_overview()
    print_movers(limit=args.movers)
    print_symbol_analysis(args.symbols)

    print("\n" + "=" * 60)
    print("Analysis complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
