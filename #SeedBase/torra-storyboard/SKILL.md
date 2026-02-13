---
name: torra-storyboard
description: The evolving vision book for the Apex trading platform. A living storyboard that documents what every part of the system IS and WILL BECOME, organized as chapters using the 1-2-4-8-5-7 structure. Use when exploring new features, resolving architectural questions, onboarding into the project, or when anyone asks "what does this system do" or "where does X go". This is the single source of truth for project vision. When new information conflicts with a previous chapter, the previous chapter gets updated — consistency across the whole book is mandatory.
---

# The Apex Storyboard
### An Engineering Reference That Evolves With the System

---

## Chapter 0 — How This Book Works

This is the table of contents, the rules, and the structure. Every chapter that follows describes a real piece of the system — what it does, how it's built, what files are involved, and where it's headed. No metaphors. Just puzzle pieces and where they fit.

---

## The Six Sections (1-2-4-8-5-7)

Every chapter uses the same six sections. They exist because each one answers a different engineering question:

| # | Section | Question It Answers |
|---|---------|-------------------|
| **1** | **What It Does** | Plain description. What is this thing? What's its job in the system? |
| **2** | **Why It Exists** | What problem does it solve? What breaks if you remove it? |
| **4** | **How It's Built** | Files, routes, tables, data flows. The actual wiring. |
| **8** | **How It Thinks** | The core algorithm or logic pattern. How decisions get made. |
| **5** | **How It Feels** | The user-facing behavior. Speed, interaction flow, what you see on screen. |
| **7** | **Where It's Going** | Next steps, known gaps, future plans. What's not built yet and why. |

---

## Rules

1. **Chapters name themselves.** They emerge from the engineering, not from a pre-planned outline. When a concept comes up, it gets a chapter.

2. **One concept, one chapter.** If an explanation covers multiple distinct pieces, they get split into separate chapters. Each chapter owns one clear thing.

3. **Consistency is mandatory.** If new information conflicts with something in a previous chapter, the previous chapter gets edited to match. This book is a living record, not a changelog. Every chapter must agree with every other chapter at all times.

4. **Engineering language.** This puzzle piece fits here because of X. That route serves this data to that component. No metaphors unless they genuinely clarify a technical relationship.

