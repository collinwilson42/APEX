# fillall.py (Version 4.0 - Uses Collector Logic)
"""
MT5 DATABASE BACKFILL - Uses same logic as mt5_collector_v11_3.py
================================================================
Ensures perfect matching between historical fill and live feed.
"""

import MetaTrader5 as mt5
import sqlite3
import os
from datetime import datetime, timezone
import numpy as np
import sys
import time
import traceback

sys.path.insert(0, '.')
from config import SYMBOL_DATABASES

try:
    from fibonacci_calculator import calculate_fibonacci_data
    from ath_calculator import calculate_ath_data
    CALCULATORS_AVAILABLE = True
    print("✓ Fibonacci & ATH calculators loaded")
except ImportError as e:
    print(f"⚠️  Calculators not found: {e}")
    CALCULATORS_AVAILABLE = False

SYMBOLS_CONFIG = [
    {'symbol': config['symbol'], 'db': config['db_path'], 'name': config['name'], 'id': config['id']}
    for config in SYMBOL_DATABASES.values()
]

TIMEFRAMES = {
    '1m': mt5.TIMEFRAME_M1,
    '15m': mt5.TIMEFRAME_M15
}

MAX_BARS = 50000
ATH_LOOKBACK = 500
FIB_LOOKBACK = 100


# ============================================================================
# COPIED EXACTLY FROM mt5_collector_v11_3.py
# ============================================================================

def calculate_indicators(history_rates):
    """Calculate all indicators - EXACT COPY from collector."""
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


# ============================================================================
# BACKFILL FUNCTIONS
# ============================================================================

