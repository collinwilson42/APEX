# Structure – Seed 14 – The Virtual Broker & Interface

---

14: 2026-02-02 – The Virtual Broker: Simulation Logic & Interface Standardization ^seed-structure-virtual-broker

## Prompts & Execution
"If multiple instances are running... how can live data be parsed... use this for live trading as well... Standardize the Interface."

## 1. Seed (Intent)
- **Objective:** Create a `VirtualBroker` for simulation that implements the *exact same interface* as the Live `MT5Broker`. Implement the **"Driver Pattern"** so the strategy logic is decoupled from the execution engine.
- **Specifics:**
    - **Standard Interface (`IBroker`):** Define the required methods: `buy()`, `sell()`, `close()`, `get_pnl()`, `get_positions()`.
    - **Virtual Broker:** Implements this interface using in-memory math (Lists, PnL calc).
    - **Live Broker Adapter:** (Refactor `trade.py`) to implement this same interface wrapping the MT5 calls.
    - **Data Flow:** The Engine passes the `tick_data` to the `broker.on_tick()` method, allowing the Virtual Broker to update its internal PnL state without fetching external data.

## 2. Related (Context)
- `init2.py` (The Hub / Distributor).
- `trade.py` (The Live Implementation).
- `virtual_broker.py` (The Sim Implementation).

## 4. Foundation (Structure)
*Files to be created/modified:*
- **NEW:** `brokers/base_broker.py` (The Abstract Interface).
- **NEW:** `brokers/virtual_broker.py` (The Sim Logic).
- **REF:** `brokers/live_broker.py` (Wraps existing `trade.py` logic).
- `init2.py`:
    - Instead of importing `trade`, it imports `BrokerFactory`.
    - `broker = BrokerFactory.get_broker(mode="SIM" or "LIVE")`.

## 8. Infinity (Patterns)
- **Pattern:** **Dependency Injection.** The strategy receives a `broker` object. It calls `broker.buy()`. It doesn't know (or care) if that money is real or fake.
- **Pattern:** **Pub/Sub (Observer).** The central loop fetches data once and "publishes" it to the active broker instance.

## Architecture Flow (The Hub & Spoke)
```mermaid
graph TD
    Hub[Data Collector (Hub)] -->|Broadcast Price: 100| InstanceA
    Hub -->|Broadcast Price: 100| InstanceB
    
    subgraph Instance_A
        InstanceA -->|Logic: Buy| BrokerA[Virtual Broker A]
        BrokerA -->|Update| StateA[Virtual PnL: +$50]
    end

    subgraph Instance_B
        InstanceB -->|Logic: Wait| BrokerB[Live Broker B]
        BrokerB -->|Send| MT5[MT5 Terminal]
    end