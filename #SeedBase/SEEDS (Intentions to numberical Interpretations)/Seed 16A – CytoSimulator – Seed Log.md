# Seed 16A – CytoSimulator: Profile-Driven Simulation Engine & Analysis Console

---

**16A**: [2026-02-11] – CytoSimulator: Profile-Driven Random-Walk Simulation with Full Vector Scoring ^seed-cyto-simulator

## Context & Lineage

**Seeds 10/10B/10C** designed the Maestro V2 profile system — a JSON configuration that defines vector weights, timeframe weights, thresholds, and risk parameters for a "Conductor" architecture. That profile was designed but **never created as an actual file**. The sentiment engine already outputs the 6 named scores (`price_action_score`, `key_levels_score`, `momentum_score`, `volume_score`, `structure_score`, `composite_score`) which CytoIntegration maps to v1→v6.

**This seed** builds the simulation engine that:
1. Creates the Maestro profile as an actual JSON file
2. Loads the profile to drive ALL simulation behavior
3. Generates 6 named sentiment scores (not anonymous vectors)
4. Uses profile weights for composite calculation
5. Uses profile thresholds for trade decisions
6. Records everything to CytoBase through the existing integration bridge

**The simulator IS the rehearsal for the real system.** Same profile, same math, same database — just random-walk inputs instead of API calls.

**Lineage:** 10 (Conductor) → 10B (Instruments) → 10C (Live Wiring) → 15A (CytoBase Schema) → 15BE (Neomorphic UI) → **16A (Simulation Engine)**

---

## 1. Seed (Intent)

Build a **CytoSimulator** — a profile-driven simulation engine that generates mean-reverting random-walk sentiment across the **6 named scoring categories**, calculates composite scores using **profile-defined weights and thresholds**, triggers trades based on **profile-defined entry/exit conditions**, records everything to `cyto_v3.db`, and exposes a **Simulation Control Panel + Analysis Console** within the CytoBase UI.

### The 6 Instruments (Sentiment Vectors)

Each bar generates a score (-1.0 to +1.0) for every instrument. These are NOT anonymous — they carry meaning:

| Vector | Key | What It Measures | Random Walk Character |
|--------|-----|------------------|-----------------------|
| v1 | `price_action_score` | Candlestick patterns, immediate moves | Fast, reactive (high volatility) |
| v2 | `key_levels_score` | Proximity to S/R, Fibonacci zones | Slow, sticky (mean-reverts strongly) |
| v3 | `momentum_score` | RSI/MACD analog — acceleration | Medium, trending (autocorrelated) |
| v4 | `volume_score` | Participation, buying/selling pressure | Spiky (occasional jumps) |
| v5 | `structure_score` | HH/HL/LH/LL geometry | Slowest, most persistent |
| v6 | `composite_score` | Overall bias across all factors | Derived (weighted sum of v1-v5) |

**Critical distinction:** `v6` (composite) is NOT independently generated. It IS the weighted sum of v1-v5 using profile weights. This mirrors how the real system works — the AI generates 5 independent assessments, and the composite is calculated from them.

### The Profile Drives Everything

```
Profile says vector_weights.price_action = 0.25
  → Simulator uses 0.25 when calculating composite

Profile says thresholds.entry_long = 0.65
  → Simulator opens a long when composite_score > 0.65

Profile says thresholds.entry_short = -0.65
  → Simulator opens a short when composite_score < -0.65

Profile says risk_management.lot_size = 1.0
  → Simulator records 1.0 lots per trade

Profile says exit_strategy.sentiment_exit.enabled = true
  → Simulator closes trade when composite flips sign
```

---

## 2. Related (Context)

