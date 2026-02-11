"""
CYTO v3 - Trading Intelligence Database Schema
Adapts the continuity database for simulation instance tracking.

288 Slots = 72 Hours @ 15-minute bars
Radius = P/L Percentile (0.618 to 1.618)
Z-Layer = Instance ID
"""

import sqlite3
import os
import json
from datetime import datetime

# ============================================
# CONSTANTS
# ============================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyto_v3.db")

SLOT_COUNT = 288  # 72 hours / 15 minutes = 288 bars
SLOT_MINUTES = 15
CYCLE_HOURS = 72

# Fibonacci percentile bands
RADIUS_FLOOR = 0.618    # Bottom 10%
RADIUS_MEDIAN = 1.000   # 50th percentile
RADIUS_CEILING = 1.618  # Top 90%

# Reference epoch for theta calculation
REFERENCE_EPOCH = datetime(2024, 1, 1, 0, 0, 0)

# ============================================
# DATABASE CONNECTION
# ============================================

def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================
# SCHEMA DEFINITION
# ============================================

def init_db():
    """Initialize the CytoBase schema for trading intelligence."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # ========================================
    # TABLE: cyto_instances
    # Tracks each simulation run / config version
    # ========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cyto_instances (
            instance_id     TEXT PRIMARY KEY,
            symbol          TEXT NOT NULL,
            profile_name    TEXT,
            config_snapshot TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at    TIMESTAMP,
            status          TEXT DEFAULT 'running' 
                            CHECK(status IN ('running', 'completed', 'failed', 'paused')),
            total_trades    INTEGER DEFAULT 0,
            total_pnl       REAL DEFAULT 0.0,
            win_rate        REAL,
            notes           TEXT
        )
    """)
    
    # ========================================
    # TABLE: cyto_nodes
    # Each node = one 15-minute bar with full sentiment + trade data
    # ========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cyto_nodes (
            node_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id     TEXT NOT NULL,
            
            -- Temporal Position
            cycle_index     INTEGER NOT NULL,
            theta_slot      INTEGER NOT NULL CHECK(theta_slot >= 0 AND theta_slot < 288),
            timestamp       TIMESTAMP NOT NULL,
            
            -- Sentiment Data (6 Vectors)
            vectors_15m     TEXT,
            weighted_15m    REAL,
            weighted_1h     REAL,
            weighted_final  REAL,
            agreement_score REAL,
            
            -- Trade Data (if trade closed this bar)
            has_trade       INTEGER DEFAULT 0,
            raw_pnl         REAL,
            pnl_normalized  REAL,
            radius          REAL CHECK(radius IS NULL OR (radius >= 0 AND radius <= 2)),
            trade_direction TEXT CHECK(trade_direction IS NULL OR trade_direction IN ('long', 'short')),
            
            -- Visualization Hints (pre-calculated for rendering speed)
            node_size       REAL,
            node_hue        TEXT CHECK(node_hue IS NULL OR node_hue IN ('bullish', 'bearish', 'neutral')),
            node_saturation REAL,
            
            -- Metadata
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (instance_id) REFERENCES cyto_instances(instance_id)
        )
    """)
    
    # ========================================
    # TABLE: cyto_trades
    # Detailed trade records linked to nodes
    # ========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cyto_trades (
            trade_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id         INTEGER NOT NULL,
            instance_id     TEXT NOT NULL,
            
            -- Trade Details
            entry_time      TIMESTAMP NOT NULL,
            exit_time       TIMESTAMP NOT NULL,
            entry_price     REAL NOT NULL,
            exit_price      REAL NOT NULL,
            lots            REAL NOT NULL,
            direction       TEXT NOT NULL CHECK(direction IN ('long', 'short')),
            
            -- P/L
            pnl_raw         REAL NOT NULL,
            pnl_normalized  REAL NOT NULL,
            pnl_pips        REAL,
            
            -- Context at entry
            entry_vectors   TEXT,
            entry_weighted  REAL,
            
            -- Context at exit
            exit_vectors    TEXT,
            exit_weighted   REAL,
            
            -- Metadata
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (node_id) REFERENCES cyto_nodes(node_id),
            FOREIGN KEY (instance_id) REFERENCES cyto_instances(instance_id)
        )
    """)
    
    # ========================================
    # TABLE: cyto_epochs
    # Pre-computed epoch metadata for fast querying
    # ========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cyto_epochs (
            epoch_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id     TEXT NOT NULL,
            cycle_index     INTEGER NOT NULL,
            
            -- Time bounds
            start_time      TIMESTAMP NOT NULL,
            end_time        TIMESTAMP NOT NULL,
            
            -- Aggregates
            node_count      INTEGER DEFAULT 0,
            trade_count     INTEGER DEFAULT 0,
            total_pnl       REAL DEFAULT 0.0,
            avg_sentiment   REAL,
            
            -- Metadata
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (instance_id) REFERENCES cyto_instances(instance_id),
            UNIQUE(instance_id, cycle_index)
        )
    """)
    
    # ========================================
    # INDEXES for query performance
    # ========================================
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_instance ON cyto_nodes(instance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_cycle ON cyto_nodes(instance_id, cycle_index)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_slot ON cyto_nodes(instance_id, cycle_index, theta_slot)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_timestamp ON cyto_nodes(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_has_trade ON cyto_nodes(has_trade)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_instance ON cyto_trades(instance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_node ON cyto_trades(node_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON cyto_trades(exit_time)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_epochs_instance ON cyto_epochs(instance_id)")
    
    conn.commit()
    conn.close()
    
    print(f"✓ CytoBase v3 initialized: {DB_PATH}")
    return DB_PATH


def drop_all_tables():
    """Drop all tables (use with caution - for testing only)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS cyto_trades")
    cursor.execute("DROP TABLE IF EXISTS cyto_nodes")
    cursor.execute("DROP TABLE IF EXISTS cyto_epochs")
    cursor.execute("DROP TABLE IF EXISTS cyto_instances")
    conn.commit()
    conn.close()
    print("✓ All CytoBase tables dropped")


def get_schema_info():
    """Return schema information for debugging."""
    conn = get_connection()
    cursor = conn.cursor()
    
    tables = {}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cyto_%'")
    for row in cursor.fetchall():
        table_name = row['name']
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [dict(col) for col in cursor.fetchall()]
        
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()['count']
        
        tables[table_name] = {
            'columns': columns,
            'row_count': count
        }
    
    conn.close()
    return tables


# ============================================
# MAIN - Testing
# ============================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("CytoBase v3 - Schema Initialization")
    print("=" * 50)
    
    # Initialize
    init_db()
    
    # Display schema info
    info = get_schema_info()
    for table, data in info.items():
        print(f"\n📋 {table} ({data['row_count']} rows)")
        for col in data['columns']:
            nullable = "" if col['notnull'] else "NULL"
            pk = "PK" if col['pk'] else ""
            print(f"   - {col['name']}: {col['type']} {pk} {nullable}".strip())
    
    print("\n" + "=" * 50)
    print("Schema ready for CytoManager")
    print("=" * 50 + "\n")
