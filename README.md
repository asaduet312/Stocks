# StocksDotNet

ASP.NET Core Razor Pages port of the Python Streamlit PSX Stocks app.

## Pages

- `/` — Stocks Dashboard
- `/TenMinBreakout` — 10-Minute Breakout Scanner
- `/CandleChart` — Candle Chart (5-minute bars, auto-refresh every 30s)

## Run

```bash
cd StocksDotNet
dotnet run
```

Open the URL shown in the console (usually `https://localhost:7xxx` or `http://localhost:5xxx`).

## Data

Watchlists live in `Data/`:

- `10MinutesWatchlist.json` — breakout scanner
- `StocksList.json` — candle chart stocks list

Logic matches the Python project (`data/market.py`): PSX trading board + intraday ticks, Karachi timezone, first completed 10-minute candle breakout filters, and 5-minute OHLC for the last two sessions.
