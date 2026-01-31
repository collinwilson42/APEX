"""
US100 FILL - US100Z25 Database Backfill (NASDAQ 100 Futures)
============================================================
Fills US100Z25_intelligence.db with 50,000 1M and 50,000 15M bars

Usage: py -3.11 100fill.py
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
SYMBOL_ID = 'US100H26'
config = SYMBOL_DATABASES[SYMBOL_ID]
SYMBOL = config['symbol']
DB_PATH = config['db_path']
SYMBOL_NAME = config['name']

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print(f"US100 FILL - {SYMBOL_NAME}")
    print(f"Database: {DB_PATH}")
    print(f"Symbol: {SYMBOL}")
    print(f"Bars per timeframe: {MAX_BARS:,}")
    print("=" * 70)
    
    if not os.path.exists(DB_PATH):
        print(f"\nERROR: Database {DB_PATH} not found!")
        print("Run init_databases.py first.")
        return
    
    confirm = input("\nType 'FILL' to delete existing data and fill database: ").strip().upper()
    if confirm != 'FILL':
        print("Aborted.")
        return
    
    # Initialize MT5
    print("\nInitializing MT5...")
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return
    
    print(f"MT5 connected: {mt5.terminal_info().name}")
    
    # Clear existing data
    clear_all_tables(DB_PATH)
    
    # Fill data
    conn = sqlite3.connect(DB_PATH)
    total = 0
    
    start_time = datetime.now()
    
    for tf_key, tf_mt5 in TIMEFRAMES.items():
        rows = fill_timeframe(conn, SYMBOL, tf_key, tf_mt5, MAX_BARS)
        total += rows
    
    # Update stats
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO collection_stats (timestamp, symbol, timeframe, bars_collected, indicators_calculated, status)
        VALUES (?, ?, 'all', ?, ?, 'completed')''', (datetime.now().isoformat(), SYMBOL, total, total * 176))
    conn.commit()
    conn.close()
    
    mt5.shutdown()
    
    elapsed = (datetime.now() - start_time).total_seconds()
    size = os.path.getsize(DB_PATH) / 1024 / 1024
    
    print("\n" + "=" * 70)
    print("FILL COMPLETE")
    print(f"  Total rows: {total:,}")
    print(f"  Database size: {size:.1f} MB")
    print(f"  Time elapsed: {elapsed:.1f} seconds")
    print("=" * 70 + "\n")

if __name__ == '__main__':
    main()
