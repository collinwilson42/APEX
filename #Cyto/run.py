"""
CYTO - 4D Temporal Database UI
Persistent epoch - gold node continues from stored time
"""

from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import threading
import time
import sqlite3
import os
import json

# ============================================
# CONSTANTS
# ============================================

PHI = 1.618033988749895
THETA_SLOTS = 360
Z_SLOTS = 10
Y_LEVELS = 6
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyto.db")

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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_type TEXT NOT NULL,
            content TEXT,
            theta_slot INTEGER NOT NULL,
            y_level INTEGER NOT NULL,
            z_slot INTEGER NOT NULL,
            w_layer INTEGER NOT NULL DEFAULT 1,
            timestamp TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
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

def save_node(node_type, content, theta_slot, y_level, z_slot, w_layer, timestamp, source='ai'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO nodes (node_type, content, theta_slot, y_level, z_slot, w_layer, timestamp, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (node_type, content, theta_slot, y_level, z_slot, w_layer, timestamp, source))
    node_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return node_id

def get_all_nodes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nodes ORDER BY w_layer, theta_slot")
    nodes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return nodes

def clear_nodes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nodes")
    conn.commit()
    conn.close()

# ============================================
# TIME ENGINE - PERSISTENT
# ============================================

class TimeEngine:
    def __init__(self):
        # Load cycle hours from DB or default to 36
        self.cycle_hours = float(get_config('cycle_hours', '36'))
        
        # Speed is session-only (not persisted) - always 1x on restart
        self.speed = 1.0
        
        # Load epoch from DB - this is the KEY to persistence
        epoch_str = get_config('epoch')
        if epoch_str:
            self.epoch = datetime.fromisoformat(epoch_str)
            # Calculate where we should be
            hours_elapsed = (datetime.now() - self.epoch).total_seconds() / 3600
            current_w = int(hours_elapsed // self.cycle_hours) + 1
            theta = (hours_elapsed % self.cycle_hours) / self.cycle_hours * 360
            print(f"✓ Loaded epoch: {self.epoch}")
            print(f"  Hours elapsed: {hours_elapsed:.2f}")
            print(f"  Current position: W{current_w} at {theta:.1f}°")
        else:
            # First run - create new epoch
            self.epoch = datetime.now()
            set_config('epoch', self.epoch.isoformat())
            print(f"✓ Created new epoch: {self.epoch}")
    
    def set_cycle(self, hours):
        self.cycle_hours = float(hours)
        set_config('cycle_hours', str(hours))
    
    def set_speed(self, speed):
        """Speed only affects display, not stored position."""
        self.speed = float(speed)
    
    def hard_reset(self):
        """Complete reset - new epoch, clear all data."""
        self.epoch = datetime.now()
        set_config('epoch', self.epoch.isoformat())
        clear_nodes()
        print(f"✓ Hard reset - new epoch: {self.epoch}")
    
    def get_position(self):
        """Calculate current position from real time since epoch."""
        now = datetime.now()
        
        # Real elapsed time (speed only affects visual updates, not position)
        real_elapsed_hours = (now - self.epoch).total_seconds() / 3600
        
        # For display with speed multiplier (testing)
        # We track a separate "simulated" offset when speed > 1
        if not hasattr(self, '_speed_offset'):
            self._speed_offset = 0
            self._last_update = now
        
        if self.speed > 1:
            # Accumulate extra time based on speed
            delta = (now - self._last_update).total_seconds() / 3600
            self._speed_offset += delta * (self.speed - 1)
        
        self._last_update = now
        
        # Total hours = real + speed offset
        total_hours = real_elapsed_hours + self._speed_offset
        
        # Calculate position
        w = max(1, int(total_hours // self.cycle_hours) + 1)
        hours_in_cycle = total_hours % self.cycle_hours
        theta = (hours_in_cycle / self.cycle_hours) * 360
        
        # Section calculation
        if theta >= 340 or theta < 20:
            section = 9
        else:
            section = int((theta - 20) / 40) + 1
        
        return {
            'w': w,
            'theta': theta,
            'section': section,
            'progress': hours_in_cycle / self.cycle_hours,
            'total_hours': total_hours,
            'real_hours': real_elapsed_hours,
            'cycle_hours': self.cycle_hours,
            'speed': self.speed,
            'epoch': self.epoch.isoformat()
        }
    
    def timestamp_to_position(self, timestamp):
        """Convert a timestamp to CYTO coordinates."""
        if timestamp < self.epoch:
            return None
        
        hours = (timestamp - self.epoch).total_seconds() / 3600
        w = int(hours // self.cycle_hours) + 1
        theta = (hours % self.cycle_hours) / self.cycle_hours * 360
        
        return {
            'w': w,
            'theta_slot': int(theta) % 360,
            'theta': theta
        }


# ============================================
# HTML
# ============================================

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CYTO</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #1a1a2e;
            color: #e0e0e0;
            font-family: 'Segoe UI', sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        #viewport {
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            background: linear-gradient(#0d0d1a, #1a1a2e);
        }
        #time {
            position: absolute;
            top: 15px;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
        }
        #time .t { font-size: 2rem; color: #d4af37; }
        #time .d { font-size: 0.85rem; color: #888; }
        #viewInfo {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(0,0,0,0.6);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
        }
        #viewInfo .m { color: #ffd700; }
        #viewInfo .l { color: #888; }
        #overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.9);
            border: 2px solid #d4af37;
            padding: 20px 35px;
            border-radius: 10px;
            font-size: 1.2rem;
            color: #ffd700;
            display: none;
            text-align: center;
            z-index: 100;
        }
        #overlay.show { display: block; }
        #overlay .sub { font-size: 0.85rem; color: #888; margin-top: 5px; }
        #hints {
            position: absolute;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            padding: 6px 12px;
            border-radius: 5px;
            font-size: 0.65rem;
            color: #888;
            display: flex;
            gap: 10px;
        }
        #hints kbd {
            background: rgba(255,255,255,0.1);
            padding: 1px 4px;
            border-radius: 2px;
            color: #d4af37;
        }
        #panel {
            height: 38%;
            background: #252540;
            padding: 12px 18px;
            border-top: 1px solid rgba(212,175,55,0.2);
            display: flex;
            flex-direction: column;
            gap: 8px;
            overflow-y: auto;
        }
        .row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
        .title { font-size: 1rem; color: #d4af37; }
        .btns { display: flex; gap: 4px; align-items: center; }
        .btns span { color: #888; font-size: 0.7rem; margin-right: 3px; }
        .btn {
            background: #252540;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
            color: #d4af37;
            font-size: 0.75rem;
            cursor: pointer;
            box-shadow: 2px 2px 4px rgba(0,0,0,0.5), -2px -2px 4px rgba(255,255,255,0.03);
        }
        .btn:hover { color: #fff; }
        .btn.active { box-shadow: inset 2px 2px 4px rgba(0,0,0,0.5); color: #ffd700; }
        .btn.danger { color: #ff6b6b; }
        .btn.green { color: #4ade80; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
            gap: 5px;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .stat { text-align: center; }
        .stat .lbl { font-size: 0.5rem; color: #888; text-transform: uppercase; }
        .stat .val { font-size: 0.9rem; color: #d4af37; }
        .srow { display: flex; align-items: center; gap: 6px; }
        .srow label { color: #888; font-size: 0.7rem; width: 35px; }
        .srow input[type=range] {
            width: 100px;
            -webkit-appearance: none;
            height: 3px;
            background: rgba(0,0,0,0.3);
            border-radius: 2px;
        }
        .srow input::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 10px; height: 10px;
            background: #d4af37;
            border-radius: 50%;
        }
        .srow .v { color: #d4af37; font-size: 0.75rem; width: 35px; }
        .epoch-info { 
            font-size: 0.65rem; 
            color: #666; 
            margin-top: 5px;
            padding: 5px;
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
        }
        .epoch-info strong { color: #d4af37; }
    </style>
</head>
<body tabindex="0">
    <div id="viewport">
        <div id="time">
            <div class="t" id="clock">--:--:--</div>
            <div class="d" id="date">Loading...</div>
        </div>
        <div id="viewInfo">
            <div class="m" id="vMode">Full View</div>
            <div class="l" id="vLayers">All Layers</div>
        </div>
        <div id="overlay">
            <div id="oText">Select Layer...</div>
            <div class="sub" id="oSub"></div>
        </div>
        <canvas id="c"></canvas>
        <div id="hints">
            <span><kbd>Ctrl</kbd>+<kbd>1-9</kbd> Focus</span>
            <span><kbd>Ctrl</kbd>+<kbd>n</kbd><kbd>m</kbd> Range</span>
            <span><kbd>Ctrl</kbd>+<kbd>Space</kbd> Current</span>
            <span><kbd>Esc</kbd> Full</span>
            <span><kbd>Back</kbd> Undo</span>
        </div>
    </div>
    <div id="panel">
        <div class="row">
            <div class="title">CYTO</div>
            <div class="btns">
                <button class="btn green" onclick="testNodes()">+Nodes</button>
                <button class="btn danger" onclick="clearNodes()">Clear Nodes</button>
                <button class="btn danger" onclick="hardReset()">Reset DB</button>
            </div>
        </div>
        <div class="row">
            <div class="btns">
                <span>Cycle:</span>
                <button class="btn" onclick="setCycle(7.2)" id="c7">7.2h</button>
                <button class="btn active" onclick="setCycle(36)" id="c36">36h</button>
                <button class="btn" onclick="setCycle(72)" id="c72">72h</button>
            </div>
            <div class="btns">
                <span>Speed:</span>
                <button class="btn active" onclick="setSpeed(1)" id="s1">1x</button>
                <button class="btn" onclick="setSpeed(60)" id="s60">60x</button>
                <button class="btn" onclick="setSpeed(360)" id="s360">360x</button>
                <button class="btn" onclick="setSpeed(3600)" id="s3600">3600x</button>
            </div>
            <div class="srow">
                <label>Zoom:</label>
                <input type="range" id="zoom" min="0.3" max="2.5" step="0.05" value="1">
                <span class="v" id="zv">1.0x</span>
            </div>
        </div>
        <div class="stats">
            <div class="stat"><div class="lbl">Layer</div><div class="val" id="sW">W1</div></div>
            <div class="stat"><div class="lbl">Section</div><div class="val" id="sSec">9</div></div>
            <div class="stat"><div class="lbl">θ</div><div class="val" id="sTheta">0°</div></div>
            <div class="stat"><div class="lbl">Progress</div><div class="val" id="sProg">0%</div></div>
            <div class="stat"><div class="lbl">Layers</div><div class="val" id="sLayers">1</div></div>
            <div class="stat"><div class="lbl">Visible</div><div class="val" id="sVis">1</div></div>
            <div class="stat"><div class="lbl">Nodes</div><div class="val" id="sNodes">0</div></div>
        </div>
        <div class="epoch-info">
            <strong>Epoch:</strong> <span id="epochTime">-</span><br>
            <strong>Running:</strong> <span id="runningTime">-</span>
        </div>
    </div>

<script>
const socket = io();
const PHI = 1.618033988749895;
const c = document.getElementById('c');
const ctx = c.getContext('2d');

// State
let S = { w: 1, theta: 0, section: 9, progress: 0, speed: 1, cycle: 36, epoch: '', totalHours: 0 };
let nodes = [];
let zoom = 1;

// View
let V = { mode: 'full', layers: [], map: {}, history: [] };

// Keyboard
let K = { ctrl: false, shift: false, first: null };

// ============================================
// RESIZE
// ============================================
function resize() {
    const vp = document.getElementById('viewport');
    const sz = Math.min(vp.clientWidth, vp.clientHeight) - 30;
    c.width = sz; c.height = sz;
    render();
}
window.onresize = resize;
resize();

// ============================================
// GEOMETRY
// ============================================
function geom(pos) {
    return { pos, inner: (pos-1) + (PHI-1), mid: pos, outer: pos + (PHI-1) };
}

function yToR(g, y, sync) {
    const t = y / 5;
    return sync ? g.mid + (g.outer - g.mid) * t * 0.85 : g.mid - (g.mid - g.inner) * t * 0.85;
}

// ============================================
// VIEW
// ============================================
function fullView() {
    saveHist();
    V.mode = 'full';
    V.layers = [];
    V.map = {};
    for (let w = 1; w <= S.w; w++) {
        V.layers.push(w);
        V.map[w] = w;
    }
    updView();
    render();
}

function singleView(w) {
    if (w < 1 || w > S.w) return;
    saveHist();
    V.mode = 'single';
    V.layers = [w];
    V.map = {}; V.map[w] = 1;
    updView();
    render();
}

function rangeView(a, b, rev) {
    if (a < 1 || b < 1 || a > S.w || b > S.w) return;
    saveHist();
    V.mode = 'range';
    V.layers = [];
    V.map = {};
    
    let pos = 1;
    if (rev) {
        for (let w = a; w >= b; w--) { V.layers.push(w); V.map[w] = pos++; }
    } else {
        for (let w = b; w <= a; w++) { V.layers.push(w); V.map[w] = pos++; }
    }
    updView();
    render();
}

function currentView() { singleView(S.w); }

function saveHist() {
    V.history.push({ mode: V.mode, layers: [...V.layers], map: {...V.map} });
    if (V.history.length > 20) V.history.shift();
}

function goBack() {
    if (!V.history.length) return;
    const h = V.history.pop();
    V.mode = h.mode; V.layers = h.layers; V.map = h.map;
    updView();
    render();
}

function updView() {
    const m = document.getElementById('vMode');
    const l = document.getElementById('vLayers');
    if (V.mode === 'full') {
        m.textContent = 'Full View';
        l.textContent = 'W1 - W' + S.w;
    } else if (V.mode === 'single') {
        m.textContent = 'Single';
        l.textContent = 'W' + V.layers[0];
    } else {
        m.textContent = 'Range';
        const sorted = [...V.layers].sort((a,b) => a-b);
        l.textContent = 'W' + sorted[0] + ' → W' + sorted[sorted.length-1];
    }
    document.getElementById('sVis').textContent = V.layers.length;
}

// ============================================
// KEYBOARD
// ============================================
window.addEventListener('keydown', function(e) {
    const overlay = document.getElementById('overlay');
    const oText = document.getElementById('oText');
    const oSub = document.getElementById('oSub');
    
    if (e.key === 'Escape') {
        K.ctrl = false; K.shift = false; K.first = null;
        overlay.classList.remove('show');
        fullView();
        e.preventDefault();
        return;
    }
    
    if (e.key === 'Backspace') {
        goBack();
        e.preventDefault();
        return;
    }
    
    if (e.key === 'Control') {
        K.ctrl = true;
        K.first = null;
        overlay.classList.add('show');
        oText.textContent = K.shift ? 'Shift + Layer...' : 'Select Layer...';
        oSub.textContent = 'Press 1-9 or Space';
        e.preventDefault();
        return;
    }
    
    if (e.key === 'Shift') {
        K.shift = true;
        if (K.ctrl) {
            oText.textContent = K.first ? 'Shift+W' + K.first + ' → ?' : 'Shift + Layer...';
        }
        return;
    }
    
    if (K.ctrl && e.code === 'Space') {
        K.ctrl = false;
        overlay.classList.remove('show');
        currentView();
        e.preventDefault();
        return;
    }
    
    if (K.ctrl && e.key >= '1' && e.key <= '9') {
        const n = parseInt(e.key);
        
        if (K.first === null) {
            K.first = n;
            oText.textContent = K.shift ? 'Shift+W' + n + ' → ?' : 'W' + n + ' → ?';
            oSub.textContent = 'Press another number or release Ctrl';
        } else {
            overlay.classList.remove('show');
            if (K.shift) {
                rangeView(K.first, n, true);
            } else {
                rangeView(K.first, n, false);
            }
            K.ctrl = false; K.shift = false; K.first = null;
        }
        e.preventDefault();
        return;
    }
}, true);

window.addEventListener('keyup', function(e) {
    const overlay = document.getElementById('overlay');
    
    if (e.key === 'Control') {
        if (K.first !== null) {
            singleView(K.first);
        }
        K.ctrl = false;
        K.first = null;
        overlay.classList.remove('show');
    }
    
    if (e.key === 'Shift') {
        K.shift = false;
    }
}, true);

// ============================================
// RENDER
// ============================================
function render() {
    const w = c.width, h = c.height;
    const cx = w/2, cy = h/2;
    
    ctx.fillStyle = '#0d0d1a';
    ctx.fillRect(0, 0, w, h);
    
    if (!V.layers.length) { fullView(); return; }
    
    const maxPos = Math.max(...Object.values(V.map));
    const maxOuter = maxPos + (PHI - 1);
    const unit = (Math.min(w, h) / (maxOuter * 2.5)) * zoom;
    
    const sorted = [...V.layers].sort((a,b) => V.map[b] - V.map[a]);
    for (const actualW of sorted) {
        const g = geom(V.map[actualW]);
        drawLayer(cx, cy, unit, g, actualW, actualW === S.w);
    }
    
    ctx.strokeStyle = 'rgba(212,175,55,0.1)';
    ctx.lineWidth = 0.5;
    const inner0 = geom(1).inner * unit;
    const outer0 = maxOuter * unit;
    for (let i = 0; i < 36; i++) {
        const a = (i * 10 - 90) * Math.PI / 180;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(a) * inner0, cy + Math.sin(a) * inner0);
        ctx.lineTo(cx + Math.cos(a) * outer0, cy + Math.sin(a) * outer0);
        ctx.stroke();
    }
    
    ctx.fillStyle = 'rgba(212,175,55,0.5)';
    ctx.font = '11px Segoe UI';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const lr = maxOuter * unit + 18;
    for (let i = 1; i <= 9; i++) {
        const deg = i === 9 ? 0 : 20 + (i-1) * 40 + 20;
        const rad = (deg - 90) * Math.PI / 180;
        ctx.fillText(i, cx + Math.cos(rad) * lr, cy + Math.sin(rad) * lr);
    }
    
    drawNodes(cx, cy, unit);
    
    if (V.layers.includes(S.w)) {
        drawGold(cx, cy, unit);
    }
}

function drawLayer(cx, cy, unit, g, actualW, active) {
    const ir = g.inner * unit;
    const mr = g.mid * unit;
    const or = g.outer * unit;
    if (or < 5) return;
    
    const grad = ctx.createRadialGradient(cx, cy, Math.max(0, ir), cx, cy, or);
    grad.addColorStop(0, 'rgba(30,30,50,0.85)');
    grad.addColorStop(0.5, 'rgba(45,45,70,0.95)');
    grad.addColorStop(1, 'rgba(30,30,50,0.85)');
    
    ctx.beginPath();
    ctx.arc(cx, cy, or, 0, Math.PI*2);
    ctx.arc(cx, cy, Math.max(0, ir), 0, Math.PI*2, true);
    ctx.fillStyle = grad;
    ctx.fill();
    
    const alpha = active ? 0.9 : 0.35;
    [ir, mr, or].forEach((r, i) => {
        if (r < 1) return;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI*2);
        ctx.strokeStyle = 'rgba(212,175,55,' + (i === 1 ? alpha : alpha * 0.5) + ')';
        ctx.lineWidth = i === 1 ? 2.5 : 1;
        ctx.stroke();
    });
    
    if (mr > 25) {
        ctx.fillStyle = 'rgba(212,175,55,' + alpha * 0.8 + ')';
        ctx.font = 'bold 10px Segoe UI';
        ctx.textAlign = 'left';
        ctx.fillText('W' + actualW, cx + mr + 5, cy - 3);
    }
}

function drawNodes(cx, cy, unit) {
    nodes.forEach(n => {
        if (!V.layers.includes(n.w_layer)) return;
        const g = geom(V.map[n.w_layer]);
        const sync = n.node_type === 'sync';
        const r = yToR(g, n.y_level, sync) * unit;
        const a = (n.theta_slot - 90) * Math.PI / 180;
        const zo = (n.z_slot - 4.5) * 2;
        const x = cx + Math.cos(a) * (r + zo);
        const y = cy + Math.sin(a) * (r + zo);
        
        const col = sync ? '#4ade80' : '#60a5fa';
        const al = n.w_layer === S.w ? 1 : 0.5;
        
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI*2);
        ctx.fillStyle = col;
        ctx.globalAlpha = al;
        ctx.fill();
        ctx.globalAlpha = 1;
    });
}

function drawGold(cx, cy, unit) {
    const pos = V.map[S.w];
    if (!pos) return;
    const g = geom(pos);
    const mr = g.mid * unit;
    if (mr < 10) return;
    
    const a = (S.theta - 90) * Math.PI / 180;
    const x = cx + Math.cos(a) * mr;
    const y = cy + Math.sin(a) * mr;
    
    const glow = ctx.createRadialGradient(x, y, 0, x, y, 18);
    glow.addColorStop(0, 'rgba(255,215,0,0.9)');
    glow.addColorStop(0.5, 'rgba(255,215,0,0.3)');
    glow.addColorStop(1, 'rgba(255,215,0,0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, y, 18, 0, Math.PI*2);
    ctx.fill();
    
    ctx.beginPath();
    ctx.arc(x, y, 7, 0, Math.PI*2);
    ctx.fillStyle = '#ffd700';
    ctx.fill();
    ctx.strokeStyle = '#b8860b';
    ctx.lineWidth = 2;
    ctx.stroke();
}

// ============================================
// SOCKET
// ============================================
socket.on('connect', () => { socket.emit('get_nodes'); });

socket.on('state', data => {
    document.getElementById('clock').textContent = data.time;
    document.getElementById('date').textContent = data.date;
    
    const prevW = S.w;
    S.w = data.w;
    S.theta = data.theta;
    S.section = data.section;
    S.progress = data.progress;
    S.cycle = data.cycle_hours;
    S.speed = data.speed;
    S.epoch = data.epoch;
    S.totalHours = data.total_hours;
    
    // Update cycle button state
    document.querySelectorAll('[id^="c"]').forEach(b => b.classList.remove('active'));
    const cycleBtn = document.getElementById('c' + (S.cycle === 7.2 ? '7' : S.cycle));
    if (cycleBtn) cycleBtn.classList.add('active');
    
    // Add new layers to view if in full mode
    if (S.w > prevW && V.mode === 'full') {
        for (let w = prevW + 1; w <= S.w; w++) {
            V.layers.push(w);
            V.map[w] = w;
        }
    }
    
    // Update stats
    document.getElementById('sW').textContent = 'W' + S.w;
    document.getElementById('sSec').textContent = S.section;
    document.getElementById('sTheta').textContent = Math.floor(S.theta) + '°';
    document.getElementById('sProg').textContent = Math.floor(S.progress * 100) + '%';
    document.getElementById('sLayers').textContent = S.w;
    document.getElementById('sNodes').textContent = nodes.length;
    
    // Update epoch info
    const epochDate = new Date(S.epoch);
    document.getElementById('epochTime').textContent = epochDate.toLocaleString();
    
    const hours = Math.floor(S.totalHours);
    const mins = Math.floor((S.totalHours % 1) * 60);
    document.getElementById('runningTime').textContent = hours + 'h ' + mins + 'm';
    
    updView();
    render();
});

socket.on('nodes', data => { nodes = data; render(); });
socket.on('node', n => { nodes.push(n); render(); });

// ============================================
// CONTROLS
// ============================================
function setCycle(h) {
    fetch('/api/cycle', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({hours: h}) });
}

function setSpeed(s) {
    document.querySelectorAll('[id^="s"]').forEach(b => b.classList.remove('active'));
    document.getElementById('s' + s).classList.add('active');
    fetch('/api/speed', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({speed: s}) });
}

function testNodes() { fetch('/api/test_nodes', { method: 'POST' }); }
function clearNodes() { nodes = []; fetch('/api/clear', { method: 'POST' }); render(); }
function hardReset() {
    if (confirm('Reset database? This clears all nodes and starts a new epoch.')) {
        nodes = [];
        V.history = [];
        fetch('/api/reset', { method: 'POST' }).then(() => {
            V.layers = [1];
            V.map = {1: 1};
            render();
        });
    }
}

document.getElementById('zoom').oninput = e => {
    zoom = parseFloat(e.target.value);
    document.getElementById('zv').textContent = zoom.toFixed(1) + 'x';
    render();
};

document.body.focus();
fullView();
</script>
</body>
</html>
'''

# ============================================
# FLASK
# ============================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cyto'
socketio = SocketIO(app, cors_allowed_origins="*")

init_db()
engine = TimeEngine()

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/cycle', methods=['POST'])
def api_cycle():
    engine.set_cycle(request.json.get('hours', 36))
    return jsonify({'ok': True})

@app.route('/api/speed', methods=['POST'])
def api_speed():
    engine.set_speed(request.json.get('speed', 1))
    return jsonify({'ok': True})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    engine.hard_reset()
    socketio.emit('nodes', [])
    return jsonify({'ok': True})

@app.route('/api/clear', methods=['POST'])
def api_clear():
    clear_nodes()
    socketio.emit('nodes', [])
    return jsonify({'ok': True})

@app.route('/api/test_nodes', methods=['POST'])
def api_test():
    import random
    pos = engine.get_position()
    ts = int(pos['theta']) % 360
    w = pos['w']
    now = datetime.now().isoformat()
    
    for i in range(5):
        for typ in ['sync', 'integration']:
            y = random.randint(0, 5)
            z = random.randint(0, 9)
            t = (ts + random.randint(-15, 15)) % 360
            nid = save_node(typ, f'{typ[:1].upper()}{i}', t, y, z, w, now, 'test')
            socketio.emit('node', {'id': nid, 'node_type': typ, 'theta_slot': t, 'y_level': y, 'z_slot': z, 'w_layer': w})
    return jsonify({'ok': True})

@app.route('/api/import_node', methods=['POST'])
def api_import():
    data = request.json
    node_type = data.get('type', 'sync')
    content = data.get('content', '')
    y_level = data.get('y_level', 0)
    z_slot = data.get('z_slot', 0)
    ts_str = data.get('timestamp', datetime.now().isoformat())
    
    try:
        ts = datetime.fromisoformat(ts_str)
    except:
        ts = datetime.now()
    
    pos = engine.timestamp_to_position(ts)
    if not pos:
        return jsonify({'error': 'Timestamp before epoch'}), 400
    
    nid = save_node(node_type, content, pos['theta_slot'], y_level, z_slot, pos['w'], ts_str, 'api')
    node = {'id': nid, 'node_type': node_type, 'content': content, 'theta_slot': pos['theta_slot'], 'y_level': y_level, 'z_slot': z_slot, 'w_layer': pos['w']}
    socketio.emit('node', node)
    return jsonify({'ok': True, 'node': node})

@socketio.on('connect')
def on_connect():
    pass

@socketio.on('get_nodes')
def on_get_nodes():
    emit('nodes', get_all_nodes())

def broadcast():
    while True:
        p = engine.get_position()
        now = datetime.now()
        socketio.emit('state', {
            'time': now.strftime('%I:%M:%S %p'),
            'date': now.strftime('%B %d, %Y'),
            'w': p['w'],
            'theta': p['theta'],
            'section': p['section'],
            'progress': p['progress'],
            'total_hours': p['total_hours'],
            'cycle_hours': p['cycle_hours'],
            'speed': p['speed'],
            'epoch': p['epoch']
        })
        time.sleep(0.1)

if __name__ == '__main__':
    threading.Thread(target=broadcast, daemon=True).start()
    
    # Show startup info
    pos = engine.get_position()
    print("\n" + "="*50)
    print("CYTO - 4D Temporal Database")
    print("="*50)
    print(f"Epoch: {engine.epoch}")
    print(f"Running: {pos['total_hours']:.2f} hours")
    print(f"Current: W{pos['w']} at {pos['theta']:.1f}°")
    print("="*50)
    print("http://localhost:5000")
    print("="*50 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
