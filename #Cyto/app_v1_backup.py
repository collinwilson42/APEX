"""
CYTO - 4D Temporal Database UI

Flask server with WebSocket for real-time updates.
Layers expand outward, view zooms dynamically.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import threading
import time

from core import init_db, get_view_state, update_zoom_for_layers, LayerGeometry

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


@app.route('/api/add_layer', methods=['POST'])
def add_layer():
    """Add a new W-layer (expands outward)."""
    from core.schema import get_connection
    
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


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"Client connected")
    # Send initial state
    view_state = get_view_state()
    emit('initial_state', view_state)


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


if __name__ == '__main__':
    # Start time broadcast thread
    time_thread = threading.Thread(target=time_broadcast_thread, daemon=True)
    time_thread.start()
    
    print("\n" + "="*50)
    print("CYTO - 4D Temporal Database")
    print("="*50)
    print("Starting server at http://localhost:5000")
    print("Layers expand outward with dynamic zoom")
    print("="*50 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
