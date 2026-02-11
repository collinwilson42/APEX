# Seed 15BD – CytoBase UI Structure (No Data)

---

**15BD**: [2026-02-04] – CytoBase Intelligence Console: UI Structure First ^seed-cytobase-ui

## Context from 15BC

We attempted Phase 1 (Rename & Extract) but created a disconnected UI. The cytobase.html file was created with demo data that doesn't reflect the actual Cyto architecture. This seed focuses on **structure only** - no data flow yet.

---

## 1. Seed (Intent)

Build the **visual scaffold** for CytoBase inside Apex:
1. Replace Metatron view content with CytoBase structure
2. Create the 288-slot radial grid (empty placeholders)
3. Position torus engine as overhead particle layer
4. Recycle matte grey control panel structure
5. Enable fullscreen toggle per section

**Explicit Non-Goals:**
- NO data fetching
- NO CytoManager integration  
- NO real sentiment/trade display
- NO API connections

**Deliverable:** A beautiful empty shell that shows WHERE data will go.

---

## 2. Architecture Reference

### CytoBase Database Schema (from cyto_schema.py)

```
cyto_instances     → Simulation runs (instance_id, symbol, profile_name, status)
cyto_nodes         → 288-slot bars (theta_slot 0-287, sentiment vectors, trades)
cyto_trades        → Trade details linked to nodes
cyto_epochs        → Pre-computed 72h cycle metadata
```

**Key Constants:**
```python
SLOT_COUNT = 288        # 72 hours / 15 minutes = 288 bars
SLOT_MINUTES = 15
CYCLE_HOURS = 72
RADIUS_FLOOR = 0.618    # Inner ring (losers)
RADIUS_MEDIAN = 1.000   # Middle ring
RADIUS_CEILING = 1.618  # Outer ring (winners)
```

### Visual Encoding (Future - NOT this seed)

| Property | Data Source | Visual Representation |
|----------|-------------|----------------------|
| Position (θ) | theta_slot (0-287) | Angle on radial grid |
| Position (r) | pnl_normalized | Fibonacci ring band |
| Size | weighted_final magnitude | 4px - 16px diameter |
| Hue | trade_direction | Teal (bull) / Coral (bear) / Grey (neutral) |
| Saturation | agreement_score | Muted → Vivid |
| Glow | has_trade | Mint ring if true |

---

## 3. UI Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  APEX TAB BAR  [ Gold F... | Crude O... | Radial ... ]              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                         VIEW PANEL (iframe)                         │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │   LAYER 3: Torus Particles (overhead, semi-transparent)       │ │
│  │   ═══════════════════════════════════════════════════════════ │ │
│  │                                                               │ │
│  │   LAYER 2: 288-Slot Radial Grid                               │ │
│  │            - 3 Fibonacci rings (0.618, 1.0, 1.618)            │ │
│  │            - Slot markers every 15° (24 visible divisions)    │ │
│  │            - Empty node placeholders                          │ │
│  │   ═══════════════════════════════════════════════════════════ │ │
│  │                                                               │ │
│  │   LAYER 1: Dark radial background                             │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                      CONTROL CENTER (bottom)                        │
│                                                                     │
│  ┌─────────────────────────────┬─────────────────────────────────┐ │
│  │  ● INTELLIGENCE DATABASE    │                                 │ │
│  │  Radial Database            │   (Reserved for Inspector)      │ │
│  │                             │                                 │ │
│  │  ● CYTOBASE RADIAL DATABASE │   - Node details               │ │
│  │                             │   - Sentiment radar chart       │ │
│  │  [Instance Filter Dropdown] │   - Trade P/L if applicable    │ │
│  │                             │                                 │ │
│  │  Epoch: ◀ [Live] ▶          │                                 │ │
│  │                             │                                 │ │
│  └─────────────────────────────┴─────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. File Structure

### Current State (broken)
```
templates/
  ├── cytobase.html      ← Created but has wrong demo data
  └── metatron_radial.html ← Original (preserved)

init2.py
  └── /metatron route → now serves cytobase.html (changed)

static/js/apex_views.js
  └── renderMetatronView() → loads /cytobase iframe (changed)
```

### Target State (this seed)
```
templates/
  └── cytobase.html      ← REWRITE with correct structure:
                            - 288-slot radial grid (canvas/SVG)
                            - Torus engine overhead (Three.js)
                            - Control panel placeholders
                            - No demo data, just structure

init2.py
  └── /metatron, /cytobase → serve cytobase.html (keep as-is)

static/js/apex_views.js
  └── renderMetatronView() → loads /cytobase (keep as-is)
```

---

## 5. Radial Grid Specification

### Canvas/SVG Requirements

```javascript
// Grid constants (match cyto_schema.py)
const SLOT_COUNT = 288;
const RINGS = [
    { r: 0.618, label: 'Loss', color: '#FF6B6B33' },
    { r: 1.000, label: 'Break-even', color: '#6B8DD644' },
    { r: 1.618, label: 'Profit', color: '#00f2ea44' }
];

// Visual grid
const VISIBLE_DIVISIONS = 24;  // Every 15° (360° / 24 = 15°)
const SLOT_ANGLE = 360 / SLOT_COUNT;  // 1.25° per slot

// Center region
const CENTER_RADIUS = 0.4;  // Reserved for epoch indicator
```

