# Seed 15BE – CytoBase Neomorphic Schema

---

**15BE**: [2026-02-11] – CytoBase: Neomorphic Radial Timepiece & Collapsible Control Panel ^seed-cytobase-neomorphic

## Context & Lineage

This seed **supersedes 15BD** (CytoBase UI Structure). The previous attempt created a disconnected React app with demo data, wrong color palette (purple/magenta), and a boxed layout that didn't match the Apex family. This is a ground-up visual schema redesign.

**Lineage:** 15A (Database Schema) → 15B (Console Redesign) → 15BD (UI Structure - incomplete) → **15BE (Definitive Visual Schema)**

**Reference Image:** Neomorphic concentric ring timepiece with depth created through CSS shadow layers, time markers on the outer perimeter with pin dots, sunken center disc. This is the visual DNA.

---

## 1. Seed (Intent)

Build the **definitive visual schema** for CytoBase — a full-screen neomorphic radial timepiece with a collapsible 4-quadrant control panel.

### Core Principles

1. **The Radial Database is the stage** — always full-screen, always in the background, never resizes
2. **Depth through shadow, not lines** — concentric rings are conveyed via neomorphic shading (inset/outset shadows), not drawn strokes
3. **The Control Panel floats on top** — collapsible from half-screen to a thin status bar
4. **Two accent colors only** — Mint Green (`#ADEBB3` / `#00ff9d`) and Teal Blue (`#20B2AA` / `#00f2ea`)
5. **Family resemblance** — Control Panel matches Intelligence Database's 4-quadrant neomorphic grid exactly

### Explicit Non-Goals (This Seed)
- NO data fetching or API connections
- NO CytoManager integration
- NO real sentiment/trade display
- NO torus particle engine (separate seed)

**Deliverable:** A beautiful empty shell — the neomorphic timepiece with 3 Fibonacci rings, 288 time slot markers, and a collapsible control panel with placeholder quadrants.

---

## 2. Related (Context)

- `15A` — CytoBase database schema (cyto_schema.py) — defines the 288 slots, Fibonacci bands, 72h epochs
- `15B` — Console redesign intent (teal/mint palette, neomorphic matte)
- `Seed 9 / Fruit Log` — 4-Quadrant Grid implementation for Intelligence Database (the template for our control panel)
- `static/css/databases_database_panels.css` — **THE** reference for quadrant styling
- `static/css/database.css` — Intelligence Database header/hero styling
- **Reference Image** — Neomorphic concentric ring timepiece (provided by Collin)

---

## 4. Foundation (Structure)

### Files to Create/Rewrite

```
templates/
  └── cytobase.html          ← FULL REWRITE — single self-contained file
                                 (HTML + CSS + JS, no React, no external deps)

No new CSS/JS files — everything inline for isolation until stable
```

### Architecture: Two Layers

```
┌─────────────────────────────────────────────────────────┐
│                    FULL VIEWPORT                         │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │          RADIAL DATABASE (Canvas)                │   │
│   │          Always full-screen                      │   │
│   │          position: fixed; inset: 0;              │   │
│   │                                                  │   │
│   │     ╭─── 1.618 ring (outer) ───╮                │   │
│   │     │  ╭── 1.000 ring ──╮      │                │   │
│   │     │  │  ╭ 0.618 ╮     │      │                │   │
│   │     │  │  │ CENTER │     │      │                │   │
│   │     │  │  ╰────────╯     │      │                │   │
│   │     │  ╰─────────────────╯      │                │   │
│   │     ╰───────────────────────────╯                │   │
│   │                                                  │   │
│   │   288 time markers on outer perimeter            │   │
│   │   24 major divisions (15° each)                  │   │
│   │   Pin dots at each major division                │   │
│   │   Timestamps rotated along perimeter             │   │
│   │                                                  │   │
│   └─────────────────────────────────────────────────┘   │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │       CONTROL PANEL (Floating, z-index: 100)     │   │
│   │       position: fixed; bottom: 0;                │   │
│   │       height: 50vh (expanded) or 40px (collapsed)│   │
│   │       border-radius: 16px 16px 0 0;             │   │
│   │       Neomorphic shadow styling                  │   │
│   │                                                  │   │
│   │   EXPANDED STATE:                                │   │
│   │   ┌──────────────┬──────────────┐                │   │
│   │   │  Q1: Class   │  Q2: Config  │                │   │
│   │   │  Browser     │  / Inspector │                │   │
│   │   ├──────────────┼──────────────┤                │   │
│   │   │  Q3: Instance│  Q4: Epoch   │                │   │
│   │   │  List        │  Navigator   │                │   │
│   │   └──────────────┴──────────────┘                │   │
│   │                                                  │   │
│   │   COLLAPSED STATE:                               │   │
│   │   ┌──────────────────────────────────────────┐   │   │
│   │   │ CYTOBASE │ Epoch: Live │ Nodes: 0 │ [▲]  │   │   │
│   │   └──────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. The Neomorphic Radial Timepiece

### Ring System (Shadow-Based Depth)

The rings are NOT drawn as strokes. They are **concentric CSS/Canvas shadow layers** that create the illusion of depth — like the reference image where each ring feels *pressed into* the surface.

```
RING STRUCTURE (outside → inside):

