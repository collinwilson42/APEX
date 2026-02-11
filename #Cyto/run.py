"""
TORRA / CYTO - 4D Temporal Database UI
Asset classes → Algo instances → W-layers
Epoch locks on first real data sample
Default view: current 72-hour window
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
import threading
import time
import sqlite3
import os
import json

# ============================================
# CONSTANTS
# ============================================

PHI = 1.618033988749895
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyto.db")

ASSET_CLASSES = [
    {"id": "oil", "name": "Crude Oil", "symbol": "USOILH26"},
    {"id": "gold", "name": "Gold", "symbol": "XAUJ26"},
    {"id": "btc", "name": "Bitcoin", "symbol": "BTCF26"},
    {"id": "us30", "name": "US30", "symbol": "US30H26"},
    {"id": "us100", "name": "US100", "symbol": "US100H26"},
    {"id": "us500", "name": "US500", "symbol": "US500H26"},
]

# ============================================
# DATABASE
# ============================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Config table
    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Asset classes
    c.execute("""
        CREATE TABLE IF NOT EXISTS asset_classes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Algo instances within asset classes
    c.execute("""
        CREATE TABLE IF NOT EXISTS algo_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_class_id TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'inactive',
            config TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_class_id) REFERENCES asset_classes(id)
        )
    """)

    # Generic nodes - structure first, meaning later
    c.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_class_id TEXT NOT NULL,
            instance_id INTEGER,
            node_type TEXT NOT NULL DEFAULT 'data',
            content TEXT,
            timestamp TEXT NOT NULL,
            w_layer INTEGER NOT NULL DEFAULT 1,
            theta REAL NOT NULL DEFAULT 0,
            meta TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_class_id) REFERENCES asset_classes(id),
            FOREIGN KEY (instance_id) REFERENCES algo_instances(id)
        )
    """)

    # Seed default asset classes
    for ac in ASSET_CLASSES:
        c.execute("INSERT OR IGNORE INTO asset_classes (id, name, symbol) VALUES (?, ?, ?)",
                  (ac["id"], ac["name"], ac["symbol"]))

    conn.commit()
    conn.close()
    print(f"✓ Database: {DB_PATH}")

def get_config(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else default

def set_config(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_asset_classes():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM asset_classes ORDER BY name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_instances(asset_class_id=None):
    conn = get_connection()
    c = conn.cursor()
    if asset_class_id:
        c.execute("SELECT * FROM algo_instances WHERE asset_class_id = ? ORDER BY name", (asset_class_id,))
    else:
        c.execute("SELECT * FROM algo_instances ORDER BY asset_class_id, name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def create_instance(asset_class_id, name, config=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO algo_instances (asset_class_id, name, config) VALUES (?, ?, ?)",
              (asset_class_id, name, json.dumps(config or {})))
    iid = c.lastrowid
    conn.commit()
    conn.close()
    return iid

def get_nodes(asset_class_id=None, instance_id=None, hours=72):
    """Get nodes within the time window. Default 72 hours."""
    conn = get_connection()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    query = "SELECT * FROM nodes WHERE timestamp >= ?"
    params = [cutoff]
    
    if asset_class_id:
        query += " AND asset_class_id = ?"
        params.append(asset_class_id)
    if instance_id:
        query += " AND instance_id = ?"
        params.append(instance_id)
    
    query += " ORDER BY timestamp DESC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_node_count():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM nodes")
    cnt = c.fetchone()['cnt']
    conn.close()
    return cnt

def save_node(asset_class_id, instance_id, node_type, content, timestamp, w_layer, theta, meta=None):
    # Lock epoch on first real data
    epoch_str = get_config('epoch')
    if not epoch_str:
        set_config('epoch', timestamp)
        print(f"✓ Epoch locked: {timestamp}")
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO nodes (asset_class_id, instance_id, node_type, content, timestamp, w_layer, theta, meta)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (asset_class_id, instance_id, node_type, content, timestamp, w_layer, theta, json.dumps(meta or {})))
    nid = c.lastrowid
    conn.commit()
    conn.close()
    return nid

def clear_nodes():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM nodes")
    conn.commit()
    conn.close()

# ============================================
# TIME ENGINE
# ============================================

