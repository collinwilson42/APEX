"""
INIT DATABASES - Initialize 6 Intelligence Database Files
============================================================
Creates the database schema for:
  - 5 Symbol Databases (XAUG26, BTCZ25, US500Z25, US100Z25, US30Z25)
  - 1 Analytics Database (cross-symbol analysis)

Run this BEFORE fillall.py to create empty databases with proper schema.

Usage: py -3.11 init_databases.py
"""

import sqlite3
import os
from datetime import datetime

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Import from central config
import sys
sys.path.insert(0, '.')  # Ensure current directory is in path
from config import SYMBOL_DATABASES

# Convert to format expected by this script
SYMBOL_DB_CONFIG = {
    sym_id: {
        'db': config['db_path'],
        'symbol': config['symbol'],
        'name': config['name']
    }
    for sym_id, config in SYMBOL_DATABASES.items()
}

ANALYTICS_DB = 'analytics_intelligence.db'

# ============================================================================
# SCHEMA DEFINITIONS
# ============================================================================

def create_symbol_database_schema(conn):
    """Create full schema for a symbol database"""
    cursor = conn.cursor()
    
    # Core 15m OHLCV data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS core_15m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT DEFAULT '15m',
            symbol TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    ''')
    
    # Basic indicators (ATR, EMA, Supertrend)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS basic_15m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT DEFAULT '15m',
            symbol TEXT,
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
    ''')
    
    # Advanced indicators (172 columns)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advanced_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT DEFAULT '15m',
            symbol TEXT,
            
            -- RSI (14 periods: 1-14)
            rsi_1 REAL, rsi_2 REAL, rsi_3 REAL, rsi_4 REAL, rsi_5 REAL,
            rsi_6 REAL, rsi_7 REAL, rsi_8 REAL, rsi_9 REAL, rsi_10 REAL,
            rsi_11 REAL, rsi_12 REAL, rsi_13 REAL, rsi_14 REAL,
            
            -- CCI (14 periods: 1-14)
            cci_1 REAL, cci_2 REAL, cci_3 REAL, cci_4 REAL, cci_5 REAL,
            cci_6 REAL, cci_7 REAL, cci_8 REAL, cci_9 REAL, cci_10 REAL,
            cci_11 REAL, cci_12 REAL, cci_13 REAL, cci_14 REAL,
            
            -- Stochastic (14 periods: 1-14) - K and D values
            stoch_k_1 REAL, stoch_d_1 REAL, stoch_k_2 REAL, stoch_d_2 REAL,
            stoch_k_3 REAL, stoch_d_3 REAL, stoch_k_4 REAL, stoch_d_4 REAL,
            stoch_k_5 REAL, stoch_d_5 REAL, stoch_k_6 REAL, stoch_d_6 REAL,
            stoch_k_7 REAL, stoch_d_7 REAL, stoch_k_8 REAL, stoch_d_8 REAL,
            stoch_k_9 REAL, stoch_d_9 REAL, stoch_k_10 REAL, stoch_d_10 REAL,
            stoch_k_11 REAL, stoch_d_11 REAL, stoch_k_12 REAL, stoch_d_12 REAL,
            stoch_k_13 REAL, stoch_d_13 REAL, stoch_k_14 REAL, stoch_d_14 REAL,
            
            -- Williams %R (14 periods: 1-14)
            williams_r_1 REAL, williams_r_2 REAL, williams_r_3 REAL, williams_r_4 REAL,
            williams_r_5 REAL, williams_r_6 REAL, williams_r_7 REAL, williams_r_8 REAL,
            williams_r_9 REAL, williams_r_10 REAL, williams_r_11 REAL, williams_r_12 REAL,
            williams_r_13 REAL, williams_r_14 REAL,
            
            -- ADX (14 periods: 1-14)
            adx_1 REAL, adx_2 REAL, adx_3 REAL, adx_4 REAL, adx_5 REAL,
            adx_6 REAL, adx_7 REAL, adx_8 REAL, adx_9 REAL, adx_10 REAL,
            adx_11 REAL, adx_12 REAL, adx_13 REAL, adx_14 REAL,
            
            -- Momentum (14 periods: 1-14)
            momentum_1 REAL, momentum_2 REAL, momentum_3 REAL, momentum_4 REAL,
            momentum_5 REAL, momentum_6 REAL, momentum_7 REAL, momentum_8 REAL,
            momentum_9 REAL, momentum_10 REAL, momentum_11 REAL, momentum_12 REAL,
            momentum_13 REAL, momentum_14 REAL,
            
            -- Bollinger Bands (period 20)
            bb_upper_20 REAL, bb_middle_20 REAL, bb_lower_20 REAL, bb_width_20 REAL, bb_pct_20 REAL,
            
            -- MACD (12, 26)
            macd_line_12_26 REAL, macd_signal_12_26 REAL, macd_histogram_12_26 REAL,
            
            -- OBV
            obv REAL,
            
            -- Volume MA (20)
            volume_ma_20 REAL, volume_ratio REAL,
            
            -- CMF (20)
            cmf_20 REAL,
            
            -- Parabolic SAR
            sar REAL, sar_trend TEXT,
            
            -- Ichimoku
            ichimoku_tenkan REAL, ichimoku_kijun REAL, ichimoku_senkou_a REAL, ichimoku_senkou_b REAL,
            
            -- ROC (14 periods: 1-14)
            roc_1 REAL, roc_2 REAL, roc_3 REAL, roc_4 REAL, roc_5 REAL,
            roc_6 REAL, roc_7 REAL, roc_8 REAL, roc_9 REAL, roc_10 REAL,
            roc_11 REAL, roc_12 REAL, roc_13 REAL, roc_14 REAL,
            
            -- Fibonacci Pivot Points
            fib_pivot REAL, fib_r1 REAL, fib_r2 REAL, fib_r3 REAL,
            fib_s1 REAL, fib_s2 REAL, fib_s3 REAL,
            
            -- ATR variations (13 periods: 1-13)
            atr_1 REAL, atr_2 REAL, atr_3 REAL, atr_4 REAL, atr_5 REAL,
            atr_6 REAL, atr_7 REAL, atr_8 REAL, atr_9 REAL, atr_10 REAL,
            atr_11 REAL, atr_12 REAL, atr_13 REAL,
            
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    ''')
    
    # Fibonacci data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fibonacci_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT DEFAULT '15m',
            symbol TEXT,
            pivot_high REAL,
            pivot_low REAL,
            fib_level_0000 REAL,
            fib_level_0236 REAL,
            fib_level_0382 REAL,
            fib_level_0500 REAL,
            fib_level_0618 REAL,
            fib_level_0786 REAL,
            fib_level_1000 REAL,
            fib_level_1272 REAL,
            fib_level_1618 REAL,
            fib_level_2000 REAL,
            fib_level_2618 REAL,
            fib_level_3618 REAL,
            fib_level_4236 REAL,
            current_fib_zone TEXT,
            in_golden_zone INTEGER,
            zone_multiplier REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    ''')
    
    # ATH tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ath_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            timeframe TEXT DEFAULT '15m',
            symbol TEXT,
            current_ath REAL,
            current_close REAL,
            ath_distance_pct REAL,
            ath_multiplier REAL,
            ath_zone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, timeframe, symbol)
        )
    ''')
    
    # Collection stats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS collection_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT,
            timeframe TEXT,
            bars_collected INTEGER,
            indicators_calculated INTEGER,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_core_15m_timestamp ON core_15m(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_basic_15m_timestamp ON basic_15m(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_advanced_timestamp ON advanced_indicators(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fibonacci_timestamp ON fibonacci_data(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ath_timestamp ON ath_tracking(timestamp)')
    
    conn.commit()
    print(f"    - Created 5 tables with indexes")


def create_analytics_database_schema(conn):
    """Create schema for the analytics database (cross-symbol analysis)"""
    cursor = conn.cursor()
    
    # Cross-symbol correlation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbol_correlations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol_a TEXT,
            symbol_b TEXT,
            correlation_1h REAL,
            correlation_4h REAL,
            correlation_1d REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Market regime detection
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_regime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            regime TEXT,
            confidence REAL,
            volatility_percentile REAL,
            trend_strength REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Signal history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT,
            signal_type TEXT,
            direction TEXT,
            confidence REAL,
            entry_price REAL,
            exit_price REAL,
            profit_loss REAL,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Performance metrics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT,
            timeframe TEXT,
            win_rate REAL,
            profit_factor REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            total_trades INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    print(f"    - Created 4 analytics tables")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print("INITIALIZE INTELLIGENCE DATABASES")
    print("=" * 70)
    print(f"\nThis will create {len(SYMBOL_DB_CONFIG)} symbol databases + 1 analytics database")
    print("\nDatabases to create:")
    for key, config in SYMBOL_DB_CONFIG.items():
        exists = "EXISTS" if os.path.exists(config['db']) else "NEW"
        print(f"  - {config['db']:30s} ({config['name']}) [{exists}]")
    
    exists = "EXISTS" if os.path.exists(ANALYTICS_DB) else "NEW"
    print(f"  - {ANALYTICS_DB:30s} (Cross-Symbol Analysis) [{exists}]")
    
    print("\n" + "-" * 70)
    confirm = input("Type 'INIT' to create/initialize all databases: ").strip()
    
    if confirm != 'INIT':
        print("\nAborted.")
        return
    
    print("\n" + "-" * 70)
    print("CREATING DATABASES...")
    print("-" * 70)
    
    # Create symbol databases
    for key, config in SYMBOL_DB_CONFIG.items():
        db_path = config['db']
        print(f"\n[{key}] {config['name']}")
        
        try:
            conn = sqlite3.connect(db_path)
            create_symbol_database_schema(conn)
            
            # Insert initial collection stat
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO collection_stats 
                (timestamp, symbol, timeframe, bars_collected, indicators_calculated, status)
                VALUES (?, ?, ?, 0, 0, 'initialized')
            ''', (datetime.now().isoformat(), config['symbol'], '15m'))
            conn.commit()
            conn.close()
            
            size = os.path.getsize(db_path)
            print(f"    - Size: {size / 1024:.1f} KB")
            
        except Exception as e:
            print(f"    - ERROR: {e}")
    
    # Create analytics database
    print(f"\n[ANALYTICS] Cross-Symbol Analysis")
    try:
        conn = sqlite3.connect(ANALYTICS_DB)
        create_analytics_database_schema(conn)
        conn.close()
        
        size = os.path.getsize(ANALYTICS_DB)
        print(f"    - Size: {size / 1024:.1f} KB")
        
    except Exception as e:
        print(f"    - ERROR: {e}")
    
    print("\n" + "=" * 70)
    print("DATABASE INITIALIZATION COMPLETE")
    print("=" * 70)
    print("\nNext step: Run 'py -3.11 fillall.py' to backfill data from MT5")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
