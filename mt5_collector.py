#!/usr/bin/env python3
"""
MT5 Meta Agent V9 - Data Collector
Collects CORE + BASIC data from MT5 every 15 minutes
"""

import MetaTrader5 as mt5
import sqlite3
import time
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Configuration
DB_PATH = 'intelligence.db'
SYMBOL = 'XAUG26.sim'
TIMEFRAME = mt5.TIMEFRAME_M15
COLLECTION_INTERVAL = 60  # Check every 60 seconds

# Indicator periods
ATR_PERIOD = 14
ATR_AVG_PERIOD = 50
EMA_SHORT_PERIOD = 4
EMA_MEDIUM_PERIOD = 22
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 2.5

class MT5Collector:
    def __init__(self):
        self.last_bar_time = None
        self.collection_count = 0
        self.error_count = 0
        
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
        print(f"  Symbol: {SYMBOL}")
        print(f"  Timeframe: 15M")
        print(f"  Server: {mt5.account_info().server}")
        print()
        
        return True
    
    def calculate_atr(self, highs, lows, closes, period):
        """Calculate Average True Range"""
        tr_list = []
        
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return None
        
        atr = np.mean(tr_list[-period:])
        return round(atr, 2)
    
    def calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])  # Start with SMA
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return round(ema, 2)
    
    def calculate_supertrend(self, highs, lows, closes, period, multiplier):
        """Calculate Supertrend direction (1=bullish, 0=bearish)"""
        atr = self.calculate_atr(highs, lows, closes, period)
        
        if atr is None:
            return None
        
        # Basic bands
        hl_avg = (highs[-1] + lows[-1]) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        # Direction: 1 if close above lower band, 0 if below upper band
        close = closes[-1]
        
        if close > lower_band:
            return 1  # Bullish
        elif close < upper_band:
            return 0  # Bearish
        else:
            return 1  # Default bullish
    
    def collect_data(self):
        """Collect CORE + BASIC data from MT5"""
        
        # Get last 100 bars for indicator calculations
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)
        
        if rates is None or len(rates) == 0:
            raise Exception(f"Failed to get rates: {mt5.last_error()}")
        
        # Latest bar (index 0 is most recent in copy_rates_from_pos)
        latest = rates[-1]
        
        # Check if this is a new bar
        bar_time = datetime.fromtimestamp(latest['time'])
        
        if self.last_bar_time and bar_time <= self.last_bar_time:
            return None  # Not a new bar yet
        
        self.last_bar_time = bar_time
        
        # Extract arrays for calculations
        closes = rates['close']
        highs = rates['high']
        lows = rates['low']
        
        # ====================================================================
        # CORE DATA
        # ====================================================================
        core_data = {
            'timestamp': bar_time.strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': SYMBOL,
            'open': round(latest['open'], 2),
            'high': round(latest['high'], 2),
            'low': round(latest['low'], 2),
            'close': round(latest['close'], 2),
            'volume': int(latest['tick_volume'])
        }
        
        # ====================================================================
        # BASIC INDICATORS
        # ====================================================================
        atr_14 = self.calculate_atr(highs, lows, closes, ATR_PERIOD)
        atr_50_avg = self.calculate_atr(highs, lows, closes, ATR_AVG_PERIOD)
        atr_ratio = round(atr_14 / atr_50_avg, 3) if (atr_14 and atr_50_avg and atr_50_avg != 0) else None
        
        ema_short = self.calculate_ema(closes, EMA_SHORT_PERIOD)
        ema_medium = self.calculate_ema(closes, EMA_MEDIUM_PERIOD)
        ema_distance = round(ema_short - ema_medium, 2) if (ema_short and ema_medium) else None
        
        supertrend_dir = self.calculate_supertrend(highs, lows, closes, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER)
        
        basic_data = {
            'timestamp': core_data['timestamp'],
            'atr_14': atr_14,
            'atr_50_avg': atr_50_avg,
            'atr_ratio': atr_ratio,
            'ema_short': ema_short,
            'ema_medium': ema_medium,
            'ema_distance': ema_distance,
            'supertrend_direction': supertrend_dir
        }
        
        return {
            'core': core_data,
            'basic': basic_data
        }
    
    def save_to_database(self, data):
        """Save collected data to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Insert CORE data
            cursor.execute('''
                INSERT INTO core_15m (timestamp, symbol, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['core']['timestamp'],
                data['core']['symbol'],
                data['core']['open'],
                data['core']['high'],
                data['core']['low'],
                data['core']['close'],
                data['core']['volume']
            ))
            
            core_id = cursor.lastrowid
            
            # Insert BASIC data
            cursor.execute('''
                INSERT INTO basic_15m (timestamp, core_id, atr_14, atr_50_avg, atr_ratio, 
                                      ema_short, ema_medium, ema_distance, supertrend_direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['basic']['timestamp'],
                core_id,
                data['basic']['atr_14'],
                data['basic']['atr_50_avg'],
                data['basic']['atr_ratio'],
                data['basic']['ema_short'],
                data['basic']['ema_medium'],
                data['basic']['ema_distance'],
                data['basic']['supertrend_direction']
            ))
            
            # Update collector status
            cursor.execute('''
                UPDATE collector_status 
                SET status = 'RUNNING',
                    last_collection = ?,
                    total_collections = total_collections + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (data['core']['timestamp'],))
            
            conn.commit()
            
            self.collection_count += 1
            
            print(f"[{data['core']['timestamp']}] ✓ Data saved (Collection #{self.collection_count})")
            print(f"  Close: {data['core']['close']} | ATR: {data['basic']['atr_14']} | ST: {'BULL' if data['basic']['supertrend_direction'] == 1 else 'BEAR'}")
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def update_error_status(self, error_msg):
        """Update database with error status"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE collector_status 
                SET errors_count = errors_count + 1,
                    last_error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (str(error_msg),))
            
            conn.commit()
            conn.close()
            
            self.error_count += 1
            
        except:
            pass
    
    def run(self):
        """Main collection loop"""
        print("=" * 70)
        print("MT5 META AGENT V9 - DATA COLLECTOR")
        print("=" * 70)
        print()
        
        if not self.connect_mt5():
            sys.exit(1)
        
        print("[COLLECTOR] Starting collection loop...")
        print(f"  Checking for new bars every {COLLECTION_INTERVAL} seconds")
        print(f"  Press Ctrl+C to stop")
        print()
        print("-" * 70)
        print()
        
        try:
            while True:
                try:
                    data = self.collect_data()
                    
                    if data:
                        self.save_to_database(data)
                    
                    time.sleep(COLLECTION_INTERVAL)
                    
                except Exception as e:
                    print(f"✗ Collection error: {e}")
                    self.update_error_status(str(e))
                    time.sleep(COLLECTION_INTERVAL)
                    
        except KeyboardInterrupt:
            print()
            print("-" * 70)
            print()
            print("[SHUTDOWN] Stopping collector...")
            
            # Update status
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE collector_status 
                SET status = 'STOPPED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''')
            conn.commit()
            conn.close()
            
            mt5.shutdown()
            
            print(f"✓ Collector stopped")
            print(f"  Total collections: {self.collection_count}")
            print(f"  Total errors: {self.error_count}")
            print()

if __name__ == '__main__':
    # Check if MetaTrader5 is installed
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("✗ MetaTrader5 package not installed")
        print()
        print("Install with:")
        print("  pip install MetaTrader5 --break-system-packages")
        print()
        sys.exit(1)
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print("✗ Database not found. Run database_init.py first.")
        sys.exit(1)
    
    collector = MT5Collector()
    collector.run()