# METATRON RADIAL DATABASE - Recovery & Development Phases

## Overview
The **Radial Time-Capsule Database** is a 4D coordinate system for organizing development nodes using Fibonacci ring geometry with a Metatron arm for navigation and filtering.

---

## PHASE 1: 4D COORDINATE SYSTEM

| Axis | Name | Description | Range |
|------|------|-------------|-------|
| **X** | Theta (θ) | Angular position based on timestamp | 0-360° (12-hour clock) |
| **Y** | Radius (r) | Ring zone position | 0.382 → 1.000 |
| **Z** | Depth | Ring-specific (siblings OR insights) | Integer index |
| **W** | Layer | Temporal stack index | 12-increment scale |

---

## PHASE 2: FIBONACCI RING STRUCTURE

```
                     OUTER PERIMETER (r = 1.000)
                   ╱                              ╲
                 ╱    SYNC NODES                    ╲
               ╱      (Tree expansion)               ╲
             ╱                                        ╲
           ╱━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╲  r = 0.618 GOLDEN LINE
          │                                            │
          │        CODE NODE PAIRS (r = 0.500)         │
          │                                            │
          │     UNIFIED MODULES (r = 0.382)            │
           ╲                                          ╱
             ╲        CENTER (r = 0)                ╱
               ╲____________________________________╱
```

### Ring Ratios
- **1.000** - Sync Nodes (Outer perimeter)
- **0.618** - Golden Line (Tree root anchors)
- **0.500** - Code Node Pairs
- **0.382** - Unified Modules

---

## PHASE 3: FULL SYNC NODE LIST (r = 1.000)

### Tree 1.x - System Foundation
| ID | Title | θ | W | Status |
|----|-------|---|---|--------|
| 1.0 | System Foundation | 0° | 0 | active |
| 1.1 | Core Architecture | 15° | 0 | active |
| 1.11 | Database Layer | 22.5° | 0 | active |

### Tree 6.x - UI/UX Foundation
| ID | Title | θ | W | Status |
|----|-------|---|---|--------|
| 6.0 | UI/UX Foundation | 180° | 0 | active |
| 6.1 | Neumorphic System | 187.5° | 0 | active |
| 6.2 | Component Library | 195° | 0 | active |
| 6.3 | Chart Components | 202.5° | 0 | active |
| 6.4 | Control Panels | 210° | 0 | active |
| 6.5 | Navigation System | 217.5° | 0 | active |
| 6.6 | Instance Types | 225° | 0 | active |
| 6.7 | Tab System | 232.5° | 0 | active |

### Tree 7.x - Radial Database
| ID | Title | θ | W | Status |
|----|-------|---|---|--------|
| 7.0 | Radial Database Root | 90° | 0 | active |
| 7.1 | Position Calculator | 97.5° | 0 | active |
| 7.10 | 4D Coordinate Engine | 105° | 0 | active |
| 7.11 | Theta Calculation | 112.5° | 0 | active |
| 7.12 | Radius Mapping | 120° | 0 | active |
| 7.13 | Z-Depth Logic | 127.5° | 0 | active |
| 7.14 | W-Scale Config | 135° | 0 | active |
| 7.15 | Fan Positioning | 142.5° | 0 | active |
| 7.16 | Collision Avoidance | 150° | 0 | active |
| 7.17 | Batch Processing | 157.5° | 0 | active |

### Tree 8.x - UI Architecture
| ID | Title | θ | W | Status |
|----|-------|---|---|--------|
| 8.0 | UI Architecture | 45° | 0 | active |
| 8.1 | Control Panel System | 52.5° | 0 | active |
| 8.2 | Radial Visualization | 60° | 0 | active |

### Tree 9.x - Python Integration
| ID | Title | θ | W | Status |
|----|-------|---|---|--------|
| 9.0 | Python Integration | 270° | 0 | active |
| 9.1 | Flask API Layer | 277.5° | 0 | active |
| 9.2 | Blueprint System | 285° | 0 | active |

### Tree 10.x - Database Schema
| ID | Title | θ | W | Status |
|----|-------|---|---|--------|
| 10.0 | Database Schema | 315° | 1 | superseded |
| 10.1 | Node Storage | 322.5° | 0 | active |

---

## PHASE 4: INTEGRATION NODES

### Code Nodes (r = 0.500)
| ID | Title | θ | Parent | Status |
|----|-------|---|--------|--------|
| CN-7.1 | position_calculator.py | 97.5° | 7.1 | active |
| CN-7.10 | coordinate_engine.py | 105° | 7.10 | pending |
| CN-8.1 | ControlPanel.jsx | 52.5° | 8.1 | pending |
| CN-8.2 | RadialDatabase.jsx | 60° | 8.2 | active |
| CN-9.2 | radial_api.py | 285° | 9.2 | active |

### Unified Modules (r = 0.382)
| ID | Title | θ | Parent | Status |
|----|-------|---|--------|--------|
| UM-7.1 | radial_core | 97.5° | CN-7.1 | pending |
| UM-9.0 | flask_integration | 270° | 9.0 | pending |

---

## PHASE 5: QUADRANT LAYOUT (Target)

```
┌─────────────────────────────────────────────────────────────┐
│                      METATRON HEADER                        │
│   [APEX Logo] ▼ Radial Database    [θ slider] [⌀ slider]   │
├────────────────────────┬────────────────────────────────────┤
│                        │                                    │
│    TOP-LEFT QUADRANT   │    TOP-RIGHT QUADRANT             │
│    (Future: Radial     │    (Future: Node Details          │
│     Visualization)     │     / Insights Panel)             │
│                        │                                    │
├────────────────────────┼────────────────────────────────────┤
│                        │                                    │
│  BOTTOM-LEFT: SYNC     │  BOTTOM-RIGHT: INTEGRATION        │
│  (Outer layer nodes)   │  (Code nodes + Modules)           │
│  r = 1.000             │  r = 0.500 + 0.382                │
│                        │                                    │
└────────────────────────┴────────────────────────────────────┘
```

### Current Implementation (Bottom Hemisphere Only)
- **SYNC Panel (Left)**: Shows nodes at r = 1.000, filtered by arm
- **INTEGRATION Panel (Right)**: Shows code nodes + modules

---

## PHASE 6: COLOR SYSTEM

| Name | Hex | Usage |
|------|-----|-------|
| **Mint** | #ADEBB3 | Sync nodes, active status |
| **Teal** | #20B2AA | Golden line, zone tags |
| **Blue** | #6B8DD6 | Integration panel, code nodes |
| **Magenta** | #C084FC | Metatron arm, W-layer tags |
| **Golden** | #D4AF37 | Insights, parent tethers |

---

## PHASE 7: FILES STATUS

| File | Status |
|------|--------|
| `init2.py` | ✅ Has /metatron route |
| `static/img/apex_logo.png` | 🔲 Need to copy |
| `templates/metatron_radial.html` | 🔲 Rebuild with full nodes |
| `radial_db/position_calculator.py` | 🔲 To be created |
| `radial_db/radial_api.py` | 🔲 To be created |
