# Structure – Fruit Log

---

F: 2026-01-31 – Seed: Retroactive-Architecture ^fruit-entry-point

**Review:**
- **CRITICAL:** `flask_apex.py` was acting as a "Shadow App," causing split logic.
- The `init2.py` file is the only valid entry point (`py init2.py`).

**Adjustments:**
- **Rule:** Any feature currently in `flask_apex.py` (Profile Manager, Instance API, Sentiment Routes) MUST be migrated to `init2.py`.
- **Action:** Deprecate `flask_apex.py` immediately after migration.