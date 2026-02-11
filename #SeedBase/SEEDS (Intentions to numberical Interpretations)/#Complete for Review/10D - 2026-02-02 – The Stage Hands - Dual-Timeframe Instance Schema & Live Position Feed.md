# Logic – Seed Log (Part D)

---

10D: 2026-02-02 – The Stage Hands: Dual-Timeframe Instance Schema & Live Position Feed ^seed-logic-stage-hands

## Prompts & Execution
"The bottom left quadrant instances need to be split into two 15m and 1hr because we have sentiments for both. Though positions can stay as one database per algorithm. We also need to add columns for the sentiment scores... Also we need to connect up a live feed from MT5 for positions into the specific instance when active. Multiple instances should be able to run at once."

## 1. Seed (Intent)
- **Objective:** Restructure the Instance Browser (Q3) to display **dual-timeframe sentiments** (15m and 1h tabs) while maintaining **unified position tracking**, and wire **live MT5 position data** into active instances.
- **Specifics:**
    - **Dual-Timeframe Tabs:** The SENTIMENTS tab in the Instance Browser splits into two sub-tabs: "15M" and "1H" (see screenshot circled area as reference for tab style).
    - **Score Columns:** Add the 6 numeric score columns (`price_action_score`, `key_levels_score`, `momentum_score`, `volume_score`, `structure_score`, `composite_score`) to the sentiment display table.
    - **Unified Positions:** POSITIONS tab remains single (no timeframe split) - positions are per-instance, not per-timeframe.
    - **Live MT5 Feed:** Create a position tracker thread that polls MT5 for open positions matching the instance's symbol and updates the instance database in real-time.
    - **Multi-Instance Execution:** Multiple instances can be "active" simultaneously, each with its own position tracker thread.

## 2. Related (Context)
- [[10A – The Conductor]] (Profile-driven execution loop)
- [[10B – The Instruments]] (Poly-metric scoring engine)
- [[10C – Live Data Connection]] (Real MT5 data pipe)
- `instance_database.py` (Current schema)
- `apex_instances.js` (Frontend Instance Browser)
- `apex_views.js` (Quadrant rendering)
- `mt5_position_tracker.py` (Existing position tracking module)

## 4. Foundation (Structure)
*Files to be modified/created:*

### Backend - Database Schema
- **`instance_database.py`:**
    - **Sentiment Table:** Already has score columns ✓ (verified in code)
    - **Add Index:** Create compound index on `(instance_id, timeframe, timestamp)` for fast tab switching
    - **Position Table:** Add columns for live MT5 sync: `mt5_ticket`, `mt5_magic`, `sync_status`, `last_sync_at`

### Backend - Live Position Feed
- **`mt5_live_position_sync.py` (NEW):**
    - `PositionSyncManager` class
    - `start_sync(instance_id, symbol)` - Starts polling thread for an instance
    - `stop_sync(instance_id)` - Stops polling thread
    - `_poll_mt5_positions()` - Fetches positions from MT5 matching symbol
    - `_sync_to_database()` - Upserts position data into instance table
    - Poll interval: 1 second (configurable)
    - Support multiple simultaneous syncs (one per active instance)

### Backend - API Routes
- **`init2.py`:**
    - `/api/instance/<id>/sentiments/<timeframe>` - Get sentiments for specific timeframe
    - `/api/instance/<id>/sentiments/latest` - Get latest sentiment for BOTH timeframes (for dashboard)
    - `/api/instance/<id>/positions/live` - Get live positions with MT5 sync status
    - `/api/instance/<id>/sync/start` - Start MT5 position sync for instance
    - `/api/instance/<id>/sync/stop` - Stop MT5 position sync

### Frontend - Instance Browser (Q3)
- **`static/js/apex_instances.js`:**
    - **Tab Structure:** POSITIONS | SENTIMENTS [15M | 1H] | TRANSITIONS | MATRICES
    - **Sentiment Table Columns:** TIME | PA | KL | MOM | VOL | STR | COMPOSITE | BIAS
    - **Score Formatting:** Color-coded cells: green (>0.3), neutral (-0.3 to 0.3), red (<-0.3)
    - **Live Indicator:** Pulsing dot when position sync is active

