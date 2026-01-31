"""
MT5 META AGENT V3.1 - DATABASE SCHEMA UPDATE
Adds position_state_tracking table for screenshot + vision analysis
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = 'mt5_intelligence.db'

def add_position_state_tracking_table():
    """Add position_state_tracking table to existing database"""
    
    try:
        print("="*70)
        print("MT5 META AGENT V3.1 - ADDING POSITION STATE TRACKING")
        print("="*70)
        
        if not os.path.exists(DB_PATH):
            print("[ERROR] Database not found: {}".format(DB_PATH))
            print("Run database_init_sqlite.py first!")
            return False
        
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        
        print("\nCreating position_state_tracking table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_state_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL DEFAULT '15m',
                symbol TEXT NOT NULL,
                
                -- Screenshot Data
                screenshot_path TEXT NOT NULL,
                screenshot_timestamp TEXT NOT NULL,
                
                -- Vision Analysis Results
                snapshot_analysis TEXT NOT NULL,
                
                -- Directional Confidence (0-100)
                bullish_confidence INTEGER,
                bearish_confidence INTEGER,
                neutral_confidence INTEGER,
                primary_direction TEXT,
                
                -- Risk Assessment
                risk_level TEXT,
                risk_score INTEGER,
                
                -- Key Levels Identified
                resistance_levels TEXT,
                support_levels TEXT,
                
                -- Next 15m Prediction
                next_bar_prediction TEXT,
                prediction_confidence INTEGER,
                
                -- Pattern Recognition
                patterns_detected TEXT,
                trend_strength TEXT,
                
                -- Market Context
                market_regime TEXT,
                volatility_assessment TEXT,
                
                -- Metadata
                analysis_duration_ms INTEGER,
                model_version TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(timestamp, timeframe, symbol)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pst_timestamp ON position_state_tracking(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pst_timeframe ON position_state_tracking(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pst_symbol ON position_state_tracking(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pst_direction ON position_state_tracking(primary_direction)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pst_risk ON position_state_tracking(risk_level)")
        
        connection.commit()
        print("[OK] position_state_tracking table created with indexes")
        
        # Verify table creation
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='position_state_tracking'")
        if cursor.fetchone():
            print("[OK] Table verified in database")
            
            # Show table schema
            cursor.execute("PRAGMA table_info(position_state_tracking)")
            columns = cursor.fetchall()
            print("\nTable has {} columns:".format(len(columns)))
            for col in columns:
                print("  - {} ({})".format(col[1], col[2]))
        
        cursor.close()
        connection.close()
        
        print("\n" + "="*70)
        print("[OK] V3.1 DATABASE SCHEMA UPDATE COMPLETE")
        print("="*70)
        print("\nNext steps:")
        print("  1. Run screenshot_capture.py to test chart capture")
        print("  2. Run vision_analyzer.py to test Claude analysis")
        print("  3. Integrate with mt5_collector.py")
        print("="*70)
        
        return True
        
    except Exception as e:
        print("[ERROR] Error: {}".format(e))
        import traceback
        traceback.print_exc()
        return False

def verify_schema():
    """Verify all V3.1 schema components"""
    
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        
        print("\n" + "="*70)
        print("DATABASE SCHEMA VERIFICATION")
        print("="*70)
        
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print("\nTotal tables: {}".format(len(tables)))
        for table in tables:
            table_name = table[0]
            cursor.execute("SELECT COUNT(*) FROM {}".format(table_name))
            count = cursor.fetchone()[0]
            
            status = "[OK]" if table_name == 'position_state_tracking' else "     "
            print("  {} {}: {} records".format(status, table_name, count))
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print("[ERROR] Verification error: {}".format(e))
        return False

if __name__ == "__main__":
    print("MT5 META AGENT V3.1 - Database Schema Update")
    print("Adding Position State Tracking table...\n")
    
    if add_position_state_tracking_table():
        verify_schema()
    else:
        print("\n[ERROR] Schema update failed")
