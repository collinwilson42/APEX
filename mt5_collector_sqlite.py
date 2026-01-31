#!/usr/bin/env python3
"""
MT5 META AGENT V10 - Data Collector (SQLite Edition)
Collects CORE + BASIC data from MT5 with dual timeframe support
NO MYSQL/XAMPP REQUIRED
"""

import MetaTrader5 as mt5
import sqlite3
import time
import numpy as np
from datetime import datetime
import sys

# Import Fibonacci calculator (V2.021)
from fibonacci_calculator import calculate_fibonacci_data

# Import ATH calculator (V2.032)
from ath_calculator import calculate_ath_data

# Configuration
DB_PATH = 'mt5_intelligence.db'
SYMBOL = 'XAUG26.sim'  # Gold futures - updated for your broker

# Timeframe mapping
TIMEFRAMES = {
    '1m': mt5.TIMEFRAME_M1,
    '15m': mt5.TIMEFRAME_M15
}

# Indicator periods
ATR_PERIOD = 14
ATR_AVG_PERIOD = 50
EMA_SHORT_PERIOD = 4
EMA_MEDIUM_PERIOD = 22
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 2.5

class MT5Collector:
    def __init__(self, timeframes=['15m']):
        self.timeframes = timeframes
        self.last_bar_times = {tf: None for tf in timeframes}
        self.collection_counts = {tf: 0 for tf in timeframes}
        self.error_counts = {tf: 0 for tf in timeframes}
        
    def connect_mt5(self):
        """Initialize MT5 connection"""
        print("[MT5] Connecting to MetaTrader 5...")
        
        if not mt5.initialize():
            print(f"✗ MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Verify symbol
        symbol_info = mt5.symbol_info(SYMBOL)
        if symbol_info is None:
            print(f"✗ Symbol {SYMBOL} not found")
            mt5.shutdown()
            return False
        
        if not symbol_info.visible:
            if not mt5.symbol_select(SYMBOL, True):
                print(f"✗ Failed to select {SYMBOL}")
                mt5.shutdown()
                return False
        
        print(f"✓ Connected to MT5")
        print(f"✓ Symbol: {SYMBOL}")
        print(f"✓ Timeframes: {', '.join(self.timeframes)}")
        return True
    
    def check_database(self):
        """Check if database exists"""
        import os
        if not os.path.exists(DB_PATH):
            print(f"✗ Database not found. Run init.py first.")
            return False
        return True
    
    def calculate_atr(self, highs, lows, closes, period):
        """Calculate Average True Range"""
        tr_list = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return None
        
        atr = np.mean(tr_list[-period:])
        return round(atr, 5)
    
    def calculate_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = data[0]
        
        for price in data[1:]:
            ema = (price - ema) * multiplier + ema
        
        return round(ema, 5)
    
    def calculate_supertrend(self, highs, lows, closes, atr, period, multiplier):
        """Calculate Supertrend indicator"""
        if atr is None or len(closes) < period:
            return "NONE"
        
        # Basic ATR bands
        hl_avg = (highs[-1] + lows[-1]) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        # Simple trend determination
        if closes[-1] > upper_band:
            return "BULL"
        elif closes[-1] < lower_band:
            return "BEAR"
        else:
            return "NEUTRAL"
    
    def collect_data(self, timeframe_str):
        """Collect data for a specific timeframe"""
        timeframe = TIMEFRAMES[timeframe_str]
        
        # Get latest bar
        rates = mt5.copy_rates_from_pos(SYMBOL, timeframe, 0, 100)
        
        if rates is None or len(rates) == 0:
            print(f"✗ [{timeframe_str}] No data available")
            self.error_counts[timeframe_str] += 1
            return False
        
        latest = rates[-1]
        # Use broker time directly - no conversion needed
        bar_time = datetime.fromtimestamp(latest['time'])
        
        # Check if this is a new bar
        if self.last_bar_times[timeframe_str] == bar_time:
            return False  # Already collected this bar
        
        self.last_bar_times[timeframe_str] = bar_time
        
        # Extract OHLCV
        timestamp = bar_time.strftime('%Y-%m-%d %H:%M:%S')
        open_price = round(latest['open'], 5)
        high_price = round(latest['high'], 5)
        low_price = round(latest['low'], 5)
        close_price = round(latest['close'], 5)
        volume = int(latest['tick_volume'])
        
        # Calculate indicators
        highs = rates['high']
        lows = rates['low']
        closes = rates['close']
        
        atr_14 = self.calculate_atr(highs, lows, closes, ATR_PERIOD)
        atr_50_avg = self.calculate_atr(highs, lows, closes, ATR_AVG_PERIOD)
        atr_ratio = round(atr_14 / atr_50_avg, 5) if atr_14 and atr_50_avg else 0.0
        
        ema_short = self.calculate_ema(closes, EMA_SHORT_PERIOD)
        ema_medium = self.calculate_ema(closes, EMA_MEDIUM_PERIOD)
        ema_distance = round(ema_short - ema_medium, 5) if ema_short and ema_medium else 0.0
        
        supertrend = self.calculate_supertrend(
            highs, lows, closes, atr_14, 
            SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER
        )
        
        # Save to database
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Insert core data
            cursor.execute("""
                INSERT OR REPLACE INTO core_15m 
                (timestamp, timeframe, symbol, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, timeframe_str, SYMBOL, open_price, high_price, 
                  low_price, close_price, volume))
            
            # Insert basic indicators
            cursor.execute("""
                INSERT OR REPLACE INTO basic_15m
                (timestamp, timeframe, symbol, atr_14, atr_50_avg, atr_ratio,
                 ema_short, ema_medium, ema_distance, supertrend)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, timeframe_str, SYMBOL, atr_14, atr_50_avg, atr_ratio,
                  ema_short, ema_medium, ema_distance, supertrend))
            
            # === V2.021 - FIBONACCI CALCULATION ===
            fib_data = {'current_fib_zone': 'N/A'}  # Default if calculation fails
            try:
                # Calculate Fibonacci data
                fib_data = calculate_fibonacci_data(
                    highs=highs,
                    lows=lows,
                    close_price=close_price,
                    lookback_bars=100  # Default from Pine Script
                )
                
                # Insert Fibonacci data
                cursor.execute("""
                    INSERT OR REPLACE INTO fibonacci_data
                    (timestamp, timeframe, symbol, 
                     pivot_high, pivot_low, fib_range, lookback_bars,
                     fib_level_0000, fib_level_0118, fib_level_0236, fib_level_0309,
                     fib_level_0382, fib_level_0441, fib_level_0500, fib_level_0559,
                     fib_level_0618, fib_level_0702, fib_level_0786, fib_level_0893,
                     fib_level_1000, current_fib_zone, in_golden_zone, zone_multiplier,
                     distance_to_next_level, zone_time_percentile)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?)
                """, (
                    timestamp, timeframe_str, SYMBOL,
                    fib_data['pivot_high'], fib_data['pivot_low'], fib_data['fib_range'],
                    fib_data['lookback_bars'],
                    fib_data['fib_level_0000'], fib_data['fib_level_0118'], 
                    fib_data['fib_level_0236'], fib_data['fib_level_0309'],
                    fib_data['fib_level_0382'], fib_data['fib_level_0441'],
                    fib_data['fib_level_0500'], fib_data['fib_level_0559'],
                    fib_data['fib_level_0618'], fib_data['fib_level_0702'],
                    fib_data['fib_level_0786'], fib_data['fib_level_0893'],
                    fib_data['fib_level_1000'],
                    fib_data['current_fib_zone'], fib_data['in_golden_zone'],
                    fib_data['zone_multiplier'], fib_data['distance_to_next_level'],
                    fib_data['zone_time_percentile']
                ))
                
            except Exception as fib_error:
                print(f"✗ [{timeframe_str}] Fibonacci calculation error: {fib_error}")
                # Continue without Fibonacci data if calculation fails
            
            # === V2.032 - ATH (ALL-TIME HIGH) CALCULATION ===
            ath_data = {'ath_zone': 'N/A', 'ath_multiplier': 0.0}  # Default if calculation fails
            try:
                # Calculate ATH data
                ath_data = calculate_ath_data(
                    highs=highs,
                    current_close=close_price,
                    lookback_bars=500,  # ATH lookback from Pine Script
                    min_threshold=-3.0,
                    max_threshold=1.0,
                    mult_min=0.0,
                    mult_max=2.0
                )
                
                # Insert ATH data
                cursor.execute("""
                    INSERT OR REPLACE INTO ath_tracking
                    (timestamp, timeframe, symbol,
                     current_ath, ath_lookback_bars, current_close,
                     ath_distance_points, ath_distance_pct,
                     ath_min_threshold, ath_max_threshold, ath_multiplier,
                     ath_zone, distance_from_ath_percentile)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, timeframe_str, SYMBOL,
                    ath_data['current_ath'], ath_data['ath_lookback_bars'],
                    ath_data['current_close'],
                    ath_data['ath_distance_points'], ath_data['ath_distance_pct'],
                    ath_data['ath_min_threshold'], ath_data['ath_max_threshold'],
                    ath_data['ath_multiplier'],
                    ath_data['ath_zone'], ath_data['distance_from_ath_percentile']
                ))
                
            except Exception as ath_error:
                print(f"✗ [{timeframe_str}] ATH calculation error: {ath_error}")
                # Continue without ATH data if calculation fails
            
            # Update stats
            cursor.execute("""
                UPDATE collection_stats
                SET total_collections = total_collections + 1,
                    successful_collections = successful_collections + 1,
                    last_collection = ?,
                    updated_at = ?
                WHERE timeframe = ?
            """, (timestamp, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), timeframe_str))
            
            conn.commit()
            conn.close()
            
            self.collection_counts[timeframe_str] += 1
            
            print(f"✓ [{timeframe_str}] {timestamp} | Close: {close_price} | "
                  f"ATR: {atr_14} | ST: {supertrend} | Fib Zone: {fib_data.get('current_fib_zone', 'N/A')} | "
                  f"ATH: {ath_data.get('ath_zone', 'N/A')} ({ath_data.get('ath_multiplier', 0.0):.1f}x) | "
                  f"Count: {self.collection_counts[timeframe_str]}")
            
            return True
            
        except Exception as e:
            print(f"✗ [{timeframe_str}] Database error: {e}")
            self.error_counts[timeframe_str] += 1
            return False
    
    def run(self):
        """Main collection loop"""
        if not self.connect_mt5():
            return
        
        if not self.check_database():
            return
        
        print("\n" + "="*70)
        print("MT5 COLLECTOR RUNNING")
        print("="*70)
        print(f"Symbol: {SYMBOL}")
        print(f"Timeframes: {', '.join(self.timeframes)}")
        print(f"Database: {DB_PATH}")
        print("Press Ctrl+C to stop")
        print("="*70 + "\n")
        
        try:
            while True:
                for tf in self.timeframes:
                    self.collect_data(tf)
                
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("COLLECTION STOPPED")
            print("="*70)
            for tf in self.timeframes:
                print(f"[{tf}] Collections: {self.collection_counts[tf]} | "
                      f"Errors: {self.error_counts[tf]}")
            print("="*70)
            mt5.shutdown()

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python mt5_collector_sqlite.py [1m|15m|dual]")
        print("  1m   - Collect 1-minute data only")
        print("  15m  - Collect 15-minute data only")
        print("  dual - Collect both 1m and 15m data")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == 'dual':
        timeframes = ['1m', '15m']
    elif mode in ['1m', '15m']:
        timeframes = [mode]
    else:
        print(f"✗ Invalid mode: {mode}")
        print("Use: 1m, 15m, or dual")
        sys.exit(1)
    
    collector = MT5Collector(timeframes)
    collector.run()
