# ═══════════════════════════════════════════════════════════════════════════
# SEED 23 — HEADLESS CHART CAPTURE
# ═══════════════════════════════════════════════════════════════════════════
# 
# PROBLEM: 
#   The TORRA trader was using mss (monitor screenshot) to capture charts.
#   This captured whatever window was in focus — often the Claude chat window
#   instead of the TradingView chart. The agents correctly identified they
#   were looking at "a Claude chat conversation about CSS styling" and scored
#   everything as 0.00. Risk gate issued FULL VETO.
#
# SOLUTION:
#   Replace monitor screenshots with headless Playwright browser capture.
#   The new chart_capture.py module:
#     1. Launches headless Chromium
#     2. Navigates to localhost:5000 (Apex app)
#     3. Waits for Plotly charts to render
#     4. Exports via Plotly.toImage() → base64 PNG
#     5. Returns clean chart image guaranteed to be the actual chart
#
# PRIORITY: Playwright > mss region > mss fullscreen
# FALLBACK: If Playwright unavailable, falls back to mss with region config
#
# FILES CHANGED:
#   NEW:  chart_capture.py — Headless Plotly export via Playwright
#   MOD:  torra_trader.py — Uses chart_capture as primary, mss as fallback
#   MOD:  init2.py — Registers /api/chart-capture/<timeframe> endpoint
#
# SETUP:
#   pip install playwright
#   playwright install chromium
#
# LENS 7 — EVOLUTION:
#   Seed 22 → Seed 23: Screenshot system evolved from "grab whatever's on
#   screen" to "headless browser exports the exact chart". This eliminates
#   the entire class of "wrong window" errors permanently.
# ═══════════════════════════════════════════════════════════════════════════
