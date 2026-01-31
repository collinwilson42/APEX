"""
MT5 META AGENT - COMPLETE DATABASE INITIALIZATION
Creates: core_15m, basic_15m, advanced_indicators
Run ONCE before starting the app
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = 'mt5_intelligence.db'

def init_database():
    """Create all required tables"""
    
    print("="*60)
    print("MT5 META AGENT - DATABASE INITIALIZATION")
    print("="*60)
    print(f"Database: {os.path.abspath(DB_PATH)}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("✓ Connected to SQLite")
    
    # =========================================================================
    # TABLE 1: core_15m - OHLCV data
    # =========================================================================
    print("\n[1/3] Creating core_15m table...")
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_timestamp ON core_15m(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_timeframe ON core_15m(timeframe)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_symbol ON core_15m(symbol)")
    print("  ✓ core_15m created")
    
    # =========================================================================
    # TABLE 2: basic_15m - Basic indicators
    # =========================================================================
    print("\n[2/3] Creating basic_15m table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS basic_15m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            atr_14 REAL,
            atr_50_avg REAL,
            atr_ratio REAL,
            ema_short REAL,
            ema_medium REAL,
            ema_distance REAL,
            supertrend TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_basic_timestamp ON basic_15m(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_basic_timeframe ON basic_15m(timeframe)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_basic_symbol ON basic_15m(symbol)")
    print("  ✓ basic_15m created")
    
    # =========================================================================
    # TABLE 3: advanced_indicators (172+ indicators)
    # =========================================================================
    print("\n[3/3] Creating advanced_indicators table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advanced_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            
            -- RSI periods 1-14
            rsi_1 REAL, rsi_2 REAL, rsi_3 REAL, rsi_4 REAL, rsi_5 REAL,
            rsi_6 REAL, rsi_7 REAL, rsi_8 REAL, rsi_9 REAL, rsi_10 REAL,
            rsi_11 REAL, rsi_12 REAL, rsi_13 REAL, rsi_14 REAL,
            
            -- MACD
            macd_line_12_26 REAL, macd_signal_12_26_9 REAL, macd_histogram_12_26_9 REAL,
            
            -- Stochastic periods 1-14
            stoch_k_1 REAL, stoch_k_2 REAL, stoch_k_3 REAL, stoch_k_4 REAL, stoch_k_5 REAL,
            stoch_k_6 REAL, stoch_k_7 REAL, stoch_k_8 REAL, stoch_k_9 REAL, stoch_k_10 REAL,
            stoch_k_11 REAL, stoch_k_12 REAL, stoch_k_13 REAL, stoch_k_14 REAL,
            stoch_d_14_3 REAL,
            
            -- Williams %R periods 1-14
            williams_r_1 REAL, williams_r_2 REAL, williams_r_3 REAL, williams_r_4 REAL, williams_r_5 REAL,
            williams_r_6 REAL, williams_r_7 REAL, williams_r_8 REAL, williams_r_9 REAL, williams_r_10 REAL,
            williams_r_11 REAL, williams_r_12 REAL, williams_r_13 REAL, williams_r_14 REAL,
            
            -- ADX periods 1-14
            adx_1 REAL, adx_2 REAL, adx_3 REAL, adx_4 REAL, adx_5 REAL,
            adx_6 REAL, adx_7 REAL, adx_8 REAL, adx_9 REAL, adx_10 REAL,
            adx_11 REAL, adx_12 REAL, adx_13 REAL, adx_14 REAL,
            plus_di_14 REAL, minus_di_14 REAL,
            
            -- CCI periods 1-14
            cci_1 REAL, cci_2 REAL, cci_3 REAL, cci_4 REAL, cci_5 REAL,
            cci_6 REAL, cci_7 REAL, cci_8 REAL, cci_9 REAL, cci_10 REAL,
            cci_11 REAL, cci_12 REAL, cci_13 REAL, cci_14 REAL,
            
            -- Momentum periods 1-14
            momentum_1 REAL, momentum_2 REAL, momentum_3 REAL, momentum_4 REAL, momentum_5 REAL,
            momentum_6 REAL, momentum_7 REAL, momentum_8 REAL, momentum_9 REAL, momentum_10 REAL,
            momentum_11 REAL, momentum_12 REAL, momentum_13 REAL, momentum_14 REAL,
            
            -- Bollinger Bands
            bb_upper_20 REAL, bb_middle_20 REAL, bb_lower_20 REAL, bb_width_20 REAL,
            bb_upper_14 REAL, bb_middle_14 REAL, bb_lower_14 REAL, bb_width_14 REAL,
            
            -- OBV
            obv REAL,
            
            -- Volume MA periods 1-14 + 20
            volume_ma_1 REAL, volume_ma_2 REAL, volume_ma_3 REAL, volume_ma_4 REAL, volume_ma_5 REAL,
            volume_ma_6 REAL, volume_ma_7 REAL, volume_ma_8 REAL, volume_ma_9 REAL, volume_ma_10 REAL,
            volume_ma_11 REAL, volume_ma_12 REAL, volume_ma_13 REAL, volume_ma_14 REAL, volume_ma_20 REAL,
            
            -- CMF periods 1-14
            cmf_1 REAL, cmf_2 REAL, cmf_3 REAL, cmf_4 REAL, cmf_5 REAL,
            cmf_6 REAL, cmf_7 REAL, cmf_8 REAL, cmf_9 REAL, cmf_10 REAL,
            cmf_11 REAL, cmf_12 REAL, cmf_13 REAL, cmf_14 REAL,
            
            -- Parabolic SAR
            sar_value REAL, sar_direction INTEGER,
            
            -- Ichimoku
            tenkan_sen REAL, kijun_sen REAL, senkou_span_a REAL, senkou_span_b REAL, chikou_span REAL,
            
            -- ROC periods 1-14
            roc_1 REAL, roc_2 REAL, roc_3 REAL, roc_4 REAL, roc_5 REAL,
            roc_6 REAL, roc_7 REAL, roc_8 REAL, roc_9 REAL, roc_10 REAL,
            roc_11 REAL, roc_12 REAL, roc_13 REAL, roc_14 REAL,
            
            -- ATR periods 1-14
            atr_1 REAL, atr_2 REAL, atr_3 REAL, atr_4 REAL, atr_5 REAL,
            atr_6 REAL, atr_7 REAL, atr_8 REAL, atr_9 REAL, atr_10 REAL,
            atr_11 REAL, atr_12 REAL, atr_13 REAL, atr_14 REAL,
            
            -- Fibonacci Pivots
            pivot_fibonacci REAL, r1_fibonacci REAL, r2_fibonacci REAL, r3_fibonacci REAL,
            s1_fibonacci REAL, s2_fibonacci REAL, s3_fibonacci REAL,
            
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_adv_timestamp ON advanced_indicators(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_adv_timeframe ON advanced_indicators(timeframe)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_adv_symbol ON advanced_indicators(symbol)")
    print("  ✓ advanced_indicators created")
    
    # =========================================================================
    # Additional tables for Apex Signals
    # =========================================================================
    print("\n[+] Creating fibonacci_data table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fibonacci_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            pivot_high REAL, pivot_low REAL,
            current_fib_zone INTEGER, in_golden_zone BOOLEAN, zone_multiplier REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    """)
    print("  ✓ fibonacci_data created")
    
    print("\n[+] Creating ath_tracking table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ath_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            current_ath REAL, ath_distance_pct REAL, ath_multiplier REAL, ath_zone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    """)
    print("  ✓ ath_tracking created")
    
    print("\n[+] Creating collection_stats table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeframe TEXT NOT NULL UNIQUE,
            total_collections INTEGER DEFAULT 0,
            successful_collections INTEGER DEFAULT 0,
            last_collection TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO collection_stats (timeframe) VALUES ('1m'), ('15m')")
    print("  ✓ collection_stats created")
    
    conn.commit()
    
    # Verify
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f"\nTables created: {len(tables)}")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t[0]}")
        count = cursor.fetchone()[0]
        print(f"  ✓ {t[0]}: {count} rows")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ DATABASE INITIALIZATION COMPLETE")
    print("="*60)
    print("\nNow run: python app.py")
    print("="*60)

if __name__ == "__main__":
    init_database()