### Source Systems (All Exist)
- `#Cyto/cyto_schema.py` — ✅ Database schema (288 slots, Fibonacci bands)
- `#Cyto/cyto_manager.py` — ✅ CytoManager (calc_radius, add_node, etc.)
- `#Cyto/cyto_integration.py` — ✅ CytoIntegration (record_bar, on_trade_close)
- `cyto_routes.py` — ✅ Flask API routes
- `templates/cytobase.html` — ✅ Neomorphic radial UI (Seed 15BE)
- `sentiment_engine.py` — ✅ Reference: 6 score fields, mock mode pattern

### Seeds Referenced
- **Seed 10** — The Conductor: Dynamic Profile Injection & Weighted Scoring
- **Seed 10B** — The Instruments: Poly-Metric Engine & Markov Wiring
- **Seed 10C** — Live Data, Score Persistence & Real-Time Mirroring
- **Seed 15A** — CytoBase Foundation (schema)
- **Seed 15BE** — Neomorphic Radial Timepiece (UI)

### Profile Schema Source
The Maestro V2 JSON from Seed 10 (reproduced and refined in Foundation section below)

---

## 4. Foundation (Structure)

### New Files

```
profiles/
  └── maestro_sim_v1.json      ← NEW — Simulation profile (based on Maestro V2)
                                   Defines weights, thresholds, risk, intervals

#Cyto/
  └── cyto_simulator.py        ← NEW — CytoSimulator class
                                   Profile-driven random-walk engine
                                   Threading tick loop
                                   Trade logic using profile thresholds
```

### Modified Files

```
cyto_routes.py                  ← MODIFY — Add simulator API endpoints
templates/cytobase.html         ← MODIFY — Add sim controls + analysis panel
```

### Existing Files (Read Only)

```
#Cyto/cyto_schema.py            ← READ — Constants, DB schema
#Cyto/cyto_manager.py           ← READ — CytoManager class
#Cyto/cyto_integration.py       ← READ — CytoIntegration bridge
sentiment_engine.py             ← READ — Reference for score field names
```

### The Profile: `profiles/maestro_sim_v1.json`

```json
{
  "meta": {
    "name": "Maestro Simulation V1",
    "version": "1.0",
    "description": "Simulation profile for CytoBase testing. Same structure as live Maestro — random walk inputs instead of API.",
    "author": "Apex Architect",
    "mode": "simulation"
  },

  "execution": {
    "default_speed": "fast",
    "speeds": {
      "realtime": 900,
      "fast": 5,
      "turbo": 1
    },
    "bars_per_epoch": 288,
    "slot_minutes": 15
  },

  "sentiment_engine": {
    "vector_weights": {
      "price_action":     0.25,
      "key_levels":       0.15,
      "momentum":         0.15,
      "volume_flow":      0.15,
      "market_structure":  0.10,
      "overall_bias":      0.20
    },
    "timeframe_weights": {
      "15m": 0.70,
      "1h":  0.30
    },
    "thresholds": {
      "entry_long":       0.55,
      "entry_short":     -0.55,
      "strong_confirm":   0.80,
      "exit_long_soft":   0.10,
      "exit_short_soft": -0.10,
      "sentiment_flip":   0.0
    }
  },

  "random_walk": {
    "mean_reversion_strength": 0.92,
    "vector_volatility": {
      "price_action":     0.18,
      "key_levels":       0.08,
      "momentum":         0.14,
      "volume_flow":      0.20,
      "market_structure":  0.06
    },
    "correlation_clusters": {
      "trend_group":  ["price_action", "momentum", "market_structure"],
      "flow_group":   ["volume_flow", "key_levels"]
    },
    "regime_drift": {
      "enabled": true,
      "drift_rate": 0.02,
      "regime_duration_bars": [20, 80]
    }
  },

  "trade_simulation": {
    "base_probability": 0.0,
    "threshold_driven": true,
    "pnl_distribution": {
      "mean": -5.0,
      "std": 80.0,
      "skew_factor": 1.3
    },
    "lot_size": 1.0,
    "max_open": 1,
    "hold_duration_bars": [2, 12]
  },

  "exit_strategy": {
    "sentiment_exit": {
      "enabled": true,
      "trigger": "sentiment_flip"
    },
    "hard_stops": {
      "stop_loss_usd": 150,
      "take_profit_usd": 400
    },
    "time_exit": {
      "enabled": true,
      "max_bars": 24
    }
  },

  "risk_management": {
    "max_daily_drawdown_usd": 500,
    "consecutive_loss_halt": 3,
    "max_open_positions": 1
  }
}
```

