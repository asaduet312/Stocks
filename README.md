# Stocks Dashboard

Streamlit app for Pakistan Stock Exchange with three forms:

1. **Stocks Dashboard** — home / navigation
2. **10-Minute Breakout Scanner** — watchlist scan for first-10-minute breakouts
3. **Candle Chart** — 5-minute candles for the latest two sessions

## Run locally

```bash
# Windows
run_app.bat

# PowerShell
.\run_app.ps1

# macOS / Linux
./run_app.sh
```

Or:

```bash
pip install -r requirements.txt
streamlit run examples/stock_analysis_ui.py
```

Open http://localhost:8501

## Watchlists

| File | Used by |
|------|---------|
| `10MinutesWatchlist.json` | 10-Minute Breakout Scanner |
| `Stocks List.json` | Candle Chart (also seeds the breakout list on first run) |

## Project layout

```
examples/stock_analysis_ui.py   # Streamlit app (entry point)
examples/form_template.py       # Shared watchlist + report grid shell
psxdata/                        # Realtime trading-board + HTTP helpers
Stocks List.json
10MinutesWatchlist.json
```
