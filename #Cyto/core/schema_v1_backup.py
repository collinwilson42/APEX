"""
CYTO 4D Database Schema

Tables:
- nodes: Core data nodes with 4D coordinates
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
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Nodes table - 4D positioned data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_type TEXT NOT NULL CHECK(node_type IN ('sync', 'integration', 'root')),
            content TEXT,
            theta REAL NOT NULL,
            radius REAL NOT NULL,
            z REAL DEFAULT 0.0,
            w INTEGER NOT NULL DEFAULT 1,
            section INTEGER NOT NULL,
            parent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES nodes(id)
        )
    """)
    
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
    
    # Layers table - W-layer metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS layers (
            w INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            node_count INTEGER DEFAULT 0,
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
    print(f"✓ CYTO database initialized at {DB_PATH}")


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


if __name__ == "__main__":
    init_db()