### Draw Order (back to front)
1. **Background** - Dark radial gradient
2. **Rings** - Three Fibonacci circles (dashed lines)
3. **Radials** - 24 spoke lines from center to edge
4. **Slot Markers** - 288 tiny tick marks (optional, subtle)
5. **Epoch Indicator** - Center circle showing current cycle
6. **Torus Particles** - Overhead layer (Three.js canvas overlay)

---

## 6. Torus Engine Modifications

### Current (metatron_radial.html)
```javascript
camera.position.set(0, 4, 9);  // Above-front angle
torusGeometry(3, 0.9, 64, 128);  // Thick torus
torus.rotation.x = Math.PI / 5;  // Tilted
```

### Target (cytobase.html)
```javascript
camera.position.set(0, 15, 0);   // Directly overhead
camera.lookAt(0, 0, 0);
torusGeometry(4, 0.15, 32, 288); // Thin ring matching 288 slots
torus.rotation.x = Math.PI / 2;  // Flat (viewing from above)

// Particle flow follows the slot perimeter
// Golden particles = "now" indicator flowing around the ring
```

---

## 7. Control Panel Structure

### Left Side (Q3)
```html
<div class="control-panel-left">
    <!-- Header -->
    <div class="panel-label teal">● INTELLIGENCE DATABASE</div>
    <div class="panel-title">Radial Database</div>
    
    <!-- Menu Item -->
    <div class="menu-item">
        <span class="dot magenta">●</span>
        <span>CYTOBASE RADIAL DATABASE</span>
    </div>
    
    <!-- Instance Filter (placeholder) -->
    <div class="filter-section">
        <label>Instance</label>
        <select disabled>
            <option>All Instances</option>
        </select>
    </div>
    
    <!-- Epoch Navigation (placeholder) -->
    <div class="epoch-nav">
        <button disabled>◀</button>
        <span class="epoch-label">Epoch: Live</span>
        <button disabled>▶</button>
    </div>
</div>
```

### Right Side (Q4) - Reserved
```html
<div class="control-panel-right">
    <div class="panel-label">NODE INSPECTOR</div>
    <div class="placeholder-message">
        Select a node to inspect
    </div>
</div>
```

---

## 8. Execution Checklist

### Phase 1: Rewrite cytobase.html
- [ ] Remove all demo SYNC/INTEGRATION data
- [ ] Create radial grid canvas (288 slots, 3 rings)
- [ ] Add epoch center indicator
- [ ] Keep torus engine but modify camera to overhead
- [ ] Make torus semi-transparent (particles only, no solid mesh)
- [ ] Match bottom panel to screenshot structure

### Phase 2: Styling
- [ ] Dark radial background (#050608 center, #0a0b0d edge)
- [ ] Fibonacci rings with correct colors
- [ ] Subtle slot tick marks
- [ ] Control panel matches Apex matte grey aesthetic

### Phase 3: Placeholders
- [ ] Empty node array (will populate later)
- [ ] Disabled epoch navigation buttons
- [ ] Disabled instance filter dropdown
- [ ] "Select a node" placeholder in inspector

### Phase 4: Fullscreen Toggle
- [ ] Add fullscreen button to radial view header
- [ ] CSS for fullscreen mode (position: fixed; inset: 0)

---

## 9. Wake-Up Prompt

```
@SEEDS/Seed 15BD – CytoBase UI Structure.md
@#Cyto/cyto_schema.py

Execute Seed 15BD: Build the CytoBase UI structure WITHOUT any data.

CONTEXT:
- templates/cytobase.html exists but has wrong demo data
- We need to REWRITE it with the correct empty structure
- The torus engine should be overhead (camera directly above)
- The radial grid should show 288 slots and 3 Fibonacci rings
- Control panel should have placeholders matching the layout spec

INSTRUCTIONS:
1. Rewrite templates/cytobase.html with:
   - Radial grid canvas (288 slots, rings at 0.618, 1.0, 1.618)
   - Torus engine in overhead mode (camera at 0, 15, 0)
   - Torus particles semi-transparent as ambient layer
   - Bottom control panel with INTELLIGENCE DATABASE structure
   - Empty placeholders where data will go later

2. DO NOT:
   - Add any demo data
   - Connect to any APIs
   - Import CytoManager
   - Fetch from databases

3. The result should be a beautiful empty shell showing:
   - Where the 288 time slots will display
   - Where nodes will be placed on the radial grid
   - Where the epoch indicator lives (center)
   - How the torus particles flow overhead

This is structure only. Data flow comes in Seed 15BE.
```

---

## 10. Success Criteria

**Visual Test:**
1. Open Apex → Click METATRON tab
2. See empty radial grid with 3 visible rings
3. See 24 spoke lines dividing the circle
4. See torus particles flowing overhead (semi-transparent)
5. See "Epoch: Live" in control panel
6. See "Select a node to inspect" placeholder

**No Errors:**
- No 404s or "not found" messages
- No console errors about missing data
- Torus engine animates smoothly
- Fullscreen toggle works

---

*Structure before substance. The scaffold must be sound before we hang the data on it.*