class TimeEngine:
    def __init__(self):
        self.cycle_hours = float(get_config('cycle_hours', '72'))
        epoch_str = get_config('epoch')
        if epoch_str:
            self.epoch = datetime.fromisoformat(epoch_str)
            hours_elapsed = (datetime.now() - self.epoch).total_seconds() / 3600
            print(f"✓ Epoch loaded: {self.epoch}")
            print(f"  Hours elapsed: {hours_elapsed:.2f}")
        else:
            self.epoch = None
            print("✓ No epoch yet — will lock on first data")

    def get_position(self):
        now = datetime.now()
        if not self.epoch:
            return {
                'w': 0, 'theta': 0, 'section': 0, 'progress': 0,
                'total_hours': 0, 'cycle_hours': self.cycle_hours,
                'epoch': None, 'epoch_set': False
            }
        
        total_hours = (now - self.epoch).total_seconds() / 3600
        w = max(1, int(total_hours // self.cycle_hours) + 1)
        hours_in_cycle = total_hours % self.cycle_hours
        theta = (hours_in_cycle / self.cycle_hours) * 360
        
        return {
            'w': w,
            'theta': theta,
            'section': int(theta / 40) + 1 if theta >= 0 else 1,
            'progress': hours_in_cycle / self.cycle_hours,
            'total_hours': total_hours,
            'cycle_hours': self.cycle_hours,
            'epoch': self.epoch.isoformat(),
            'epoch_set': True
        }

    def timestamp_to_w(self, timestamp_str):
        """Convert timestamp to W-layer based on epoch and cycle."""
        if not self.epoch:
            return 1
        try:
            ts = datetime.fromisoformat(timestamp_str)
        except:
            return 1
        hours = (ts - self.epoch).total_seconds() / 3600
        return max(1, int(hours // self.cycle_hours) + 1)

    def timestamp_to_theta(self, timestamp_str):
        """Convert timestamp to theta position within its cycle."""
        if not self.epoch:
            return 0
        try:
            ts = datetime.fromisoformat(timestamp_str)
        except:
            return 0
        hours = (ts - self.epoch).total_seconds() / 3600
        hours_in_cycle = hours % self.cycle_hours
        return (hours_in_cycle / self.cycle_hours) * 360


# ============================================
# FLASK APP
# ============================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'torra'
socketio = SocketIO(app, cors_allowed_origins="*")

init_db()
engine = TimeEngine()

@app.route('/')
def index():
    return render_template('cyto.html')

# --- Asset Classes ---
@app.route('/api/classes', methods=['GET'])
def api_classes():
    return jsonify(get_asset_classes())

# --- Instances ---
@app.route('/api/instances', methods=['GET'])
def api_instances():
    ac = request.args.get('class')
    return jsonify(get_instances(ac))

@app.route('/api/instances', methods=['POST'])
def api_create_instance():
    data = request.json
    iid = create_instance(data['asset_class_id'], data['name'], data.get('config'))
    return jsonify({'ok': True, 'id': iid})

# --- Nodes ---
@app.route('/api/nodes', methods=['GET'])
def api_nodes():
    ac = request.args.get('class')
    inst = request.args.get('instance')
    hours = int(request.args.get('hours', 72))
    return jsonify(get_nodes(ac, inst, hours))

@app.route('/api/nodes', methods=['POST'])
def api_add_node():
    data = request.json
    ts = data.get('timestamp', datetime.now().isoformat())
    w = engine.timestamp_to_w(ts)
    theta = engine.timestamp_to_theta(ts)
    
    nid = save_node(
        data['asset_class_id'],
        data.get('instance_id'),
        data.get('type', 'data'),
        data.get('content', ''),
        ts, w, theta,
        data.get('meta')
    )
    
    # Reload epoch if it just got set
    if not engine.epoch:
        epoch_str = get_config('epoch')
        if epoch_str:
            engine.epoch = datetime.fromisoformat(epoch_str)
    
    node = {'id': nid, 'asset_class_id': data['asset_class_id'],
            'instance_id': data.get('instance_id'), 'node_type': data.get('type', 'data'),
            'content': data.get('content', ''), 'timestamp': ts, 'w_layer': w, 'theta': theta}
    socketio.emit('node', node)
    return jsonify({'ok': True, 'node': node})

@app.route('/api/nodes/clear', methods=['POST'])
def api_clear_nodes():
    clear_nodes()
    socketio.emit('nodes', [])
    return jsonify({'ok': True})

# --- Stats ---
@app.route('/api/stats', methods=['GET'])
def api_stats():
    pos = engine.get_position()
    return jsonify({
        'position': pos,
        'node_count': get_node_count(),
        'class_count': len(ASSET_CLASSES),
        'instance_count': len(get_instances())
    })

# --- Socket ---
@socketio.on('connect')
def on_connect():
    pass

@socketio.on('get_state')
def on_get_state():
    pos = engine.get_position()
    now = datetime.now()
    emit('state', {
        'time': now.strftime('%I:%M:%S %p'),
        'date': now.strftime('%B %d, %Y'),
        **pos,
        'node_count': get_node_count(),
    })

def broadcast():
    while True:
        pos = engine.get_position()
        now = datetime.now()
        socketio.emit('state', {
            'time': now.strftime('%I:%M:%S %p'),
            'date': now.strftime('%B %d, %Y'),
            **pos,
            'node_count': get_node_count(),
        })
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=broadcast, daemon=True).start()
    
    pos = engine.get_position()
    print("\n" + "="*50)
    print("TORRA / CYTO - 4D Temporal Database")
    print("="*50)
    if engine.epoch:
        print(f"Epoch: {engine.epoch}")
        print(f"Running: {pos['total_hours']:.2f} hours")
        print(f"Current: W{pos['w']} at {pos['theta']:.1f}°")
    else:
        print("Epoch: Not set (waiting for first data)")
    print(f"Asset Classes: {len(ASSET_CLASSES)}")
    print(f"Instances: {len(get_instances())}")
    print("="*50)
    print("http://localhost:5000")
    print("="*50 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