### Profile Design Notes

**`vector_weights` sums to 1.0** — These are the EXACT weights used in composite calculation:
```
composite = (PA × 0.25) + (KL × 0.15) + (Mom × 0.15) + (Vol × 0.15) + (Struct × 0.10) + (Bias × 0.20)
```

**`overall_bias` (v6) in simulation mode** is derived from v1-v5 weighted sum, NOT independently generated. In live mode the AI generates it independently, but for simulation we derive it so the math stays clean. The profile weight on `overall_bias` (0.20) means the composite factors it in as 20% of itself — creating a slight self-reinforcing effect that mimics the AI's tendency toward conviction.

**`threshold_driven: true`** means trades trigger when composite crosses a threshold, NOT at random probability. This is how the real system works — the profile's entry thresholds ARE the trade signal.

**`random_walk.vector_volatility`** gives each instrument its own character:
- `price_action: 0.18` — fast, reactive
- `key_levels: 0.08` — slow, sticky
- `volume_flow: 0.20` — spiky
- `market_structure: 0.06` — glacial

**`correlation_clusters`** — instruments within the same group share a portion of their random noise, creating realistic correlation (momentum and price_action tend to agree).

**`regime_drift`** — every 20-80 bars, the mean of the random walk shifts (bullish drift → bearish drift), creating natural trending/ranging regimes.

---

## 5. Senses (UX/DX)

### Simulation Control Panel (Q3 Quadrant)