5. **Section 4 is the anchor.** Every chapter must have a concrete Section 4 (How It's Built) that maps to real files and real code. If you can't write Section 4, the chapter isn't ready.

6. **Sections can be short.** A two-line Section 7 is fine. An empty Section 5 for a backend-only component is fine. Write what's real.

7. **Cross-references link chapters.** When one piece depends on another: `(→ Ch.3)`. When a chapter doesn't exist yet for something referenced: `(→ needs chapter)`.

8. **This is the tiebreaker.** When there's a question about where something belongs or how two pieces connect, this book is the authority. If the book doesn't have the answer, we write it in.

---

## Chapter Index

*Chapters are added as concepts are explained. They are not pre-planned.*

| Ch | Title | One-Line Summary | Status |
|----|-------|-----------------|--------|
| 0 | How This Book Works | The structure, rules, and index. | ✅ Active |
| 1 | The Intelligence Database | Raw market data imported from MT5 and TradingView. | ✅ Active |
| 2 | The Instance Database | Per-algorithm storage for sentiment, positions, and Markov state. | ✅ Active |
| 3 | The Profile & Config System | Identity, tuning, and the JSON config that controls how the algo trades. | ✅ Active |

---

## How to Use This

**Starting a new feature:** Find the chapter that owns the area. Read Section 4 to see what's there. Read Section 7 to see what's planned. Build. Update the chapter.

**Resolving a question:** Find the relevant chapter. If two chapters disagree, one of them is stale — fix it.

**New session:** Read Chapter 0 and the index. Dive into specific chapters as needed.

**New concept explained:** Create a new chapter. Link it to existing chapters where the pieces connect. Check for conflicts and resolve them immediately.

---
---

## Chapter 1 — The Intelligence Database

*Raw market data imported from MT5 and TradingView — the system's data foundation.*

### 1. What It Does

The Intelligence Database is the bottom-right quadrant of the Database page. It stores raw market data — OHLCV candles, TradingView indicator calculations, and bulk Pine Script exports. This is the system's ground truth for what happened in the market. Nothing here is opinion or signal — it's just data, imported from external sources.

It receives data two ways: real-time webhooks from TradingView alerts (15m and 1m intervals), and bulk imports of historical Pine Logs data via a Tampermonkey script. Both write to the same SQLite database.

### 2. Why It Exists

Without this, the system has no market context. The trader (→ needs chapter) makes decisions by reading live charts via screenshot, but the Intelligence Database provides the historical context that future features need — backtesting, pattern validation, and simulation replay. If you remove it, you lose the ability to answer "what did the market look like when this signal was generated?"

It also serves as the data backbone for the TradingView indicator pipeline. The Pine Script indicators calculate dozens of technical metrics per bar (SuperTrend, EMA alignment, RSI divergences, Fibonacci zones, ATR volatility, spike detection, etc.), and this database is where those calculations land.

### 3. How It's Built

**Database:** `v6_intelligence.db` (SQLite)

**Server:** `unified_webhook_server.py` — standalone Flask app on port 5001

**Tables:**

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `bulk_analysis_15m` | 15-minute full analysis bars | timestamp (unique), symbol, OHLCV, 60+ indicator columns |
| `recalibration_1m` | 1-minute recalibration snapshots | timestamp (unique), symbol, EMA/RSI/ATR subset |

**Routes:**

| Route | Method | Purpose |
|-------|--------|---------|
| `/webhook/15m` | POST | Receive 15m TradingView alerts |
| `/webhook/1m` | POST | Receive 1m recalibration alerts |
| `/api/bulk-import` | POST | Bulk import Pine Logs (array of records) |
| `/api/15m/latest` | GET | Query latest 15m records (param: `limit`) |
| `/api/15m/count` | GET | Total record count |
| `/api/health` | GET | Health check |

**Data flow:**
```
TradingView Alert → POST /webhook/15m → bulk_analysis_15m table
Tampermonkey Script → POST /api/bulk-import → bulk_analysis_15m table
```

**Note:** This server runs independently from the main Apex server (init2.py on port 5000). They are separate Flask processes. The Intelligence Database does not depend on any other Apex component.

### 8. How It Thinks

No logic here — this is pure storage. Data comes in, gets INSERT OR REPLACE'd by timestamp (deduplication), and sits there for querying. The `bulk_analysis_15m` table has ~70 columns covering every indicator the Pine Script calculates. The schema mirrors the TradingView output exactly so no transformation is needed on ingest.

The timestamp column is the primary key for dedup. If the same bar arrives twice (e.g., webhook + bulk import), the second write replaces the first.

### 5. How It Feels

Bottom-right quadrant of the Database page. Shows record counts, latest timestamps, and import status. The bulk import from Pine Logs can process hundreds of records in a single POST. Webhook writes are real-time as TradingView fires alerts.

### 7. Where It's Going

- Currently only stores MGC (Micro Gold) data. Needs to support all six symbols in `config.py` SYMBOL_DATABASES (XAUJ26, USOILH26, US500H26, US100H26, US30H26, BTCF26).
- The 1m recalibration table exists but isn't actively used since the Great Migration to 15m/1h timeframes.
- Future: This data feeds into backtesting and simulation replay (→ needs chapter). The trader currently works from screenshots, but eventually it could also consume this structured data for hybrid analysis.

---
---

## Chapter 2 — The Instance Database

*Per-algorithm storage for sentiment scores, positions, Markov state, and trade history.*

### 1. What It Does

The Instance Database is the bottom-left quadrant of the Database page. While the Intelligence Database (→ Ch.1) stores raw market data, this stores everything about what the *algorithm* is doing — its sentiment readings, its positions, its state transitions, and its Markov probability matrices.

Each algorithm instance gets its own set of tables, dynamically created when the instance is created. So if you create an instance for XAUJ26, you get `sentiment_xauj26_sim_abc123`, `positions_xauj26_sim_abc123`, `state_transitions_xauj26_sim_abc123`, and `markov_matrices_xauj26_sim_abc123`. This means every instance's data is fully isolated — you can run GOLD and BTC simultaneously and their data never crosses.

### 2. Why It Exists

The trader (→ needs chapter) generates sentiment scores every 15 minutes and hourly. Those scores need to persist somewhere so the system can track how sentiment evolved over time, detect state transitions (bullish → bearish), and build Markov probability matrices that predict what state comes next.

Positions need to be tracked per-instance so the system knows what's open, what the P&L is, and how to manage exits. Without this, the system would be stateless — every 15-minute tick would have no memory of what came before.

If you remove this, the algo has no memory, no position tracking, and no state machine.

### 4. How It's Built

**Database:** `apex_instances.db` (SQLite, WAL mode)

**Manager:** `instance_database.py` — singleton `InstanceDatabaseManager` accessed via `get_instance_db()`

**Core tables (global):**

| Table | Purpose |
|-------|---------|
| `algorithm_instances` | Registry of all instances (id, symbol, account_type, profile_id, status) |
| `profiles` | Trading profile configs (→ Ch.3) |

**Per-instance tables (created dynamically on instance creation):**

| Table Pattern | Purpose | Key Fields |
|--------------|---------|------------|
| `sentiment_{id}` | Sentiment readings from Claude API | 5 vector scores (-1.0 to +1.0), composite, timeframe, source_model |
| `positions_{id}` | Position tracking | direction, entry/exit price, lots, SL/TP, P&L, pyramid level, MT5 sync fields |
| `state_transitions_{id}` | Markov state changes | from_state, to_state (-2 to +2), trigger source, scores at transition |
| `markov_matrices_{id}` | 5×5 probability matrices | matrix_data (JSON), transition_counts, stability_score, trend_bias |

**The five Markov states:**

| State | Label |
|-------|-------|
| -2 | Strong Bearish |
| -1 | Bearish |
| 0 | Neutral |
| +1 | Bullish |
| +2 | Strong Bullish |

**Key methods on `InstanceDatabaseManager`:**

| Method | What It Does |
|--------|-------------|
| `create_instance(symbol, account_type)` | Creates instance record + all 4 per-instance tables |
| `get_instance(instance_id)` | Returns `AlgorithmInstance` dataclass |
| `save_sentiment(instance_id, data)` | Inserts sentiment row, auto-calculates matrix_bias |
| `list_instances()` | Returns all non-archived instances |
| `_get_conn()` | Returns SQLite connection (WAL mode) |

**Data flow (per 15m tick):**
```
torra_trader.py → score_chart() → 5 vector scores
    → save_sentiment() → sentiment_{id} table
    → auto-triggers state transition check
    → if state changed → state_transitions_{id} + update markov_matrices_{id}
```

### 8. How It Thinks

The Markov state machine is the core logic pattern. Every sentiment reading gets mapped to one of 5 discrete states (-2 to +2) based on the composite score. The system tracks every transition between states and builds a 5×5 probability matrix: "when we're in state X, what's the probability we move to state Y?"

This means the system doesn't just know "sentiment is bullish right now" — it knows "when sentiment was bullish in the past, it stayed bullish 60% of the time and moved to neutral 25% of the time." That's predictive information.

The matrix updates incrementally — each new transition adds to the count matrix, and probabilities are recalculated. The `stability_score` measures diagonal dominance (how often states persist), and `trend_bias` measures the overall directional tendency.

### 5. How It Feels

Bottom-left quadrant of the Database page. You can browse instances, select one, and see its sentiment history, position log, and current Markov state. The Instance Browser on the Algo page (→ needs chapter) also reads from this database to display which instances exist and their status.

### 7. Where It's Going

- Position tracking currently has MT5 sync fields (mt5_ticket, sync_status) from Seed 10D, but live MT5 synchronization was deprioritized in favor of simulation-first approach (Seed 14B). These fields are ready for when live sync comes back.
- Pyramid position support is in the schema (pyramid_level, parent_position_id, trade_group_id) but not fully wired into the trader logic yet.
- The Markov matrix is built but not yet used for *predictive* trading decisions — it's currently observational. Future: the matrix probabilities could feed back into the decision engine as an additional input.

---
---

## Chapter 3 — The Profile & Config System

*The identity and tuning layer — who trades, with what personality, and how aggressively.*

### 1. What It Does

The Profile & Config system is the top half of the Database page. It's where you create, configure, test, and assign trading profiles. A profile defines *how* an algorithm instance trades — its sentiment weights, its decision thresholds, its risk parameters, and its API connection.

The left side is the Profile Manager where you set up the profile identity (name, API provider, API key, model selection) and test the API connection. The right side is the Stats & Config panel where the JSON trading configuration lives. This JSON config is the control surface for the entire trading algorithm — every number in it directly controls a decision the Python trader makes.

A profile gets assigned to an algorithm instance (→ Ch.2). One profile can be assigned to multiple instances, but each instance has exactly one active profile.

### 2. Why It Exists

Without profiles, every instance would trade the same way with the same settings. The whole point of running multiple instances across different symbols is that GOLD might need different sensitivity than BTC. Profiles solve this — you can create "Aggressive Gold" with a low threshold and high lots, and "Conservative BTC" with a wide dead zone and tight risk.

More importantly, the config system exists to enable optimization through experimentation. You create variations of a config, run them in parallel simulations (→ needs chapter), compare results, and evolve toward what performs best. The config is the DNA of the trading strategy — everything else is infrastructure.

If you remove profiles, you're back to hardcoded trading parameters with no way to test alternatives.

### 4. How It's Built

**Frontend storage:** Profiles are created and managed in the frontend Profile Manager (`static/js/profile_manager.js`). The API key, provider, and model are stored in `localStorage` — the API key never touches the backend database.

**Backend storage:** The `profiles` table in `apex_instances.db` (→ Ch.2) stores the trading configuration:

| Column | Type | What It Controls |
|--------|------|-----------------|
| `sentiment_weights` | JSON text | Weight per sentiment vector (→ see config breakdown below) |
| `sentiment_model` | text | Which AI model scores the charts (e.g., `claude-sonnet-4-20250514`) |
| `sentiment_threshold` | real | The composite score that triggers a BUY or SELL |
| `position_sizing` | JSON text | `base_lots`, `max_lots` |
| `risk_config` | JSON text | `max_drawdown_pct`, `daily_loss_limit` |
| `entry_rules` | JSON text | Timeframe weights, gut veto threshold, dead zone bounds |
| `exit_rules` | JSON text | SL/TP points, signal limits, cooldown, sentiment exit toggle |
| `pyramid_enabled` | int | Whether pyramid entries are active |
| `pyramid_max_levels` | int | Max pyramid depth |
| `pyramid_config` | JSON text | `add_threshold`, `lot_scaling` array |

**The JSON Config (current version):**

This is the config that gets stored across those columns and controls `torra_trader.py` (→ needs chapter):

```json
{
  "sentiment_weights": {
    "price_action": 0.30,
    "key_levels":   0.15,
    "momentum":     0.25,
    "volume":       0.10,
    "structure":    0.20
  },
  "timeframe_weights": {
    "15m": 0.40,
    "1h":  0.60
  },
  "thresholds": {
    "buy":       0.55,
    "sell":     -0.55,
    "dead_zone": 0.25,
    "gut_veto":  0.30
  },
  "risk": {
    "base_lots":             1.0,
    "max_lots":              1.0,
    "stop_loss_points":      80,
    "take_profit_points":    200,
    "max_signals_per_hour":  3,
    "cooldown_seconds":      300,
    "consecutive_loss_halt": 2,
    "sentiment_exit":        true
  }
}
```

**What each field does:**

**`sentiment_weights`** — Controls how much each of the 5 sentiment vectors contributes to the final composite score. All weights must sum to 1.0. The trader calls Claude's vision API with a chart screenshot, and Claude returns a score from -1.0 to +1.0 for each of these five categories:

| Vector | Weight | What Claude Scores |
|--------|--------|--------------------|
| `price_action` | 0.30 | What is price doing right now? Candle patterns, direction, engulfings. |
| `key_levels` | 0.15 | Where is price relative to support/resistance, EMAs, Bollinger bands? |
| `momentum` | 0.25 | Is the move accelerating or fading? RSI, MACD slope, divergences. |
| `volume` | 0.10 | Does volume confirm or deny the move? Climax bars, dry-ups. |
| `structure` | 0.20 | Higher highs/lows? Trend intact? Chart pattern forming? |

The weighted composite = `Σ(score × weight)` across all five vectors. In the current config, price action and momentum carry the most influence (0.30 + 0.25 = 55% of the decision), while volume is intentionally lowest (0.10) because futures volume data from MT5 is less reliable than equities.

**`timeframe_weights`** — Controls how the 15-minute and 1-hour analyses blend together.

| Timeframe | Weight | Schedule | Behavior |
|-----------|--------|----------|----------|
| `15m` | 0.40 | Runs at X:01, X:16, X:31, X:46 | Fresh reading every 15 minutes |
| `1h` | 0.60 | Runs at X:02 (hourly only) | **Persists until the next hourly reading** |

The 1-hour score has 60% weight because it represents the higher timeframe trend. It only updates once per hour (at X:02, one minute after the hourly candle closes), but it stays active and continues to influence every 15-minute decision until the next hourly reading replaces it. So between X:02 and X+1:02, the same 1h score is blended with four different 15m scores.

The final blended score = `(15m_composite × 0.40) + (1h_composite × 0.60)`.

**`thresholds`** — The decision boundaries that turn a numeric score into an action.

| Threshold | Value | What It Does |
|-----------|-------|-------------|
| `buy` | 0.55 | If blended score ≥ 0.55, signal is BUY |
| `sell` | -0.55 | If blended score ≤ -0.55, signal is SELL |
| `dead_zone` | 0.25 | If abs(blended score) < 0.25, always HOLD regardless of threshold. Prevents trading on weak signals. |
| `gut_veto` | 0.30 | If the weighted math says BUY but Claude's "gut" composite_bias is negative by more than 0.30 (or vice versa), the signal is vetoed to HOLD. This lets Claude's holistic read override the math when they disagree strongly. |

The dead zone creates a buffer: scores between -0.25 and +0.25 never trade. Between 0.25 and 0.55 (or -0.25 and -0.55), the system is "leaning" but not confident enough to act.

**`risk`** — Position sizing and safety limits.

| Field | Value | What It Does |
|-------|-------|-------------|
| `base_lots` | 1.0 | Default lot size per trade |
| `max_lots` | 1.0 | Maximum lot size (caps partial approval from margin gate) |
| `stop_loss_points` | 80 | SL distance in points from entry. **Note:** currently not sent to MT5 because the trader doesn't have live price — the EA's own protection handles risk (→ Ch.1 of future Guardian chapter). |
| `take_profit_points` | 200 | TP distance in points from entry. Same note as SL. |
| `max_signals_per_hour` | 3 | Rate limit — no more than 3 trade signals per hour |
| `cooldown_seconds` | 300 | Minimum 5 minutes between signals |
| `consecutive_loss_halt` | 2 | After 2 consecutive losing trades, stop sending signals until a winner |
| `sentiment_exit` | true | If sentiment flips (e.g., was bullish, now bearish), close the position even without hitting SL/TP |

**Files involved:**

| File | Role |
|------|------|
| `static/js/profile_manager.js` | Frontend: create/edit/test profiles, store API key in localStorage |
| `static/js/torra_trader_bridge.js` | Frontend: grabs profile config + API key on activate, POSTs to backend |
| `trader_routes.py` | Backend: receives config, upserts to DB profiles table, spawns trader |
| `torra_trader.py` | Backend: loads profile from DB, uses weights/thresholds/risk for all decisions |
| `instance_database.py` | Backend: profiles table schema, CRUD operations |
| `profiles/trading_config_default.json` | Default config template applied to new profiles |

**Bridge flow (frontend → backend):**
```
Profile Manager (localStorage) → has API key, provider, model
    ↓ double-tap activate on algo page
torra_trader_bridge.js → reads active profile → POSTs to /api/trader/toggle
    ↓
trader_routes.py → saves trading_config to DB profiles table
                 → spawns torra_trader.py with API key as TORRA_API_KEY env var
    ↓
torra_trader.py → loads profile from DB → uses config for all decisions
```

The API key flows from localStorage → POST body → environment variable on the subprocess. It never touches the database.

### 8. How It Thinks

The profile is a set of coefficients that control a linear scoring model. The 5 sentiment weights are literally the multipliers in a weighted average. The timeframe weights are the blend ratio. The thresholds are the decision boundaries. Change any number and you change how the algorithm behaves.

This makes the config the most important tuning surface in the entire system. Two profiles with different weights will make different decisions on the same chart at the same time. That's the point — it enables A/B testing of trading strategies.

### 5. How It Feels

Top half of the Database page. Left panel: profile creation form with name, API provider dropdown, API key input, model selector, and a "Test Connection" button that verifies the API key works. Right panel: stats (total trades, P&L, win rate, profit factor, Sharpe ratio) and the JSON config editor where you can directly edit the config object.

Profile assignment happens on the Algo page (→ needs chapter) — you select a profile from a dropdown and it links to the active instance.

### 7. Where It's Going

The JSON config is designed to grow. Known future additions:

- **Config families:** Create variations of a config (e.g., threshold 0.55 vs 0.45 vs 0.65), assign each to a separate simulation instance, run them side-by-side, and compare which performs best. This is the primary optimization loop — not manual tuning, but systematic testing.
- **Per-profile analytics rollup:** Each profile already has stats columns (total_trades, win_rate, profit_factor, sharpe_ratio) but these aren't populated yet. When simulation runs complete, these should auto-update.
- **Config inheritance:** A "family" of configs could share a base and override specific fields, so you can test one variable at a time without duplicating the entire config.
- **Pyramid config activation:** The pyramid fields exist in the DB schema but aren't wired into the trader yet. When activated, the config would control add_threshold (score required to pyramid in), lot_scaling (how much each level adds), and max pyramid depth.
- **Scoring rubric customization:** Currently `scoring_rubric.py` uses a fixed prompt for all profiles. Future: the profile could include custom rubric overrides — for example, a "momentum-focused" profile could have a rubric that tells Claude to weight momentum indicators more heavily in its analysis.
- **Sentiment exit logic:** The `sentiment_exit: true` flag is in the config but the actual exit logic (close position when sentiment flips) isn't fully implemented in the trader yet.

The long-term vision: the config is the thing you optimize. Everything else — the API calls, the screenshot pipeline, the signal writing, the EA execution — is plumbing. The config is where alpha lives.
