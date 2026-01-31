# mt5_collector_v11_3.py (Corrected Class-based Version 2.0)
"""
MT5 META AGENT V11.3 - ADVANCED INDICATOR COLLECTOR (CLASS-BASED)
This version is designed to be imported and instantiated by a master script
(like init.py) to collect data for a specific symbol into a specific database.
"""

import MetaTrader5 as mt5
import sqlite3
import time
import numpy as np
from datetime import datetime
import sys
import os

# Import calculators safely
try:
    from fibonacci_calculator import calculate_fibonacci_data
    from ath_calculator import calculate_ath_data
    CALCULATORS_AVAILABLE = True
except ImportError:
    print("⚠️  Calculators not found - Fibonacci & ATH data will be skipped.")
    CALCULATORS_AVAILABLE = False

# Default periods
ATR_PERIOD = 14
ATR_AVG_PERIOD = 50
EMA_SHORT_PERIOD = 4
EMA_MEDIUM_PERIOD = 22
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 2.5
FIB_LOOKBACK = 100
ATH_LOOKBACK = 500

class MT5AdvancedCollector:
    # MODIFIED: __init__ now accepts symbol and db_path
    def __init__(self, symbol: str, db_path: str, timeframes: list = ['1m', '15m']):
        """
        Initializes the collector for a specific symbol and database.
        Args:
            symbol (str): The MT5 symbol to collect (e.g., 'XAUG26.sim').
            db_path (str): The path to the SQLite database file.
            timeframes (list): A list of timeframes to collect (e.g., ['1m', '15m']).
        """
        self.symbol = symbol
        self.db_path = db_path
        self.timeframes_to_collect = timeframes
        self.mt5_timeframes = {
            '1m': mt5.TIMEFRAME_M1,
            '15m': mt5.TIMEFRAME_M15
        }
        self.last_bar_times = {tf: None for tf in timeframes}
        self.collection_counts = {tf: 0 for tf in timeframes}
        self.error_count = 0
        self.running = False

    def connect_mt5(self):
        print(f"[{self.symbol}] Connecting to MetaTrader 5...")
        # MODIFIED: Use self.symbol
        if not mt5.initialize(path=None, portable=False, timeout=10000):
            print(f"[{self.symbol}] ✗ MT5 initialization failed: {mt5.last_error()}")
            return False

        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"[{self.symbol}] ✗ Symbol not found in MT5.")
            mt5.shutdown()
            return False

        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                print(f"[{self.symbol}] ✗ Failed to select symbol in Market Watch.")
                mt5.shutdown()
                return False

        print(f"[{self.symbol}] ✓ Connected to MT5.")
        return True

    def collect_and_save(self, timeframe_str):
        """Collects and saves data for a single timeframe."""
        timeframe_mt5 = self.mt5_timeframes[timeframe_str]

        # MODIFIED: Use self.symbol
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe_mt5, 0, 1)
        if rates is None or len(rates) == 0:
            # This is normal if there's no new bar, so we don't print an error
            return

        latest_bar_time = datetime.fromtimestamp(rates[0]['time'])
        if self.last_bar_times[timeframe_str] and latest_bar_time <= self.last_bar_times[timeframe_str]:
            return # Not a new bar

        self.last_bar_times[timeframe_str] = latest_bar_time

        # Fetch more history for indicator calculation
        history_rates = mt5.copy_rates_from_pos(self.symbol, timeframe_mt5, 0, ATH_LOOKBACK + 1)
        if history_rates is None or len(history_rates) < 50:
            print(f"[{self.symbol}-{timeframe_str}] Not enough historical data for indicators.")
            return

        latest_rate = history_rates[-1]
        timestamp = datetime.fromtimestamp(latest_rate['time']).strftime('%Y-%m-%d %H:%M:%S')

        try:
            # MODIFIED: Use self.db_path
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO core_15m 
                    (timestamp, timeframe, symbol, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, timeframe_str, self.symbol, 
                    float(latest_rate['open']), float(latest_rate['high']), 
                    float(latest_rate['low']), float(latest_rate['close']), 
                    int(latest_rate['tick_volume'])
                ))
                # NOTE: Add your other indicator table insertions here if needed
                conn.commit()
                self.collection_counts[timeframe_str] += 1
                print(f"[{self.symbol}-{timeframe_str}] ✓ Saved bar for {timestamp}. Total: {self.collection_counts[timeframe_str]}")
        except Exception as e:
            self.error_count += 1
            print(f"[{self.symbol}-{timeframe_str}] ✗ DB Error: {e}")

    def run(self):
        """Main collection loop for this instance."""
        self.running = True
        print(f"[{self.symbol}] Collector starting. DB: '{self.db_path}'")

        while self.running:
            try:
                for tf in self.timeframes_to_collect:
                    self.collect_and_save(tf)
                time.sleep(30) # Check for new bars every 30 seconds
            except Exception as e:
                print(f"[{self.symbol}] ✗ Unhandled error in run loop: {e}")
                self.error_count += 1
                time.sleep(60) # Wait longer after an error

        print(f"[{self.symbol}] Collector stopping.")

# This main block is removed as the file is now intended to be used as a module.
# if __name__ == "__main__":
#     ...