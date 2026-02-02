# Logic – Seed Log (Part C)

---

10C: 2026-02-01 – The Instruments: Poly-Metric Engine, Markov Wiring & Live Data Connection ^seed-logic-instruments-live

## Prompts & Execution
"Update the seed to also include that this should initiate real results instead of the current mock results... get this system LIVE with the new config system."

## 1. Seed (Intent)
- **Objective:** Upgrade the core logic to calculate **6 Distinct Sentiment Vectors**, wire the **Markov Matrix**, and **PERMANENTLY REMOVE MOCK DATA** to go Live.
- **Specifics:**
    - **De-Mocking:** Identify and delete any `random.uniform()` or static return values in `sentiment_engine.py` and `init2.py`.
    - **Real Data Pipe:** Ensure `init2.py` imports and calls `mt5_collector_v11_3.get_latest_data()` (or the most robust collector available in the repo).
    - **Poly-Metric Refactor:** Break `sentiment_engine.py` into 6 real calculation functions using that live data.
    - **Live Execution:** Ensure `trade.py` is actually attempting to place orders via `MetaTrader5` library.

## 2. Related (Context)
- [[Logic – Seed Log]] (Part A: The Conductor).
- `profiles/maestro_v2.json` (The Sheet Music - Mode: "Live").
- `init2.py` (The Engine).
- `mt5_collector_v11_3.py` (The Source of Truth).

## 4. Foundation (Structure)
*Files to be modified:*
- `sentiment_engine.py`:
    - **CRITICAL:** Replace mock calculations with real logic:
        - `_analyze_price_action(data)` -> Uses real Candle patterns (Pinbar/Engulfing).
        - `_analyze_volume_flow(data)` -> Uses real Tick Volume deltas.
        - `_analyze_structure(data)` -> Uses real High/Low pivots.
- `init2.py`:
    - **Verify Import:** `from mt5_collector_v11_3 import AdvancedCollector` (or equivalent).
    - **Data Flow:** `real_data = collector.fetch_data()` -> `sentiment = engine.analyze(real_data)`.
- `profiles/maestro_v2.json`:
    - Ensure `"execution": { "mode": "live" }`.

## 8. Infinity (Patterns/Debt)
- **Anti-Pattern:** **"The Placebo Button."** (Mock Data). We must ensure that when the logs say "Volume High," it is because the MT5 Tick Volume is actually high.
- **Pattern:** **Fail-Fast.** If MT5 is not connected or data is stale (> 5 minutes old), the Engine must throw an error, not guess.

## 5. Senses (UX/DX)
- **Reality Check:** The logs should show real prices (e.g., "Gold @ 2034.50"), not generic placeholders.
- **Latency:** Real data takes time. Expect 100-200ms delay per cycle.

## 7. Evolution (Real-Time Log)
*Claude: Log milestones here.*
- [ ] [PURGED all mock data generators]
- [ ] [Connected `init2.py` to `mt5_collector_v11_3`]
- [ ] [Refactored `sentiment_engine.py` to use Real OHLCV]
- [ ] [Verified Trade Execution pathway is Live]

