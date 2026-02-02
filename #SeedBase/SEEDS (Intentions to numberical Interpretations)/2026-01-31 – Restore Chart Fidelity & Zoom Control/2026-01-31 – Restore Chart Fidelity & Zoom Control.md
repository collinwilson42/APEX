# Visuals – Seed Log

---

6: 2026-01-31 – Restore Chart Fidelity & Zoom Control ^seed-visuals-fidelity

## Prompts & Execution
"Next seed as you can see in the two images is the same data with very different looks the flask apex version is clean and complete showing full bar movement including wicks and candles. We need to migrate this style over to init2.py. Also while were at it lets fix that not all of the indicator lines extend the full width of the screen. Also in init2.py i cant change the number of bars but in flask_apex.py i can change the number of bar smoothly so lets migrate over everything thats working from flask_apex.py and make the indicator lines extend the full width of the panel."

## 1. Seed (Intent)
- **Objective:** Fix visual regressions in `init2.py` to match the "clean" look of the legacy app.
- **Specifics:**
    - **Full Width Indicators:** Align API limits so indicators (EMA/ATR) extend the full length of the chart (Fix 100 vs 300 bar mismatch).
    - **Candle Fidelity:** Ensure `high`/`low` data is correctly parsed to render wicks.
    - **Zoom/Bar Count:** Enable the "Number of Bars" UI control to dynamically update the `limit` parameter in `init2.py`.

## 2. Related (Context)
- `init2.py` (The target backend with the mismatched defaults).
- `static/js/apex_views.js` (Chart data fetching).
- `static/js/apex_indicators.js` (Bar count settings).

## 4. Foundation (Structure)
*Files modified:*
- `init2.py`:
  - `/api/chart-data` default limit: 200 → 300
  - `/api/basic` default limit: 100 → 300
  - `/api/advanced` default limit: 100 → 300
  - `/api/fibonacci` default limit: 100 → 300
  - `/api/ath` default limit: 100 → 300
- `static/js/apex_views.js`:
  - `loadChartData()` now reads `ApexIndicators.getBarCount(timeframe)` for dynamic limit

## 5. Senses (UX/DX)
- **Visual:** "Full Screen" lines. No cutoff.
- **Interaction:** Smooth, responsive zooming when changing bar count.
- **Detail:** Wicks and candles must be visible (not just close prices).

## 7. Evolution (Real-Time Log)
*Claude: Log completed milestones here as you work.*
- [x] Analyzed image comparison — flask_apex clean, init2.py has sparse 15m data
- [x] Updated init2.py `/api/chart-data` default limit to 300
- [x] Updated init2.py `/api/basic` default limit to 300
- [x] Updated init2.py `/api/advanced` default limit to 300
- [x] Updated init2.py `/api/fibonacci` default limit to 300
- [x] Updated init2.py `/api/ath` default limit to 300
- [x] Updated apex_views.js to pass dynamic `limit` from ApexIndicators.getBarCount()
- [x] **BUG FIX:** `/api/chart-data` was missing `symbol` filter in SQL query — added `AND symbol = ?`
- [ ] Test: Verify charts render with full-width indicators
- [ ] Test: Verify bar count slider updates chart correctly

## 8. Infinity (Patterns)
- **Pattern:** **Synchronized Data Depths.** (If Chart=300, Indicators must=300).

## Architecture Flow

```mermaid
graph TD
    UI[Zoom Control / Bar Slider] -->|getBarCount| Ind[ApexIndicators]
    Ind -->|limit=N| Fetch[loadChartData]
    Fetch -->|limit=N| API[init2.py]
    API -->|Fetch N| DB[(SQLite)]
    DB -->|N Bars| R1[/api/chart-data]
    DB -->|N Bars| R2[/api/basic]
    DB -->|N Bars| R3[/api/advanced]
    R1 & R2 & R3 -->|Unified Depth| JS[Frontend Renderer]
    JS -->|Draw| Canvas[Full Width Chart]
```
