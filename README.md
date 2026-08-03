# Stocks Dashboard

Streamlit app for Pakistan Stock Exchange. **Stocks Dashboard** is the home page.

Each report is an **independent page** under `app_pages/`.

- **Dashboard** shows report buttons only
- Opening a report goes to that page (no dashboard buttons)
- Report pages have **← Back**, which returns to the dashboard

1. **Stocks Dashboard** — home + report launchers
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
app.py                         # Entry: registers pages + top button nav
app_pages/                     # Independent report pages (edit/copy these)
  stocks_dashboard.py
  ten_min_breakout.py
  candle_chart.py
data/                          # Watchlists + live market helpers
ui/                            # Shared styles, nav, FormTemplate, chart helper
psxdata/                       # Realtime trading-board + HTTP helpers
Stocks List.json
10MinutesWatchlist.json
```

To add a new report: copy a file in `app_pages/`, register it in `app.py`, add a launcher on the dashboard, and call `render_back_to_dashboard()` at the top of the report page.