```
┌─────────────────────────────────────────────────────┐
│  ● SIMULATION ENGINE                                 │
│                                                      │
│  Profile: Maestro Sim V1       Symbol: XAUUSD       │
│  Instance: XAUUSD_SIM_240211   Status: ● RUNNING    │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │  [▶ Play]  [⏸ Pause]  [⏹ Reset]               │ │
│  │                                                  │ │
│  │  Speed: ○ Real (15m)  ● Fast (5s)  ○ Turbo (1s)│ │
│  │                                                  │ │
│  │  Bar: 47/288  │  Epoch: 0  │  Trades: 8         │ │
│  │  ▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░  16.3%           │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  ── LIVE SCORES ────────────────────────────────    │
│  PA:  [▓▓▓▓▓▓░░░░]  +0.62                         │
│  KL:  [▓▓▓▓░░░░░░]  +0.38                         │
│  Mom: [▓▓▓▓▓▓▓░░░]  +0.71                         │
│  Vol: [▓▓▓░░░░░░░]  +0.24                         │
│  Str: [▓▓▓▓▓░░░░░]  +0.48                         │
│  ───────────────────────────────────────────        │
│  15m:  +0.512  │  1H: +0.387  │  Agree: 0.78      │
│  Final: +0.474 │  Signal: ── HOLD ──               │
│                                                      │
│  ── PROFILE WEIGHTS (from JSON) ────────────────   │
│  PA: 25%  KL: 15%  Mom: 15%  Vol: 15%  Str: 10%   │
│  Entry Long: >0.55  │  Entry Short: <-0.55         │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Analysis Panel (Q4 Quadrant, Tabbed)

```
┌─────────────────────────────────────────────────────┐
│  ● ANALYSIS   [P/L] [Vectors] [Distribution]        │
│                                                      │
│  ── P/L TAB ──────────────────────────────────────  │
│                                                      │
│  Cumulative P/L: +$487.30     Open P/L: +$32.00    │
│  ┌──────────────────────────────────────────┐       │
│  │  equity curve (canvas)                    │       │
│  └──────────────────────────────────────────┘       │
│  Win: 58.3%  │  PF: 1.63  │  Avg W: +$62  │  DD: -$142│
│  Best: +$185  │  Worst: -$92  │  Trades: 12│        │
│                                                      │
│  ── VECTORS TAB ──────────────────────────────────  │
│                                                      │
│  Time-spread of each instrument:                    │
│  ┌──────────────────────────────────────────┐       │
│  │  PA  ~~~~ (fast, jagged)                 │       │
│  │  Mom ~~~~ (medium, trending)             │       │
│  │  KL  ──── (slow, sticky)                │       │
│  │  Vol ⚡⚡⚡ (spiky)                       │       │
│  │  Str ──── (glacial)                      │       │
│  │                                           │       │
│  │  ─── 1H weighted (thick slow line) ───   │       │
│  │  ░░░ agreement band ░░░                  │       │
│  └──────────────────────────────────────────┘       │
│                                                      │
│  15m Avg: +0.234  │  1H Avg: +0.187  │  Agree: 0.72│
│                                                      │
│  ── DISTRIBUTION TAB ─────────────────────────────  │
│                                                      │
│  Radius Histogram (P/L percentile bands):           │
│  0.618 ▓▓▓░░░░░░░░░░░░░░░░░░░░░ 1.618            │
│                                                      │
│  Vector Contribution (which instrument drove P/L):  │
│  ┌──────────────────────────────┐                   │
│  │  Winning trades avg vectors: │                   │
│  │  PA: +0.72  Mom: +0.68      │                   │
│  │  Losing trades avg vectors:  │                   │
│  │  PA: +0.31  Vol: -0.22      │                   │
│  └──────────────────────────────┘                   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Color Palette (CytoBase — No New Colors)
- Mint `#ADEBB3` / `#00ff9d` — Profit, bullish bars, active state
- Teal `#20B2AA` / `#00f2ea` — Data lines, interactive, structure
- Bearish signals shown via reduced saturation / dimmed teal, NOT red/coral
- All controls inherit neomorphic shadows from 15BE

---

## 7. Evolution (The Shift)

- **From:** CytoBase is a beautiful empty shell (15BE). Maestro V2 profile exists only as text in Seed 10.
- **To:** CytoBase is a living profile-driven simulation system. The JSON profile IS the control surface.

### Phase 1: Profile + Backend `profiles/maestro_sim_v1.json` + `#Cyto/cyto_simulator.py`
- [ ] Create `profiles/` directory and `maestro_sim_v1.json`
- [ ] `CytoSimulator` class with profile loader
- [ ] Random-walk generator for 5 named instruments (PA, KL, Mom, Vol, Str)
- [ ] Composite calculation: `v6 = Σ(vi × wi)` using profile vector_weights
- [ ] 1H sticky persistence (recalculates every 4th bar, persists between)
- [ ] `weighted_final` = `(15m_composite × 0.70) + (1h_composite × 0.30)` per profile
- [ ] Threshold-driven trade entry: open when `weighted_final` crosses profile threshold
- [ ] Sentiment-flip exit: close when composite crosses zero (if enabled in profile)
- [ ] Hard stop exits: close when running P/L exceeds stop_loss/take_profit from profile
- [ ] Time exit: close after max_bars from profile
- [ ] P/L generated from skewed normal distribution (profile configures mean/std/skew)
- [ ] Radius percentile via `CytoManager.calc_radius()`
- [ ] All data written through `CytoIntegration.record_bar()` and `.on_trade_close()`
- [ ] Threading tick loop with speed control
- [ ] Reset: wipe instance, re-create, restart from bar 0

