"""
2D RADIAL FINGERPRINT SYSTEM - DATABASE SCHEMA
Fibonacci Rings (2, 3, 5, 8, 13, 21) with 3D Migration Prep
"""

import sqlite3
import json
from datetime import datetime


def init_fingerprint_tables(db_path='mt5_intelligence.db'):
    """
    Initialize fingerprint system tables:
    - fingerprint_nodes: 2D radial positioning with Fibonacci rings
    - fingerprint_versions: Calibration history
    - control_factors: 3D tensegrity parameters
    - ring_config: Fibonacci ring definitions
    """
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("INITIALIZING FINGERPRINT SYSTEM")
    print("="*70)
    
    # ================================================================
    # FIBONACCI RING CONFIGURATION
    # ================================================================
    
    print("\n[1/4] Creating ring_config table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ring_config (
            id INTEGER PRIMARY KEY CHECK (id >= 1 AND id <= 6),
            ring_number INTEGER NOT NULL UNIQUE,
            fibonacci_index INTEGER NOT NULL,
            radius REAL NOT NULL,
            band_label TEXT NOT NULL,
            fingerprint_min REAL NOT NULL,
            fingerprint_max REAL NOT NULL,
            hex_color TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Populate Fibonacci rings (F3 to F8)
    cursor.execute("SELECT COUNT(*) FROM ring_config")
    if cursor.fetchone()[0] == 0:
        rings = [
            (1, 1, 3, 2.0, 'CORE_TRUSTED', 0.90, 1.00, '#BB9847', 'Innermost - Production ready'),
            (2, 2, 4, 3.0, 'STRONG_EVOLVING', 0.75, 0.89, '#4CAF50', 'Proven but refining'),
            (3, 3, 5, 5.0, 'VALIDATED', 0.60, 0.74, '#2196F3', 'Tested and stable'),
            (4, 4, 6, 8.0, 'EXPERIMENTAL', 0.40, 0.59, '#FFC107', 'Active testing'),
            (5, 5, 7, 13.0, 'EXPLORATORY', 0.20, 0.39, '#FF9800', 'Early exploration'),
            (6, 6, 8, 21.0, 'DEPRECATED', 0.00, 0.19, '#9E9E9E', 'Outermost - Low confidence')
        ]
        cursor.executemany("""
            INSERT INTO ring_config 
            (id, ring_number, fibonacci_index, radius, band_label, 
             fingerprint_min, fingerprint_max, hex_color, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rings)
    print("  ✓ ring_config populated with F3-F8 Fibonacci radii")
    
    # ================================================================
    # FINGERPRINT NODES (2D Radial Positioning)
    # ================================================================
    
    print("\n[2/4] Creating fingerprint_nodes table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fingerprint_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            domain TEXT NOT NULL CHECK (domain IN ('EXECUTION', 'INTENT', 'RISK', 'META')),
            description TEXT,
            
            -- 2D Radial Coordinates
            ring_id INTEGER NOT NULL,
            radius REAL NOT NULL,
            angle_degrees REAL NOT NULL CHECK (angle_degrees >= 0 AND angle_degrees < 360),
            x_coord REAL NOT NULL,
            y_coord REAL NOT NULL,
            
            -- Fingerprint Scoring
            fingerprint_value REAL NOT NULL CHECK (fingerprint_value >= 0 AND fingerprint_value <= 1),
            band_label TEXT NOT NULL,
            hex_color TEXT NOT NULL,
            
            -- Performance Metrics (for North Star calculation)
            north_star_score REAL DEFAULT 0,
            profit_factor REAL DEFAULT 0,
            net_profit REAL DEFAULT 0,
            win_rate REAL DEFAULT 0,
            trades_count INTEGER DEFAULT 0,
            
            -- 3D Migration Prep
            z_component REAL DEFAULT 0,
            hemisphere TEXT CHECK (hemisphere IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')) DEFAULT 'NEUTRAL',
            
            -- Metadata
            metadata TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (ring_id) REFERENCES ring_config(id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fp_domain ON fingerprint_nodes(domain)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fp_ring ON fingerprint_nodes(ring_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fp_fingerprint ON fingerprint_nodes(fingerprint_value)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fp_hemisphere ON fingerprint_nodes(hemisphere)")
    print("  ✓ fingerprint_nodes table created with 2D radial schema")
    
    # ================================================================
    # VERSION HISTORY (Calibration Tracking)
    # ================================================================
    
    print("\n[3/4] Creating fingerprint_versions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fingerprint_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            node_code TEXT NOT NULL,
            
            old_fingerprint REAL NOT NULL,
            new_fingerprint REAL NOT NULL,
            delta REAL NOT NULL,
            
            old_ring_id INTEGER,
            new_ring_id INTEGER,
            
            reason TEXT,
            backtest_data TEXT,
            
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (node_id) REFERENCES fingerprint_nodes(id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fpv_node ON fingerprint_versions(node_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fpv_timestamp ON fingerprint_versions(created_at)")
    print("  ✓ fingerprint_versions table created for calibration history")
    
    # ================================================================
    # 3D CONTROL FACTORS (Tensegrity Parameters)
    # ================================================================
    
    print("\n[4/4] Creating control_factors table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS control_factors (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            
            -- Gravitational Force Parameters
            g_force_base REAL DEFAULT 1.0,
            g_force_multiplier REAL DEFAULT 1.0,
            
            -- North Star Vector Split (±z hemispheres)
            north_star_positive_weight REAL DEFAULT 0.5,
            north_star_negative_weight REAL DEFAULT 0.5,
            
            -- Tension Coefficients per Ring (F3-F8)
            tension_ring_1 REAL DEFAULT 1.0,
            tension_ring_2 REAL DEFAULT 1.0,
            tension_ring_3 REAL DEFAULT 1.0,
            tension_ring_4 REAL DEFAULT 1.0,
            tension_ring_5 REAL DEFAULT 1.0,
            tension_ring_6 REAL DEFAULT 1.0,
            
            -- Octahedral Symmetry (21/3 = 7 per axis)
            symmetry_lock_enabled INTEGER DEFAULT 1,
            axis_load_x REAL DEFAULT 7.0,
            axis_load_y REAL DEFAULT 7.0,
            axis_load_z REAL DEFAULT 7.0,
            
            -- Equilibrium Calculation
            total_equilibrium REAL DEFAULT 213.0,
            equilibrium_formula TEXT DEFAULT '2π∑Fn ≈ 213',
            
            -- Adaptive Tension Formula
            tension_formula TEXT DEFAULT 'T∝φz ensures zero net ΔT',
            phi_coefficient REAL DEFAULT 1.618,
            
            -- 3D Model Status
            dimension_mode TEXT DEFAULT '2D' CHECK (dimension_mode IN ('2D', '3D')),
            octahedral_enabled INTEGER DEFAULT 0,
            
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default control factors
    cursor.execute("""
        INSERT OR IGNORE INTO control_factors (id) VALUES (1)
    """)
    print("  ✓ control_factors table created with tensegrity parameters")
    
    conn.commit()
    
    # ================================================================
    # VERIFICATION
    # ================================================================
    
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    
    cursor.execute("SELECT COUNT(*) FROM ring_config")
    ring_count = cursor.fetchone()[0]
    print(f"✓ Fibonacci rings configured: {ring_count}")
    
    cursor.execute("SELECT ring_number, radius, band_label FROM ring_config ORDER BY ring_number")
    for row in cursor.fetchall():
        print(f"  Ring {row[0]}: r={row[1]:5.1f} | {row[2]}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✓ FINGERPRINT SYSTEM INITIALIZED")
    print("="*70 + "\n")
    
    return True


def seed_sample_nodes(db_path='mt5_intelligence.db'):
    """Create sample fingerprint nodes for testing"""
    
    import math
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("SEEDING SAMPLE FINGERPRINT NODES")
    print("="*70)
    
    # Sample nodes with strategic placement
    sample_nodes = [
        # EXECUTION domain (90° - East quadrant)
        ('NC-ATR-001', 'ATR Entry Filter', 'EXECUTION', 'Dynamic ATR entry logic', 0.88, 85, 2.5, 0.85),
        ('NC-PYRAMID', 'Progressive Pyramiding', 'EXECUTION', '1→3→6→9 lot system', 0.92, 75, 3.2, 0.72),
        ('NC-EMA-ALIGN', 'EMA Momentum', 'EXECUTION', 'EMA alignment confirmation', 0.78, 95, 2.1, 0.68),
        
        # INTENT domain (0° - North quadrant)
        ('NC-NORTH-STAR', 'North Star Equation', 'INTENT', '(PF×0.7)+(NP×0.3)', 0.95, 10, 4.5, 0.92),
        ('NC-CONVICTION', 'Directional Conviction', 'INTENT', 'Score-based frequency', 0.82, 350, 2.8, 0.78),
        ('NC-TUNITY', 'TUNITY Optimization', 'INTENT', 'T×O×C×C formula', 0.89, 5, 3.5, 0.88),
        
        # RISK domain (270° - West quadrant)
        ('NC-DRAWDOWN', 'Drawdown Protection', 'RISK', 'Session equity stop', 0.93, 265, 4.0, 0.89),
        ('NC-LOSS-THROTTLE', 'Loss Throttling', 'RISK', 'Consecutive loss guard', 0.87, 280, 3.1, 0.82),
        ('NC-SESSION-MULTI', 'Session Multiplier', 'RISK', 'Time-based risk', 0.91, 275, 3.8, 0.86),
        
        # META domain (180° - South quadrant)
        ('NC-WEBHOOK', 'Webhook Integration', 'META', 'TradingView→MT5', 0.88, 185, 2.9, 0.83),
        ('NC-BAR-LOCK', 'Bar Lock Mechanism', 'META', 'Duplicate prevention', 0.94, 175, 4.2, 0.91),
        ('NC-FTMO-RULES', 'FTMO Compliance', 'META', 'Prop firm rules', 0.86, 190, 2.7, 0.80),
        
        # Experimental nodes (outer rings)
        ('NC-RSI-RESET', 'RSI Reset Filter', 'EXECUTION', 'Testing RSI cooldown', 0.55, 100, 1.8, 0.45),
        ('NC-VOL-SPIKE', 'Volume Spike', 'RISK', 'High volume detection', 0.48, 260, 1.5, 0.38),
        ('NC-FIBRATIO', 'Fibonacci Ratio', 'INTENT', 'Golden ratio analysis', 0.42, 15, 1.2, 0.35),
    ]
    
    inserted = 0
    
    for node_code, name, domain, desc, fp, angle, pf, wr in sample_nodes:
        # Determine ring based on fingerprint value
        cursor.execute("""
            SELECT id, radius, band_label, hex_color 
            FROM ring_config 
            WHERE ? BETWEEN fingerprint_min AND fingerprint_max
        """, (fp,))
        
        ring = cursor.fetchone()
        if not ring:
            continue
        
        ring_id, radius, band, color = ring
        
        # Calculate cartesian coordinates
        angle_rad = math.radians(angle)
        x = radius * math.cos(angle_rad)
        y = radius * math.sin(angle_rad)
        
        # Calculate North Star score
        north_star = (pf * 0.7) + (wr * 0.3)
        
        # Determine hemisphere for 3D prep
        if north_star > 2.0:
            hemisphere = 'POSITIVE'
            z_component = north_star - 2.0
        elif north_star < 1.5:
            hemisphere = 'NEGATIVE'
            z_component = -(2.0 - north_star)
        else:
            hemisphere = 'NEUTRAL'
            z_component = 0.0
        
        try:
            cursor.execute("""
                INSERT INTO fingerprint_nodes 
                (node_code, name, domain, description, ring_id, radius, angle_degrees,
                 x_coord, y_coord, fingerprint_value, band_label, hex_color,
                 north_star_score, profit_factor, win_rate, z_component, hemisphere,
                 metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_code, name, domain, desc, ring_id, radius, angle,
                x, y, fp, band, color, north_star, pf, wr, z_component, hemisphere,
                json.dumps({'version': 'v11.3', 'strategy': 'core'})
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # Node already exists
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Inserted {inserted} sample fingerprint nodes")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    # Initialize tables
    init_fingerprint_tables()
    
    # Seed sample data
    seed_sample_nodes()
    
    print("Ready for 2D radial visualization!")
    print("Run init.py to start the application")
