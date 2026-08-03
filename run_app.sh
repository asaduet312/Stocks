#!/usr/bin/env bash
# Stocks Dashboard — launch web UI (Linux / macOS / WSL)
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
  else
    echo "Python 3.11+ not found. Install Python and retry." >&2
    exit 1
  fi
fi

"$PYTHON" -m pip install -r requirements.txt -q
exec "$PYTHON" -m streamlit run examples/stock_analysis_ui.py \
  --server.headless true \
  --server.port "${PORT:-8501}" \
  --server.address 0.0.0.0 \
  --browser.gatherUsageStats false