### Phase 2: API Routes (additions to `cyto_routes.py`)
- [ ] POST `/api/cyto/simulator/start` — body: `{symbol, profile, speed}`
- [ ] POST `/api/cyto/simulator/stop` — pause
- [ ] POST `/api/cyto/simulator/reset` — wipe + restart
- [ ] GET `/api/cyto/simulator/status` — state, progress, live scores, current signal
- [ ] POST `/api/cyto/simulator/speed` — change interval live
- [ ] GET `/api/cyto/simulator/analysis` — P/L, vector stats, distribution
- [ ] GET `/api/cyto/simulator/profile` — return the loaded profile JSON
- [ ] GET `/api/cyto/simulator/scores` — return latest bar's 6 named scores + weights

### Phase 3: UI Integration (modifications to `templates/cytobase.html`)
- [ ] Q3: Simulation engine controls + live score bars + profile weights display
- [ ] Q4: Analysis tabs (P/L, Vectors, Distribution)
- [ ] Radial nodes appear as simulation progresses
- [ ] Progress bar, epoch counter, trade counter
- [ ] Poll `/api/cyto/simulator/status` at tick interval
- [ ] Poll `/api/cyto/instances/<id>/radial` to update timepiece
- [ ] Canvas charts for equity curve and vector time-spread

---

## 8. Infinity (Patterns/Debt)

### Pattern: Profile-Driven Architecture (from Seed 10)
The simulator does not contain ANY hardcoded thresholds, weights, or risk parameters. Every decision constant lives in the profile JSON. This mirrors the "Dependency Injection" pattern from Seed 10 — the engine is the orchestra, the profile is the sheet music.

### Pattern: Named Vectors (from Seed 10B)
Each score has a NAME and a MEANING. Logs read:
```
[BAR 47] PA: +0.62 | KL: +0.38 | Mom: +0.71 | Vol: +0.24 | Str: +0.48
         Composite(15m): +0.512 | 1H: +0.387 | Final: +0.474
         Signal: HOLD (threshold: ±0.55)
```
Not: `[BAR 47] v1: 0.62 v2: 0.38 ... Score: 0.47`

### Pattern: Derived Composite
`v6` (composite/overall_bias) is **calculated**, not independently generated. This prevents the composite from disagreeing with its own components — a problem the real system avoids by having the AI weight its own assessment.

### Pattern: 1H Sticky Persistence
```
Bar 0:  15m_composite=+0.51  1h_composite=+0.38  ← 1H RECALCULATES (bar % 4 == 0)
Bar 1:  15m_composite=+0.62  1h_composite=+0.38  ← 1H PERSISTS (same value)
Bar 2:  15m_composite=+0.44  1h_composite=+0.38  ← 1H PERSISTS
Bar 3:  15m_composite=+0.58  1h_composite=+0.38  ← 1H PERSISTS
Bar 4:  15m_composite=+0.33  1h_composite=+0.47  ← 1H RECALCULATES (new 4-bar avg)
```

### Pattern: Regime Drift
The simulation doesn't just random-walk — it creates natural **trending and ranging periods**:
- Every 20-80 bars, a regime shift occurs
- During "bull" regime: all vectors drift positive (mean shifts to +0.2)
- During "bear" regime: all vectors drift negative (mean shifts to -0.2)
- During "range" regime: mean stays near 0, volatility increases
- This creates realistic clustering of trades and sentiment patterns

### Pattern: Correlation Clusters (from Seed 10B)
Instruments aren't independent — they share noise within clusters:
- **Trend group** (PA + Momentum + Structure) — when PA spikes, momentum tends to follow
- **Flow group** (Volume + Key Levels) — volume spikes near key levels

### Debt to Avoid
- ❌ Don't bypass CytoIntegration — always go through the bridge
- ❌ Don't hardcode weights — ALWAYS read from profile JSON
- ❌ Don't generate composite independently — ALWAYS derive from v1-v5
- ❌ Don't trigger trades randomly — use profile thresholds
- ❌ Don't block Flask thread — simulation runs in its own thread
- ❌ Don't add new colors — mint and teal only

---

## Architecture Flow

