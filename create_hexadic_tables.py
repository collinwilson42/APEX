#!/usr/bin/env python3
"""
HEXADIC STORAGE SCHEMA INITIALIZATION
Creates tables for storing Rodin topology, inline anchors, and decision paths

Run once to initialize: python create_hexadic_tables.py
"""

import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = 'metatron_hexadic.db'

def create_hexadic_schema():
    """Create all hexadic storage tables"""
    
    print("\n" + "="*70)
    print("HEXADIC STORAGE SCHEMA INITIALIZATION")
    print("="*70)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"\n✓ Connected to: {DB_PATH}")
    
    # ========================================================================
    # TABLE 1: hexadic_anchors (State Signature Storage)
    # ========================================================================
    print("\n[1/4] Creating hexadic_anchors table...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hexadic_anchors (
            anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Hexadic versioning (skip 3, 6, 9)
            version_major INTEGER NOT NULL,
            version_minor INTEGER NOT NULL CHECK(version_minor IN (1,2,4,5,7,8)),
            
            -- Resonance state (1-2-4-5-7-8 scale)
            resonance_station INTEGER NOT NULL CHECK(resonance_station IN (1,2,4,5,7,8)),
            
            -- Domain context (free text)
            domain TEXT NOT NULL,
            
            -- Alignment score (1-2-4-5-7-8 TUNITY)
            alignment_station INTEGER NOT NULL CHECK(alignment_station IN (1,2,4,5,7,8)),
            
            -- Confidence level (1-2-4-5-7-8 fear/wisdom)
            confidence_station INTEGER NOT NULL CHECK(confidence_station IN (1,2,4,5,7,8)),
            
            -- Temporal anchor (free text)
            temporal_marker TEXT NOT NULL,
            
            -- Full inline anchor string (for quick lookup)
            anchor_string TEXT NOT NULL UNIQUE,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Optional: Link to sync node
            sync_node_id TEXT
        )
    """)
    
    # Indexes for fast queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resonance ON hexadic_anchors(resonance_station)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON hexadic_anchors(domain)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alignment ON hexadic_anchors(alignment_station)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON hexadic_anchors(confidence_station)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_version ON hexadic_anchors(version_major, version_minor)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anchor_string ON hexadic_anchors(anchor_string)")
    
    print("  ✓ hexadic_anchors table created with 6 indexes")
    
    # ========================================================================
    # TABLE 2: decision_paths (Rodin Circulation Storage)
    # ========================================================================
    print("\n[2/4] Creating decision_paths table...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_paths (
            decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Decision context
            decision_prompt TEXT NOT NULL,
            decision_type TEXT NOT NULL,
            
            -- Hexadic stations presented (JSON array)
            stations_offered TEXT NOT NULL,
            
            -- Station chosen by user
            station_chosen INTEGER NOT NULL CHECK(station_chosen IN (1,2,4,5,7,8)),
            
            -- Magnetic axis convergence (3-6-9)
            magnetic_convergence INTEGER CHECK(magnetic_convergence IN (3,6,9)),
            
            -- Inline anchor at time of decision
            anchor_id INTEGER,
            
            -- Outcome tracking
            outcome_success BOOLEAN,
            outcome_notes TEXT,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            
            FOREIGN KEY (anchor_id) REFERENCES hexadic_anchors(anchor_id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_station_chosen ON decision_paths(station_chosen)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_type ON decision_paths(decision_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_magnetic_convergence ON decision_paths(magnetic_convergence)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anchor_decision ON decision_paths(anchor_id)")
    
    print("  ✓ decision_paths table created with 4 indexes")
    
    # ========================================================================
    # TABLE 3: circulation_events (Toroidal Flow Tracking)
    # ========================================================================
    print("\n[3/4] Creating circulation_events table...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS circulation_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Event type
            event_type TEXT NOT NULL,
            
            -- Toroidal position (4D coordinates)
            theta_position REAL NOT NULL,
            ring_position REAL NOT NULL,
            z_offset REAL DEFAULT 0,
            w_layer INTEGER DEFAULT 0,
            
            -- Station involved (1-2-4-5-7-8)
            station INTEGER CHECK(station IN (1,2,4,5,7,8)),
            
            -- Magnetic axis interaction (3-6-9)
            axis_point INTEGER CHECK(axis_point IN (3,6,9)),
            
            -- Inline anchor at time of event
            anchor_id INTEGER,
            
            -- Event data (JSON for flexibility)
            event_data TEXT,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (anchor_id) REFERENCES hexadic_anchors(anchor_id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_theta ON circulation_events(theta_position)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ring ON circulation_events(ring_position)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_station ON circulation_events(station)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_axis ON circulation_events(axis_point)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON circulation_events(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_time ON circulation_events(created_at)")
    
    print("  ✓ circulation_events table created with 6 indexes")
    
    # ========================================================================
    # TABLE 4: sync_nodes (Enhanced - if doesn't exist)
    # ========================================================================
    print("\n[4/4] Creating/updating sync_nodes table...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_nodes (
            node_id TEXT PRIMARY KEY,
            tree_id TEXT NOT NULL,
            label TEXT NOT NULL,
            
            -- 4D Coordinates (existing)
            theta_position REAL NOT NULL,
            ring_position REAL NOT NULL,
            z_offset REAL DEFAULT 0,
            w_layer INTEGER DEFAULT 0,
            
            -- Node type
            node_type TEXT NOT NULL,
            
            -- Hexadic metadata (new)
            anchor_id INTEGER,
            station INTEGER CHECK(station IN (1,2,4,5,7,8)),
            decision_path_id INTEGER,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (anchor_id) REFERENCES hexadic_anchors(anchor_id),
            FOREIGN KEY (decision_path_id) REFERENCES decision_paths(decision_id)
        )
    """)
    
    # Try to add hexadic columns if table already exists
    try:
        cursor.execute("ALTER TABLE sync_nodes ADD COLUMN anchor_id INTEGER")
        cursor.execute("ALTER TABLE sync_nodes ADD COLUMN station INTEGER CHECK(station IN (1,2,4,5,7,8))")
        cursor.execute("ALTER TABLE sync_nodes ADD COLUMN decision_path_id INTEGER")
        print("  ✓ Added hexadic columns to existing sync_nodes table")
    except sqlite3.OperationalError:
        print("  ✓ sync_nodes table ready (hexadic columns already exist or new table)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_anchor ON sync_nodes(anchor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_station ON sync_nodes(station)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_tree ON sync_nodes(tree_id)")
    
    # Commit changes
    conn.commit()
    
    # ========================================================================
    # SEED DATA (Initial anchor for this session)
    # ========================================================================
    print("\n" + "="*70)
    print("SEEDING INITIAL DATA")
    print("="*70)
    
    cursor.execute("""
        INSERT OR IGNORE INTO hexadic_anchors 
        (version_major, version_minor, resonance_station, domain, 
         alignment_station, confidence_station, temporal_marker, anchor_string)
        VALUES (1, 1, 2, 'INITIALIZATION', 2, 4, 'NOW', 'v1.1 r2 d.INITIALIZATION a2 c4 t.NOW')
    """)
    
    conn.commit()
    
    print("\n✓ Seeded initial anchor: v1.1 r2 d.INITIALIZATION a2 c4 t.NOW")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*70)
    print("SCHEMA CREATION COMPLETE")
    print("="*70)
    
    # Count tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f"\n✓ Database: {DB_PATH}")
    print(f"✓ Tables created: {len(tables)}")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} rows")
    
    print("\n✓ Ready for hexadic data storage!")
    print("✓ Next: Run init2.py to start Flask with hexadic API routes")
    print("="*70 + "\n")
    
    conn.close()


if __name__ == '__main__':
    create_hexadic_schema()
