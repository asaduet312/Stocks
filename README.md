# Stocks Dashboard

Streamlit app for Pakistan Stock Exchange. **Stocks Dashboard** is the main form.

Forms (top buttons — no dropdown):

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
streamlit run app.py
```

Open http://localhost:8501

## Watchlists

| File | Used by |
|------|---------|
| `10MinutesWatchlist.json` | 10-Minute Breakout Scanner |
| `Stocks List.json` | Candle Chart (also seeds the breakout list on first run) |

## Project layout

```
app.py                      # Streamlit entry (Stocks Dashboard home)
forms/                      # Form screens
  stocks_dashboard.py
  ten_min_breakout.py
  candle_chart.py
  chart_render.py
data/                       # Watchlists + live market helpers (no Streamlit cache)
ui/                         # Shared styles, button nav, FormTemplate
psxdata/                    # Realtime trading-board + HTTP helpers
Stocks List.json
10MinutesWatchlist.json
```