## Architecture Flow (The Live Pipeline)
```mermaid
graph LR
    subgraph Real_World
        MT5[MetaTrader 5 Terminal] -->|Live Ticks| Collector[mt5_collector_v11_3]
    end

    subgraph The_Instruments
        Collector -->|DataFrame| PA[Price Action Algo]
        Collector -->|DataFrame| Vol[Volume Flow Algo]
        Collector -->|DataFrame| Str[Structure Algo]
    end

    subgraph The_Mixer
        PA -->|Score| Sum((Weighted Sum))
        Vol -->|Score| Sum
        Str -->|Score| Sum
    end

    Sum -->|Signal| Trade[trade.py]
    Trade -->|Order Send| MT5

    # Logic – Seed Log (Part B)

---

10C: 2026-02-01 – The Instruments: Live Data Wiring, Schema Expansion & Execution ^seed-logic-live

## Prompts & Execution
"The py program should be feeding live data into these score values... database should be updating with the sentiments, and we need to add columns for the 6 scores... intuitively cover gaps to go live... leave Markov out for now."

## 1. Seed (Intent)
- **Objective:** Finalize the "Poly-Metric Engine" for **LIVE TRADING**.
- **Specifics:**
    - **Schema Expansion:** Update `sentiment_engine.py` (and SQLite) to store **Numeric Scores** (float) for all 6 vectors, not just text.
    - **Live Data Pipe:** Ensure `init2.py` passes real-time MT5 data (OHLCV) into the scoring logic.
    - **Weighted Math:** Implement the weighted sum calculation: `Final_Score = (PriceAction * 0.25) + (Volume * 0.15)...` using the live scores.
    - **Real Execution:** Connect the `Final_Score` directly to `trade.py` to trigger real BUY/SELL orders.
    - **Scope:** **EXCLUDE Markov Matrix** for this iteration. Focus purely on the 6 Sentiment Vectors.

## 2. Related (Context)
- `profiles/maestro_v2.json` (Config).
- `sentiment_engine.py` (The Scorer).
- `mt5_collector_v11_3.py` (The Source).

## 4. Foundation (Structure)
*Files to be modified:*
- `sentiment_engine.py`:
    - **Schema Update:** Add columns: `price_action_score`, `key_levels_score`, `momentum_score`, `volume_score`, `structure_score`, `overall_bias_score`.
    - **Logic:** Update `analyze()` to extract these scores from the logic/response and return them in the `SentimentReading` object.
    - **Math:** Implement `calculate_composite_score(scores, weights)`.
- `init2.py`:
    - **Live Loop:** Call `collector.get_data()`, pass to `engine.analyze()`.
    - **Trade Trigger:** `if composite_score > thresholds['buy']: trade.execute_buy()`.
- `profiles/maestro_v2.json`:
    - **Strip:** Remove `markov_matrix` block.
    - **Verify:** Ensure `execution.mode` is "live".

## 8. Infinity (Patterns)
- **Pattern:** **Data Integrity.** We cannot trade on "text". We must trade on *numbers* stored in the DB.
- **Anti-Pattern:** **Phantom Trading.** The system must log the *exact* score that triggered the trade (e.g., "Bought at 0.72 score").

## 5. Senses (UX/DX)
- **Feedback:** The console should print: `[LIVE] XAUUSD | Score: 0.72 (✅ Buy) | Vol: 0.8 | PA: 0.6`.

## Architecture Flow (The Live Circuit)
```mermaid
graph LR
    MT5[MetaTrader 5] -->|Real Ticks| Collector
    Collector -->|Live Data| Engine[Sentiment Engine]
    
    subgraph The_Calculation
        Engine -->|Calc| S1[Score: PriceAction]
        Engine -->|Calc| S2[Score: Volume]
        Engine -->|Calc| S3[Score: Structure]
        S1 & S2 & S3 -->|x Weights| Final[Composite Score]
    end
    
    Final -->|Store| DB[(SQLite: +Score Cols)]
    Final -->|Signal > Threshold| Trade[trade.py]
    Trade -->|Send Order| MT5


    # Logic – Seed Log (Part B)

---

10C: 2026-02-01 – The Instruments: Live Data, Score Persistence & Real-Time Mirroring ^seed-logic-live

## Prompts & Execution
"Store the calculated avg, 15m and 1m in the database... mirror the most recent value into the front end ui automatically... go live with real data."

## 1. Seed (Intent)
- **Objective:** Finalize the "Poly-Metric Engine" for **LIVE TRADING** with full data persistence and UI feedback.
- **Specifics:**
    - **Schema Expansion (Vectors):** Update `sentiment_readings` to store numeric scores (float) for all 6 vectors (PA, Vol, etc.).
    - **Schema Expansion (Decisions):** Create a NEW `decision_logs` table to store the **Aggregated State** per cycle: `score_1m`, `score_15m`, and `final_weighted_score`.
    - **Live Data Pipe:** Ensure `init2.py` passes real MT5 data into the scoring logic.
    - **UI Mirroring:** Create an API endpoint (`/api/system_pulse`) that feeds the latest `decision_log` values to the frontend.
    - **Execution:** Wire the `final_weighted_score` to `trade.py`.

## 2. Related (Context)
- `profiles/maestro_v2.json` (Config - Live Mode).
- `sentiment_engine.py` (Scorer).
- `init2.py` (Engine).
- `dashboard.js` (UI).

## 4. Foundation (Structure)
*Files to be modified:*
- **DB Schema (`database_v3_schema.py` or similar):**
    - Add `decision_logs` table: `(id, timestamp, symbol, score_1m, score_15m, final_score, action_taken)`.
- **`sentiment_engine.py`:**
    - Add numeric columns to `sentiment_readings` table.
    - Logic to extract and return floats.
- **`init2.py`:**
    - **The Math:** `Final = (Latest_1m * W_1m) + (Latest_15m * W_15m)`.
    - **The Log:** Insert this result into `decision_logs`.
    - **The Trigger:** Call `trade.py` if `Final > Threshold`.
- **`app.py` / `flask_apex.py`:**
    - Add route `/api/system_pulse`: Returns the latest row from `decision_logs`.
- **`static/js/dashboard.js`:**
    - Add polling (every 5s) to fetch `/api/system_pulse` and update the UI Score widgets.

## 8. Infinity (Patterns)
- **Pattern:** **The Black Box Recorder.** Every trade decision must be traceable. We must know that we bought because "1m was 0.8 and 15m was 0.6", not just "The Algo said so."

## Architecture Flow (The Mirror)
```mermaid
graph TD
    subgraph Backend
        MT5[MT5 Live] --> Engine
        Engine -->|Calc| S1[1m Score: 0.8]
        Engine -->|Calc| S2[15m Score: 0.6]
        S1 & S2 -->|Avg| Final[Final: 0.7]
        Final -->|Insert| DB[(decision_logs)]
    end
    
    subgraph Frontend
        DB -->|API| JSON[/api/system_pulse]
        JSON -->|Poll| UI[Dashboard UI]
        UI -->|Display| Widget["1m: 0.8 | 15m: 0.6 | AVG: 0.7"]
    end