Outer Border Ring ──── Thin bright accent (teal, 0.3 opacity)
                 ╲
1.618 Band ─────── Shadow valley between 1.618 and 1.0
                 ╲     (dark inset shadow, matte black)
1.000 Band ─────── The median line — subtle teal glow
                 ╲     (only accent-colored ring)
0.618 Band ─────── Shadow valley between 1.0 and 0.618  
                 ╲     (deeper inset, darker)
Center Disc ────── Sunken circle (deepest shadow)
                    Epoch indicator lives here
```

### Shadow Recipe (CSS for each concentric step)
```css
/* Neomorphic depth — each ring is a div or canvas layer */
/* Outer shell */
box-shadow: 
    12px 12px 24px rgba(0, 0, 0, 0.8),     /* dark outer */
    -12px -12px 24px rgba(40, 44, 52, 0.3), /* light outer */
    inset 6px 6px 12px rgba(0, 0, 0, 0.6),  /* dark inner */
    inset -6px -6px 12px rgba(40, 44, 52, 0.15); /* light inner */
```

### Perimeter Time Markers

Following the reference image aesthetic:
- **288 minor tick marks** — tiny dots/dashes along the outer ring perimeter
- **24 major divisions** — larger pin dots every 15° (every 12 slots = 3 hours)
- **Timestamps at major divisions** — rotated text following the circle curvature
- **Format:** Date at top (`FEB 11, 2026`), time at other positions (`03:00 PM`)
- **Styling:** Mint green text, small caps, JetBrains Mono

### Center Disc

- Deepest neomorphic inset
- Displays: Epoch status (`LIVE` / `EPOCH 47`)
- Subtle teal ring around the disc edge (the 0.618 marker glow)

---

## 5. Senses (UX/DX)

### Color Palette (STRICT — Two Accents Only)

```css
/* Backgrounds */
--cyto-bg-deep:     #0a0b0d;    /* Deepest shadow */
--cyto-bg-core:     #12141a;    /* Main background */
--cyto-bg-surface:  #1a1d24;    /* Raised surfaces */
--cyto-bg-elevated: #22262f;    /* Control panel bg */

/* Accent Colors — ONLY THESE TWO */
--cyto-mint:        #ADEBB3;    /* Profit / Growth / Active */
--cyto-mint-bright: #00ff9d;    /* Hover / Emphasis */
--cyto-teal:        #20B2AA;    /* Data / Structure / Lines */
--cyto-teal-bright: #00f2ea;    /* Interactive / Selected */

/* Text */
--cyto-text-primary:   #F2F4F7;
--cyto-text-secondary: #A4A9B3;
--cyto-text-dim:       #6B7280;

/* Neomorphic Shadows */
--cyto-shadow-dark:  rgba(0, 0, 0, 0.7);
--cyto-shadow-light: rgba(40, 44, 52, 0.2);
```

**BANNED COLORS:** No purple, no magenta, no gold, no coral, no blue (#6B8DD6). Only mint and teal.

### Typography
- **Headers:** Inter, 600 weight, uppercase, letter-spacing 1px
- **Data/Mono:** JetBrains Mono, 400 weight
- **Perimeter text:** JetBrains Mono, 10px, mint green

### Neomorphism Rules
- Every panel: `border-radius: 12px` minimum
- Every raised surface: dual shadow (dark bottom-right, light top-left)
- Every inset surface: inverted shadow (dark top-left, light bottom-right)
- NO flat borders — depth comes from shadow, not from `border: 1px solid`
- Subtle `rgba(255,255,255,0.03)` top highlight on raised elements

---

## 6. Control Panel Specification

### Layout: Exact Match to Intelligence Database Quadrant Grid

```css
/* Reuse the EXACT pattern from databases_database_panels.css */
.cyto-quadrant-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    height: 100%;
    padding: 8px;
}

