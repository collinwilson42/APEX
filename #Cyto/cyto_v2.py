"""
CYTO v2 - Continuity-Driven Development Database
Vertical 4-Quadrant Layout with Neumorphic Design
Mint Green + Deep Navy Color Scheme
"""

from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import threading
import time
import sqlite3
import os
import json
import math

# ============================================
# CONSTANTS
# ============================================

PHI = 1.618033988749895
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyto_v2.db")

# Development Zones (θ ranges)
ZONES = {
    'inception':   {'start': 0,   'end': 40,  'mid': 20,  'focus': 'Ideas & triggers'},
    'research':    {'start': 40,  'end': 80,  'mid': 60,  'focus': 'Investigation'},
    'planning':    {'start': 80,  'end': 120, 'mid': 100, 'focus': 'Design & decisions'},
    'foundation':  {'start': 120, 'end': 160, 'mid': 140, 'focus': 'Core implementation'},
    'building':    {'start': 160, 'end': 200, 'mid': 180, 'focus': 'Feature development'},
    'testing':     {'start': 200, 'end': 240, 'mid': 220, 'focus': 'Validation'},
    'integration': {'start': 240, 'end': 280, 'mid': 260, 'focus': 'Connecting pieces'},
    'review':      {'start': 280, 'end': 320, 'mid': 300, 'focus': 'Documentation'},
    'completion':  {'start': 320, 'end': 360, 'mid': 340, 'focus': 'Wrap-up'}
}

# Y-Level meanings for Sync nodes (outward: research/planning)
Y_SYNC = {
    0: {'digit': 1, 'name': 'observation', 'label': 'Observation', 'prompt': 'What was noticed?'},
    1: {'digit': 2, 'name': 'context',     'label': 'Context',     'prompt': 'What relates?'},
    2: {'digit': 4, 'name': 'structure',   'label': 'Structure',   'prompt': 'What constraints?'},
    3: {'digit': 5, 'name': 'exploration', 'label': 'Exploration', 'prompt': 'What options?'},
    4: {'digit': 7, 'name': 'insight',     'label': 'Insight',     'prompt': 'What pattern?'},
    5: {'digit': 8, 'name': 'decision',    'label': 'Decision',    'prompt': 'What was decided?'}
}

# Y-Level meanings for Integration nodes (inward: code/synthesis)
Y_INTEGRATION = {
    0: {'digit': 3, 'name': 'implementation', 'label': 'Implementation', 'prompt': 'What was built?'},
    1: {'digit': 6, 'name': 'validation',     'label': 'Validation',     'prompt': 'Does it work?'},
    2: {'digit': 9, 'name': 'completion',     'label': 'Completion',     'prompt': 'What learned?'}
}

TETHER_TYPES = ['derived', 'related', 'blocked_by', 'enables', 'supersedes', 'references']

# ============================================
# DATABASE
# ============================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            node_type       TEXT NOT NULL CHECK(node_type IN ('sync', 'integration')),
            w_layer         INTEGER NOT NULL DEFAULT 1,
            theta_slot      INTEGER NOT NULL CHECK(theta_slot >= 0 AND theta_slot < 360),
            y_level         INTEGER NOT NULL CHECK(y_level >= 0 AND y_level <= 5),
            z_slot          INTEGER NOT NULL DEFAULT 0 CHECK(z_slot >= 0 AND z_slot <= 9),
            title           TEXT NOT NULL,
            content         TEXT,
            parent_id       INTEGER,
            decision_id     INTEGER,
            zone            TEXT,
            y_meaning       TEXT,
            status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'superseded', 'abandoned', 'complete')),
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES nodes(id),
            FOREIGN KEY (decision_id) REFERENCES nodes(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tethers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id       INTEGER NOT NULL,
            target_id       INTEGER NOT NULL,
            tether_type     TEXT NOT NULL,
            weight          REAL DEFAULT 1.0,
            note            TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES nodes(id),
            FOREIGN KEY (target_id) REFERENCES nodes(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phases (
            w_layer         INTEGER PRIMARY KEY,
            name            TEXT NOT NULL,
            goal            TEXT,
            started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at    TIMESTAMP,
            status          TEXT DEFAULT 'active'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key             TEXT PRIMARY KEY,
            value           TEXT
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_w ON nodes(w_layer)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_zone ON nodes(zone)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id)")
    
    conn.commit()
    conn.close()
    print(f"✓ Database: {DB_PATH}")

def get_config(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def set_config(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# ============================================
# PHASE MANAGEMENT
# ============================================

def get_current_phase():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM phases WHERE status = 'active' ORDER BY w_layer DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_phase(name, goal=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(w_layer) FROM phases")
    row = cursor.fetchone()
    next_w = (row[0] or 0) + 1
    cursor.execute("""
        INSERT INTO phases (w_layer, name, goal, started_at, status)
        VALUES (?, ?, ?, ?, 'active')
    """, (next_w, name, goal, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"✓ Phase W{next_w}: {name}")
    return next_w

def get_all_phases():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM phases ORDER BY w_layer DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def set_active_phase(w_layer):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE phases SET status = 'inactive' WHERE status = 'active'")
    cursor.execute("UPDATE phases SET status = 'active' WHERE w_layer = ?", (w_layer,))
    conn.commit()
    conn.close()

# ============================================
# NODE MANAGEMENT
# ============================================

def theta_to_zone(theta):
    for name, z in ZONES.items():
        if z['start'] <= theta < z['end']:
            return name
    return 'inception'

def zone_to_theta(zone_name, offset=0):
    zone = ZONES.get(zone_name)
    return (zone['mid'] + offset) % 360 if zone else 0

def get_y_meaning(node_type, y_level):
    if node_type == 'sync':
        return Y_SYNC.get(y_level, {}).get('name', 'unknown')
    return Y_INTEGRATION.get(y_level, {}).get('name', 'unknown')

def create_node(node_type, title, content=None, zone=None, theta=None, y_level=0, z_slot=0,
                w_layer=None, parent_id=None, decision_id=None):
    if w_layer is None:
        phase = get_current_phase()
        w_layer = phase['w_layer'] if phase else 1
    
    if theta is not None:
        theta_slot = int(theta) % 360
        zone_name = theta_to_zone(theta_slot)
    elif zone is not None:
        theta_slot = zone_to_theta(zone)
        zone_name = zone
    else:
        theta_slot = 0
        zone_name = 'inception'
    
    y_meaning = get_y_meaning(node_type, y_level)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Auto-increment Z
    cursor.execute("""
        SELECT MAX(z_slot) FROM nodes 
        WHERE w_layer = ? AND theta_slot = ? AND y_level = ? AND node_type = ?
    """, (w_layer, theta_slot, y_level, node_type))
    row = cursor.fetchone()
    if row[0] is not None and z_slot == 0:
        z_slot = min(row[0] + 1, 9)
    
    cursor.execute("""
        INSERT INTO nodes (node_type, w_layer, theta_slot, y_level, z_slot, 
                          title, content, parent_id, decision_id, zone, y_meaning, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """, (node_type, w_layer, theta_slot, y_level, z_slot, 
          title, content, parent_id, decision_id, zone_name, y_meaning))
    
    node_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
    node = dict(cursor.fetchone())
    conn.close()
    
    print(f"✓ {node_type} #{node_id}: {title}")
    return node

def get_all_nodes(w_layer=None, zone=None, node_type=None, status='active'):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM nodes WHERE 1=1"
    params = []
    
    if w_layer is not None:
        query += " AND w_layer = ?"
        params.append(w_layer)
    if zone is not None:
        query += " AND zone = ?"
        params.append(zone)
    if node_type is not None:
        query += " AND node_type = ?"
        params.append(node_type)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    nodes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return nodes

def get_node(node_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def backtrack(node_id, max_depth=20):
    chain = []
    visited = set()
    current_id = node_id
    
    conn = get_connection()
    cursor = conn.cursor()
    
    while current_id and len(chain) < max_depth:
        if current_id in visited:
            break
        visited.add(current_id)
        
        cursor.execute("SELECT * FROM nodes WHERE id = ?", (current_id,))
        row = cursor.fetchone()
        if not row:
            break
        
        node = dict(row)
        chain.append(node)
        current_id = node.get('parent_id')
    
    conn.close()
    return list(reversed(chain))

def get_zone_summary(w_layer=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT zone, node_type, COUNT(*) as count FROM nodes WHERE status = 'active'"
    params = []
    if w_layer:
        query += " AND w_layer = ?"
        params.append(w_layer)
    query += " GROUP BY zone, node_type"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    summary = {}
    for row in rows:
        zone = row['zone'] or 'unknown'
        if zone not in summary:
            summary[zone] = {'sync': 0, 'integration': 0}
        summary[zone][row['node_type']] = row['count']
    return summary

def create_tether(source_id, target_id, tether_type, weight=1.0, note=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tethers (source_id, target_id, tether_type, weight, note)
        VALUES (?, ?, ?, ?, ?)
    """, (source_id, target_id, tether_type, weight, note))
    tether_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tether_id

