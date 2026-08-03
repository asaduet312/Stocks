"""TradingView Lightweight Charts renderer for Candle Chart."""
from __future__ import annotations

import json

import pandas as pd
import streamlit.components.v1 as components

from data.market import normalize_ohlc


def _bars_to_tradingview_payload(bars: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Convert OHLCV bars to Lightweight Charts candle and volume payloads."""
    candles: list[dict] = []
    volumes: list[dict] = []

    for _, row in bars.iterrows():
        ts = int(row["timestamp"])
        open_, high, low, close = normalize_ohlc(
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
    max_candles: int | None = None,
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
