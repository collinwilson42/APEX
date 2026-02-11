# Structure – Seed 15C – The Apex Lab Workbench (Dual-Panel UI)

---

15C: 2026-02-03 – The Lab Workbench: Dynamic Split-Screen & Node Graph Explorer ^seed-structure-lab-ui

## Prompts & Execution
"Dynamic adjustable bottom half... Right half is Gemini Pro API... Left can be assigned to relevant display... Default base screen is a tree node explorer... Visually displaying progression of simulations... Apex colors."

## 1. Seed (Intent)
- **Objective:** Transformation of the bottom UI into a **Split-Pane Workbench**.
- **Right Panel (The Brain):** A Chat Interface connected to Gemini Pro (`cyto_agent`).
- **Left Panel (The Workspace):** A dynamic container.
    - **Default View:** A **Force-Directed Graph** (Node Explorer) visualizing the "Family Tree" of your simulations and configs.
    - **Swappable Views:** Can dynamically load the JSON Editor, Profile Analysis, or Log View based on context.
- **Visuals:** Apex Theme (Teal/Mint Nodes on Matte Black).

## 2. Related (Context)
- `cyto_v2.db` (Data Source for the Graph).
- `apex.html` (The Container).
- `static/js/cyto_visualizer.js` (Existing Logic).

## 4. Foundation (Structure)
*Files to be created/modified:*
- **Library:** Download/Include `vis-network.min.js` (Lightweight, powerful graph visualizer).
- **Layout:** `templates/apex.html`
    - Create `#workbench-container` (Flexbox row).
    - `#workbench-left` (The Dynamic Stage).
    - `#workbench-right` (The AI Chat).
- **Graph Logic:** `static/js/apex_graph.js`
    - `renderSimulationTree(data)`: Draws Nodes (Sims) and Edges (Parent Config -> Child Config).
    - `onNodeClick(id)`: Context switches the Right Panel or opens details.
- **Chat Logic:** `static/js/apex_chat.js`
    - Connects to `/api/gemini/chat`.
    - Handles "Tool Calls" (e.g., AI says "Opening JSON Editor" -> Left Panel changes).

## 8. Infinity (Patterns)
- **Pattern:** **The Lineage.** We don't just list files; we show *evolution*.
    - Node A (Parent) -> Node B (Fork) -> Node C (Winner).
- **Pattern:** **Context Awareness.** The AI (Right) can "see" what is in the Left panel and manipulate it.

## 5. Senses (UX/DX)
- **Visuals:**
    - **Nodes:** Matte Black circles with Neon Teal borders.
    - **Edges:** Thin Grey lines (lineage).
    - **Active Node:** Glowing Mint Green.
    - **Background:** Deep Grid (Subtle).
- **Interaction:** Drag nodes, zoom in/out, click to expand.

## Architecture Flow (The Workbench)
```mermaid
graph TD
    User[User] -->|Asks: "Compare Sim A and B"| Chat[Right Panel: AI]
    Chat -->|Command: Load Graph| UI[Left Panel: Graph View]
    
    DB[(CytoBase)] -->|Query Lineage| Graph[Vis.js Network]
    Graph -->|Render| Visual[Tree: Sim A -> Sim B]
    
    User -->|Click Node B| Graph
    Graph -->|Event| Chat
    Chat -->|Response| "Sim B had 20% higher ROI..."
The Wake-Up Prompt (Seed 15C)
Paste this to Claude to build the Workbench.

Plaintext
@SEEDS (INTENTIONS)/Structure – Seed 15C – The Apex Lab Workbench.md
@templates/apex.html
@static/css/apex_relativity.css

We are executing Seed 15C: "The Lab Workbench".

OBJECTIVE: Redesign the bottom half into a Dynamic Split-Pane with a Node Graph Explorer.

INSTRUCTIONS:
1. **The Layout (HTML/CSS):**
   - In 'apex.html', replace the existing bottom panel with a split container `#workbench-container`.
   - **Left Panel (#workbench-left):** Default content is `<div id="sim-tree-graph"></div>`.
   - **Right Panel (#workbench-right):** A Chat Interface (Input + Log) styled in Apex Colors.
   - Use 'vis-network.js' (via CDN) for the graph.

2. **The Graph Visualizer (JS):**
   - Create 'static/js/apex_graph.js'.
   - Implement `initGraph()` using `vis.Network`.
   - **Style:** Nodes = Teal/Mint dots. Edges = Grey lines. Background = Transparent/Matte.
   - **Mock Data:** Create a dummy tree for now:
     - "Master Profile" -> "Sim Run 1"
     - "Master Profile" -> "Sim Run 2" -> "Sim Run 2.1 (Optimized)"

3. **The Chat Interface (JS):**
   - Create 'static/js/apex_chat.js'.
   - Simple logic to append user messages to the log.
   - (We will wire the Gemini API in the next step, just build the UI now).

4. **The "Dynamic View" Logic:**
   - Add a global function `setWorkbenchView(viewName)` that can swap the inner HTML of `#workbench-left` (e.g., from Graph to a placeholder for "JSON Editor").

Let's build the Command Center