def get_all_tethers(w_layer=None):
    conn = get_connection()
    cursor = conn.cursor()
    if w_layer:
        cursor.execute("""
            SELECT t.* FROM tethers t
            JOIN nodes n1 ON t.source_id = n1.id
            JOIN nodes n2 ON t.target_id = n2.id
            WHERE n1.w_layer = ? OR n2.w_layer = ?
        """, (w_layer, w_layer))
    else:
        cursor.execute("SELECT * FROM tethers")
    tethers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tethers

# ============================================
# ENGINE
# ============================================

class PhaseEngine:
    def __init__(self):
        self.current_theta = 20
        self.selected_theta = None
        self.selected_range = 40  # Degrees to show in 3D view
        
        if not get_current_phase():
            create_phase("Foundation", "Initial setup and core architecture")
    
    def get_state(self):
        phase = get_current_phase()
        w = phase['w_layer'] if phase else 1
        zone = theta_to_zone(self.current_theta)
        
        return {
            'w': w,
            'phase_name': phase['name'] if phase else 'Unknown',
            'phase_goal': phase.get('goal', '') if phase else '',
            'theta': self.current_theta,
            'zone': zone,
            'zone_focus': ZONES.get(zone, {}).get('focus', ''),
            'selected_theta': self.selected_theta,
            'selected_range': self.selected_range
        }
    
    def set_zone(self, zone_name):
        if zone_name in ZONES:
            self.current_theta = ZONES[zone_name]['mid']
            return True
        return False
    
    def set_theta(self, theta):
        self.current_theta = int(theta) % 360
    
    def select_area(self, theta, range_deg=40):
        self.selected_theta = theta
        self.selected_range = range_deg

