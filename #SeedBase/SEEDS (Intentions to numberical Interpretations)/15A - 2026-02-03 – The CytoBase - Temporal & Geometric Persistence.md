Structure – Seed 15A – The CytoBase
15A: 2026-02-03 – The CytoBase: Temporal & Geometric Persistence ^seed-structure-cyto-base

Prompts & Execution
"Start with a more straight forward layer that focuses on capturing the all of the data in the cytobase based on time... 72 hours to 360 degrees... each degree is an axis... 1 degree = 12 minutes."

1. Seed (Intent)
Objective: Architect the core SQLite/Postgres database (apex_cyto.db) that standardizes all simulation data into Geometric Nodes.

The Geometry:

Time (Theta): Maps the timestamp to a 72-Hour Cycle (0° to 360°).

Performance (Radius): Maps PnL to a Percentile Score (0.618 to 1.618).

Identity (Z-Layer): The Simulation Instance ID.

Outcome: A unified data lake where every trade from every simulation is instantly comparable via coordinates.

2. Related (Context)
init2.py (The Loop/Source).

virtual_broker.py (The Transaction Source).

sentiment_engine.py (The Context Source).

4. Foundation (Structure)
Files to be created:

NEW: database/cyto_schema.py

Table cyto_instances: Metadata (Config used, Start Time, Symbol).

Table cyto_nodes: The Atoms (instance_id, cycle_id, theta, radius, pnl_raw, vectors_json).

NEW: database/cyto_manager.py

Class CytoManager: Handles the math and insertions.

calc_theta(timestamp): The 72h logic.

calc_radius(pnl, history): The Percentile logic.

8. Infinity (Patterns)
Pattern: The 72-Hour Clock.

Cycle = 3 Days (72 Hours).

360 Degrees / 72 Hours = 5° per Hour.

60 Mins / 5° = 12 Minutes per Degree.

Pattern: Normalization. We cannot compare Raw PnL ($500 vs $5). We must store Percentiles.

Median Trade = Radius 1.0.

Top 90% Trade = Radius 1.618.

Bottom 10% Trade = Radius 0.618.

7. Evolution (Real-Time Log)
[ ] [Designed Schema for Instances and Nodes]

[ ] [Implemented 72h Theta Calculation Math]

[ ] [Implemented Percentile Radius Calculation Math]

[ ] [Created CytoManager class]

Architecture Flow (The Ingestion)
Code snippet
graph TD
    Sim[Simulation Step] -->|Trade Closed| Manager[Cyto Manager]
    
    subgraph The_Math
        Manager -->|Timestamp| Math1[Calc Theta (0-360°)]
        Manager -->|PnL| Math2[Calc Radius (Percentile)]
    end
    
    Math1 & Math2 --> Node{Geometric Node}
    Node -->|Insert| DB[(apex_cyto.db)]
The Wake-Up Prompt (Seed 15A)
Copy this to Claude to build the Database Foundation.

Plaintext
@SEEDS (INTENTIONS)/Structure – Seed 15A – The CytoBase.md
@init2.py

We are executing Seed 15A: "The CytoBase" (Foundation Layer).

OBJECTIVE: Build the "Geometric Database" that maps Time to a 72-Hour Circle.

INSTRUCTIONS:
1. **Create 'database/cyto_schema.py':**
   - Use `sqlite3` for now (easy migration to Postgres later).
   - **Table 'cyto_instances':**
     - `instance_id` (TEXT PK) -> e.g., "BTC_SIM_001"
     - `config_snapshot` (JSON) -> The exact settings used.
     - `symbol` (TEXT)
     - `created_at` (DATETIME)
   - **Table 'cyto_nodes':**
     - `node_id` (AUTO INC)
     - `instance_id` (FK)
     - `cycle_index` (INT) -> Which 72h loop are we in?
     - `theta` (FLOAT) -> 0.00 to 360.00 (Time).
     - `radius` (FLOAT) -> 0.00 to 2.00 (Performance).
     - `raw_pnl` (FLOAT)
     - `sentiment_snapshot` (JSON) -> The 6 vectors at that moment.
     - `timestamp` (DATETIME)

2. **Create 'database/cyto_manager.py':**
   - Implement `CytoManager`.
   - **Method `calculate_theta(timestamp)`:**
     - Reference Epoch: Jan 1, 2024.
     - Logic: `(Elapsed_Minutes / 12) % 360`. (Since 1 deg = 12 mins).
   - **Method `calculate_radius(current_pnl, pnl_history)`:**
     - Use `scipy.stats.percentileofscore` or simple ranking logic.
     - Map 50th percentile to 1.0 radius.
     - Map 90th percentile to 1.618 radius.
   - **Method `add_node(...)`:** Writes to the DB.