```mermaid
graph TD
    subgraph Profile["maestro_sim_v1.json"]
        WEIGHTS[vector_weights]
        THRESH[thresholds]
        TF_W[timeframe_weights: 15m=0.7, 1h=0.3]
        RISK[risk_management]
        EXIT[exit_strategy]
        RW[random_walk config]
    end

    subgraph SimEngine["CytoSimulator (Thread)"]
        TICK[Tick Loop] -->|every N seconds| GEN[Generate 5 Instruments]
        
        GEN --> PA[PA Score]
        GEN --> KL[KL Score]
        GEN --> MOM[Mom Score]
        GEN --> VOL[Vol Score]
        GEN --> STR[Str Score]
        
        PA & KL & MOM & VOL & STR -->|× profile weights| COMP_15[Composite 15m]
        
        COMP_15 --> STICKY{Bar % 4 == 0?}
        STICKY -->|Yes| UPDATE_1H[Recalc 1H Composite]
        STICKY -->|No| PERSIST_1H[Use Cached 1H]
        
        UPDATE_1H --> BLEND[Final = 15m×0.7 + 1H×0.3]
        PERSIST_1H --> BLEND
        
        BLEND --> SIGNAL{Final vs Thresholds}
        SIGNAL -->|> entry_long| OPEN_LONG[Open Long]
        SIGNAL -->|< entry_short| OPEN_SHORT[Open Short]
        SIGNAL -->|in range| HOLD[Hold / Check Exits]
        
        OPEN_LONG --> RECORD[CytoIntegration.record_bar + on_trade_close]
        OPEN_SHORT --> RECORD
        HOLD --> CHECK_EXIT{Has Open Trade?}
        CHECK_EXIT -->|Yes| EXIT_CHECK[Check Sentiment Flip / Stops / Time]
        CHECK_EXIT -->|No| RECORD_BAR[CytoIntegration.record_bar]
        EXIT_CHECK -->|Exit| CLOSE[Close Trade]
        EXIT_CHECK -->|Hold| RECORD_BAR
        CLOSE --> RECORD
    end

    WEIGHTS --> COMP_15
    THRESH --> SIGNAL
    TF_W --> BLEND
    RISK --> OPEN_LONG
    RISK --> OPEN_SHORT
    EXIT --> EXIT_CHECK
    RW --> GEN

    subgraph Database["CytoBase (cyto_v3.db)"]
        RECORD --> NODES[(cyto_nodes)]
        RECORD --> TRADES[(cyto_trades)]
        RECORD_BAR --> NODES
    end

    subgraph API["Flask Routes"]
        START[/simulator/start] --> TICK
        STATUS[/simulator/status] --> TICK
        SCORES[/simulator/scores] --> GEN
        ANALYSIS[/simulator/analysis] --> NODES
        RADIAL[/instances/id/radial] --> NODES
        PROF[/simulator/profile] --> Profile
    end

    subgraph UI["CytoBase UI"]
        Q3[Q3: Sim Controls + Live Scores] -->|POST/GET| API
        Q4[Q4: Analysis Tabs] -->|GET| API
        RADIAL_VIZ[Radial Timepiece] -->|GET poll| RADIAL
    end
```

---

## What Gets Recorded Per Bar