# ============================================
# HTML TEMPLATE
# ============================================

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CYTO v2</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        :root {
            --navy-deep: #0a1628;
            --navy-mid: #0f1f38;
            --navy-light: #162a4a;
            --navy-border: #1e3a5f;
            --mint: #3eb489;
            --mint-bright: #5dfcb8;
            --mint-dim: #2a7a62;
            --mint-glow: rgba(62, 180, 137, 0.4);
            --text: #e0f0ea;
            --text-dim: #6a9a8a;
            --shadow-out: 4px 4px 10px #050d18, -4px -4px 10px #0f1f38;
            --shadow-in: inset 3px 3px 8px #050d18, inset -3px -3px 8px #0f1f38;
            --shadow-btn: 3px 3px 6px #050d18, -3px -3px 6px #0f1f38;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background: var(--navy-deep);
            color: var(--text);
            font-family: 'Segoe UI', system-ui, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        /* Header */
        header {
            background: var(--navy-mid);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: var(--shadow-out);
            z-index: 10;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo h1 {
            color: var(--mint);
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: 2px;
        }
        
        .logo span {
            color: var(--text-dim);
            font-size: 0.75rem;
            font-weight: 400;
        }
        
        .phase-display {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        
        .badge {
            background: var(--navy-light);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.8rem;
            box-shadow: var(--shadow-out);
        }
        
        .badge.phase {
            color: var(--mint);
            border: 1px solid var(--mint-dim);
        }
        
        .badge.zone {
            color: var(--mint-bright);
            border: 1px solid var(--mint);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.7rem;
        }
        
        /* Main Grid - Vertical 4 Quadrants */
        .main-grid {
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 8px;
            padding: 8px;
            overflow: hidden;
        }
        
        .quadrant {
            background: var(--navy-mid);
            border-radius: 16px;
            box-shadow: var(--shadow-out);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .q-header {
            padding: 10px 15px;
            background: var(--navy-light);
            border-bottom: 1px solid var(--navy-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .q-title {
            color: var(--mint);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .q-subtitle {
            color: var(--text-dim);
            font-size: 0.65rem;
        }
        
        .q-content {
            flex: 1;
            padding: 10px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        /* Q1: 2D Ring View */
        #q1 .q-content {
            justify-content: center;
            align-items: center;
            padding: 5px;
        }
        
        #canvas2d {
            max-width: 100%;
            max-height: 100%;
        }
        
        /* Q2: 3D Viewport */
        #q2 .q-content {
            justify-content: center;
            align-items: center;
            background: radial-gradient(ellipse at center, var(--navy-light) 0%, var(--navy-deep) 100%);
        }
        
        #canvas3d {
            max-width: 100%;
            max-height: 100%;
        }
        
        /* Q3: Node Panel */
        .node-form {
            background: var(--navy-light);
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 10px;
            box-shadow: var(--shadow-in);
        }
        
        .form-row {
            margin-bottom: 10px;
        }
        
        .form-row label {
            display: block;
            color: var(--text-dim);
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .form-row input,
        .form-row textarea,
        .form-row select {
            width: 100%;
            background: var(--navy-deep);
            border: 1px solid var(--navy-border);
            border-radius: 8px;
            padding: 10px 12px;
            color: var(--text);
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        
        .form-row input:focus,
        .form-row textarea:focus,
        .form-row select:focus {
            outline: none;
            border-color: var(--mint);
            box-shadow: 0 0 10px var(--mint-glow);
        }
        
        .form-row textarea {
            min-height: 60px;
            resize: vertical;
            font-family: inherit;
        }
        
        .btn-row {
            display: flex;
            gap: 8px;
        }
        
        .btn {
            flex: 1;
            padding: 10px 12px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            transition: all 0.2s;
            box-shadow: var(--shadow-btn);
        }
        
        .btn:active {
            box-shadow: var(--shadow-in);
        }
        
        .btn-sync {
            background: var(--navy-light);
            color: var(--mint);
            border: 1px solid var(--mint-dim);
        }
        
        .btn-sync:hover {
            background: var(--mint-dim);
            color: var(--text);
        }
        
        .btn-int {
            background: var(--navy-light);
            color: #60a5fa;
            border: 1px solid #3b82f6;
        }
        
        .btn-int:hover {
            background: #1e40af;
            color: var(--text);
        }
        
        /* Node List */
        .node-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        
        .node-card {
            background: var(--navy-light);
            border-radius: 10px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid var(--mint-dim);
            box-shadow: var(--shadow-out);
        }
        
        .node-card:hover {
            transform: translateX(3px);
            border-left-color: var(--mint);
        }
        
        .node-card.sync { border-left-color: var(--mint); }
        .node-card.integration { border-left-color: #60a5fa; }
        .node-card.selected {
            box-shadow: 0 0 15px var(--mint-glow);
            border-left-color: var(--mint-bright);
        }
        
        .node-card .title {
            color: var(--text);
            font-size: 0.85rem;
            margin-bottom: 4px;
        }
        
        .node-card .meta {
            color: var(--text-dim);
            font-size: 0.7rem;
            display: flex;
            gap: 10px;
        }
        
        .node-card .y-label {
            color: var(--mint-dim);
            text-transform: capitalize;
        }
        
        /* Q4: Continuity Panel */
        .phase-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 15px;
        }
        
        .phase-item {
            background: var(--navy-light);
            border-radius: 10px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: var(--shadow-out);
            border-left: 3px solid transparent;
        }
        
        .phase-item:hover {
            transform: translateX(3px);
        }
        
        .phase-item.active {
            border-left-color: var(--mint);
            background: var(--navy-border);
        }
        
        .phase-item .name {
            color: var(--mint);
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .phase-item .goal {
            color: var(--text-dim);
            font-size: 0.7rem;
            margin-top: 2px;
        }
        
        .phase-item .stats {
            color: var(--text-dim);
            font-size: 0.65rem;
            margin-top: 4px;
            display: flex;
            gap: 10px;
        }
        
        .phase-item .stats span { color: var(--mint-dim); }
        
        /* Backtrack Chain */
        .chain-section {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid var(--navy-border);
        }
        
        .chain-title {
            color: var(--text-dim);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .chain-item {
            padding: 6px 10px;
            margin-bottom: 4px;
            border-left: 2px solid var(--navy-border);
            font-size: 0.75rem;
            color: var(--text-dim);
            transition: all 0.2s;
        }
        
        .chain-item:hover {
            border-left-color: var(--mint);
            color: var(--text);
        }
        
        .chain-item.origin {
            border-left-color: var(--mint);
            color: var(--mint);
        }
        
        .chain-item.current {
            border-left-color: var(--mint-bright);
            background: rgba(62, 180, 137, 0.1);
            color: var(--text);
        }
        
        /* Zone Selector */
        .zone-bar {
            display: flex;
            gap: 4px;
            padding: 8px;
            background: var(--navy-light);
            border-radius: 10px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        
        .zone-btn {
            padding: 6px 10px;
            border: none;
            border-radius: 6px;
            background: var(--navy-deep);
            color: var(--text-dim);
            font-size: 0.65rem;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
        }
        
        .zone-btn:hover {
            color: var(--mint);
        }
        
        .zone-btn.active {
            background: var(--mint-dim);
            color: var(--text);
        }
        
        /* Selected Node Detail */
        .node-detail {
            background: var(--navy-light);
            border-radius: 10px;
            padding: 12px;
            margin-top: 10px;
            box-shadow: var(--shadow-in);
        }
        
        .node-detail h3 {
            color: var(--mint);
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        
        .node-detail .content {
            color: var(--text);
            font-size: 0.8rem;
            line-height: 1.5;
            margin-bottom: 8px;
        }
        
        .node-detail .coords {
            font-family: monospace;
            font-size: 0.7rem;
            color: var(--text-dim);
            background: var(--navy-deep);
            padding: 6px 10px;
            border-radius: 6px;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: var(--navy-deep);
        }
        ::-webkit-scrollbar-thumb {
            background: var(--navy-border);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--mint-dim);
        }
        
        /* Empty state */
        .empty-state {
            color: var(--text-dim);
            font-size: 0.8rem;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <header>
        <div class="logo">
            <h1>CYTO</h1>
            <span>Continuity Database v2</span>
        </div>
        <div class="phase-display">
            <div class="badge phase" id="phaseBadge">W1: Foundation</div>
            <div class="badge zone" id="zoneBadge">Inception</div>
        </div>
    </header>
    
    <div class="main-grid">
        <!-- Q1: 2D Ring View -->
        <div class="quadrant" id="q1">
            <div class="q-header">
                <div class="q-title">2D Layer View</div>
                <div class="q-subtitle" id="q1Info">W1 • 0 nodes</div>
            </div>
            <div class="q-content">
                <canvas id="canvas2d"></canvas>
            </div>
        </div>
        
        <!-- Q2: 3D Viewport -->
        <div class="quadrant" id="q2">
            <div class="q-header">
                <div class="q-title">3D Depth View</div>
                <div class="q-subtitle" id="q2Info">Select area in 2D view</div>
            </div>
            <div class="q-content">
                <canvas id="canvas3d"></canvas>
            </div>
        </div>
        
        <!-- Q3: Node Panel -->
        <div class="quadrant" id="q3">
            <div class="q-header">
                <div class="q-title">Nodes</div>
                <div class="q-subtitle" id="q3Info">Create & Browse</div>
            </div>
            <div class="q-content">
                <div class="zone-bar" id="zoneBar"></div>
                
                <div class="node-form">
                    <div class="form-row">
                        <label>Title</label>
                        <input type="text" id="nodeTitle" placeholder="Brief description...">
                    </div>
                    <div class="form-row">
                        <label>Content</label>
                        <textarea id="nodeContent" placeholder="Full details..."></textarea>
                    </div>
                    <div class="form-row">
                        <label>Depth Level</label>
                        <select id="nodeY">
                            <option value="s0">Sync: Observation</option>
                            <option value="s1">Sync: Context</option>
                            <option value="s2">Sync: Structure</option>
                            <option value="s3">Sync: Exploration</option>
                            <option value="s4">Sync: Insight</option>
                            <option value="s5">Sync: Decision</option>
                            <option value="i0">Integration: Implementation</option>
                            <option value="i1">Integration: Validation</option>
                            <option value="i2">Integration: Completion</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label>Parent Node ID (optional)</label>
                        <input type="number" id="nodeParent" placeholder="Link to parent...">
                    </div>
                    <div class="btn-row">
                        <button class="btn btn-sync" onclick="createNode()">+ Create Node</button>
                    </div>
                </div>
                
                <div class="node-list" id="nodeList"></div>
            </div>
        </div>
        
        <!-- Q4: Continuity Panel -->
        <div class="quadrant" id="q4">
            <div class="q-header">
                <div class="q-title">Continuity</div>
                <div class="q-subtitle">Phases & Chains</div>
            </div>
            <div class="q-content">
                <div class="chain-title">W-Layers (Phases)</div>
                <div class="phase-list" id="phaseList"></div>
                
                <button class="btn btn-sync" onclick="createNewPhase()" style="width: 100%; margin-bottom: 15px;">+ New Phase</button>
                
                <div id="selectedDetail" style="display: none;">
                    <div class="node-detail">
                        <h3 id="detailTitle"></h3>
                        <div class="content" id="detailContent"></div>
                        <div class="coords" id="detailCoords"></div>
                    </div>
                    
                    <div class="chain-section">
                        <div class="chain-title">Backtrack Chain</div>
                        <div id="backtrackChain"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

<script>
const socket = io();
const PHI = 1.618033988749895;
const c2d = document.getElementById('canvas2d');
const ctx2d = c2d.getContext('2d');
const c3d = document.getElementById('canvas3d');
const ctx3d = c3d.getContext('2d');

const ZONES = {
    inception:   {start: 0,   end: 40,  mid: 20},
    research:    {start: 40,  end: 80,  mid: 60},
    planning:    {start: 80,  end: 120, mid: 100},
    foundation:  {start: 120, end: 160, mid: 140},
    building:    {start: 160, end: 200, mid: 180},
    testing:     {start: 200, end: 240, mid: 220},
    integration: {start: 240, end: 280, mid: 260},
    review:      {start: 280, end: 320, mid: 300},
    completion:  {start: 320, end: 360, mid: 340}
};

const Y_SYNC = ['observation','context','structure','exploration','insight','decision'];
const Y_INT = ['implementation','validation','completion'];

let state = {w: 1, phase_name: 'Foundation', theta: 20, zone: 'inception'};
let nodes = [];
let phases = [];
let selectedNode = null;
let selectedTheta = null;

// Colors
const MINT = '#3eb489';
const MINT_BRIGHT = '#5dfcb8';
const MINT_DIM = '#2a7a62';
const NAVY = '#0a1628';
const NAVY_MID = '#0f1f38';
const NAVY_LIGHT = '#162a4a';
const BLUE = '#60a5fa';

// ============================================
// RESIZE
// ============================================
function resize() {
    const q1 = document.querySelector('#q1 .q-content');
    const q2 = document.querySelector('#q2 .q-content');
    
    const size1 = Math.min(q1.clientWidth, q1.clientHeight) - 10;
    c2d.width = size1;
    c2d.height = size1;
    
    const size2 = Math.min(q2.clientWidth, q2.clientHeight) - 10;
    c3d.width = size2;
    c3d.height = size2;
    
    render();
}
window.addEventListener('resize', resize);
setTimeout(resize, 100);

// ============================================
// 2D RENDER
// ============================================
function render2D() {
    const w = c2d.width, h = c2d.height;
    const cx = w/2, cy = h/2;
    const maxR = Math.min(w, h) / 2 - 25;
    
    // Background
    ctx2d.fillStyle = NAVY;
    ctx2d.fillRect(0, 0, w, h);
    
    // Zone arcs
    Object.entries(ZONES).forEach(([name, z]) => {
        const startA = (z.start - 90) * Math.PI / 180;
        const endA = (z.end - 90) * Math.PI / 180;
        const isActive = name === state.zone;
        
        // Zone fill
        ctx2d.beginPath();
        ctx2d.moveTo(cx, cy);
        ctx2d.arc(cx, cy, maxR, startA, endA);
        ctx2d.closePath();
        ctx2d.fillStyle = isActive ? 'rgba(62,180,137,0.15)' : 'rgba(62,180,137,0.03)';
        ctx2d.fill();
        
        // Zone arc line
        ctx2d.beginPath();
        ctx2d.arc(cx, cy, maxR, startA, endA);
        ctx2d.strokeStyle = isActive ? MINT : MINT_DIM;
        ctx2d.lineWidth = isActive ? 2 : 1;
        ctx2d.stroke();
        
        // Zone label
        const midA = (z.mid - 90) * Math.PI / 180;
        const lx = cx + Math.cos(midA) * (maxR + 15);
        const ly = cy + Math.sin(midA) * (maxR + 15);
        ctx2d.fillStyle = isActive ? MINT : MINT_DIM;
        ctx2d.font = '9px Segoe UI';
        ctx2d.textAlign = 'center';
        ctx2d.textBaseline = 'middle';
        ctx2d.fillText(name.slice(0,3).toUpperCase(), lx, ly);
    });
    
    // 1.000 line (main ring)
    ctx2d.beginPath();
    ctx2d.arc(cx, cy, maxR * 0.6, 0, Math.PI * 2);
    ctx2d.strokeStyle = MINT;
    ctx2d.lineWidth = 2;
    ctx2d.stroke();
    
    // Inner and outer bounds
    [0.35, 0.85].forEach(r => {
        ctx2d.beginPath();
        ctx2d.arc(cx, cy, maxR * r, 0, Math.PI * 2);
        ctx2d.strokeStyle = 'rgba(62,180,137,0.2)';
        ctx2d.lineWidth = 1;
        ctx2d.stroke();
    });
    
    // Radial lines every 40° (zone boundaries)
    for (let i = 0; i < 9; i++) {
        const a = (i * 40 - 90) * Math.PI / 180;
        ctx2d.beginPath();
        ctx2d.moveTo(cx + Math.cos(a) * maxR * 0.35, cy + Math.sin(a) * maxR * 0.35);
        ctx2d.lineTo(cx + Math.cos(a) * maxR, cy + Math.sin(a) * maxR);
        ctx2d.strokeStyle = 'rgba(62,180,137,0.15)';
        ctx2d.lineWidth = 1;
        ctx2d.stroke();
    }
    
    // Draw nodes for current W-layer only
    const layerNodes = nodes.filter(n => n.w_layer === state.w);
    layerNodes.forEach(n => {
        const a = (n.theta_slot - 90) * Math.PI / 180;
        const baseR = maxR * 0.6;
        const yOffset = (n.y_level / 5) * (maxR * 0.2);
        const r = n.node_type === 'sync' ? baseR + yOffset : baseR - yOffset;
        const zOffset = (n.z_slot - 4.5) * 2;
        
        const x = cx + Math.cos(a) * r + Math.cos(a + Math.PI/2) * zOffset;
        const y = cy + Math.sin(a) * r + Math.sin(a + Math.PI/2) * zOffset;
        
        const color = n.node_type === 'sync' ? MINT : BLUE;
        const isSelected = selectedNode && selectedNode.id === n.id;
        
        // Glow for selected
        if (isSelected) {
            ctx2d.beginPath();
            ctx2d.arc(x, y, 12, 0, Math.PI * 2);
            ctx2d.fillStyle = 'rgba(62,180,137,0.3)';
            ctx2d.fill();
        }
        
        // Node
        ctx2d.beginPath();
        ctx2d.arc(x, y, 5, 0, Math.PI * 2);
        ctx2d.fillStyle = color;
        ctx2d.fill();
    });
    
    // Gold node (current position)
    const goldA = (state.theta - 90) * Math.PI / 180;
    const goldR = maxR * 0.6;
    const goldX = cx + Math.cos(goldA) * goldR;
    const goldY = cy + Math.sin(goldA) * goldR;
    
    // Gold glow
    const glow = ctx2d.createRadialGradient(goldX, goldY, 0, goldX, goldY, 12);
    glow.addColorStop(0, 'rgba(255,215,0,0.8)');
    glow.addColorStop(1, 'rgba(255,215,0,0)');
    ctx2d.fillStyle = glow;
    ctx2d.beginPath();
    ctx2d.arc(goldX, goldY, 12, 0, Math.PI * 2);
    ctx2d.fill();
    
    // Gold dot
    ctx2d.beginPath();
    ctx2d.arc(goldX, goldY, 5, 0, Math.PI * 2);
    ctx2d.fillStyle = '#ffd700';
    ctx2d.fill();
    
    // Update info
    document.getElementById('q1Info').textContent = `W${state.w} • ${layerNodes.length} nodes`;
}

// ============================================
// 3D RENDER (Depth view of selected zone)
// ============================================
function render3D() {
    const w = c3d.width, h = c3d.height;
    const cx = w/2, cy = h/2;
    
    // Background gradient
    const bg = ctx3d.createRadialGradient(cx, cy, 0, cx, cy, Math.max(w,h)/2);
    bg.addColorStop(0, NAVY_LIGHT);
    bg.addColorStop(1, NAVY);
    ctx3d.fillStyle = bg;
    ctx3d.fillRect(0, 0, w, h);
    
    // Get nodes in current zone
    const zoneNodes = nodes.filter(n => n.w_layer === state.w && n.zone === state.zone);
    
    if (zoneNodes.length === 0) {
        ctx3d.fillStyle = MINT_DIM;
        ctx3d.font = '12px Segoe UI';
        ctx3d.textAlign = 'center';
        ctx3d.fillText('No nodes in ' + state.zone, cx, cy);
        document.getElementById('q2Info').textContent = state.zone + ' • empty';
        return;
    }
    
    // Draw Y-level lanes (looking into the tube)
    const laneHeight = h / 8;
    const centerY = cy;
    
    // 1.000 line (center)
    ctx3d.strokeStyle = MINT;
    ctx3d.lineWidth = 2;
    ctx3d.beginPath();
    ctx3d.moveTo(20, centerY);
    ctx3d.lineTo(w - 20, centerY);
    ctx3d.stroke();
    
    ctx3d.fillStyle = MINT_DIM;
    ctx3d.font = '10px Segoe UI';
    ctx3d.textAlign = 'left';
    ctx3d.fillText('1.000', 5, centerY - 5);
    
    // Sync lanes (above center)
    for (let y = 0; y <= 5; y++) {
        const ly = centerY - (y + 1) * laneHeight * 0.4;
        ctx3d.strokeStyle = 'rgba(62,180,137,0.2)';
        ctx3d.lineWidth = 1;
        ctx3d.beginPath();
        ctx3d.moveTo(20, ly);
        ctx3d.lineTo(w - 20, ly);
        ctx3d.stroke();
    }
    
    // Integration lanes (below center)
    for (let y = 0; y <= 2; y++) {
        const ly = centerY + (y + 1) * laneHeight * 0.5;
        ctx3d.strokeStyle = 'rgba(96,165,250,0.2)';
        ctx3d.lineWidth = 1;
        ctx3d.beginPath();
        ctx3d.moveTo(20, ly);
        ctx3d.lineTo(w - 20, ly);
        ctx3d.stroke();
    }
    
    // Plot nodes
    const zone = ZONES[state.zone];
    const zoneWidth = zone.end - zone.start;
    
    zoneNodes.forEach(n => {
        // X position based on theta within zone
        const thetaInZone = n.theta_slot - zone.start;
        const x = 30 + (thetaInZone / zoneWidth) * (w - 60);
        
        // Y position based on type and y_level
        let y;
        if (n.node_type === 'sync') {
            y = centerY - (n.y_level + 1) * laneHeight * 0.4;
        } else {
            y = centerY + (n.y_level + 1) * laneHeight * 0.5;
        }
        
        // Z offset (depth - shown as size)
        const size = 4 + n.z_slot * 0.5;
        
        const color = n.node_type === 'sync' ? MINT : BLUE;
        const isSelected = selectedNode && selectedNode.id === n.id;
        
        // Glow
        if (isSelected) {
            ctx3d.beginPath();
            ctx3d.arc(x, y, size + 8, 0, Math.PI * 2);
            ctx3d.fillStyle = 'rgba(62,180,137,0.3)';
            ctx3d.fill();
        }
        
        // Node
        ctx3d.beginPath();
        ctx3d.arc(x, y, size, 0, Math.PI * 2);
        ctx3d.fillStyle = color;
        ctx3d.fill();
        
        // Label
        ctx3d.fillStyle = 'rgba(255,255,255,0.6)';
        ctx3d.font = '8px Segoe UI';
        ctx3d.textAlign = 'center';
        ctx3d.fillText('#' + n.id, x, y - size - 3);
    });
    
    // Labels
    ctx3d.fillStyle = MINT;
    ctx3d.font = '9px Segoe UI';
    ctx3d.textAlign = 'right';
    ctx3d.fillText('SYNC ↑', w - 10, 20);
    
    ctx3d.fillStyle = BLUE;
    ctx3d.fillText('INT ↓', w - 10, h - 10);
    
    document.getElementById('q2Info').textContent = state.zone + ' • ' + zoneNodes.length + ' nodes';
}

function render() {
    render2D();
    render3D();
}

// ============================================
// UI UPDATES
// ============================================
function updateZoneBar() {
    const bar = document.getElementById('zoneBar');
    bar.innerHTML = Object.keys(ZONES).map(name => {
        const active = name === state.zone ? 'active' : '';
        return `<button class="zone-btn ${active}" onclick="selectZone('${name}')">${name.slice(0,4)}</button>`;
    }).join('');
}

function updatePhaseList() {
    const list = document.getElementById('phaseList');
    list.innerHTML = phases.map(p => {
        const active = p.w_layer === state.w ? 'active' : '';
        const nodeCount = nodes.filter(n => n.w_layer === p.w_layer).length;
        return `
            <div class="phase-item ${active}" onclick="selectPhase(${p.w_layer})">
                <div class="name">W${p.w_layer}: ${p.name}</div>
                <div class="goal">${p.goal || 'No goal set'}</div>
                <div class="stats"><span>${nodeCount}</span> nodes</div>
            </div>
        `;
    }).join('');
}

function updateNodeList() {
    const zoneNodes = nodes.filter(n => n.w_layer === state.w && n.zone === state.zone);
    const list = document.getElementById('nodeList');
    
    if (zoneNodes.length === 0) {
        list.innerHTML = '<div class="empty-state">No nodes in this zone</div>';
        return;
    }
    
    list.innerHTML = zoneNodes.map(n => {
        const yLabel = n.node_type === 'sync' ? Y_SYNC[n.y_level] : Y_INT[n.y_level];
        const selected = selectedNode && selectedNode.id === n.id ? 'selected' : '';
        return `
            <div class="node-card ${n.node_type} ${selected}" onclick="selectNode(${n.id})">
                <div class="title">${n.title}</div>
                <div class="meta">
                    <span>#${n.id}</span>
                    <span>Y${n.y_level}.Z${n.z_slot}</span>
                    <span class="y-label">${yLabel}</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateHeader() {
    document.getElementById('phaseBadge').textContent = `W${state.w}: ${state.phase_name}`;
    document.getElementById('zoneBadge').textContent = state.zone;
}

// ============================================
// INTERACTIONS
// ============================================
function selectZone(zone) {
    fetch('/api/zone', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({zone})
    });
}

function selectPhase(w) {
    fetch('/api/phase/select', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({w_layer: w})
    });
}

function selectNode(id) {
    selectedNode = nodes.find(n => n.id === id);
    if (!selectedNode) return;
    
    document.getElementById('selectedDetail').style.display = 'block';
    document.getElementById('detailTitle').textContent = selectedNode.title;
    document.getElementById('detailContent').textContent = selectedNode.content || '(no content)';
    document.getElementById('detailCoords').textContent = 
        `W${selectedNode.w_layer}.θ${selectedNode.theta_slot}.Y${selectedNode.y_level}.Z${selectedNode.z_slot} | ${selectedNode.y_meaning}`;
    
    // Fetch backtrack
    fetch(`/api/backtrack/${id}`)
        .then(r => r.json())
        .then(chain => {
            const div = document.getElementById('backtrackChain');
            if (chain.length <= 1) {
                div.innerHTML = '<div class="chain-item origin">Origin node</div>';
            } else {
                div.innerHTML = chain.map((n, i) => {
                    const cls = i === 0 ? 'origin' : (i === chain.length - 1 ? 'current' : '');
                    return `<div class="chain-item ${cls}">#${n.id} ${n.title}</div>`;
                }).join('');
            }
        });
    
    updateNodeList();
    render();
}

function createNode() {
    const title = document.getElementById('nodeTitle').value.trim();
    const content = document.getElementById('nodeContent').value.trim();
    const yVal = document.getElementById('nodeY').value;
    const parentId = document.getElementById('nodeParent').value;
    
    if (!title) { alert('Title required'); return; }
    
    const nodeType = yVal.startsWith('s') ? 'sync' : 'integration';
    const yLevel = parseInt(yVal.slice(1));
    
    fetch('/api/node', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            node_type: nodeType,
            title,
            content: content || null,
            y_level: yLevel,
            parent_id: parentId ? parseInt(parentId) : null
        })
    }).then(() => {
        document.getElementById('nodeTitle').value = '';
        document.getElementById('nodeContent').value = '';
        document.getElementById('nodeParent').value = '';
    });
}

function createNewPhase() {
    const name = prompt('Phase name:');
    if (!name) return;
    const goal = prompt('Phase goal (optional):');
    
    fetch('/api/phase', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, goal: goal || null})
    });
}

// Canvas click to select area
c2d.addEventListener('click', (e) => {
    const rect = c2d.getBoundingClientRect();
    const x = e.clientX - rect.left - c2d.width/2;
    const y = e.clientY - rect.top - c2d.height/2;
    const theta = (Math.atan2(y, x) * 180 / Math.PI + 90 + 360) % 360;
    
    // Find zone
    for (const [name, z] of Object.entries(ZONES)) {
        if (theta >= z.start && theta < z.end) {
            selectZone(name);
            break;
        }
    }
});

// ============================================
// SOCKET
// ============================================
socket.on('connect', () => socket.emit('get_state'));

socket.on('state', data => {
    state = data;
    updateHeader();
    updateZoneBar();
    render();
});

socket.on('nodes', data => {
    nodes = data;
    updateNodeList();
    render();
});

socket.on('phases', data => {
    phases = data;
    updatePhaseList();
});

socket.on('node_created', node => {
    nodes.push(node);
    updateNodeList();
    render();
});

// Init
setTimeout(() => {
    resize();
    updateZoneBar();
}, 200);
</script>
</body>
</html>
'''

# ============================================
# FLASK APP INITIALIZATION
# ============================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cyto_v2_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

init_db()
engine = PhaseEngine()

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/node', methods=['POST'])
def api_create_node():
    data = request.json
    node = create_node(
        node_type=data.get('node_type', 'sync'),
        title=data.get('title', 'Untitled'),
        content=data.get('content'),
        zone=data.get('zone') or theta_to_zone(engine.current_theta),
        theta=data.get('theta'),
        y_level=data.get('y_level', 0),
        z_slot=data.get('z_slot', 0),
        w_layer=data.get('w_layer'),
        parent_id=data.get('parent_id'),
        decision_id=data.get('decision_id')
    )
    socketio.emit('node_created', node)
    socketio.emit('nodes', get_all_nodes())
    return jsonify(node)

@app.route('/api/nodes', methods=['GET'])
def api_get_nodes():
    return jsonify(get_all_nodes())

@app.route('/api/backtrack/<int:node_id>', methods=['GET'])
def api_backtrack(node_id):
    return jsonify(backtrack(node_id))

@app.route('/api/zone', methods=['POST'])
def api_set_zone():
    zone = request.json.get('zone')
    if engine.set_zone(zone):
        socketio.emit('state', engine.get_state())
        socketio.emit('nodes', get_all_nodes())
        return jsonify({'ok': True})
    return jsonify({'error': 'Invalid zone'}), 400

@app.route('/api/phase', methods=['POST'])
def api_create_phase():
    name = request.json.get('name', 'New Phase')
    goal = request.json.get('goal')
    w = create_phase(name, goal)
    set_active_phase(w)
    socketio.emit('phases', get_all_phases())
    socketio.emit('state', engine.get_state())
    return jsonify({'ok': True, 'w_layer': w})

@app.route('/api/phase/select', methods=['POST'])
def api_select_phase():
    w = request.json.get('w_layer')
    set_active_phase(w)
    socketio.emit('phases', get_all_phases())
    socketio.emit('state', engine.get_state())
    socketio.emit('nodes', get_all_nodes())
    return jsonify({'ok': True})

@app.route('/api/tether', methods=['POST'])
def api_create_tether():
    data = request.json
    tid = create_tether(
        source_id=data['source_id'],
        target_id=data['target_id'],
        tether_type=data.get('tether_type', 'related'),
        weight=data.get('weight', 1.0),
        note=data.get('note')
    )
    return jsonify({'ok': True, 'tether_id': tid})

# ============================================
# SOCKET
# ============================================

@socketio.on('connect')
def handle_connect():
    emit('state', engine.get_state())
    emit('nodes', get_all_nodes())
    emit('phases', get_all_phases())

@socketio.on('get_state')
def handle_get_state():
    emit('state', engine.get_state())
    emit('nodes', get_all_nodes())
    emit('phases', get_all_phases())

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("CYTO v2 - Continuity Database")
    print("="*50)
    
    phase = get_current_phase()
    if phase:
        print(f"Phase: W{phase['w_layer']} - {phase['name']}")
    
    total = len(get_all_nodes())
    print(f"Nodes: {total}")
    print("="*50)
    print("http://localhost:5000")
    print("="*50 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
