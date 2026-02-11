# Structure – Seed 15B – Cyto Visualization & Interface

---

15B: 2026-02-03 – The Cyto Console: Redesign, Navigation & Filtering ^seed-structure-cyto-ui

## Prompts & Execution
"Maximize manual filtering and sorting... Redesign removing purple/gold... Teal blue and Mint green... Matte black shadowing... View database in instances... Replace Metatron tab."

## 1. Seed (Intent)
- **Objective:** Build the **Cyto Intelligence Console**—a fully interactive UI for navigating the 72-Hour Epochs stored in the CytoBase.
- **Visuals:** Rebrand to "Apex Aesthetics" (Teal/Mint/Matte).
- **Navigation:** Default view = *Current Epoch*. Add "Previous/Next Epoch" controls.
- **Filtering:** Manual controls to Toggle Z-Layers (Instances) and Switch Metrics (PnL vs Sentiment).

## 2. Related (Context)
- `cyto_v2.db` (The Source).
- `apex.html` (The Shell).
- `static/css/apex_relativity.css` (The Design Language).

## 4. Foundation (Structure)
*Files to be created/modified:*
- **Style:** `static/css/cyto.css`
    - Replace Purple/Gold variables with `--apex-teal` and `--apex-mint`.
    - Add "Neumorphic Matte" shadow classes.
- **Logic:** `static/js/cyto_visualizer.js`
    - `loadEpoch(cycle_id)`: Fetches only the 288 slots for that specific 72h window.
    - `renderRadial(nodes)`: Draws the 288-slot grid.
    - `filterLayers(active_layers)`: Hides/Shows specific Z-instances.
- **Backend:** `cyto_manager.py` (API)
    - `get_epoch_data(cycle_id)`: Returns filtered JSON for the frontend.
- **Structure:** `templates/apex.html`
    - Rename tab `#metatron` to `#cyto`.
    - Add "Epoch Control" widget (Prev/Next buttons).

## 8. Infinity (Patterns)
- **Pattern:** **The Slice.** We never show the whole database. We show *Time Slices* (Epochs). This keeps the UI fast and the mind focused.
- **Pattern:** **Consistency.** Cyto is not a separate app; it is a *View* of the Apex system. It must look exactly like the Trading Console.

## 7. Evolution (Real-Time Log)
- [ ] [Replaced Metatron Tab with Cyto]
- [ ] [Applied Apex Teal/Mint Color Scheme]
- [ ] [Implemented "Current Epoch" Loader]
- [ ] [Added Manual Z-Layer Toggles]

## 5. Senses (UX/DX)
- **Depth:** The "Matte Black" shadows should make the active layer pop out, while inactive layers recede.
- **Clarity:** "Olo/Mint Green" represents *Profit/Growth*. "Teal Blue" represents *Data/Structure*.

## Architecture Flow (The View)
```mermaid
graph TD
    User[User: Click 'Next Epoch'] -->|Request| API[Cyto API]
    API -->|Query (Cycle ID: 50)| DB[(CytoBase)]
    DB -->|Return 288 Slots| UI[Cyto Visualizer]
    
    UI -->|Render| Grid[Radial Grid]
    User -->|Toggle| Filter[Filter: Hide 'Gold']
    Filter -->|Update| Grid
The Wake-Up Prompt (Seed 15C)
Paste this to Claude to build the Interface.

Plaintext
@SEEDS (INTENTIONS)/Structure – Seed 15C – Cyto Visualization.md
@static/css/cyto.css
@static/js/cyto_visualizer.js
@templates/apex.html

We are executing Seed 15C: "The Cyto Console".

OBJECTIVE: Build the Visualization Layer with the new Apex Branding and Manual Filtering.

INSTRUCTIONS:
1. **The Rebranding (CSS):**
   - Update 'cyto.css'.
   - **Palette:** - Background: Dark Matte (#1e1e1e / #121212).
     - Accents: Neon Teal (#00f2ea), Mint Green (#00ff9d).
     - Shadows: Deep Matte Black (`box-shadow: 10px 10px 20px #0b0b0b, -10px -10px 20px #252525`).
   - Remove all references to "Cosmic Purple" or "Gold".

2. **The Integration (HTML):**
   - In 'apex.html', find the "Metatron" navigation item and container.
   - Rename it to **Cyto**.
   - Add a **Control Bar** inside the Cyto panel:
     - `<button id="prev-epoch"> < </button>`
     - `<span id="current-epoch-label">Epoch: Live</span>`
     - `<button id="next-epoch"> > </button>`
     - `<div id="layer-toggles"></div>` (For manual filtering).

3. **The Logic (JS):**
   - In 'cyto_visualizer.js', implement `fetchEpoch(cycle_index)`.
   - It should call the API endpoint (we'll assume '/api/cyto/epoch/<id>' exists).
   - Implement `renderRadial(data)` using the 288-slot logic (1.25 degrees per slot).
   - Implement `toggleLayer(instance_id)` to hide/show specific Z-Layers without reloading data.

Let's make it look like part of the family.