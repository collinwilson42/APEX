"""
BTC FILL - BTCF26 Database Backfill (Bitcoin Futures)
=====================================================
Fills BTCF26_intelligence.db with 50,000 1M and 50,000 15M bars

Usage: py -3.11 btcfill.py
"""

import MetaTrader5 as mt5
import sqlite3
import os
from datetime import datetime
import sys

# Import all functions from goldfill
from goldfill import (
    clear_all_tables, fill_timeframe, 
    TIMEFRAMES, MAX_BARS
)

# Import from central config
import sys
sys.path.insert(0, '.')
from config import SYMBOL_DATABASES

# Get symbol config
SYMBOL_ID = 'BTCF26'
config = SYMBOL_DATABASES[SYMBOL_ID]
SYMBOL = config['symbol']
DB_PATH = config['db_path']
SYMBOL_NAME = config['name']

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print(f"BTC FILL - {SYMBOL_NAME}")
    print(f"Database: {DB_PATH}")
    print("=" * 70)
    
    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"\n✗ Database not found: {DB_PATH}")
        print("Run init_databases.py first!")
        return
    
    # Initialize MT5
    print("\nInitializing MT5...")
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return
    
    print(f"MT5 connected: {mt5.terminal_info().name}")
    
    # Check symbol
    if not mt5.symbol_select(SYMBOL, True):
        print(f"✗ Symbol not found: {SYMBOL}")
        mt5.shutdown()
        return
    
    print(f"✓ Symbol found: {SYMBOL}")
    
    # Clear existing data
    clear_all_tables(DB_PATH, SYMBOL)
    
    # Fill each timeframe
    conn = sqlite3.connect(DB_PATH)
    total_bars = 0
    
    for tf_key, tf_mt5 in TIMEFRAMES.items():
        print(f"\n--- Filling {tf_key.upper()} ---")
        bars = fill_timeframe(conn, SYMBOL, tf_key, tf_mt5, MAX_BARS)
        total_bars += bars
    
    conn.close()
    mt5.shutdown()
    
    # Summary
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print("\n" + "=" * 70)
    print(f"COMPLETE: {total_bars:,} total bars")
    print(f"Database size: {size_mb:.1f} MB")
    print("=" * 70)


if __name__ == '__main__':
    main()