def clear_tables(db_path):
    """Clear all tables before backfill."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for table in ['core_15m', 'basic_15m', 'advanced_indicators', 'fibonacci_data', 'ath_tracking']:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except:
            pass
    conn.commit()
    conn.close()


def backfill_timeframe(symbol, db_path, timeframe_str, mt5_timeframe):
    """Backfill one timeframe using collector logic."""
    
    print(f"    [{timeframe_str}] Fetching {MAX_BARS:,} bars...")
    
    # Fetch all historical bars
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, MAX_BARS)
    if rates is None or len(rates) == 0:
        print(f"    [{timeframe_str}] No data!")
        return 0
    
    total = len(rates)
    print(f"    [{timeframe_str}] Got {total:,} bars, processing...")
    print(f"    [{timeframe_str}] Starting from index {ATH_LOOKBACK}, will process {total - ATH_LOOKBACK} bars")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Process each bar with lookback window (like collector does)
    inserted = 0
    errors = 0
    
    # First bar - debug output
    print(f"    [{timeframe_str}] Processing first bar for debug...")
    i = ATH_LOOKBACK
    history = rates[max(0, i - ATH_LOOKBACK):i + 1]
    latest = history[-1]
    timestamp = datetime.fromtimestamp(latest['time']).strftime('%Y-%m-%d %H:%M:%S')
    print(f"    [{timeframe_str}] First timestamp: {timestamp}")
    print(f"    [{timeframe_str}] Latest bar: O={latest['open']}, H={latest['high']}, L={latest['low']}, C={latest['close']}")
    
    basic, adv = calculate_indicators(history)
    print(f"    [{timeframe_str}] Basic keys ({len(basic)}): {list(basic.keys())}")
    print(f"    [{timeframe_str}] Advanced keys ({len(adv)}): {len(adv)} columns")
    
    # Check DB schema
    cursor.execute("PRAGMA table_info(core_15m)")
    core_cols = cursor.fetchall()
    print(f"    [{timeframe_str}] core_15m schema: {len(core_cols)} columns")
    
    cursor.execute("PRAGMA table_info(advanced_indicators)")
    adv_cols_schema = cursor.fetchall()
    print(f"    [{timeframe_str}] advanced_indicators schema: {len(adv_cols_schema)} columns")
    print(f"    [{timeframe_str}] advanced_indicators needs: {len(adv) + 3} columns (3 base + {len(adv)} indicators)")
    
    # Now process all bars
    for i in range(ATH_LOOKBACK, total):
        # Get lookback window ending at this bar
        history = rates[max(0, i - ATH_LOOKBACK):i + 1]
        latest = history[-1]
        
        timestamp = datetime.fromtimestamp(latest['time']).strftime('%Y-%m-%d %H:%M:%S')
        close_price = float(latest['close'])
        
        highs = np.array([float(r['high']) for r in history])
        lows = np.array([float(r['low']) for r in history])
        
        # Calculate indicators using EXACT collector function
        basic, adv = calculate_indicators(history)
        
        # Core - EXACT same insert as collector
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO core_15m 
                (timestamp, timeframe, symbol, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, timeframe_str, symbol, 
                  float(latest['open']), float(latest['high']), 
                  float(latest['low']), float(latest['close']), 
                  int(latest['tick_volume'])))
        except Exception as e:
            if errors < 3:
                print(f"    CORE INSERT ERROR: {e}")
            errors += 1
            continue
        
        # Basic - EXACT same insert as collector
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO basic_15m 
                (timestamp, timeframe, symbol, atr_14, atr_50_avg, atr_ratio, 
                 ema_short, ema_medium, ema_distance, supertrend)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, timeframe_str, symbol,
                  basic['atr_14'], basic['atr_50_avg'], basic['atr_ratio'],
                  basic['ema_short'], basic['ema_medium'], basic['ema_distance'],
                  basic['supertrend']))
        except Exception as e:
            if errors < 3:
                print(f"    BASIC INSERT ERROR: {e}")
            errors += 1
            continue
        
        # Advanced - EXACT same insert as collector
        try:
            adv_cols = list(adv.keys())
            adv_vals = [adv[k] for k in adv_cols]
            cols_str = ','.join(['timestamp', 'timeframe', 'symbol'] + adv_cols)
            placeholders = ','.join(['?' for _ in range(len(adv_cols) + 3)])
            cursor.execute(f"""
                INSERT OR REPLACE INTO advanced_indicators ({cols_str})
                VALUES ({placeholders})
            """, [timestamp, timeframe_str, symbol] + adv_vals)
        except Exception as e:
            if errors < 3:
                print(f"    ADVANCED INSERT ERROR: {e}")
            errors += 1
            continue
        
        # Fib - EXACT same insert as collector
        if CALCULATORS_AVAILABLE and len(history) >= FIB_LOOKBACK:
            try:
                fib_data = calculate_fibonacci_data(highs, lows, close_price, FIB_LOOKBACK)
                cursor.execute("""
                    INSERT OR REPLACE INTO fibonacci_data 
                    (timestamp, timeframe, symbol, pivot_high, pivot_low,
                     fib_level_0000, fib_level_0236, fib_level_0382, fib_level_0500,
                     fib_level_0618, fib_level_0786, fib_level_1000, fib_level_1272,
                     fib_level_1618, fib_level_2000, fib_level_2618, fib_level_3618, fib_level_4236,
                     current_fib_zone, in_golden_zone, zone_multiplier)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, timeframe_str, symbol,
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
            except Exception as e:
                if errors < 3:
                    print(f"    FIB INSERT ERROR: {e}")
                pass
        
        # ATH - EXACT same insert as collector
        if CALCULATORS_AVAILABLE and len(history) >= ATH_LOOKBACK:
            try:
                ath_data = calculate_ath_data(highs, close_price, ATH_LOOKBACK)
                cursor.execute("""
                    INSERT OR REPLACE INTO ath_tracking 
                    (timestamp, timeframe, symbol, current_ath, current_close,
                     ath_distance_pct, ath_multiplier, ath_zone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, timeframe_str, symbol,
                      ath_data['current_ath'], close_price,
                      ath_data['ath_distance_pct'],
                      ath_data['ath_multiplier'], ath_data['ath_zone']))
            except:
                pass
        
        inserted += 1
        
        # Progress every 1000 bars with live DB check
        if inserted % 1000 == 0:
            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM core_15m WHERE timeframe=?", (timeframe_str,))
            db_count = cursor.fetchone()[0]
            print(f"    [{timeframe_str}] ... {inserted:,} / {total - ATH_LOOKBACK:,} processed | DB has {db_count:,} rows | {errors} errors")
    
    conn.commit()
    
    # Verify data was inserted
    cursor.execute("SELECT COUNT(*) FROM core_15m WHERE timeframe=?", (timeframe_str,))
    actual_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"    [{timeframe_str}] ✓ {inserted:,} bars processed, {actual_count:,} in DB, {errors} errors")
    return inserted


def backfill_symbol(config):
    """Backfill all timeframes for one symbol."""
    symbol = config['symbol']
    db_path = config['db']
    name = config['name']
    
    print(f"\n{'='*60}")
    print(f"BACKFILL: {name} ({symbol})")
    print(f"Database: {db_path}")
    print('='*60)
    
    if not os.path.exists(db_path):
        print(f"  ERROR: Database not found. Run init_databases.py first.")
        return False
    
    if not mt5.symbol_select(symbol, True):
        print(f"  ERROR: Could not select symbol in MT5.")
        return False
    
    print(f"  Clearing tables...")
    clear_tables(db_path)
    
    total = 0
    for tf_str, tf_mt5 in TIMEFRAMES.items():
        bars = backfill_timeframe(symbol, db_path, tf_str, tf_mt5)
        total += bars
    
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"  DONE: {total:,} total bars, {size_mb:.1f} MB")
    return True


def main():
    print("="*60)
    print("MT5 DATABASE BACKFILL (V4.0 - Collector Logic)")
    print("="*60)
    print("\nSymbols:")
    for c in SYMBOLS_CONFIG:
        print(f"  - {c['name']} ({c['symbol']})")
    
    confirm = input("\nType 'FILL' to begin: ").strip().upper()
    if confirm != 'FILL':
        print("Aborted.")
        return
    
    print("\nConnecting to MT5...")
    if not mt5.initialize():
        print("MT5 failed!")
        return
    print(f"✓ MT5: {mt5.terminal_info().name}")
    
    start = datetime.now()
    
    for config in SYMBOLS_CONFIG:
        try:
            backfill_symbol(config)
        except Exception as e:
            print(f"\nERROR on {config['name']}: {e}")
            traceback.print_exc()
    
    mt5.shutdown()
    
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'='*60}")
    print(f"COMPLETE - {elapsed/60:.1f} minutes")
    print('='*60)


if __name__ == '__main__':
    main()