- **`static/css/apex_instances.css`:**
    - `.sentiment-score-cell` - Base cell styling
    - `.sentiment-score-cell--bullish` - Green background gradient
    - `.sentiment-score-cell--bearish` - Red background gradient
    - `.sentiment-score-cell--neutral` - Gray background
    - `.sync-indicator` - Pulsing animation for live feed

### Frontend - Views Integration
- **`static/js/apex_views.js`:**
    - Update `renderInstanceBrowser()` to include timeframe sub-tabs
    - Add `switchSentimentTimeframe(timeframe)` function
    - Wire up automatic refresh when new sentiment arrives (via WebSocket or polling)

## 8. Infinity (Patterns/Debt)
- **Pattern: Observer/Pub-Sub.** When a new sentiment is saved to the database, emit an event that the frontend can subscribe to for real-time updates.
- **Pattern: Thread-Safe Singleton.** The `PositionSyncManager` must handle multiple instances without race conditions. Use a dictionary of threads keyed by `instance_id`.
- **Anti-Pattern: Polling Storms.** Don't poll MT5 per-tab-switch. Cache the latest data and refresh on a timer.
- **Debt: WebSocket Migration.** Current implementation uses polling; future iteration should use WebSockets for true real-time.

## 5. Senses (UX/DX)
- **Visual:** Score cells should be glanceable - color tells the story at a glance without reading numbers.
- **Feedback:** When switching between 15M and 1H tabs, there should be no visible loading delay (data should be pre-cached or fetched in parallel).
- **Live Indicator:** The POSITIONS tab should show "LIVE" badge with pulsing animation when sync is active. When offline, show "OFFLINE" in muted gray.
- **Multi-Instance:** User should be able to see at a glance which instances have active position syncs (perhaps a small MT5 icon in the instance list).

## 7. Evolution (Real-Time Log)
*Claude: Log milestones here as you work.*
- [x] [Add `mt5_ticket`, `sync_status` columns to positions table] - Done: instance_database.py updated
- [x] [Create `mt5_live_position_sync.py` with PositionSyncManager] - Done: New file created
- [x] [Add timeframe sub-tabs to SENTIMENTS in Instance Browser] - Done: apex_instances.js v3.0
- [x] [Add score columns to sentiment table display] - Done: PA, KL, MOM, VOL, STR, COMP columns
- [x] [Implement color-coded score cells CSS] - Done: apex_instances.css SEED 10D section
- [x] [Wire API endpoints for sentiment timeframe queries] - Done: /api/instance/{id}/sentiments/{tf}
- [x] [Wire API endpoints for position sync control] - Done: /api/instance/{id}/sync/start|stop|status
- [ ] [Test multi-instance simultaneous sync]

## Architecture Flow (The Stage Hands)

```mermaid
graph TD
    subgraph MT5_Terminal
        MT5[MetaTrader 5]
    end
    
    subgraph Position_Sync_Layer
        PSM[PositionSyncManager]
        PSM -->|Thread 1| Sync1[Instance A Sync]
        PSM -->|Thread 2| Sync2[Instance B Sync]
        Sync1 -->|Poll 1s| MT5
        Sync2 -->|Poll 1s| MT5
    end
    
    subgraph Instance_Database
        Sync1 -->|Upsert| PosA[(positions_instance_a)]
        Sync2 -->|Upsert| PosB[(positions_instance_b)]
        
        SentA15[(sentiment_a: 15m)]
        SentA1H[(sentiment_a: 1h)]
        SentB15[(sentiment_b: 15m)]
        SentB1H[(sentiment_b: 1h)]
    end
    
    subgraph Frontend [Instance Browser Q3]
        Tabs[POSITIONS | SENTIMENTS | TRANSITIONS | MATRICES]
        Tabs --> SubTabs{SENTIMENTS}
        SubTabs -->|15M| Table15[15M Score Table]
        SubTabs -->|1H| Table1H[1H Score Table]
        
        PosA --> LivePos[Live Position Table]
        SentA15 --> Table15
        SentA1H --> Table1H
    end
```

