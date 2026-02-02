"""
CYTO - 4D Temporal Database UI with Live Inline Anchor Streaming

Flask server with WebSocket for real-time anchor updates.
Anchors appear on 1.000 line, sync/integration nodes branch from them.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import threading
import time
import re

from core import init_db, get_view_state, update_zoom_for_layers, LayerGeometry
from core.schema_updated import create_anchor_node, get_all_anchors, STATION_COLORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cyto_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database on startup
init_db()


@app.route('/')
def index():
    """Serve main UI."""
    return render_template('index.html')


@app.route('/api/layers')
def get_layers():
    """Get all layer geometries for rendering."""
    view_state = get_view_state()
    max_w = view_state.get('max_visible_w', 1)
    
    layers = []
    for w in range(1, max_w + 1):
        geo = LayerGeometry(w)
        layers.append({
            'w': w,
            'inner': geo.inner,
            'mid': geo.mid,
            'outer': geo.outer
        })
    
    return jsonify({
        'layers': layers,
        'zoom_scale': view_state.get('zoom_scale', 1.0),
        'max_w': max_w
    })


@app.route('/api/anchors')
def get_anchors_api():
    """Get all inline anchor nodes."""
    w_layer = request.args.get('w', type=int)
    anchors = get_all_anchors(w_layer)
    return jsonify({'success': True, 'anchors': anchors, 'count': len(anchors)})


@app.route('/api/anchor/create', methods=['POST'])
def api_create_anchor():
    """
    Create inline anchor from API call.
    
    POST body:
    {
        "anchor_string": "v1.5 r5 d.RODIN a8 c8 t.NOW",
        "source": "claude_chat" | "api" | "manual"
    }
    """
    data = request.get_json()
    anchor_string = data.get('anchor_string')
    
    if not anchor_string:
        return jsonify({'success': False, 'error': 'anchor_string required'}), 400
    
    # Parse anchor string
    parsed = parse_anchor_string(anchor_string)
    if not parsed:
        return jsonify({'success': False, 'error': 'Invalid anchor format'}), 400
    
    # Add metadata
    parsed['anchor_string'] = anchor_string
    parsed['timestamp'] = datetime.now()
    parsed['source'] = data.get('source', 'api')
    
    try:
        # Create node
        node_id = create_anchor_node(parsed)
        
        # Broadcast to all clients
        broadcast_anchor_created(node_id, parsed)
        
        return jsonify({
            'success': True,
            'node_id': node_id,
            'anchor': anchor_string
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/add_layer', methods=['POST'])
def add_layer():
    """Add a new W-layer (expands outward)."""
    from core.schema_updated import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current max W
    cursor.execute("SELECT MAX(w) as max_w FROM layers")
    result = cursor.fetchone()
    current_max = result['max_w'] if result['max_w'] else 1
    
    # Add new layer
    new_w = current_max + 1
    cursor.execute("INSERT INTO layers (w) VALUES (?)", (new_w,))
    conn.commit()
    conn.close()
    
    # Update zoom
    zoom_scale = update_zoom_for_layers()
    
    # Get new layer geometry
    geo = LayerGeometry(new_w)
    
    # Broadcast to all clients
    socketio.emit('layer_added', {
        'w': new_w,
        'inner': geo.inner,
        'mid': geo.mid,
        'outer': geo.outer,
        'zoom_scale': zoom_scale
    })
    
    return jsonify({'success': True, 'new_w': new_w, 'zoom_scale': zoom_scale})


@app.route('/api/view_state')
def api_view_state():
    """Get current view state."""
    return jsonify(get_view_state())


# ============================================================================
# WEBSOCKET HANDLERS - Live Anchor Streaming
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"✓ Client connected")
    
    # Send initial state
    view_state = get_view_state()
    emit('initial_state', view_state)
    
    # Send all existing anchors
    anchors = get_all_anchors()
    emit('initial_anchors', {
        'anchors': anchors,
        'count': len(anchors)
    })


@socketio.on('anchor_created')
def handle_anchor_created(data):
    """
    Receive inline anchor from Claude session (live stream).
    
    Data format:
    {
        "anchor_string": "v1.5 r5 d.RODIN a8 c8 t.NOW",
        "timestamp": "2026-01-21T10:15:23",
        "source": "claude_chat"
    }
    """
    print(f"📡 Anchor received: {data.get('anchor_string')}")
    
    anchor_string = data.get('anchor_string')
    if not anchor_string:
        emit('error', {'message': 'Missing anchor_string'})
        return
    
    # Parse anchor
    parsed = parse_anchor_string(anchor_string)
    if not parsed:
        emit('error', {'message': 'Invalid anchor format'})
        return
    
    # Add metadata
    parsed['anchor_string'] = anchor_string
    parsed['timestamp'] = datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now()
    parsed['source'] = data.get('source', 'websocket')
    
    try:
        # Create node in database
        node_id = create_anchor_node(parsed)
        
        # Broadcast to ALL clients (including sender)
        broadcast_anchor_created(node_id, parsed)
        
        print(f"✓ Anchor created: ID={node_id}, Station={parsed['resonance_station']}, Domain={parsed['domain']}")
        
    except Exception as e:
        print(f"✗ Error creating anchor: {e}")
        emit('error', {'message': str(e)})


@socketio.on('request_layers')
def handle_request_layers():
    """Client requesting layer data."""
    view_state = get_view_state()
    max_w = view_state.get('max_visible_w', 1)
    
    layers = []
    for w in range(1, max_w + 1):
        geo = LayerGeometry(w)
        layers.append({
            'w': w,
            'inner': geo.inner,
            'mid': geo.mid,
            'outer': geo.outer
        })
    
    emit('layers_data', {
        'layers': layers,
        'zoom_scale': view_state.get('zoom_scale', 1.0)
    })


@socketio.on('request_anchors')
def handle_request_anchors(data=None):
    """Client requesting all anchors."""
    w_layer = data.get('w') if data else None
    anchors = get_all_anchors(w_layer)
    
    emit('anchors_data', {
        'anchors': anchors,
        'count': len(anchors)
    })


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_anchor_string(anchor_str):
    """
    Parse inline anchor string into components.
    
    Format: v1.5 r5 d.RODIN a8 c8 t.NOW
    
    Returns dict or None if invalid.
    """
    # Pattern: v{major}.{minor} r{station} d.{domain} a{align} c{conf} t.{temporal}
    pattern = r'v(\d+)\.(\d+)\s+r(\d)\s+d\.(\w+)\s+a(\d)\s+c(\d)\s+t\.(\w+)'
    match = re.match(pattern, anchor_str.strip())
    
    if not match:
        return None
    
    return {
        'version_major': int(match.group(1)),
        'version_minor': int(match.group(2)),
        'resonance_station': int(match.group(3)),
        'domain': match.group(4),
        'alignment_station': int(match.group(5)),
        'confidence_station': int(match.group(6)),
        'temporal_marker': match.group(7)
    }


def broadcast_anchor_created(node_id, anchor_data):
    """Broadcast anchor creation to all connected clients."""
    from core.position import TimeMapper
    
    # Calculate position
    time_mapper = TimeMapper()
    theta = time_mapper.time_to_theta(anchor_data['timestamp'])
    section = time_mapper.theta_to_section(theta)
    
    # Get station color
    station = anchor_data['resonance_station']
    color = STATION_COLORS.get(station, '#FFFFFF')
    
    socketio.emit('anchor_added', {
        'id': node_id,
        'anchor_string': anchor_data['anchor_string'],
        'theta': theta,
        'radius': 1.000,  # Always on the golden ratio line
        'w': 1,
        'section': section,
        'station': station,
        'domain': anchor_data['domain'],
        'alignment': anchor_data['alignment_station'],
        'confidence': anchor_data['confidence_station'],
        'temporal': anchor_data['temporal_marker'],
        'color': color,
        'timestamp': anchor_data['timestamp'].isoformat(),
        'source': anchor_data.get('source', 'unknown')
    })


def time_broadcast_thread():
    """Background thread to broadcast current time."""
    while True:
        now = datetime.now()
        socketio.emit('time_update', {
            'time': now.strftime('%I:%M:%S %p'),
            'date': now.strftime('%B %d, %Y'),
            'timestamp': now.isoformat()
        })
        time.sleep(1)


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    # Start time broadcast thread
    time_thread = threading.Thread(target=time_broadcast_thread, daemon=True)
    time_thread.start()
    
    print("\n" + "="*60)
    print("CYTO - 4D Temporal Database with Live Anchor Streaming")
    print("="*60)
    print("Server:  http://localhost:5000")
    print("WebSocket: Live anchor stream active")
    print("="*60)
    print("\n📡 Listening for inline anchors...")
    print("✨ Anchors appear on the 1.000 golden ratio line")
    print("🎨 Color-coded by station (r-value)")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
