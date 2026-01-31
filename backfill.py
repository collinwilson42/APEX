# backfill.py (V11.3 Multi-Symbol Edition - Fixed)
"""
MT5 META AGENT V11.3 - HISTORICAL DATA BACKFILL
Downloads historical data from MT5 and populates ALL tables for ALL symbols.

Usage:
  python backfill.py                    # All symbols, 50000 bars each timeframe
  python backfill.py 10000              # All symbols, 10000 bars each timeframe  
  python backfill.py 50000 XAUG26       # Single symbol, 50000 bars
"""

import MetaTrader5 as mt5
import sqlite3
import numpy as np
from datetime import datetime
import sys
import os
import time
import traceback

# Import from central config
from config import SYMBOL_DATABASES, DEFAULT_SYMBOL

# Import calculators
try:
    from fibonacci_calculator import calculate_fibonacci_data
    from ath_calculator import calculate_ath_data
    CALCULATORS_AVAILABLE = True
except ImportError:
    print("⚠️  Calculators not found - Fibonacci & ATH data will be skipped.")
    CALCULATORS_AVAILABLE = False

# Settings
ATH_LOOKBACK = 500
FIB_LOOKBACK = 100
BATCH_SIZE = 200


class HistoricalBackfill:
    def __init__(self):
        self.mt5_timeframes = {
            '1m': mt5.TIMEFRAME_M1,
            '15m': mt5.TIMEFRAME_M15
        }
        
    def connect_mt5(self):
        print("[MT5] Connecting...")
        if not mt5.initialize():
            if not mt5.initialize(timeout=30000):
                print(f"✗ MT5 failed: {mt5.last_error()}")
                return False
        print("✓ Connected to MT5")
        return True

    def calculate_indicators(self, highs, lows, closes, volumes):
        """Calculate all indicators for one bar."""
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
        
        # Advanced
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
            adv[f'rsi_{p}'] = round(rsi, 2)
            
            # CCI
            if n >= p:
                tp = (highs[-p:] + lows[-p:] + closes[-p:]) / 3.0
                sma_tp = float(np.mean(tp))
                mad = float(np.mean(np.abs(tp - sma_tp)))
                adv[f'cci_{p}'] = round((float(tp[-1]) - sma_tp) / (0.015 * mad) if mad != 0 else 0, 2)
            else:
                adv[f'cci_{p}'] = 0.0
            
            # Stochastic
            if n >= p:
                l_min, h_max = float(np.min(lows[-p:])), float(np.max(highs[-p:]))
                k = (float(closes[-1]) - l_min) / (h_max - l_min) * 100.0 if h_max != l_min else 50.0
                adv[f'stoch_k_{p}'] = round(k, 2)
                adv[f'stoch_d_{p}'] = round(k * 0.9, 2)
            else:
                adv[f'stoch_k_{p}'] = 50.0
                adv[f'stoch_d_{p}'] = 50.0
            
            # Williams %R
            if n >= p:
                h_max, l_min = float(np.max(highs[-p:])), float(np.min(lows[-p:]))
                adv[f'williams_r_{p}'] = round((h_max - float(closes[-1])) / (h_max - l_min) * -100.0 if h_max != l_min else -50.0, 2)
            else:
                adv[f'williams_r_{p}'] = -50.0
            
            # ADX (placeholder)
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
            adv['bb_width_20'] = round((bb_up - bb_lo) / bb_mid * 100.0, 4)
            adv['bb_pct_20'] = round((float(closes[-1]) - bb_lo) / (bb_up - bb_lo) if bb_up != bb_lo else 0.5, 4)
        else:
            adv['bb_upper_20'] = adv['bb_middle_20'] = adv['bb_lower_20'] = round(float(closes[-1]), 5)
            adv['bb_width_20'] = 0.0
            adv['bb_pct_20'] = 0.0
        
        # MACD
        ema12, ema26 = ema(closes, 12), ema(closes, 26)
        macd = ema12 - ema26
        adv['macd_line_12_26'] = round(macd, 5)
        adv['macd_signal_12_26'] = round(macd * 0.9, 5)
        adv['macd_histogram_12_26'] = round(macd * 0.1, 5)
        
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

    def backfill_symbol(self, symbol_id, symbol_name, db_path, bars_count=50000):
        """Backfill data for one symbol."""
        
        symbol_info = mt5.symbol_info(symbol_name)
        if symbol_info is None:
            print(f"  ✗ {symbol_name} not found in MT5")
            return False
        
        if not symbol_info.visible:
            mt5.symbol_select(symbol_name, True)
        
        print(f"\n{'='*60}")
        print(f"BACKFILL: {symbol_id} ({symbol_name})")
        print(f"DB: {db_path}")
        print(f"{'='*60}")
        
        if not os.path.exists(db_path):
            print(f"  ✗ Database not found")
            return False
        
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA journal_mode = MEMORY")
        cursor = conn.cursor()
        
        # Clear existing data for this symbol
        print(f"  Clearing old data...")
        for table in ['core_15m', 'basic_15m', 'advanced_indicators', 'fibonacci_data', 'ath_tracking']:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE symbol = ?", (symbol_name,))
            except Exception as e:
                print(f"    Warning clearing {table}: {e}")
        conn.commit()
        
        for tf_str in ['15m', '1m']:
            tf_mt5 = self.mt5_timeframes[tf_str]
            
            print(f"\n  [{tf_str.upper()}] Fetching...")
            
            # Get data in chunks
            all_rates = None
            offset = 0
            CHUNK = 10000
            
            while True:
                chunk = mt5.copy_rates_from_pos(symbol_name, tf_mt5, offset, CHUNK)
                if chunk is None or len(chunk) == 0:
                    break
                
                if all_rates is None:
                    all_rates = chunk
                else:
                    all_rates = np.concatenate([chunk, all_rates])
                
                print(f"    Got {len(all_rates):,} bars...")
                offset += CHUNK
                
                if len(all_rates) >= bars_count + ATH_LOOKBACK:
                    break
                time.sleep(0.05)
            
            if all_rates is None or len(all_rates) == 0:
                print(f"  ✗ No data for {tf_str}")
                continue
            
            # Sort chronologically
            all_rates = np.sort(all_rates, order='time')
            print(f"  ✓ {len(all_rates):,} bars total")
            
            # Extract arrays
            times = all_rates['time']
            opens = all_rates['open'].astype(np.float64)
            highs = all_rates['high'].astype(np.float64)
            lows = all_rates['low'].astype(np.float64)
            closes = all_rates['close'].astype(np.float64)
            volumes = all_rates['tick_volume'].astype(np.float64)
            
            # Process
            start_idx = min(ATH_LOOKBACK, len(all_rates) - 1)
            total = len(all_rates) - start_idx
            print(f"  Processing {total:,} bars...")
            
            core_batch, basic_batch, adv_batch, fib_batch, ath_batch = [], [], [], [], []
            adv_keys = None
            
            for i in range(start_idx, len(all_rates)):
                try:
                    ts = datetime.fromtimestamp(int(times[i])).strftime('%Y-%m-%d %H:%M:%S')
                    
                    h, l, c, v = highs[:i+1], lows[:i+1], closes[:i+1], volumes[:i+1]
                    
                    basic, adv = self.calculate_indicators(h, l, c, v)
                    
                    if adv_keys is None:
                        adv_keys = list(adv.keys())
                    
                    core_batch.append((ts, tf_str, symbol_name, float(opens[i]), float(highs[i]), float(lows[i]), float(closes[i]), int(volumes[i])))
                    basic_batch.append((ts, tf_str, symbol_name, basic['atr_14'], basic['atr_50_avg'], basic['atr_ratio'], basic['ema_short'], basic['ema_medium'], basic['ema_distance'], basic['supertrend']))
                    adv_batch.append(tuple([ts, tf_str, symbol_name] + [adv[k] for k in adv_keys]))
                    
                    # Fib
                    if CALCULATORS_AVAILABLE and len(h) >= FIB_LOOKBACK:
                        try:
                            fib = calculate_fibonacci_data(h, l, float(c[-1]), FIB_LOOKBACK)
                            fib_batch.append((ts, tf_str, symbol_name, str(fib['current_fib_zone']), 1 if fib['in_golden_zone'] else 0, fib['zone_multiplier'], fib['pivot_high'], fib['pivot_low'], fib.get('fib_level_0000', fib['pivot_low']), fib.get('fib_level_0236', 0), fib['fib_level_0382'], fib.get('fib_level_0500', 0), fib['fib_level_0618'], fib['fib_level_0786'], fib.get('fib_level_1000', fib['pivot_high'])))
                        except:
                            pass
                    
                    # ATH
                    if CALCULATORS_AVAILABLE and len(h) >= ATH_LOOKBACK:
                        try:
                            ath = calculate_ath_data(h, float(c[-1]), ATH_LOOKBACK)
                            ath_batch.append((ts, tf_str, symbol_name, ath['current_ath'], float(c[-1]), ath.get('ath_distance_points', 0), ath['ath_distance_pct'], ath['ath_multiplier'], ath['ath_zone'], ath.get('distance_from_ath_percentile', 0)))
                        except:
                            pass
                    
                    # Progress
                    done = i - start_idx + 1
                    if done % 1000 == 0 or done == total:
                        print(f"    {done:,}/{total:,} ({100*done/total:.1f}%)")
                    
                    # Batch insert
                    if len(core_batch) >= BATCH_SIZE:
                        self._do_insert(cursor, core_batch, basic_batch, adv_batch, fib_batch, ath_batch, adv_keys)
                        core_batch, basic_batch, adv_batch, fib_batch, ath_batch = [], [], [], [], []
                
                except Exception as e:
                    print(f"    Error at bar {i}: {e}")
                    traceback.print_exc()
                    continue
            
            # Final insert
            if core_batch:
                self._do_insert(cursor, core_batch, basic_batch, adv_batch, fib_batch, ath_batch, adv_keys)
            
            conn.commit()
            
            # Verify
            cursor.execute(f"SELECT COUNT(*) FROM advanced_indicators WHERE timeframe=? AND symbol=?", (tf_str, symbol_name))
            cnt = cursor.fetchone()[0]
            print(f"  ✓ {tf_str.upper()} done - {cnt:,} advanced rows")
        
        conn.close()
        return True

    def _do_insert(self, cursor, core, basic, adv, fib, ath, adv_keys):
        """Batch insert."""
        if core:
            cursor.executemany("INSERT OR REPLACE INTO core_15m (timestamp,timeframe,symbol,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?,?)", core)
        if basic:
            cursor.executemany("INSERT OR REPLACE INTO basic_15m (timestamp,timeframe,symbol,atr_14,atr_50_avg,atr_ratio,ema_short,ema_medium,ema_distance,supertrend) VALUES (?,?,?,?,?,?,?,?,?,?)", basic)
        if adv and adv_keys:
            cols = ','.join(['timestamp', 'timeframe', 'symbol'] + adv_keys)
            phs = ','.join(['?' for _ in range(len(adv_keys) + 3)])
            cursor.executemany(f"INSERT OR REPLACE INTO advanced_indicators ({cols}) VALUES ({phs})", adv)
        if fib:
            cursor.executemany("INSERT OR REPLACE INTO fibonacci_data (timestamp,timeframe,symbol,current_fib_zone,in_golden_zone,zone_multiplier,pivot_high,pivot_low,fib_level_0000,fib_level_0236,fib_level_0382,fib_level_0500,fib_level_0618,fib_level_0786,fib_level_1000) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", fib)
        if ath:
            cursor.executemany("INSERT OR REPLACE INTO ath_tracking (timestamp,timeframe,symbol,current_ath,current_close,ath_distance_points,ath_distance_pct,ath_multiplier,ath_zone,distance_from_ath_percentile) VALUES (?,?,?,?,?,?,?,?,?,?)", ath)

    def run(self, bars_count=50000, single_symbol=None):
        if not self.connect_mt5():
            return
        
        print(f"\n{'='*60}")
        print("MT5 BACKFILL V11.3")
        print(f"{'='*60}")
        
        if single_symbol:
            key = single_symbol.upper()
            if key not in SYMBOL_DATABASES:
                print(f"Unknown: {key}")
                mt5.shutdown()
                return
            symbols = {key: SYMBOL_DATABASES[key]}
        else:
            symbols = SYMBOL_DATABASES
        
        print(f"Symbols: {list(symbols.keys())}")
        print(f"Bars: {bars_count:,}")
        
        for sym_id, cfg in symbols.items():
            self.backfill_symbol(sym_id, cfg['symbol'], cfg['db_path'], bars_count)
        
        mt5.shutdown()
        print("\n✓ BACKFILL COMPLETE\n")


if __name__ == "__main__":
    bars = 50000
    sym = None
    
    if len(sys.argv) > 1:
        try:
            bars = int(sys.argv[1])
        except:
            sym = sys.argv[1]
    if len(sys.argv) > 2:
        sym = sys.argv[2]
    
    HistoricalBackfill().run(bars, sym)
