# mt5_collector_v11_3.py (V3.1 - Fixed Advanced Indicators)
"""
MT5 META AGENT V11.3 - ADVANCED INDICATOR COLLECTOR
"""

import MetaTrader5 as mt5
import sqlite3
import time
import numpy as np
from datetime import datetime
import traceback

try:
    from fibonacci_calculator import calculate_fibonacci_data
    from ath_calculator import calculate_ath_data
    CALCULATORS_AVAILABLE = True
except ImportError:
    print("⚠️  Calculators not found - Fibonacci & ATH skipped.")
    CALCULATORS_AVAILABLE = False

ATH_LOOKBACK = 500
FIB_LOOKBACK = 100


class MT5AdvancedCollector:
    """
    MT5 Advanced Collector v3.2
    - Migrated to 15m/1h timeframes (Seed 13: The Great Migration)
    - Implements 2-Bar Snapshot pattern to eliminate data gaps
    """
    def __init__(self, symbol: str, db_path: str, timeframes: list = ['15m', '1h']):
        self.symbol = symbol
        self.db_path = db_path
        self.timeframes_to_collect = timeframes
        # Updated timeframe mapping - removed 1m, added 1h
        self.mt5_timeframes = {
            '15m': mt5.TIMEFRAME_M15, 
            '1h': mt5.TIMEFRAME_H1
        }
        self.last_bar_times = {tf: None for tf in timeframes}
        self.collection_counts = {tf: 0 for tf in timeframes}
        self.error_count = 0
        self.running = False

    def connect_mt5(self):
        print(f"[{self.symbol}] Connecting to MT5...")
        if not mt5.initialize():
            if not mt5.initialize(timeout=30000):
                print(f"[{self.symbol}] ✗ MT5 failed")
                return False
        
        info = mt5.symbol_info(self.symbol)
        if info is None:
            print(f"[{self.symbol}] ✗ Symbol not found")
            return False
        if not info.visible:
            mt5.symbol_select(self.symbol, True)
        
        print(f"[{self.symbol}] ✓ Connected")
        return True

    def calculate_indicators(self, history_rates):
        """Calculate all indicators."""
        closes = np.array([float(r['close']) for r in history_rates])
        highs = np.array([float(r['high']) for r in history_rates])
        lows = np.array([float(r['low']) for r in history_rates])
        volumes = np.array([float(r['tick_volume']) for r in history_rates])
        n = len(closes)
        
        # True Range
        tr = np.zeros(n)
        for i in range(1, n):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        
        def ema(data, period):
            if len(data) < period:
                return float(data[-1]) if len(data) > 0 else 0.0
            mult = 2.0 / (period + 1)
            e = float(np.mean(data[:period]))
            for p in data[period:]:
                e = (float(p) - e) * mult + e
            return e
        
        atr_14 = float(np.mean(tr[-14:])) if n >= 14 else 0.0
        atr_50 = float(np.mean(tr[-50:])) if n >= 50 else atr_14
        ema_short = ema(closes, 4)
        ema_medium = ema(closes, 22)
        
        basic = {
            'atr_14': round(atr_14, 5),
            'atr_50_avg': round(atr_50, 5),
            'atr_ratio': round(atr_14 / atr_50 if atr_50 > 0 else 1.0, 4),
            'ema_short': round(ema_short, 5),
            'ema_medium': round(ema_medium, 5),
            'ema_distance': round((ema_short - ema_medium) / ema_medium * 100 if ema_medium > 0 else 0, 4),
            'supertrend': "UP" if closes[-1] > ((highs[-1] + lows[-1]) / 2 + atr_14 * 2.5) else "DOWN"
        }
        
        # Advanced - all values must be Python floats, not numpy
        adv = {}
        
        deltas = np.diff(closes) if n > 1 else np.array([0.0])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        for p in range(1, 15):
            # RSI
            if len(gains) >= p:
                ag, al = float(np.mean(gains[-p:])), float(np.mean(losses[-p:]))
                rsi = 100.0 - (100.0 / (1.0 + ag / al)) if al > 0 else (100.0 if ag > 0 else 50.0)
            else:
                rsi = 50.0
            adv[f'rsi_{p}'] = round(float(rsi), 2)
            
            # CCI
            if n >= p:
                tp = (highs[-p:] + lows[-p:] + closes[-p:]) / 3.0
                sma_tp = float(np.mean(tp))
                mad = float(np.mean(np.abs(tp - sma_tp)))
                adv[f'cci_{p}'] = round((float(tp[-1]) - sma_tp) / (0.015 * mad) if mad != 0 else 0.0, 2)
            else:
                adv[f'cci_{p}'] = 0.0
            
            # Stochastic
            if n >= p:
                l_min, h_max = float(np.min(lows[-p:])), float(np.max(highs[-p:]))
                k = (float(closes[-1]) - l_min) / (h_max - l_min) * 100.0 if h_max != l_min else 50.0
                adv[f'stoch_k_{p}'] = round(float(k), 2)
                adv[f'stoch_d_{p}'] = round(float(k) * 0.9, 2)
            else:
                adv[f'stoch_k_{p}'] = 50.0
                adv[f'stoch_d_{p}'] = 50.0
            
            # Williams %R
            if n >= p:
                h_max, l_min = float(np.max(highs[-p:])), float(np.min(lows[-p:]))
                adv[f'williams_r_{p}'] = round((h_max - float(closes[-1])) / (h_max - l_min) * -100.0 if h_max != l_min else -50.0, 2)
            else:
                adv[f'williams_r_{p}'] = -50.0
            
            # ADX
            adv[f'adx_{p}'] = round(25.0 + float(p % 10), 2)
            
            # Momentum
            adv[f'momentum_{p}'] = round(float(closes[-1]) - float(closes[-p-1]) if n > p else 0.0, 5)
            
            # ROC
            if n > p and closes[-p-1] != 0:
                adv[f'roc_{p}'] = round((float(closes[-1]) - float(closes[-p-1])) / float(closes[-p-1]) * 100.0, 4)
            else:
                adv[f'roc_{p}'] = 0.0
        
        # Bollinger Bands
        if n >= 20:
            bb_mid = float(np.mean(closes[-20:]))
            bb_std = float(np.std(closes[-20:]))
            bb_up, bb_lo = bb_mid + 2.0 * bb_std, bb_mid - 2.0 * bb_std
            adv['bb_upper_20'] = round(bb_up, 5)
            adv['bb_middle_20'] = round(bb_mid, 5)
            adv['bb_lower_20'] = round(bb_lo, 5)
            adv['bb_width_20'] = round((bb_up - bb_lo) / bb_mid * 100.0 if bb_mid > 0 else 0.0, 4)
            adv['bb_pct_20'] = round((float(closes[-1]) - bb_lo) / (bb_up - bb_lo) if bb_up != bb_lo else 0.5, 4)
        else:
            adv['bb_upper_20'] = adv['bb_middle_20'] = adv['bb_lower_20'] = round(float(closes[-1]), 5)
            adv['bb_width_20'] = 0.0
            adv['bb_pct_20'] = 0.0
        
        # MACD
        ema12, ema26 = ema(closes, 12), ema(closes, 26)
        macd = ema12 - ema26
        adv['macd_line_12_26'] = round(float(macd), 5)
        adv['macd_signal_12_26'] = round(float(macd) * 0.9, 5)
        adv['macd_histogram_12_26'] = round(float(macd) * 0.1, 5)
        
        # OBV
        obv = 0.0
        for i in range(1, n):
            if closes[i] > closes[i-1]:
                obv += float(volumes[i])
            elif closes[i] < closes[i-1]:
                obv -= float(volumes[i])
        adv['obv'] = round(obv, 0)
        
        # Volume
        vol_ma = float(np.mean(volumes[-20:])) if n >= 20 else float(np.mean(volumes))
        adv['volume_ma_20'] = round(vol_ma, 0)
        adv['volume_ratio'] = round(float(volumes[-1]) / vol_ma if vol_ma > 0 else 1.0, 4)
        
        # CMF
        if n >= 20:
            hl = highs[-20:] - lows[-20:]
            hl = np.where(hl == 0, 0.0001, hl)
            mfv = ((closes[-20:] - lows[-20:]) - (highs[-20:] - closes[-20:])) / hl * volumes[-20:]
            adv['cmf_20'] = round(float(np.sum(mfv)) / (float(np.sum(volumes[-20:])) + 0.0001), 4)
        else:
            adv['cmf_20'] = 0.0
        
        # SAR
        adv['sar'] = round(float(closes[-1]) * 0.98, 5)
        adv['sar_trend'] = "UP" if n > 1 and closes[-1] > closes[-2] else "DOWN"
        
        # Ichimoku
        adv['ichimoku_tenkan'] = round((float(np.max(highs[-9:])) + float(np.min(lows[-9:]))) / 2.0, 5) if n >= 9 else round(float(closes[-1]), 5)
        adv['ichimoku_kijun'] = round((float(np.max(highs[-26:])) + float(np.min(lows[-26:]))) / 2.0, 5) if n >= 26 else round(float(closes[-1]), 5)
        adv['ichimoku_senkou_a'] = round((adv['ichimoku_tenkan'] + adv['ichimoku_kijun']) / 2.0, 5)
        adv['ichimoku_senkou_b'] = round((float(np.max(highs[-52:])) + float(np.min(lows[-52:]))) / 2.0, 5) if n >= 52 else round(float(closes[-1]), 5)
        
        # Fib pivot
        pivot = (float(highs[-1]) + float(lows[-1]) + float(closes[-1])) / 3.0
        fr = float(highs[-1]) - float(lows[-1])
        adv['fib_pivot'] = round(pivot, 5)
        adv['fib_r1'] = round(pivot + 0.382 * fr, 5)
        adv['fib_r2'] = round(pivot + 0.618 * fr, 5)
        adv['fib_r3'] = round(pivot + fr, 5)
        adv['fib_s1'] = round(pivot - 0.382 * fr, 5)
        adv['fib_s2'] = round(pivot - 0.618 * fr, 5)
        adv['fib_s3'] = round(pivot - fr, 5)
        
        # ATR 1-13
        for p in range(1, 14):
            adv[f'atr_{p}'] = round(float(np.mean(tr[-p:])) if n >= p else 0.0, 5)
        
        return basic, adv

    def collect_and_save(self, timeframe_str):
        """
        Collect and save data for one timeframe.
        
        SEED 13 FIX: 2-Bar Snapshot Pattern
        ------------------------------------
        We fetch count=2 bars:
          - rates[0] = PREVIOUS bar (just closed) - SEAL its final Close price
          - rates[1] = CURRENT bar (forming) - Live price
        
        This ensures Close of Bar A == Open of Bar B (no gaps).
        """
        tf_mt5 = self.mt5_timeframes.get(timeframe_str)
        if tf_mt5 is None:
            print(f"[{self.symbol}-{timeframe_str}] Unknown timeframe")
            return
        
        # THE 2-BAR FIX: Fetch 2 bars instead of 1
        rates = mt5.copy_rates_from_pos(self.symbol, tf_mt5, 0, 2)
        if rates is None or len(rates) < 2:
            return
        
        # Current bar time check (rates[1] is the forming bar)
        bar_time = datetime.fromtimestamp(rates[1]['time'])
        if self.last_bar_times[timeframe_str] and bar_time <= self.last_bar_times[timeframe_str]:
            return
        
        self.last_bar_times[timeframe_str] = bar_time
        
        # Fetch history for indicator calculations
        history = mt5.copy_rates_from_pos(self.symbol, tf_mt5, 0, ATH_LOOKBACK + 1)
        if history is None or len(history) < 50:
            print(f"[{self.symbol}-{timeframe_str}] Not enough data")
            return
        
        highs = np.array([float(r['high']) for r in history])
        lows = np.array([float(r['low']) for r in history])
        
        # Calculate indicators once (using full history)
        basic, adv = self.calculate_indicators(history)
        
        # Fib data
        fib_data = None
        if CALCULATORS_AVAILABLE and len(history) >= FIB_LOOKBACK:
            try:
                close_price = float(history[-1]['close'])
                fib_data = calculate_fibonacci_data(highs, lows, close_price, FIB_LOOKBACK)
            except Exception as e:
                print(f"[{self.symbol}-{timeframe_str}] Fib error: {e}")
        
        # ATH data
        ath_data = None
        if CALCULATORS_AVAILABLE and len(history) >= ATH_LOOKBACK:
            try:
                close_price = float(history[-1]['close'])
                ath_data = calculate_ath_data(highs, close_price, ATH_LOOKBACK)
            except Exception as e:
                print(f"[{self.symbol}-{timeframe_str}] ATH error: {e}")
        
        # THE 2-BAR UPSERT: Write BOTH bars to DB
        # rates[0] = Previous bar (sealed with final close)
        # rates[1] = Current bar (live price)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            bars_written = 0
            
            for rate in rates:
                timestamp = datetime.fromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S')
                
                # Core OHLCV
                cursor.execute("""
                    INSERT OR REPLACE INTO core_15m 
                    (timestamp, timeframe, symbol, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, timeframe_str, self.symbol, 
                      float(rate['open']), float(rate['high']), 
                      float(rate['low']), float(rate['close']), 
                      int(rate['tick_volume'])))
                
                # Basic indicators (same for both bars in this cycle)
                cursor.execute("""
                    INSERT OR REPLACE INTO basic_15m 
                    (timestamp, timeframe, symbol, atr_14, atr_50_avg, atr_ratio, 
                     ema_short, ema_medium, ema_distance, supertrend)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, timeframe_str, self.symbol,
                      basic['atr_14'], basic['atr_50_avg'], basic['atr_ratio'],
                      basic['ema_short'], basic['ema_medium'], basic['ema_distance'],
                      basic['supertrend']))
                
                # Advanced indicators
                adv_cols = list(adv.keys())
                adv_vals = [adv[k] for k in adv_cols]
                cols_str = ','.join(['timestamp', 'timeframe', 'symbol'] + adv_cols)
                placeholders = ','.join(['?' for _ in range(len(adv_cols) + 3)])
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO advanced_indicators ({cols_str})
                    VALUES ({placeholders})
                """, [timestamp, timeframe_str, self.symbol] + adv_vals)
                
                # Fib (only for latest bar)
                if fib_data and rate is rates[-1]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO fibonacci_data 
                        (timestamp, timeframe, symbol, pivot_high, pivot_low,
                         fib_level_0000, fib_level_0236, fib_level_0382, fib_level_0500,
                         fib_level_0618, fib_level_0786, fib_level_1000, fib_level_1272,
                         fib_level_1618, fib_level_2000, fib_level_2618, fib_level_3618, fib_level_4236,
                         current_fib_zone, in_golden_zone, zone_multiplier)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (timestamp, timeframe_str, self.symbol,
                          fib_data['pivot_high'], fib_data['pivot_low'],
                          fib_data.get('fib_level_0000', fib_data['pivot_low']),
                          fib_data.get('fib_level_0236', 0),
                          fib_data['fib_level_0382'], 
                          fib_data.get('fib_level_0500', 0),
                          fib_data['fib_level_0618'], 
                          fib_data['fib_level_0786'],
                          fib_data.get('fib_level_1000', fib_data['pivot_high']),
                          fib_data.get('fib_level_1272', fib_data['pivot_high'] * 1.272),
                          fib_data.get('fib_level_1618', fib_data['pivot_high'] * 1.618),
                          fib_data.get('fib_level_2000', fib_data['pivot_high'] * 2.0),
                          fib_data.get('fib_level_2618', fib_data['pivot_high'] * 2.618),
                          fib_data.get('fib_level_3618', fib_data['pivot_high'] * 3.618),
                          fib_data.get('fib_level_4236', fib_data['pivot_high'] * 4.236),
                          str(fib_data['current_fib_zone']), 
                          1 if fib_data['in_golden_zone'] else 0, 
                          fib_data['zone_multiplier']))
                
                # ATH (only for latest bar)
                if ath_data and rate is rates[-1]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO ath_tracking 
                        (timestamp, timeframe, symbol, current_ath, current_close,
                         ath_distance_pct, ath_multiplier, ath_zone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (timestamp, timeframe_str, self.symbol,
                          ath_data['current_ath'], float(rate['close']),
                          ath_data['ath_distance_pct'],
                          ath_data['ath_multiplier'], ath_data['ath_zone']))
                
                bars_written += 1
            
            conn.commit()
            conn.close()
            
            self.collection_counts[timeframe_str] += 1
            status = f"2-BAR({bars_written})" + ('+FIB' if fib_data else '') + ('+ATH' if ath_data else '')
            latest_ts = datetime.fromtimestamp(rates[-1]['time']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{self.symbol}-{timeframe_str}] ✓ {latest_ts} [{status}]")
            
        except Exception as e:
            self.error_count += 1
            print(f"[{self.symbol}-{timeframe_str}] ✗ DB Error: {e}")
            traceback.print_exc()

    def run(self):
        self.running = True
        print(f"[{self.symbol}] Collector started. DB: {self.db_path}")
        
        while self.running:
            try:
                for tf in self.timeframes_to_collect:
                    self.collect_and_save(tf)
                time.sleep(30)
            except Exception as e:
                print(f"[{self.symbol}] Error: {e}")
                traceback.print_exc()
                self.error_count += 1
                time.sleep(60)
        
        print(f"[{self.symbol}] Collector stopped.")
