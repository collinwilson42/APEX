# Structure – Seed 14B – The Virtual Broker: Implementation Blueprint

---

14B: 2026-02-02 – The Virtual Broker: Implementation Blueprint & Database Integration ^seed-structure-virtual-broker-impl

## Prompts & Execution
"This looks like a solid foundation combining what you just laid out with Gemini's Seed 14. Lets develop Seed 14B to cover anything important that was missed and we can jump into developing. Lets make sure the database endpoints are all connected up, new columns are created if needed, and the frontend algo page maps to the most recent relevant data cell."

## 1. Seed (Intent)
- **Objective:** Implement the complete **VirtualBroker** system with database persistence, API endpoints, and frontend integration.
- **Key Deliverables:**
    - `IBroker` abstract interface
    - `VirtualBroker` for simulation (in-memory + DB persist)
    - `LiveBroker` wrapping MT5 API calls
    - `BrokerFactory` to create the right broker based on mode
    - API endpoints for broker operations
    - Frontend broker state display

## 2. Related (Context)
- [[14 – The Virtual Broker]] (Gemini's original architecture)
- [[10D – The Stage Hands]] (Position sync + dual-timeframe sentiments)
- `instance_database.py` (Current position/sentiment schema)
- `trade.py` (Webhook bridge - becomes `live_broker.py`)
- `init2.py` (The Hub)

## 4. Foundation (Structure)
*Files to create/modify:*
- **DONE:** `brokers/__init__.py` ✅
- **DONE:** `brokers/base_broker.py` (IBroker interface) ✅
- **DONE:** `brokers/virtual_broker.py` (Simulation logic) ✅
- **DONE:** `brokers/live_broker.py` (MT5 wrapper) ✅
- **DONE:** `brokers/broker_factory.py` ✅
- **PENDING:** `instance_database.py` (Add broker_state table + columns)
- **PENDING:** `init2.py` (Add broker API routes)
- **PENDING:** `static/js/apex_instances.js` (Broker state header)
- **PENDING:** `static/css/apex_instances.css` (Broker styling)

## 8. Infinity (Patterns)
- **Dependency Injection:** Strategy receives broker, doesn't know if SIM or LIVE ✅
- **Factory Pattern:** BrokerFactory.get_broker(instance_id, mode) ✅
- **Interface Segregation:** IBroker defines only trading methods ✅
- **Singleton per Instance:** Factory caches brokers to prevent duplicates ✅
- **Hub Pattern:** BrokerFactory.broadcast_tick() sends price to all brokers ✅

## 7. Evolution (Real-Time Log)
- [x] Phase 1: Create brokers/ directory and interface ✅ (2026-02-02)
  - Created `base_broker.py` with IBroker, Position, OrderResult dataclasses
  - Created `virtual_broker.py` with full SIM logic + SL/TP auto-close
  - Created `live_broker.py` wrapping MT5 API calls
  - Created `broker_factory.py` with singleton registry + broadcast_tick
  - Created `__init__.py` with clean exports
- [ ] Phase 2: Database persistence (broker_state table)
- [ ] Phase 3: API routes in init2.py
- [ ] Phase 4: Frontend integration
- [ ] Phase 5: Wire up to existing strategy execution

## Implementation Phases

### Phase 1: Interface & Factory ✅ COMPLETE
Files created:
- `brokers/base_broker.py` - IBroker abstract class, Position/OrderResult dataclasses
- `brokers/virtual_broker.py` - Full simulation with PnL tracking, SL/TP auto-close
- `brokers/live_broker.py` - MT5 wrapper (conditional import)
- `brokers/broker_factory.py` - Factory with singleton cache + broadcast_tick
- `brokers/__init__.py` - Package exports

### Phase 2: Database Persistence (NEXT)
- Add `broker_positions` table for position persistence
- Add `broker_trades` table for trade history
- Modify VirtualBroker to persist on trade events

### Phase 3: API Routes
- POST `/api/broker/create` - Create broker for instance
- POST `/api/broker/{instance}/buy` - Execute buy
- POST `/api/broker/{instance}/sell` - Execute sell
- POST `/api/broker/{instance}/close` - Close position
- GET `/api/broker/{instance}/state` - Get broker state
- GET `/api/broker/all` - Get all broker states

### Phase 4: Frontend Integration
- Broker mode indicator (SIM/LIVE badge)
- Position list with live PnL
- Trade buttons (if manual control enabled)
- Equity curve visualization

### Phase 5: Strategy Wiring
- Modify init2.py to use BrokerFactory
- Strategy signals route through broker.buy()/sell()
- Tick data broadcasts to all active brokers
