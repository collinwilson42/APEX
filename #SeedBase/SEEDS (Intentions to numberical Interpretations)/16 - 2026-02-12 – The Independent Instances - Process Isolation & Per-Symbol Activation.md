# Instance Independence – Seed Log

---

16: 2026-02-12 – The Independent Instances - Process Isolation & Per-Symbol Activation ^seed-independent-instances

## Prompts & Execution
"Diversification and instance independence. Each instance should run independently and multiple instances should be able to run at once. Only activate the instance I activate from the algo page, one at a time. Also accurately reflect what instances are running in the control panel in the cytobase."

## 1. Seed (Intent)
- **Replace monolithic simulation** (all 6 classes spawned at once) with **independent per-symbol processes**
- Each instance = its own Python process, spawned on-demand from the algo page
- init2.py becomes the **process orchestrator**, not the runtime host
- Multiple instances can run simultaneously but are started/stopped individually
- Crash isolation: one instance dying doesn't take down the others
- CytoBase control panel shows live instance status with start/stop controls

## 2. Related (Context)
- [[14B – The Virtual Broker]] (IBroker pattern — this replaces thread-based approach with processes)
- [[15BE/15BF – CytoBase Simulation]] (Monolithic CytoSimulator being replaced)
- `init2.py` (The Hub — gains process manager role)
- `cyto_simulator.py` (Logic extracted into instance_runner.py)
- `apex_views.js` (ACTIVE double-tap now per-symbol)
- `cytobase.html` (Q3 Instance Manager now shows live process status)

## 4. Foundation (Structure)

### NEW FILES
- `process_manager.py` — Orchestrator class with Flask routes
- `instance_runner.py` — Standalone process entry point (CLI args)

### MODIFIED FILES
- `init2.py` — Swapped cyto_simulator import for process_manager
- `static/js/apex_views.js` — ACTIVE handler now per-symbol + _getSymbolKey helper
- `templates/cytobase.html` — Q3 replaced with live CytoBaseStatus component

## 8. Infinity (Patterns/Debt)
- Process-per-Instance via subprocess.Popen
- Database as IPC (SQLite WAL, no sockets/queues)
- Graceful shutdown via SIGTERM/CTRL_BREAK
- Singleton per symbol enforced
- Mode agnostic (--mode SIM or --mode LIVE)

## 7. Evolution (Real-Time Log)
- [x] Created `process_manager.py` ✅ 2026-02-12
- [x] Created `instance_runner.py` ✅ 2026-02-12
- [x] Replaced cyto_simulator in init2.py with process_manager ✅ 2026-02-12
- [x] Updated apex_views.js ACTIVE handler to per-symbol + _getSymbolKey ✅ 2026-02-12
- [x] Added CytoBaseStatus live panel to cytobase.html Q3 ✅ 2026-02-12
- [x] SQLite WAL mode enforced in CytoDBWriter ✅ 2026-02-12
- [x] Orphan cleanup on init2.py startup ✅ 2026-02-12
- [x] ALL FILES WIRED INTO CODEBASE ✅ 2026-02-12
- [ ] Pending: Restart Flask and test end-to-end
- [ ] Pending: Test crash isolation (start BTC + GOLD, kill BTC, verify GOLD survives)

## 5. Senses (UX/DX)
- Algo page: Double-tap ACTIVE on BTC → only BTC's process starts
- CytoBase Q3: 3×2 grid of neomorphic cards, teal glow on running instances
- Click any card in CytoBase to toggle that instance on/off
- Console output prefixed per-instance: [BTC-SIM] Bar 42: ...
- `python instance_runner.py --symbol BTC --mode SIM` works standalone for debugging