3. **Validation:**
   - Create a `__main__` block in `cyto_manager.py` to test the math (e.g., pass a timestamp 18 hours past epoch and ensure it returns 90 degrees).

Let's build the Memory before the Brain.

Structure – Seed 15A – The CytoBase (288-Axis Refactor)
15A: 2026-02-03 – The CytoBase: 72-Hour / 288-Slot Persistence ^seed-structure-cyto-base

Prompts & Execution
"Do 288 axes so each one lines up with a 15m bar... modify existing cyto files rather than recreate... Cyto becomes the instance database."

1. Seed (Intent)
Objective: Refactor the existing apex_cyto.db and schema to serve as the Simulation Intelligence Layer.

The Geometry:

Time (Theta Slot): 0 to 287. (1 Slot = 15 Minutes).

Cycle: 72 Hours (3 Days).

Performance (Radius): 0.618 to 1.618 (Percentile).

Identity (Z-Layer): Instance ID.

Specifics:

Update cyto_schema.py to enforce the 288-slot limit.

Repurpose the nodes table: theta_slot becomes the Bar Index. y_level / radius becomes the Score.

2. Related (Context)
cyto_v2.db (Existing Schema provided).

init2.py (The Loop).

virtual_broker.py (The Source).

4. Foundation (Structure)
Files to be modified:

EXISTING: database/cyto_schema.py (or creating the adapter for cyto_v2.db)

Table nodes Refactor:

theta_slot: CHECK(theta_slot >= 0 AND theta_slot < 288) (Was 360).

radius (New Column): FLOAT (Replacing or mapping to y_level?). Decision: Add radius column for precision, keep y_level for discrete UI rings.

raw_data (JSON): Stores the OHLCV + Sentiment Snapshot.

NEW: database/cyto_manager.py

calc_slot(timestamp): (Total_Minutes / 15) % 288.

store_trade_node(...): Inserts into the nodes table.

8. Infinity (Patterns)
Pattern: Discrete Harmony. The database stores Integers (Slots), the UI renders Angles (Slot * 1.25°). This separates Data concern from Display concern.

Pattern: Reuse. We use the existing cyto.db structure (id, w_layer, theta_slot) but change the semantic meaning of the data inside it.

7. Evolution (Real-Time Log)
[ ] [Refactored Schema to 288 Slots]

[ ] [Implemented Slot Calculation Math]

[ ] [Mapped PnL Percentiles to Radius]

Architecture Flow (The 288 Grid)
Code snippet
graph LR
    Time[Time: 12:15 PM] -->|Math| Slot[Slot: 49]
    PnL[PnL: Top 10%] -->|Math| Radius[Radius: 1.618]
    
    Slot & Radius --> Node{Node (49, 1.618)}
    Node -->|Insert| DB[(cyto_v2.db)]
    
    DB -->|Query| UI[CytoRadial]
    UI -->|Render| Angle[Rotate(61.25 deg)]
The Wake-Up Prompt (Seed 15A - Refactored)
Use this to modify your existing files instead of starting from scratch.

Plaintext
@SEEDS (INTENTIONS)/Structure – Seed 15A – The CytoBase.md
@cyto_v2.db (Schema Reference)
@init2.py

We are executing Seed 15A: "The CytoBase Refactor".

OBJECTIVE: Adapt the existing 'cyto.db' schema to store Trading Simulation Data on a 288-Axis Grid.

INSTRUCTIONS:
1. **Modify 'database/cyto_schema.py':**
   - We are pivoting from 360 degrees to **288 Slots** (matching 15m bars in 72h).
   - Update the `nodes` table definition:
     - `theta_slot`: INTEGER CHECK(theta_slot >= 0 AND theta_slot < 288).
     - Add `radius`: REAL (for precise percentile placement).
     - Add `instance_id`: TEXT (maps to z_slot/w_layer).
     - Add `vectors`: JSON (to store the 6 sentiment scores).

2. **Create 'database/cyto_manager.py':**
   - Implement `CytoManager`.
   - **Math:** - `SLOT_COUNT = 288`
     - `calc_slot(timestamp)`: `((timestamp - epoch).total_seconds() / 900) % 288` (900s = 15m).
   - **Visualization Math:**
     - The UI will calculate rotation as `slot * 1.25` degrees.

3. **Validation:**
   - Verify that the schema is compatible with the existing `cyto_v2.db` or create a migration script `migrate_cyto_v3.py` to add the new columns (`radius`, `vectors`) to the existing database.

Let's align the grid to the heartbeat.