| Field | Source | Update Rule |
|-------|--------|-------------|
| `vectors_15m.v1` | `price_action_score` | Random walk (σ=0.18), every bar |
| `vectors_15m.v2` | `key_levels_score` | Random walk (σ=0.08), every bar |
| `vectors_15m.v3` | `momentum_score` | Random walk (σ=0.14), every bar |
| `vectors_15m.v4` | `volume_score` | Random walk (σ=0.20), every bar |
| `vectors_15m.v5` | `structure_score` | Random walk (σ=0.06), every bar |
| `vectors_15m.v6` | `composite_score` | **Derived**: Σ(v1-v5 × weights), every bar |
| `weighted_15m` | 15m composite | Weighted sum via profile, every bar |
| `weighted_1h` | 1H composite | **Sticky** — recalculates every 4 bars |
| `weighted_final` | Blend | `15m × 0.70 + 1H × 0.30` per profile |
| `agreement_score` | 15m vs 1H alignment | `CytoManager.calc_agreement()`, every bar |
| `has_trade` | Threshold crossing | When `weighted_final` exceeds profile threshold |
| `raw_pnl` | Skewed normal distribution | On trade close (exit conditions from profile) |
| `radius` | Percentile rank 0.618→1.618 | `CytoManager.calc_radius()`, on trade bars |
| `trade_direction` | Sign of weighted_final at entry | `'long'` if positive, `'short'` if negative |
| `node_size` / `node_hue` / `node_saturation` | Pre-calculated visuals | `CytoManager.calc_node_visuals()`, every bar |

---

## Radius Percentile Scale

```
0.618  ═══  0th percentile (worst outcomes, inner ring)
  │
  │    Mapped via CytoManager.calc_radius():
  │    - Ranks trade P/L against all prior trades for this instance
  │    - percentile = count_below / total_history
  │    - radius = 0.618 + (percentile × 1.000)
  │
1.000  ═══  50th percentile (median, middle ring)
  │
  │
1.618  ═══  100th percentile (best outcomes, outer ring)
```

---

## Wake-Up Prompt (Phase 1)

```
@SEEDS/Seed 16A – CytoSimulator – Seed Log.md
@#Cyto/cyto_schema.py
@#Cyto/cyto_manager.py
@#Cyto/cyto_integration.py

Execute Seed 16A Phase 1: Create profile + build CytoSimulator backend.

CONTEXT:
- CytoBase schema, manager, and integration bridge all exist
- No profile JSON file exists yet — create it
- The simulator is driven by the profile, not hardcoded values
- 6 named scores: price_action, key_levels, momentum, volume, structure, composite
- Composite (v6) is DERIVED from v1-v5 using profile weights, not independently generated
- Trades trigger on threshold crossings, not random probability
- 1H sticky persistence: recalculates every 4th bar

INSTRUCTIONS:
1. Create `profiles/maestro_sim_v1.json` (from the Foundation section)
2. Create `#Cyto/cyto_simulator.py` with:
   a. Profile loader — reads and validates the JSON
   b. 5 independent random-walk generators (mean-reverting, per-instrument volatility)
   c. Composite calculation using profile vector_weights
   d. 1H sticky update logic (every 4th bar)
   e. weighted_final blend using profile timeframe_weights
   f. Threshold-driven trade entry using profile thresholds
   g. Exit logic: sentiment_flip + hard stops + time exit (all from profile)
   h. P/L from skewed normal distribution (profile configures)
   i. All writes through CytoIntegration.record_bar() and .on_trade_close()
   j. Threading tick loop with speed control
   k. Methods: start(), stop(), reset(), set_speed(), get_status(), get_analysis(), get_scores()
```

---

## Success Criteria

### Phase 1 (Backend)
- Profile loads and all weights/thresholds are read from JSON
- 5 instruments generate independently, composite is derived
- `weighted_1h` only changes every 4th bar
- Trades trigger when `weighted_final` crosses profile threshold
- Exits fire on sentiment flip / hard stop / time limit
- Nodes appear in database with named vectors and correct composite
- Radius distributes across 0.618→1.618 range
- Reset clears data and restarts from bar 0
- Speed changes take effect on next tick

### Phase 3 (UI)
- Q3 shows live scores per instrument with profile weights visible
- Q4 analysis shows equity curve, per-instrument time-spread, distribution
- Signal state (LONG / SHORT / HOLD) updates in real-time
- Profile weights visible so you can see WHY the composite is what it is

---

*The profile is the sheet music. The simulator is the rehearsal. The database is the recording. The radial is the stage.*
