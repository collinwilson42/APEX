# Seed 15BF — CytoBase Simulation Integration

## 1. Seed (Intent)
Wire mock sentiment + trade generation into the CytoBase so the radial timepiece shows real data — without spending API money.

## 2. Related (Context)
- Seed 15BE: CytoBase Neomorphic Radial (the empty shell)
- Seed 15A: CytoBase Schema + Manager (288-slot grid, Fibonacci radius)
- Seed 14B: Virtual Broker (trade structure)
- `sentiment_engine.py`: Real sentiment scheduler (replaced by mock here)
- `cyto_integration.py`: Bridge between sentiment/trades → CytoBase nodes

## 4. Foundation (Structure)

### Files Created:
- **`cyto_simulator.py`** — Mock data generator with:
  - `SentimentWalker`: Random-walk sentiment vectors with mean-reversion
  - `TradeGenerator`: Probabilistic trade firing (~25% of bars) with skewed P/L
  - `CytoSimulator`: Orchestrator — creates 6 asset class instances, runs at real 15m intervals
  - Flask routes: `/api/cyto/sim/start`, `/stop`, `/status`, `/toggle`

### Files Modified:
- **`init2.py`** — Registered `cyto_routes` + `cyto_simulator` routes
- **`static/js/apex_views.js`** — ACTIVE double-tap now calls `/api/cyto/sim/toggle`

### Architecture:
```
User double-taps ACTIVE on Algo page
    ↓
apex_views.js → POST /api/cyto/sim/start
    ↓
CytoSimulator.start()
    ↓ creates 6 instances (BTC, OIL, GOLD, US100, US30, US500)
    ↓ each gets own z-layer in cyto_v3.db
    ↓
Every 15 minutes (real speed):
    ↓
For each asset class:
    SentimentWalker.step() → 6 vectors + weighted scores
    TradeGenerator.maybe_trade() → ~25% chance of trade
    ↓
    CytoIntegration.on_sentiment_reading() → 15m (every bar)
    CytoIntegration.on_sentiment_reading() → 1h (every 4th bar, sticky)
    CytoIntegration.on_trade_close() → when trade fires
    ↓
    CytoManager.add_node() → cyto_v3.db
        theta_slot = (minutes / 15) % 288
        radius = percentile(pnl, history)  // 0.618→1.618
```

### Key Behaviors:
- **1H persistence**: 1H sentiment updates every 4 bars, persists between
- **All classes stacked**: One radial view, 6 asset classes overlaid
- **Per-instance layers**: Each instance_id = own z-layer in database
- **Radius = percentile**: 0.618 (worst) → 1.000 (median) → 1.618 (best)
- **Real 15m intervals**: First bar fires immediately, then every 900 seconds

## 8. Infinity (Patterns)
- **The Orchestra Pattern**: 6 walkers play independently, all recorded on same stage
- **Sticky 1H**: Hourly sentiment is the "tide" — it doesn't change bar-to-bar
- **Percentile Normalization**: You can't compare raw P/L across assets; radius makes them comparable

## 7. Evolution (Real-Time Log)
- [x] Created cyto_simulator.py with SentimentWalker, TradeGenerator, CytoSimulator ✅ 2026-02-11
- [x] Registered routes in init2.py (cyto_routes + simulator) ✅ 2026-02-11
- [x] Hooked ACTIVE double-tap to start/stop simulator ✅ 2026-02-11
- [ ] Frontend polling for live radial data (15BG)
- [ ] Node rendering on canvas (15BG)
- [ ] Class filtering in control panel (15BG)
