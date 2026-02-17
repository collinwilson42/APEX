# Execution Engine – Seed Log

---

24: 2026-02-14 – Dual Screenshot Capture: Per-Timeframe MSS Regions ^seed-dual-screenshot

## Prompts & Execution
"We need to update the profile config and trader program to use two separate screenshots one for 15m and one for 1hr. My screen dimensions are 3840 x 2140. Please update the config to be exact for what the 1hr and 15m should expect to capture using mss not playwright."

## 1. Seed (Intent)
- **Fix SyntaxError** in `torra_trader.py` — file has duplicated sections from a bad save, causing `SyntaxError: unterminated string literal` at line 155 which makes the trader exit immediately on activation
- **Dual mss screenshot capture** — instead of one fullscreen capture shared by both timeframes, capture **two distinct screen regions**: one targeting the TACTICAL (15m) panel and one targeting the TREND (1h) panel in the APEX three-panel layout
- **Profile config drives regions** — screenshot coordinates stored in `trading_config.screenshot_regions` so they can be tuned from the Profile Manager UI without code changes
- **mss-first, Playwright fallback removed** — Playwright headless capture was never working reliably on this setup. MSS is the primary and only capture method.

## 2. Related (Context)
- [[Seed 19 – The Rewired Engine]] (torra_trader.py full rewrite — this seed fixes the corrupted file from that rewrite)
- [[Seed 23 – Headless Chart Capture]] (Playwright approach — being superseded by mss-direct for reliability)
- [[Seed 18 – The Sentient Ledger]] (DB-driven scoring — screenshot feeds into save_sentiment pipeline)
- APEX three-panel layout: Tactical (15m) top, Trend (1h) middle, Algo controls bottom
- Screen: 3840 × 2140 native resolution
- The APEX browser window occupies center of screen with MT5 Navigator on left

## 4. Foundation (Structure)

### REWRITTEN (fixing corruption + dual capture)
- `torra_trader.py` — Fix SyntaxError (duplicated code block), add per-timeframe screenshot regions, `_tick()` selects correct region based on timeframe arg

### MODIFIED  
- `profiles/trading_config_default.json` — Add `screenshot_regions` section with 15m and 1h mss coordinates
- `profiles/maestro_gold_v1.json` — Add matching `screenshot_regions`

### READ (no changes)
- `trader_routes.py` — Spawns trader, passes trading_config (already handles arbitrary config keys)
- `instance_database.py` — save_sentiment unchanged
- `chart_capture.py` — Still exists but no longer primary capture path
- `scoring_rubric.py` — Scoring prompts unchanged

## 8. Infinity (Patterns/Debt)
- **Pattern: Region-per-timeframe** — Each timeframe gets its own `{left, top, width, height}` in config. The `_tick(timeframe)` method looks up `screenshot_regions[timeframe]` and passes to mss. This means the same trader process captures different parts of the screen at different schedule ticks.
- **Pattern: Config-driven coordinates** — If the user rearranges their APEX layout or moves monitors, they update the profile JSON — no code changes needed.
- **Debt avoided: Playwright dependency** — Removing the Playwright preference path eliminates the `playwright install chromium` requirement and the headless browser overhead.
- **Debt: DPI calibration** — The pixel coordinates are estimated from a screenshot-to-native scaling analysis. A `screenshot_calibrate.py` utility could be built later to let the user click corners and auto-generate coords. For now, manual tuning via profile config.
- **Coordinate estimates (3840×2140 native):**
  - 15m TACTICAL: `{left: 1040, top: 200, width: 1840, height: 520}`
  - 1h TREND: `{left: 1040, top: 710, width: 1840, height: 500}`
  - These include the chart + Transition Matrix panels for full AI context

## 7. Evolution (Real-Time Log)
- [x] Diagnosed SyntaxError: duplicated code block in torra_trader.py line 155
- [x] Analyzed screenshot → native pixel coordinate mapping (scale factor ~2.63x)
- [x] Planted Seed 24
- [x] Fixed torra_trader.py — clean rewrite of score_chart() regex, removed duplicate code
- [x] Added dual screenshot_regions to trading_config
- [x] Updated _tick() to use per-timeframe mss regions
- [ ] User tests activation — coordinates may need fine-tuning

## 5. Senses (UX/DX)
- Trader activation should no longer crash with "exited immediately"
- Startup banner shows capture method: `mss region (15m: 1040,200 1840×520 | 1h: 1040,710 1840×500)`
- Each tick prints: `📸 Capturing 15m chart via mss region (1040,200 1840×520)`
- If region captures a blank/wrong area, user tunes coordinates in Profile Manager and hot-reload picks up changes on next tick

## Architecture Flow
```
Activation → validate_config() → spawn torra_trader.py
  │
  ├─ _tick("15m") @ :01/:16/:31/:46
  │    └─ mss.grab(screenshot_regions["15m"]) → base64 → Claude API → save_sentiment
  │
  └─ _tick("1h") @ :02
       └─ mss.grab(screenshot_regions["1h"]) → base64 → Claude API → save_sentiment
```
