"""
CYTO 4D Database Schema - Updated for Hexadic Inline Anchors

Tables:
- nodes: Core data nodes with 4D coordinates + anchor support
- links: Connections between nodes
- layers: W-layer metadata and zoom state
"""

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "cyto.db"


def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema with anchor support."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Nodes table - NOW SUPPORTS ANCHORS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_type TEXT NOT NULL CHECK(node_type IN ('anchor', 'sync', 'integration', 'root')),
            content TEXT,
            
            -- 4D Position
            theta REAL NOT NULL,
            radius REAL NOT NULL,  -- 1.000 for anchors, variable for sync/integration
            z REAL DEFAULT 0.0,
            w INTEGER NOT NULL DEFAULT 1,
            section INTEGER NOT NULL,
            
            -- Anchor-specific fields (NULL for non-anchors)
            anchor_string TEXT UNIQUE,          -- Full anchor: v1.5 r5 d.RODIN a8 c8 t.NOW
            version_major INTEGER,
            version_minor INTEGER,
            resonance_station INTEGER CHECK(resonance_station IN (1,2,4,5,7,8) OR resonance_station IS NULL),
            domain TEXT,
            alignment_station INTEGER CHECK(alignment_station IN (1,2,4,5,7,8) OR alignment_station IS NULL),
            confidence_station INTEGER CHECK(confidence_station IN (1,2,4,5,7,8) OR confidence_station IS NULL),
            temporal_marker TEXT,
            
            -- Sync/Integration node fields
            anchor_id INTEGER,                  -- Which anchor spawned this node
            parent_id INTEGER,                  -- Tree hierarchy
            depth INTEGER DEFAULT 0,            -- Distance from anchor
            
            -- Metadata
            source TEXT DEFAULT 'manual',       -- 'claude_chat', 'api', 'manual'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (anchor_id) REFERENCES nodes(id),
            FOREIGN KEY (parent_id) REFERENCES nodes(id)
        )
    """)
    
    # Create indexes for fast queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON nodes(node_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anchor_string ON nodes(anchor_string)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON nodes(domain)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resonance ON nodes(resonance_station)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_theta ON nodes(theta)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_w_layer ON nodes(w)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON nodes(created_at)")
    
    # Links table - connections between nodes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            link_type TEXT DEFAULT 'reference',
            strength REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES nodes(id),
            FOREIGN KEY (target_id) REFERENCES nodes(id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_link_source ON links(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_link_target ON links(target_id)")
    
    # Layers table - W-layer metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS layers (
            w INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            node_count INTEGER DEFAULT 0,
            anchor_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # View state - current zoom and active layers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS view_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            max_visible_w INTEGER DEFAULT 1,
            zoom_scale REAL DEFAULT 1.0,
            rotation_offset REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Initialize view state if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO view_state (id, max_visible_w, zoom_scale)
        VALUES (1, 1, 1.0)
    """)
    
    # Initialize W=1 layer
    cursor.execute("""
        INSERT OR IGNORE INTO layers (w) VALUES (1)
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ CYTO database initialized with anchor support at {DB_PATH}")


def create_anchor_node(anchor_data):
    """
    Create an inline anchor node on the 1.000 line.
    
    Args:
        anchor_data: Dict with anchor properties
        {
            'anchor_string': 'v1.5 r5 d.RODIN a8 c8 t.NOW',
            'timestamp': datetime object,
            'version_major': 1,
            'version_minor': 5,
            'resonance_station': 5,
            'domain': 'RODIN',
            'alignment_station': 8,
            'confidence_station': 8,
            'temporal_marker': 'NOW',
            'source': 'claude_chat'
        }
    
    Returns:
        node_id of created anchor
    """
    from .position import TimeMapper
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calculate theta from timestamp
    time_mapper = TimeMapper()
    theta = time_mapper.time_to_theta(anchor_data['timestamp'])
    section = time_mapper.theta_to_section(theta)
    
    # Anchors always at radius 1.000 (golden ratio baseline)
    radius = 1.000
    
    # Always W=1 for new anchors (current time layer)
    w_layer = 1
    
    cursor.execute("""
        INSERT INTO nodes (
            node_type, content, theta, radius, z, w, section,
            anchor_string, version_major, version_minor,
            resonance_station, domain, alignment_station,
            confidence_station, temporal_marker, source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'anchor',
        anchor_data['anchor_string'],
        theta,
        radius,
        0.0,
        w_layer,
        section,
        anchor_data['anchor_string'],
        anchor_data['version_major'],
        anchor_data['version_minor'],
        anchor_data['resonance_station'],
        anchor_data['domain'],
        anchor_data['alignment_station'],
        anchor_data['confidence_station'],
        anchor_data['temporal_marker'],
        anchor_data.get('source', 'manual'),
        anchor_data['timestamp']
    ))
    
    node_id = cursor.lastrowid
    
    # Update layer anchor count
    cursor.execute("""
        UPDATE layers SET anchor_count = anchor_count + 1 WHERE w = ?
    """, (w_layer,))
    
    conn.commit()
    conn.close()
    
    return node_id


def get_all_anchors(w_layer=None):
    """Get all anchor nodes, optionally filtered by W-layer."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if w_layer:
        cursor.execute("""
            SELECT * FROM nodes 
            WHERE node_type = 'anchor' AND w = ?
            ORDER BY created_at DESC
        """, (w_layer,))
    else:
        cursor.execute("""
            SELECT * FROM nodes 
            WHERE node_type = 'anchor'
            ORDER BY created_at DESC
        """)
    
    anchors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return anchors


def get_anchors_in_time_range(start_time, end_time):
    """Get anchors within a time range."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM nodes
        WHERE node_type = 'anchor'
          AND created_at BETWEEN ? AND ?
        ORDER BY created_at ASC
    """, (start_time, end_time))
    
    anchors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return anchors


def get_max_w_layer():
    """Get the highest W-layer with nodes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(w) as max_w FROM nodes")
    result = cursor.fetchone()
    conn.close()
    return result['max_w'] if result['max_w'] else 1


def update_zoom_for_layers():
    """Update zoom scale based on max visible layer."""
    from .position import LayerGeometry
    
    max_w = get_max_w_layer()
    zoom_scale = LayerGeometry.get_zoom_scale(max_w)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE view_state 
        SET max_visible_w = ?, zoom_scale = ?, updated_at = ?
        WHERE id = 1
    """, (max_w, zoom_scale, datetime.now()))
    conn.commit()
    conn.close()
    
    return zoom_scale


def get_view_state():
    """Get current view state."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM view_state WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else {'max_visible_w': 1, 'zoom_scale': 1.0}


# Station color mapping (for reference)
STATION_COLORS = {
    1: '#ADEBB3',  # Unity - Mint
    2: '#20B2AA',  # Duality - Teal
    4: '#6B8DD6',  # Structure - Blue
    5: '#C084FC',  # Change - Magenta
    7: '#D4AF37',  # Mystery - Golden
    8: '#F4E4C1'   # Infinity - Light Gold
}


if __name__ == "__main__":
    init_db()