## Database Schema Updates

### positions_{instance_id} - Add Columns
```sql
ALTER TABLE positions_{instance_id} ADD COLUMN mt5_ticket INTEGER;
ALTER TABLE positions_{instance_id} ADD COLUMN mt5_magic INTEGER;
ALTER TABLE positions_{instance_id} ADD COLUMN sync_status TEXT DEFAULT 'PENDING';  -- PENDING | SYNCED | CLOSED_MT5 | ORPHAN
ALTER TABLE positions_{instance_id} ADD COLUMN last_sync_at TEXT;
ALTER TABLE positions_{instance_id} ADD COLUMN mt5_profit REAL;
ALTER TABLE positions_{instance_id} ADD COLUMN mt5_swap REAL;
ALTER TABLE positions_{instance_id} ADD COLUMN mt5_commission REAL;
```

### Sentiment Table Display Columns (Already in Schema)
| Column | Type | Display |
|--------|------|---------|
| timestamp | TEXT | TIME (formatted HH:MM) |
| price_action_score | REAL | PA (color-coded) |
| key_levels_score | REAL | KL (color-coded) |
| momentum_score | REAL | MOM (color-coded) |
| volume_score | REAL | VOL (color-coded) |
| structure_score | REAL | STR (color-coded) |
| composite_score | REAL | COMP (color-coded, bold) |
| matrix_bias_label | TEXT | BIAS (text badge) |

## API Response Formats

### GET /api/instance/{id}/sentiments/15m
```json
{
    "success": true,
    "timeframe": "15m",
    "data": [
        {
            "timestamp": "2026-02-02T14:15:00Z",
            "price_action_score": 0.65,
            "key_levels_score": 0.42,
            "momentum_score": 0.78,
            "volume_score": 0.31,
            "structure_score": 0.55,
            "composite_score": 0.54,
            "matrix_bias": 1,
            "matrix_bias_label": "Bullish"
        }
    ],
    "count": 50
}
```

### GET /api/instance/{id}/positions/live
```json
{
    "success": true,
    "sync_active": true,
    "last_sync": "2026-02-02T14:15:32Z",
    "positions": [
        {
            "id": 1,
            "mt5_ticket": 12345678,
            "symbol": "XAUJ26",
            "direction": "LONG",
            "lots": 0.5,
            "entry_price": 2845.50,
            "current_price": 2847.30,
            "unrealized_pnl": 90.00,
            "mt5_profit": 90.00,
            "sync_status": "SYNCED"
        }
    ]
}
```

## CSS Score Cell Styling

```css
/* Score cell base */
.score-cell {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 4px 8px;
    text-align: center;
    border-radius: 4px;
    min-width: 48px;
}

/* Bullish gradient (score > 0.3) */
.score-cell--bullish {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.3), rgba(34, 197, 94, 0.1));
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
}

/* Bearish gradient (score < -0.3) */
.score-cell--bearish {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.3), rgba(239, 68, 68, 0.1));
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Neutral (score between -0.3 and 0.3) */
.score-cell--neutral {
    background: rgba(148, 163, 184, 0.1);
    color: #94a3b8;
    border: 1px solid rgba(148, 163, 184, 0.2);
}

/* Composite cell (emphasized) */
.score-cell--composite {
    font-weight: 600;
    font-size: 12px;
}

/* Live sync indicator */
.sync-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.sync-indicator__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    animation: pulse 1.5s ease-in-out infinite;
}

.sync-indicator--offline .sync-indicator__dot {
    background: #64748b;
    animation: none;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
}
```

## Implementation Priority

1. **Database First:** Add columns and ensure schema is solid
2. **Backend APIs:** Wire the timeframe-specific sentiment endpoints
3. **Position Sync:** Create the MT5 sync manager (can run headless)
4. **Frontend Tabs:** Update Instance Browser with sub-tabs
5. **Score Styling:** Apply color-coded cells
6. **Live Indicator:** Add sync status badges
7. **Multi-Instance Test:** Verify concurrent syncs don't conflict
