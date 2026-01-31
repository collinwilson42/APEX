# mt5_multi_collector.py
"""
MT5 Multi-Symbol Collector - Single MT5 Connection, Multiple Symbols
=====================================================================
This collector manages a single MT5 connection and collects data for
multiple symbols, storing to their respective databases.

The MT5 Python API is singleton-based, so we need one connection
that handles all symbols rather than multiple connections.
"""

import MetaTrader5 as mt5
import sqlite3
import time
import numpy as np
from datetime import datetime
import threading
from typing import Dict, List, Optional

# Import calculators safely
try:
    from fibonacci_calculator import calculate_fibonacci_data
    from ath_calculator import calculate_ath_data
    CALCULATORS_AVAILABLE = True
except ImportError:
    CALCULATORS_AVAILABLE = False

# Default periods
ATR_PERIOD = 14
ATR_AVG_PERIOD = 50
EMA_SHORT_PERIOD = 4
EMA_MEDIUM_PERIOD = 22
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 2.5


class MT5MultiSymbolCollector:
    """
    Manages data collection for multiple symbols through a single MT5 connection.
    """
    
    def __init__(self, symbols_config: Dict[str, dict], timeframes: List[str] = None):
        """
        Initialize the multi-symbol collector.
        
        Args:
            symbols_config: Dict of {symbol_id: {mt5_symbol, db_path, name}}
            timeframes: List of timeframes to collect (default: ['1m', '15m'])
        """
        self.symbols_config = symbols_config
        self.timeframes = timeframes or ['1m', '15m']
        
        self.mt5_timeframes = {
            '1m': mt5.TIMEFRAME_M1,
            '15m': mt5.TIMEFRAME_M15
        }
        
        # Track last bar time per symbol per timeframe
        self.last_bar_times = {}
        for sym_id in symbols_config:
            self.last_bar_times[sym_id] = {tf: None for tf in self.timeframes}
        
        # Collection stats
        self.collection_counts = {}
        for sym_id in symbols_config:
            self.collection_counts[sym_id] = {tf: 0 for tf in self.timeframes}
        
        self.error_count = 0
        self.running = False
        self.connected = False
    
    def connect_mt5(self) -> bool:
        """Initialize MT5 connection"""
        print("[MT5] Connecting to MetaTrader 5...")
        
        if not mt5.initialize():
            print(f"[MT5] ✗ Initialization failed: {mt5.last_error()}")
            # Retry with extended timeout
            if not mt5.initialize(timeout=30000):
                print(f"[MT5] ✗ Second attempt failed: {mt5.last_error()}")
                return False
        
        terminal = mt5.terminal_info()
        if terminal:
            print(f"[MT5] ✓ Connected: {terminal.name}")
            print(f"[MT5]   Build: {terminal.build}")
        
        # Verify all symbols
        valid_symbols = []
        for sym_id, config in self.symbols_config.items():
            mt5_symbol = config['symbol']
            info = mt5.symbol_info(mt5_symbol)
            
            if info is None:
                print(f"[MT5] ⚠️  Symbol {mt5_symbol} not found")
                continue
            
            if not info.visible:
                if not mt5.symbol_select(mt5_symbol, True):
                    print(f"[MT5] ⚠️  Could not select {mt5_symbol}")
                    continue
                print(f"[MT5]   Added {mt5_symbol} to Market Watch")
            
            valid_symbols.append(sym_id)
            print(f"[MT5] ✓ {sym_id}: {mt5_symbol}")
        
        if not valid_symbols:
            print("[MT5] ✗ No valid symbols found")
            mt5.shutdown()
            return False
        
        # Remove invalid symbols from config
        self.symbols_config = {k: v for k, v in self.symbols_config.items() if k in valid_symbols}
        
        self.connected = True
        return True
    
    def disconnect_mt5(self):
        """Shutdown MT5 connection"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("[MT5] Disconnected")
    
    def calculate_basic_indicators(self, rates):
        """Calculate basic indicators from OHLCV data"""
        n = len(rates)
        
        opens = np.array([r['open'] for r in rates], dtype=np.float64)
        highs = np.array([r['high'] for r in rates], dtype=np.float64)
        lows = np.array([r['low'] for r in rates], dtype=np.float64)
        closes = np.array([r['close'] for r in rates], dtype=np.float64)
        volumes = np.array([r['tick_volume'] for r in rates], dtype=np.float64)
        
        # ATR
        tr = np.zeros(n)
        atr = np.zeros(n)
        
        tr[0] = highs[0] - lows[0]
        for i in range(1, n):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr[i] = max(hl, hc, lc)
        
        if n >= ATR_PERIOD:
            atr[ATR_PERIOD-1] = np.mean(tr[:ATR_PERIOD])
            for i in range(ATR_PERIOD, n):
                atr[i] = (atr[i-1] * (ATR_PERIOD-1) + tr[i]) / ATR_PERIOD
        
        # ATR Average (EMA)
        atr_avg = np.zeros(n)
        mult = 2 / (ATR_AVG_PERIOD + 1)
        if n >= ATR_AVG_PERIOD:
            atr_avg[ATR_AVG_PERIOD-1] = np.mean(atr[:ATR_AVG_PERIOD])
            for i in range(ATR_AVG_PERIOD, n):
                atr_avg[i] = (atr[i] - atr_avg[i-1]) * mult + atr_avg[i-1]
        
        # EMAs
        ema_short = np.zeros(n)
        ema_medium = np.zeros(n)
        mult_short = 2 / (EMA_SHORT_PERIOD + 1)
        mult_medium = 2 / (EMA_MEDIUM_PERIOD + 1)
        
        if n >= EMA_SHORT_PERIOD:
            ema_short[EMA_SHORT_PERIOD-1] = np.mean(closes[:EMA_SHORT_PERIOD])
            for i in range(EMA_SHORT_PERIOD, n):
                ema_short[i] = (closes[i] - ema_short[i-1]) * mult_short + ema_short[i-1]
        
        if n >= EMA_MEDIUM_PERIOD:
            ema_medium[EMA_MEDIUM_PERIOD-1] = np.mean(closes[:EMA_MEDIUM_PERIOD])
            for i in range(EMA_MEDIUM_PERIOD, n):
                ema_medium[i] = (closes[i] - ema_medium[i-1]) * mult_medium + ema_medium[i-1]
        
        # Supertrend
        hl2 = (highs + lows) / 2
        upper_band = hl2 + (SUPERTREND_MULTIPLIER * atr)
        lower_band = hl2 - (SUPERTREND_MULTIPLIER * atr)
        supertrend = np.zeros(n)
        direction = np.ones(n)
        
        for i in range(SUPERTREND_PERIOD, n):
            if closes[i] > upper_band[i-1]:
                direction[i] = 1
            elif closes[i] < lower_band[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
            
            if direction[i] == 1:
                lower_band[i] = max(lower_band[i], lower_band[i-1]) if direction[i-1] == 1 else lower_band[i]
                supertrend[i] = lower_band[i]
            else:
                upper_band[i] = min(upper_band[i], upper_band[i-1]) if direction[i-1] == -1 else upper_band[i]
                supertrend[i] = upper_band[i]
        
        return {
            'opens': opens,
            'highs': highs,
            'lows': lows,
            'closes': closes,
            'volumes': volumes,
            'atr_14': atr,
            'atr_50_avg': atr_avg,
            'ema_short': ema_short,
            'ema_medium': ema_medium,
            'supertrend': supertrend,
            'st_direction': direction
        }
    
    def collect_symbol_timeframe(self, sym_id: str, config: dict, tf: str):
        """Collect data for one symbol and timeframe"""
        mt5_symbol = config['symbol']
        db_path = config['db_path']
        mt5_tf = self.mt5_timeframes[tf]
        
        # Get latest bar
        rates = mt5.copy_rates_from_pos(mt5_symbol, mt5_tf, 0, 1)
        if rates is None or len(rates) == 0:
            return  # No data available
        
        latest_bar_time = datetime.fromtimestamp(rates[0]['time'])
        
        # Check if this is a new bar
        if self.last_bar_times[sym_id][tf] and latest_bar_time <= self.last_bar_times[sym_id][tf]:
            return  # Not a new bar
        
        self.last_bar_times[sym_id][tf] = latest_bar_time
        
        # Get history for indicator calculation
        history = mt5.copy_rates_from_pos(mt5_symbol, mt5_tf, 0, 100)
        if history is None or len(history) < 50:
            return  # Not enough data
        
        latest = history[-1]
        timestamp = datetime.fromtimestamp(latest['time']).strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate indicators
        indicators = self.calculate_basic_indicators(history)
        idx = -1  # Latest bar index
        
        atr_ratio = indicators['atr_14'][idx] / indicators['atr_50_avg'][idx] if indicators['atr_50_avg'][idx] != 0 else 0
        ema_dist = (indicators['closes'][idx] - indicators['ema_medium'][idx]) / indicators['atr_14'][idx] if indicators['atr_14'][idx] != 0 else 0
        st_signal = 'BULL' if indicators['st_direction'][idx] == 1 else 'BEAR'
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Insert core data - try timeframe-specific table first
                core_table = f'core_{tf}'
                basic_table = f'basic_{tf}'
                
                try:
                    cursor.execute(f"SELECT 1 FROM {core_table} LIMIT 1")
                except sqlite3.OperationalError:
                    core_table = 'core_15m'
                    basic_table = 'basic_15m'
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {core_table}
                    (timestamp, timeframe, symbol, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, tf, mt5_symbol,
                    float(latest['open']), float(latest['high']),
                    float(latest['low']), float(latest['close']),
                    int(latest['tick_volume'])
                ))
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {basic_table}
                    (timestamp, timeframe, symbol, atr_14, atr_50_avg, atr_ratio, 
                     ema_short, ema_medium, ema_distance, supertrend)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, tf, mt5_symbol,
                    float(indicators['atr_14'][idx]),
                    float(indicators['atr_50_avg'][idx]),
                    float(atr_ratio),
                    float(indicators['ema_short'][idx]),
                    float(indicators['ema_medium'][idx]),
                    float(ema_dist),
                    st_signal
                ))
                
                conn.commit()
                self.collection_counts[sym_id][tf] += 1
                
                total = self.collection_counts[sym_id][tf]
                print(f"[{sym_id}-{tf}] ✓ {timestamp} | Total: {total}")
                
        except Exception as e:
            self.error_count += 1
            print(f"[{sym_id}-{tf}] ✗ Error: {e}")
    
    def collection_cycle(self):
        """Run one collection cycle for all symbols and timeframes"""
        for sym_id, config in self.symbols_config.items():
            for tf in self.timeframes:
                try:
                    self.collect_symbol_timeframe(sym_id, config, tf)
                except Exception as e:
                    self.error_count += 1
                    print(f"[{sym_id}-{tf}] ✗ Cycle error: {e}")
    
    def run(self, interval: int = 30):
        """
        Main collection loop.
        
        Args:
            interval: Seconds between collection cycles (default: 30)
        """
        self.running = True
        print(f"\n[COLLECTOR] Starting multi-symbol collection (interval: {interval}s)")
        print(f"[COLLECTOR] Symbols: {', '.join(self.symbols_config.keys())}")
        print(f"[COLLECTOR] Timeframes: {', '.join(self.timeframes)}")
        
        while self.running:
            try:
                self.collection_cycle()
                time.sleep(interval)
            except Exception as e:
                self.error_count += 1
                print(f"[COLLECTOR] ✗ Loop error: {e}")
                time.sleep(60)  # Wait longer after error
        
        print("[COLLECTOR] Stopped")
    
    def stop(self):
        """Stop the collector"""
        self.running = False
    
    def get_stats(self) -> dict:
        """Get collection statistics"""
        total = sum(
            sum(counts.values())
            for counts in self.collection_counts.values()
        )
        
        return {
            'running': self.running,
            'connected': self.connected,
            'symbols': list(self.symbols_config.keys()),
            'collection_counts': self.collection_counts,
            'total_collected': total,
            'error_count': self.error_count
        }


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == '__main__':
    import os
    
    # Import from central config
    import sys
    sys.path.insert(0, '.')
    from config import SYMBOL_DATABASES
    
    # Convert to format expected by collector
    SYMBOLS = {
        sym_id: {
            'symbol': config['symbol'],
            'db_path': config['db_path'],
            'name': config['name']
        }
        for sym_id, config in SYMBOL_DATABASES.items()
    }
    
    # Filter to existing databases
    valid_symbols = {k: v for k, v in SYMBOLS.items() if os.path.exists(v['db_path'])}
    
    if not valid_symbols:
        print("No databases found. Run init_databases.py first.")
        exit(1)
    
    print(f"Found {len(valid_symbols)} databases")
    
    collector = MT5MultiSymbolCollector(valid_symbols)
    
    if collector.connect_mt5():
        try:
            collector.run(interval=30)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            collector.stop()
        finally:
            collector.disconnect_mt5()
    else:
        print("Failed to connect to MT5")