.cyto-quadrant {
    background: rgba(22, 24, 28, 0.95);
    border-radius: 12px;
    box-shadow: 
        0 4px 12px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
```

### Quadrant Assignments

| Quadrant | Purpose | Placeholder Content |
|----------|---------|-------------------|
| Q1 (Top-Left) | **Class Browser** | Asset class tabs (ALL, BTC, OIL, GOLD, US100, US30, US500) + instance list |
| Q2 (Top-Right) | **Config / Inspector** | NODES, LAYERS, CONFIG tabs + epoch/cycle info |
| Q3 (Bottom-Left) | **Instance Manager** | New instance input, active count, class/instance/active stats |
| Q4 (Bottom-Right) | **Epoch Navigator** | Prev/Next epoch, timeline scrubber, time window selector (24H, 72H, 1W, ALL) |

### Collapse/Expand Behavior

```
EXPANDED (default):
┌────────────────────────────────────────────────┐
│  ── drag handle ──                     [▼]     │  ← 4px rounded bar handle
├────────────────────┬───────────────────────────┤
│  Q1: Class Browser │  Q2: Config / Inspector   │
├────────────────────┼───────────────────────────┤
│  Q3: Instance Mgr  │  Q4: Epoch Navigator      │
└────────────────────┴───────────────────────────┘
Height: 50vh | Transition: 300ms ease

COLLAPSED:
┌────────────────────────────────────────────────┐
│ CYTOBASE  ▏—  0  —  │  Epoch: Live  │ Nodes 0 │  ← 40px bar
└────────────────────────────────────────────────┘
Height: 40px | Shows: title, dash stats, epoch, node count
Click anywhere or [▲] to expand
```

### The Bar (Collapsed State)

Matches the current bottom bar from the screenshot:
```
CYTOBASE  ▏—  0  —  Nodes 0                    [▲]
```
- Left: "CYTOBASE" in Inter 600, teal
- Middle: Key stats (instances, progress, nodes) in mono, dim
- Right: Expand chevron
- Background: `--cyto-bg-elevated` with neomorphic top shadow

---

## 7. Evolution (Real-Time Log)

### Phase 1: Canvas Radial Timepiece
- [x] Create `<canvas>` element, position: fixed, full viewport ✅ 2026-02-11
- [x] Draw neomorphic ring shadows (0.618, 1.0, 1.618) ✅ 2026-02-11
- [x] Implement shadow-based depth (not stroke-based) ✅ 2026-02-11
- [x] Draw center disc with deepest inset shadow ✅ 2026-02-11
- [x] Add 24 major division pin dots on outer perimeter ✅ 2026-02-11
- [x] Add 288 minor tick marks ✅ 2026-02-11
- [x] Render rotated timestamps at major divisions ✅ 2026-02-11
- [x] Add subtle teal glow on 1.0 median ring ✅ 2026-02-11

### Phase 2: Collapsible Control Panel
- [x] Create floating panel div (position: fixed, bottom: 0) ✅ 2026-02-11
- [x] Implement 4-quadrant grid (exact match to Intelligence Database CSS) ✅ 2026-02-11
- [x] Add collapse/expand toggle with 300ms transition ✅ 2026-02-11
- [x] Collapsed bar with CYTOBASE title + stats ✅ 2026-02-11
- [x] Drag handle at top of expanded panel ✅ 2026-02-11
- [x] Rounded top corners (border-radius: 16px 16px 0 0) ✅ 2026-02-11

### Phase 3: Quadrant Placeholders
- [x] Q1: Asset class tabs + "No instances" empty state ✅ 2026-02-11
- [x] Q2: NODES / LAYERS / CONFIG tab group + placeholder content ✅ 2026-02-11
- [x] Q3: New instance input + stats counters ✅ 2026-02-11
- [x] Q4: Time window buttons (24H, 72H, 1W, ALL) + epoch label ✅ 2026-02-11

### Phase 4: Polish
- [x] Verify no banned colors (purple, gold, magenta, coral) ✅ 2026-02-11
- [x] Test collapse/expand animation smoothness ✅ 2026-02-11
- [x] Ensure radial database stays fixed behind panel ✅ 2026-02-11
- [x] Header bar with clock, epoch status, class indicator ✅ 2026-02-11
- [ ] Responsive check (the radial should scale to viewport) — needs visual QA

---

## 8. Infinity (Patterns)

### Pattern: The Timepiece
The CytoBase radial is not a chart — it's a **clock face**. Time flows around the perimeter. Depth (performance) flows inward/outward. This metaphor must be preserved in every design decision.

### Pattern: Shadow as Data
In the neomorphic system, depth = meaning. The deeper an element is inset, the more "foundational" it is. The center disc is the deepest because it represents the epoch — the anchor of all data in the view.

### Pattern: The Family
CytoBase's control panel MUST look like a sibling of the Intelligence Database panel. Same grid, same shadows, same border-radius, same spacing. Different content, same skeleton.

### Debt to Avoid
- ❌ Drawing rings as SVG/Canvas strokes — use shadow-based depth
- ❌ Using React/Babel for this page — keep it vanilla JS for performance
- ❌ Hardcoding colors — use CSS custom properties throughout
- ❌ Making the radial a fixed-size box — it fills the viewport

---

## 9. Wake-Up Prompt

```
@SEEDS/Seed 15BE – CytoBase Neomorphic Schema.md
@#Cyto/cyto_schema.py
@static/css/databases_database_panels.css

Execute Seed 15BE: Build the CytoBase Neomorphic Radial Timepiece.

CONTEXT:
- templates/cytobase.html exists but needs FULL REWRITE
- The radial database is a neomorphic timepiece (reference image provided)
- Rings at 0.618, 1.0, 1.618 are depth layers via CSS shadows, NOT drawn lines
- Control panel matches Intelligence Database quadrant grid exactly
- Only two accent colors: Mint Green (#ADEBB3) and Teal Blue (#20B2AA)
- No React, no Babel — vanilla HTML/CSS/JS with Canvas

INSTRUCTIONS:
1. Rewrite templates/cytobase.html with:
   a. Full-viewport Canvas radial timepiece
      - 3 concentric shadow rings (Fibonacci bands)
      - Shadow-based depth between rings (neomorphic inset/outset)
      - 288 minor tick marks on outer perimeter
      - 24 major pin dots with rotated timestamps
      - Sunken center disc for epoch indicator
   b. Floating collapsible control panel
      - 4-quadrant grid matching databases_database_panels.css
      - Collapse to 40px status bar / expand to 50vh
      - Smooth 300ms transition
      - Top border-radius: 16px
   c. Header bar with live clock + epoch status

2. COLOR RULES:
   - Accents: ONLY mint (#ADEBB3, #00ff9d) and teal (#20B2AA, #00f2ea)
   - Backgrounds: #0a0b0d, #12141a, #1a1d24, #22262f
   - NO purple, gold, magenta, coral, blue

3. DO NOT:
   - Use React or Babel
   - Add demo/fake data
   - Connect to APIs
   - Import external JS libraries (except fonts)

4. The result should be:
   - A full-screen neomorphic radial timepiece
   - With shadow-based depth rings (not stroke lines)
   - A collapsible control panel floating on top
   - An empty shell ready for Seed 15BF (data integration)
```

---

## 10. Success Criteria

**Visual Test:**
1. Open /cytobase in browser
2. See full-viewport neomorphic radial timepiece
3. See 3 depth rings created by shadow, not by drawn circles
4. See 24 pin dots with rotated timestamps on perimeter
5. See sunken center disc with "LIVE" epoch label
6. See control panel at bottom with 4 quadrants
7. Click collapse → panel shrinks to thin status bar
8. Click expand → panel returns to 50vh with quadrant grid
9. Radial database remains full-screen behind panel at all times

**Color Test:**
- Grep the file for any hex outside the approved palette
- Zero instances of purple, gold, magenta, coral, or non-teal blue

**Performance Test:**
- No React, no Babel, no heavy libs
- Canvas renders smoothly at 60fps
- Collapse/expand animation is 300ms, no jank

---

*The timepiece doesn't show data — it shows where data will live. Structure before substance. Shadow before light.*
