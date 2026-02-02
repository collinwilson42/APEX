# Data Collection – Seed Log

---

9: 2026-02-01 – Fix OHLC Bar Alignment in MT5 Collector ^seed-data-ohlc-alignment

## Prompts & Execution
"I think i see the issue. I dont think the data is collecting at the open and close correctly it might be aligning open with half way through the bar."

## 1. Seed (Intent)
- **Objective:** Fix OHLC bar timing alignment in the MT5 data collector.
- **Hypothesis:** The collector is capturing bar data mid-bar rather than at bar close, causing:
  - `open` to reflect mid-bar price instead of true bar open
  - `close` to be offset from actual bar close
  - Wicks (high/low) that don't visually align with open/close
- **Symptom:** 15m chart shows scattered/broken candlesticks; 1m chart appears fine (offset too small to notice).

## 2. Related (Context)
- [[Visuals – Seed Log#^seed-visuals-fidelity]] (Chart fidelity issue that led to this discovery)
- `mt5_collector_v11_3.py` (The collector that writes to the database)
- `init2.py` backfill functions (`full_backfill_timeframe`, `fill_gaps_only`)

## 4. Foundation (Structure)
*Files to investigate:*
- `mt5_collector_v11_3.py`:
  - Check: How is bar completion detected?
  - Check: Is there a "wait for bar close" logic?
  - Check: `copy_rates_from_pos()` — is it fetching the current (incomplete) bar?
- `init2.py`:
  - Check: Backfill logic — does it include the current incomplete bar?
  - Check: Timestamp handling — are we using bar open time or close time?

*Potential fixes:*
- Skip the most recent bar (index 0) if it's incomplete
- Wait for bar close before writing to database
- Verify MT5 timestamp represents bar OPEN time (standard) and adjust if needed

## 5. Senses (UX/DX)
- **Visual:** Candlesticks should have proper wicks extending from body
- **Data Integrity:** OHLC values should be internally consistent (high ≥ max(open, close), low ≤ min(open, close))
- **Timing:** 15m bar at 14:00 should contain data from 14:00:00 to 14:14:59

## 7. Evolution (Real-Time Log)
*Claude: Log completed milestones here as you work.*
- [x] Identified probable cause: OHLC misalignment from mid-bar capture
- [ ] Review `mt5_collector_v11_3.py` collection logic
- [ ] Review `init2.py` backfill logic
- [ ] Identify exact offset/alignment issue
- [ ] Implement fix (skip incomplete bar or wait for close)
- [ ] Test: 15m chart should match flask_apex visual quality

## 8. Infinity (Patterns)
- **Pattern:** **Bar Completion Gate.** Never write a bar until it's closed.
- **Pattern:** **Timestamp = Bar Open.** MT5 convention: timestamp is the bar's opening time.

## Architecture Flow
```mermaid
graph TD
    subgraph Current_Problem
        MT5[MT5 Feed] -->|copy_rates| Col[Collector]
        Col -->|Includes incomplete bar?| DB[(Database)]
        DB -->|Misaligned OHLC| Chart[Broken Chart]
    end
    
    subgraph Fix
        MT5_2[MT5 Feed] -->|copy_rates| Col2[Collector]
        Col2 -->|Skip bar[0] if incomplete| Gate{Bar Complete?}
        Gate -->|Yes| DB2[(Database)]
        Gate -->|No| Wait[Wait for next tick]
        DB2 -->|Aligned OHLC| Chart2[Clean Chart]
    end
```
