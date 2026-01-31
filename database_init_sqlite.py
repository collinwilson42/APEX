"""
MT5 META AGENT V10 - DATABASE INITIALIZATION (SQLite)
Creates mt5_intelligence.db with dual timeframe support (1m + 15m)
NO MYSQL/XAMPP REQUIRED - Uses built-in SQLite
"""

import sqlite3
import os
from datetime import datetime

def create_database():
    """Initialize the mt5_intelligence SQLite database with all required tables"""
    
    db_path = 'mt5_intelligence.db'
    
    try:
        print("="*60)
        print("MT5 META AGENT V10 - DATABASE INITIALIZATION (SQLite)")
        print("="*60)
        
        # Connect to SQLite database (creates if doesn't exist)
        print(f"\nConnecting to database: {db_path}...")
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        print("✓ Connected to SQLite database")
        
        # Create core_15m table (stores both 1m and 15m data)
        print("\nCreating core_15m table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_15m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, timeframe, symbol)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_timestamp ON core_15m(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_timeframe ON core_15m(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_symbol ON core_15m(symbol)")
        print("✓ core_15m table created with indexes")
        
        # Create basic_15m table (stores both 1m and 15m indicators)
        print("\nCreating basic_15m table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS basic_15m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                symbol TEXT NOT NULL,
                atr_14 REAL NOT NULL,
                atr_50_avg REAL NOT NULL,
                atr_ratio REAL NOT NULL,
                ema_short REAL NOT NULL,
                ema_medium REAL NOT NULL,
                ema_distance REAL NOT NULL,
                supertrend TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, timeframe, symbol)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_basic_timestamp ON basic_15m(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_basic_timeframe ON basic_15m(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_basic_symbol ON basic_15m(symbol)")
        print("✓ basic_15m table created with indexes")
        
        # Create fibonacci_data table (V2.021 - Advanced Technical)
        print("\nCreating fibonacci_data table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fibonacci_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                symbol TEXT NOT NULL,
                
                -- Fibonacci Anchors
                pivot_high REAL NOT NULL,
                pivot_low REAL NOT NULL,
                fib_range REAL NOT NULL,
                lookback_bars INTEGER NOT NULL,
                
                -- All 13 Fibonacci Levels (0.000 to 1.000)
                fib_level_0000 REAL NOT NULL,
                fib_level_0118 REAL NOT NULL,
                fib_level_0236 REAL NOT NULL,
                fib_level_0309 REAL NOT NULL,
                fib_level_0382 REAL NOT NULL,
                fib_level_0441 REAL NOT NULL,
                fib_level_0500 REAL NOT NULL,
                fib_level_0559 REAL NOT NULL,
                fib_level_0618 REAL NOT NULL,
                fib_level_0702 REAL NOT NULL,
                fib_level_0786 REAL NOT NULL,
                fib_level_0893 REAL NOT NULL,
                fib_level_1000 REAL NOT NULL,
                
                -- Current Position Analysis
                current_fib_zone INTEGER NOT NULL,
                in_golden_zone BOOLEAN NOT NULL,
                zone_multiplier REAL NOT NULL,
                distance_to_next_level REAL,
                
                -- Percentile Tracking (calculated later)
                zone_time_percentile REAL,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, timeframe, symbol)
            )
        """)
        
        # Create indexes for fibonacci_data
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fib_timestamp ON fibonacci_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fib_timeframe ON fibonacci_data(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fib_symbol ON fibonacci_data(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fib_zone ON fibonacci_data(current_fib_zone)")
        print("✓ fibonacci_data table created with indexes")
        
        # Create ath_tracking table (V2.032 - Market Regime Detection)
        print("\nCreating ath_tracking table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ath_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                symbol TEXT NOT NULL,
                
                -- ATH Calculation
                current_ath REAL NOT NULL,
                ath_lookback_bars INTEGER NOT NULL,
                
                -- Current Price
                current_close REAL NOT NULL,
                
                -- Distance Metrics
                ath_distance_points REAL NOT NULL,
                ath_distance_pct REAL NOT NULL,
                
                -- Multiplier Mapping
                ath_min_threshold REAL NOT NULL,
                ath_max_threshold REAL NOT NULL,
                ath_multiplier REAL NOT NULL,
                
                -- Zone Classification
                ath_zone TEXT NOT NULL,
                
                -- Percentile Tracking
                distance_from_ath_percentile REAL,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, timeframe, symbol)
            )
        """)
        
        # Create indexes for ath_tracking
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ath_timestamp ON ath_tracking(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ath_timeframe ON ath_tracking(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ath_symbol ON ath_tracking(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ath_distance ON ath_tracking(ath_distance_pct)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ath_zone ON ath_tracking(ath_zone)")
        print("✓ ath_tracking table created with indexes")
        
        # Create collection_stats table
        print("\nCreating collection_stats table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timeframe TEXT NOT NULL UNIQUE,
                total_collections INTEGER DEFAULT 0,
                successful_collections INTEGER DEFAULT 0,
                failed_collections INTEGER DEFAULT 0,
                last_collection TEXT,
                last_error TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ collection_stats table created")
        
        # Initialize stats for both timeframes
        cursor.execute("""
            INSERT OR IGNORE INTO collection_stats (timeframe, total_collections) 
            VALUES ('1m', 0), ('15m', 0)
        """)
        print("✓ Statistics initialized for 1m and 15m")
        
        connection.commit()
        print("\n" + "="*60)
        print("✓ DATABASE INITIALIZATION COMPLETE")
        print("="*60)
        print(f"\nDatabase file: {os.path.abspath(db_path)}")
        print("Tables created:")
        print("  - core_15m (OHLCV data with timeframe column)")
        print("  - basic_15m (Indicators with timeframe column)")
        print("  - fibonacci_data (V2.021 - Fibonacci zone analysis)")
        print("  - ath_tracking (V2.032 - All-time high tracking)")
        print("  - collection_stats (Collection tracking)")
        print("\nTimeframes supported: 1m, 15m")
        print("\nYou can now run:")
        print("  python mt5_collector.py dual    # Collect both 1m and 15m")
        print("  python mt5_collector.py 1m      # Collect 1m only")
        print("  python mt5_collector.py 15m     # Collect 15m only")
        print("="*60)
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_database():
    """Check if database and tables exist"""
    
    db_path = 'mt5_intelligence.db'
    
    if not os.path.exists(db_path):
        print(f"✗ Database not found: {db_path}")
        return False
    
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        print("\n" + "="*60)
        print("DATABASE STATUS CHECK")
        print("="*60)
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nTables found: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            print(f"  ✓ {table_name}")
            
            # Get row counts
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    Rows: {count}")
        
        # Check timeframe distribution
        cursor.execute("SELECT timeframe, COUNT(*) FROM core_15m GROUP BY timeframe")
        tf_counts = cursor.fetchall()
        if tf_counts:
            print("\nTimeframe distribution (core_15m):")
            for tf, count in tf_counts:
                print(f"  {tf}: {count} records")
        
        print("="*60)
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Database check failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("MT5 META AGENT V10 - DATABASE INITIALIZATION")
    print("Using SQLite - No MySQL/XAMPP Required!")
    print("="*60)
    
    # Create database
    if create_database():
        print("\n" + "="*60)
        input("Press Enter to view database status...")
        check_database()
