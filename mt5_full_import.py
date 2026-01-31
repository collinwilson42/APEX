"""
MT5 FULL IMPORT - All Symbols, All Timeframes
==============================================
Imports historical 1M and 15M bars for all configured symbols.

Features:
- Proper MT5 connection handling
- All 5 symbol databases
- 50,000 bars per timeframe (configurable)
- Full indicator calculation
- Progress tracking

Usage:
  py -3.11 mt5_full_import.py          # Interactive mode
  py -3.11 mt5_full_import.py --auto   # Auto-run without confirmation
"""

import MetaTrader5 as mt5
import sqlite3
import os
import sys
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_BARS = 50000  # Bars per timeframe

# Import from central config
import sys
sys.path.insert(0, '.')  # Ensure current directory is in path
from config import SYMBOL_DATABASES

# Convert to format expected by this script
SYMBOLS = {
    sym_id: {
        'mt5_symbol': config['symbol'],
        'name': config['name'],
        'db_path': config['db_path']
    }
    for sym_id, config in SYMBOL_DATABASES.items()
}

TIMEFRAMES = {
    '1m': mt5.TIMEFRAME_M1,
    '15m': mt5.TIMEFRAME_M15
}

# ============================================================================
# MT5 CONNECTION
# ============================================================================

def connect_mt5() -> bool:
    """Initialize MT5 connection properly"""
    print("\n[MT5] Initializing MetaTrader 5...")
    
    # Simple initialization - let MT5 find the terminal
    if not mt5.initialize():
        error = mt5.last_error()
        print(f"[MT5] ✗ Initialization failed: {error}")
        
        # Try with timeout
        print("[MT5] Retrying with extended timeout...")
        if not mt5.initialize(timeout=30000):
            print(f"[MT5] ✗ Second attempt failed: {mt5.last_error()}")
            return False
    
    # Get terminal info
    terminal = mt5.terminal_info()
    if terminal:
        print(f"[MT5] ✓ Connected to: {terminal.name}")
        print(f"[MT5]   Path: {terminal.path}")
        print(f"[MT5]   Build: {terminal.build}")
        print(f"[MT5]   Connected: {terminal.connected}")
    
    return True


def disconnect_mt5():
    """Shutdown MT5 connection"""
    mt5.shutdown()
    print("[MT5] Disconnected")


def verify_symbol(mt5_symbol: str) -> bool:
    """Verify symbol exists and is visible in Market Watch"""
    info = mt5.symbol_info(mt5_symbol)
    if info is None:
        print(f"  ✗ Symbol {mt5_symbol} not found")
        return False
    
    if not info.visible:
        if not mt5.symbol_select(mt5_symbol, True):
            print(f"  ✗ Could not select {mt5_symbol}")
            return False
        print(f"  ✓ Added {mt5_symbol} to Market Watch")
    
    return True


# ============================================================================
# INDICATOR CALCULATIONS
# ============================================================================

def calculate_atr(highs, lows, closes, period=14):
    n = len(closes)
    tr = np.zeros(n)
    atr = np.zeros(n)
    
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr[i] = max(hl, hc, lc)
    
    if n >= period:
        atr[period-1] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i-1] * (period-1) + tr[i]) / period
    
    return atr


def calculate_ema(data, period):
    n = len(data)
    ema = np.zeros(n)
    multiplier = 2 / (period + 1)
    
    if n >= period:
        ema[period-1] = np.mean(data[:period])
        for i in range(period, n):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]
    
    return ema


def calculate_sma(data, period):
    n = len(data)
    sma = np.zeros(n)
    for i in range(period - 1, n):
        sma[i] = np.mean(data[i - period + 1:i + 1])
    return sma


def calculate_supertrend(highs, lows, closes, period=10, multiplier=2.5):
    n = len(closes)
    atr = calculate_atr(highs, lows, closes, period)
    
    hl2 = (highs + lows) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = np.zeros(n)
    direction = np.ones(n)
    
    for i in range(period, n):
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
    
    return supertrend, direction


def calculate_rsi(closes, period=14):
    n = len(closes)
    rsi = np.zeros(n)
    
    if n < period + 1:
        return rsi
    
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        rsi[period] = 100
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - (100 / (1 + rs))
    
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
        
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_cci(highs, lows, closes, period=14):
    n = len(closes)
    cci = np.zeros(n)
    tp = (highs + lows + closes) / 3
    
    for i in range(period - 1, n):
        tp_slice = tp[i - period + 1:i + 1]
        sma = np.mean(tp_slice)
        mad = np.mean(np.abs(tp_slice - sma))
        if mad != 0:
            cci[i] = (tp[i] - sma) / (0.015 * mad)
    
    return cci


def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
    n = len(closes)
    k = np.zeros(n)
    d = np.zeros(n)
    
    for i in range(k_period - 1, n):
        low_min = np.min(lows[i - k_period + 1:i + 1])
        high_max = np.max(highs[i - k_period + 1:i + 1])
        if high_max != low_min:
            k[i] = ((closes[i] - low_min) / (high_max - low_min)) * 100
    
    for i in range(k_period + d_period - 2, n):
        d[i] = np.mean(k[i - d_period + 1:i + 1])
    
    return k, d


def calculate_williams_r(highs, lows, closes, period=14):
    n = len(closes)
    wr = np.zeros(n)
    
    for i in range(period - 1, n):
        high_max = np.max(highs[i - period + 1:i + 1])
        low_min = np.min(lows[i - period + 1:i + 1])
        if high_max != low_min:
            wr[i] = ((high_max - closes[i]) / (high_max - low_min)) * -100
    
    return wr


def calculate_adx(highs, lows, closes, period=14):
    n = len(closes)
    adx = np.zeros(n)
    
    if n < period * 2:
        return adx
    
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        plus_dm[i] = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm[i] = down_move if down_move > up_move and down_move > 0 else 0
    
    atr = calculate_ema(tr, period)
    plus_di = 100 * calculate_ema(plus_dm, period) / np.where(atr > 0, atr, 1)
    minus_di = 100 * calculate_ema(minus_dm, period) / np.where(atr > 0, atr, 1)
    
    dx = 100 * np.abs(plus_di - minus_di) / np.where((plus_di + minus_di) > 0, plus_di + minus_di, 1)
    adx = calculate_ema(dx, period)
    
    return adx


def calculate_momentum(closes, period=14):
    n = len(closes)
    mom = np.zeros(n)
    for i in range(period, n):
        mom[i] = closes[i] - closes[i - period]
    return mom


def calculate_bollinger_bands(closes, period=20, std_dev=2):
    n = len(closes)
    upper = np.zeros(n)
    middle = np.zeros(n)
    lower = np.zeros(n)
    width = np.zeros(n)
    pct = np.zeros(n)
    
    for i in range(period - 1, n):
        slice_data = closes[i - period + 1:i + 1]
        sma = np.mean(slice_data)
        std = np.std(slice_data)
        
        middle[i] = sma
        upper[i] = sma + (std_dev * std)
        lower[i] = sma - (std_dev * std)
        width[i] = upper[i] - lower[i]
        if width[i] != 0:
            pct[i] = (closes[i] - lower[i]) / width[i]
    
    return upper, middle, lower, width, pct


def calculate_macd(closes, fast=12, slow=26, signal=9):
    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_obv(closes, volumes):
    n = len(closes)
    obv = np.zeros(n, dtype=np.float64)
    obv[0] = float(volumes[0])
    for i in range(1, n):
        if closes[i] > closes[i-1]:
            obv[i] = obv[i-1] + float(volumes[i])
        elif closes[i] < closes[i-1]:
            obv[i] = obv[i-1] - float(volumes[i])
        else:
            obv[i] = obv[i-1]
    return obv


def calculate_roc(closes, period=14):
    n = len(closes)
    roc = np.zeros(n)
    for i in range(period, n):
        if closes[i - period] != 0:
            roc[i] = ((closes[i] - closes[i - period]) / closes[i - period]) * 100
    return roc


def calculate_cmf(highs, lows, closes, volumes, period=20):
    n = len(closes)
    cmf = np.zeros(n)
    hl_range = highs - lows
    hl_range[hl_range == 0] = 1
    mfv = ((closes - lows) - (highs - closes)) / hl_range * volumes
    
    for i in range(period - 1, n):
        vol_sum = np.sum(volumes[i - period + 1:i + 1])
        if vol_sum != 0:
            cmf[i] = np.sum(mfv[i - period + 1:i + 1]) / vol_sum
    return cmf


def calculate_parabolic_sar(highs, lows, closes, af_start=0.02, af_max=0.2):
    n = len(closes)
    sar = np.zeros(n)
    trend = np.ones(n)
    
    sar[0] = lows[0]
    ep = highs[0]
    af = af_start
    
    for i in range(1, n):
        if trend[i-1] == 1:
            sar[i] = sar[i-1] + af * (ep - sar[i-1])
            sar[i] = min(sar[i], lows[i-1], lows[i-2] if i > 1 else lows[i-1])
            
            if lows[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep
                ep = lows[i]
                af = af_start
            else:
                trend[i] = 1
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_start, af_max)
        else:
            sar[i] = sar[i-1] + af * (ep - sar[i-1])
            sar[i] = max(sar[i], highs[i-1], highs[i-2] if i > 1 else highs[i-1])
            
            if highs[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep
                ep = highs[i]
                af = af_start
            else:
                trend[i] = -1
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_start, af_max)
    
    return sar, trend


def calculate_ichimoku(highs, lows, tenkan=9, kijun=26, senkou_b=52):
    n = len(highs)
    tenkan_sen = np.zeros(n)
    kijun_sen = np.zeros(n)
    senkou_a = np.zeros(n)
    senkou_b_line = np.zeros(n)
    
    for i in range(tenkan - 1, n):
        tenkan_sen[i] = (np.max(highs[i-tenkan+1:i+1]) + np.min(lows[i-tenkan+1:i+1])) / 2
    
    for i in range(kijun - 1, n):
        kijun_sen[i] = (np.max(highs[i-kijun+1:i+1]) + np.min(lows[i-kijun+1:i+1])) / 2
    
    for i in range(kijun - 1, n):
        senkou_a[i] = (tenkan_sen[i] + kijun_sen[i]) / 2
    
    for i in range(senkou_b - 1, n):
        senkou_b_line[i] = (np.max(highs[i-senkou_b+1:i+1]) + np.min(lows[i-senkou_b+1:i+1])) / 2
    
    return tenkan_sen, kijun_sen, senkou_a, senkou_b_line


def calculate_fibonacci_levels(highs, lows, closes, lookback=100):
    n = len(closes)
    
    fib_levels = {
        '0000': np.zeros(n), '0236': np.zeros(n), '0382': np.zeros(n),
        '0500': np.zeros(n), '0618': np.zeros(n), '0786': np.zeros(n),
        '1000': np.zeros(n), '1272': np.zeros(n), '1618': np.zeros(n),
        '2000': np.zeros(n), '2618': np.zeros(n), '3618': np.zeros(n),
        '4236': np.zeros(n)
    }
    pivot_high = np.zeros(n)
    pivot_low = np.zeros(n)
    current_zone = [''] * n
    in_golden = np.zeros(n, dtype=int)
    zone_mult = np.zeros(n)
    
    ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.618, 3.618, 4.236]
    ratio_keys = ['0000', '0236', '0382', '0500', '0618', '0786', '1000', '1272', '1618', '2000', '2618', '3618', '4236']
    
    for i in range(lookback, n):
        window_high = np.max(highs[i-lookback:i])
        window_low = np.min(lows[i-lookback:i])
        
        pivot_high[i] = window_high
        pivot_low[i] = window_low
        
        diff = window_high - window_low
        
        for j, ratio in enumerate(ratios):
            fib_levels[ratio_keys[j]][i] = window_low + diff * ratio
        
        price = closes[i]
        if diff > 0:
            position = (price - window_low) / diff
            zone_mult[i] = position
            
            if 0.382 <= position <= 0.618:
                current_zone[i] = 'GOLDEN'
                in_golden[i] = 1
            elif position < 0.236:
                current_zone[i] = 'OVERSOLD'
            elif position > 0.786:
                current_zone[i] = 'OVERBOUGHT'
            else:
                current_zone[i] = 'NEUTRAL'
    
    return fib_levels, pivot_high, pivot_low, current_zone, in_golden, zone_mult


def calculate_ath_data(highs, closes):
    n = len(closes)
    ath = np.zeros(n)
    distance_pct = np.zeros(n)
    multiplier = np.zeros(n)
    zone = [''] * n
    
    running_ath = highs[0]
    
    for i in range(n):
        if highs[i] > running_ath:
            running_ath = highs[i]
        
        ath[i] = running_ath
        
        if running_ath > 0:
            distance_pct[i] = ((running_ath - closes[i]) / running_ath) * 100
            multiplier[i] = closes[i] / running_ath
        
        if distance_pct[i] <= 1:
            zone[i] = 'AT_ATH'
        elif distance_pct[i] <= 5:
            zone[i] = 'NEAR_ATH'
        elif distance_pct[i] <= 10:
            zone[i] = 'HEALTHY'
        elif distance_pct[i] <= 20:
            zone[i] = 'CORRECTION'
        else:
            zone[i] = 'FAR_FROM_ATH'
    
    return ath, distance_pct, multiplier, zone


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def clear_tables(db_path: str):
    """Clear all data from tables"""
    print(f"    Clearing existing data...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = ['core_1m', 'core_15m', 'basic_1m', 'basic_15m', 
              'advanced_indicators', 'fibonacci_data', 'ath_tracking', 'collection_stats']
    
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except:
            pass
    
    conn.commit()
    conn.close()


def import_timeframe(conn, symbol_id: str, mt5_symbol: str, tf_key: str, mt5_tf) -> int:
    """Import data for one timeframe"""
    print(f"    [{tf_key.upper()}] Fetching {MAX_BARS:,} bars...")
    
    # Fetch data
    rates = mt5.copy_rates_from_pos(mt5_symbol, mt5_tf, 0, MAX_BARS)
    
    if rates is None or len(rates) == 0:
        print(f"    [{tf_key.upper()}] ✗ No data returned")
        return 0
    
    n = len(rates)
    print(f"    [{tf_key.upper()}] Got {n:,} bars, calculating indicators...")
    
    # Convert to numpy
    timestamps = [datetime.fromtimestamp(r['time']).isoformat() for r in rates]
    opens = np.array([r['open'] for r in rates], dtype=np.float64)
    highs = np.array([r['high'] for r in rates], dtype=np.float64)
    lows = np.array([r['low'] for r in rates], dtype=np.float64)
    closes = np.array([r['close'] for r in rates], dtype=np.float64)
    volumes = np.array([r['tick_volume'] for r in rates], dtype=np.float64)
    
    # Calculate indicators
    atr_14 = calculate_atr(highs, lows, closes, 14)
    atr_50 = calculate_ema(atr_14, 50)
    ema_4 = calculate_ema(closes, 4)
    ema_22 = calculate_ema(closes, 22)
    supertrend, st_dir = calculate_supertrend(highs, lows, closes, 10, 2.5)
    
    # Advanced indicators
    rsi = {p: calculate_rsi(closes, p) for p in range(1, 15)}
    cci = {p: calculate_cci(highs, lows, closes, p) for p in range(1, 15)}
    stoch_k, stoch_d = {}, {}
    for p in range(1, 15):
        stoch_k[p], stoch_d[p] = calculate_stochastic(highs, lows, closes, p, 3)
    williams = {p: calculate_williams_r(highs, lows, closes, p) for p in range(1, 15)}
    adx = {p: calculate_adx(highs, lows, closes, p) for p in range(1, 15)}
    momentum = {p: calculate_momentum(closes, p) for p in range(1, 15)}
    roc = {p: calculate_roc(closes, p) for p in range(1, 15)}
    atr_multi = {p: calculate_atr(highs, lows, closes, p) for p in range(1, 14)}
    
    bb_upper, bb_middle, bb_lower, bb_width, bb_pct = calculate_bollinger_bands(closes, 20, 2)
    macd_line, macd_signal, macd_hist = calculate_macd(closes, 12, 26, 9)
    obv = calculate_obv(closes, volumes)
    vol_ma = calculate_sma(volumes, 20)
    cmf = calculate_cmf(highs, lows, closes, volumes, 20)
    sar, sar_trend = calculate_parabolic_sar(highs, lows, closes)
    ich_tenkan, ich_kijun, ich_senkou_a, ich_senkou_b = calculate_ichimoku(highs, lows)
    
    fib_levels, pivot_high, pivot_low, fib_zone, in_golden, zone_mult = calculate_fibonacci_levels(highs, lows, closes, 100)
    ath, ath_dist, ath_mult, ath_zone = calculate_ath_data(highs, closes)
    
    cursor = conn.cursor()
    
    # Determine core table name
    core_table = f'core_{tf_key}'
    basic_table = f'basic_{tf_key}'
    
    # Try core_1m/core_15m first, fall back to core_15m (legacy)
    try:
        cursor.execute(f"SELECT 1 FROM {core_table} LIMIT 1")
    except:
        core_table = 'core_15m'
        basic_table = 'basic_15m'
    
    # Insert CORE data
    print(f"    [{tf_key.upper()}] Inserting into {core_table}...")
    core_data = [(timestamps[i], tf_key, mt5_symbol, float(opens[i]), float(highs[i]), 
                  float(lows[i]), float(closes[i]), int(volumes[i])) for i in range(n)]
    cursor.executemany(f'INSERT OR REPLACE INTO {core_table} (timestamp, timeframe, symbol, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', core_data)
    
    # Insert BASIC data
    print(f"    [{tf_key.upper()}] Inserting into {basic_table}...")
    basic_data = []
    for i in range(n):
        atr_ratio = atr_14[i] / atr_50[i] if atr_50[i] != 0 else 0
        ema_dist = (closes[i] - ema_22[i]) / atr_14[i] if atr_14[i] != 0 else 0
        st_signal = 'BULL' if st_dir[i] == 1 else 'BEAR'
        basic_data.append((timestamps[i], tf_key, mt5_symbol, float(atr_14[i]), float(atr_50[i]), 
                          float(atr_ratio), float(ema_4[i]), float(ema_22[i]), float(ema_dist), st_signal))
    cursor.executemany(f'INSERT OR REPLACE INTO {basic_table} (timestamp, timeframe, symbol, atr_14, atr_50_avg, atr_ratio, ema_short, ema_medium, ema_distance, supertrend) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', basic_data)
    
    # Insert ADVANCED data
    print(f"    [{tf_key.upper()}] Inserting into advanced_indicators...")
    advanced_data = []
    for i in range(n):
        vol_ratio = float(volumes[i]) / vol_ma[i] if vol_ma[i] != 0 else 0
        sar_tr = 'UP' if sar_trend[i] == 1 else 'DOWN'
        
        row = [
            timestamps[i], tf_key, mt5_symbol,
            float(rsi[1][i]), float(rsi[2][i]), float(rsi[3][i]), float(rsi[4][i]), float(rsi[5][i]),
            float(rsi[6][i]), float(rsi[7][i]), float(rsi[8][i]), float(rsi[9][i]), float(rsi[10][i]),
            float(rsi[11][i]), float(rsi[12][i]), float(rsi[13][i]), float(rsi[14][i]),
            float(cci[1][i]), float(cci[2][i]), float(cci[3][i]), float(cci[4][i]), float(cci[5][i]),
            float(cci[6][i]), float(cci[7][i]), float(cci[8][i]), float(cci[9][i]), float(cci[10][i]),
            float(cci[11][i]), float(cci[12][i]), float(cci[13][i]), float(cci[14][i]),
            float(stoch_k[1][i]), float(stoch_d[1][i]), float(stoch_k[2][i]), float(stoch_d[2][i]),
            float(stoch_k[3][i]), float(stoch_d[3][i]), float(stoch_k[4][i]), float(stoch_d[4][i]),
            float(stoch_k[5][i]), float(stoch_d[5][i]), float(stoch_k[6][i]), float(stoch_d[6][i]),
            float(stoch_k[7][i]), float(stoch_d[7][i]), float(stoch_k[8][i]), float(stoch_d[8][i]),
            float(stoch_k[9][i]), float(stoch_d[9][i]), float(stoch_k[10][i]), float(stoch_d[10][i]),
            float(stoch_k[11][i]), float(stoch_d[11][i]), float(stoch_k[12][i]), float(stoch_d[12][i]),
            float(stoch_k[13][i]), float(stoch_d[13][i]), float(stoch_k[14][i]), float(stoch_d[14][i]),
            float(williams[1][i]), float(williams[2][i]), float(williams[3][i]), float(williams[4][i]),
            float(williams[5][i]), float(williams[6][i]), float(williams[7][i]), float(williams[8][i]),
            float(williams[9][i]), float(williams[10][i]), float(williams[11][i]), float(williams[12][i]),
            float(williams[13][i]), float(williams[14][i]),
            float(adx[1][i]), float(adx[2][i]), float(adx[3][i]), float(adx[4][i]), float(adx[5][i]),
            float(adx[6][i]), float(adx[7][i]), float(adx[8][i]), float(adx[9][i]), float(adx[10][i]),
            float(adx[11][i]), float(adx[12][i]), float(adx[13][i]), float(adx[14][i]),
            float(momentum[1][i]), float(momentum[2][i]), float(momentum[3][i]), float(momentum[4][i]),
            float(momentum[5][i]), float(momentum[6][i]), float(momentum[7][i]), float(momentum[8][i]),
            float(momentum[9][i]), float(momentum[10][i]), float(momentum[11][i]), float(momentum[12][i]),
            float(momentum[13][i]), float(momentum[14][i]),
            float(bb_upper[i]), float(bb_middle[i]), float(bb_lower[i]), float(bb_width[i]), float(bb_pct[i]),
            float(macd_line[i]), float(macd_signal[i]), float(macd_hist[i]),
            float(obv[i]),
            float(vol_ma[i]), float(vol_ratio),
            float(cmf[i]),
            float(sar[i]), sar_tr,
            float(ich_tenkan[i]), float(ich_kijun[i]), float(ich_senkou_a[i]), float(ich_senkou_b[i]),
            float(roc[1][i]), float(roc[2][i]), float(roc[3][i]), float(roc[4][i]), float(roc[5][i]),
            float(roc[6][i]), float(roc[7][i]), float(roc[8][i]), float(roc[9][i]), float(roc[10][i]),
            float(roc[11][i]), float(roc[12][i]), float(roc[13][i]), float(roc[14][i]),
            float(pivot_high[i]), float(fib_levels['0618'][i]), float(fib_levels['0786'][i]), float(fib_levels['1000'][i]),
            float(fib_levels['0382'][i]), float(fib_levels['0236'][i]), float(fib_levels['0000'][i]),
            float(atr_multi[1][i]), float(atr_multi[2][i]), float(atr_multi[3][i]), float(atr_multi[4][i]),
            float(atr_multi[5][i]), float(atr_multi[6][i]), float(atr_multi[7][i]), float(atr_multi[8][i]),
            float(atr_multi[9][i]), float(atr_multi[10][i]), float(atr_multi[11][i]), float(atr_multi[12][i]),
            float(atr_multi[13][i]),
        ]
        advanced_data.append(tuple(row))
    
    adv_cols = '''timestamp, timeframe, symbol,
        rsi_1, rsi_2, rsi_3, rsi_4, rsi_5, rsi_6, rsi_7, rsi_8, rsi_9, rsi_10, rsi_11, rsi_12, rsi_13, rsi_14,
        cci_1, cci_2, cci_3, cci_4, cci_5, cci_6, cci_7, cci_8, cci_9, cci_10, cci_11, cci_12, cci_13, cci_14,
        stoch_k_1, stoch_d_1, stoch_k_2, stoch_d_2, stoch_k_3, stoch_d_3, stoch_k_4, stoch_d_4,
        stoch_k_5, stoch_d_5, stoch_k_6, stoch_d_6, stoch_k_7, stoch_d_7, stoch_k_8, stoch_d_8,
        stoch_k_9, stoch_d_9, stoch_k_10, stoch_d_10, stoch_k_11, stoch_d_11, stoch_k_12, stoch_d_12,
        stoch_k_13, stoch_d_13, stoch_k_14, stoch_d_14,
        williams_r_1, williams_r_2, williams_r_3, williams_r_4, williams_r_5, williams_r_6, williams_r_7,
        williams_r_8, williams_r_9, williams_r_10, williams_r_11, williams_r_12, williams_r_13, williams_r_14,
        adx_1, adx_2, adx_3, adx_4, adx_5, adx_6, adx_7, adx_8, adx_9, adx_10, adx_11, adx_12, adx_13, adx_14,
        momentum_1, momentum_2, momentum_3, momentum_4, momentum_5, momentum_6, momentum_7,
        momentum_8, momentum_9, momentum_10, momentum_11, momentum_12, momentum_13, momentum_14,
        bb_upper_20, bb_middle_20, bb_lower_20, bb_width_20, bb_pct_20,
        macd_line_12_26, macd_signal_12_26, macd_histogram_12_26,
        obv, volume_ma_20, volume_ratio, cmf_20,
        sar, sar_trend,
        ichimoku_tenkan, ichimoku_kijun, ichimoku_senkou_a, ichimoku_senkou_b,
        roc_1, roc_2, roc_3, roc_4, roc_5, roc_6, roc_7, roc_8, roc_9, roc_10, roc_11, roc_12, roc_13, roc_14,
        fib_pivot, fib_r1, fib_r2, fib_r3, fib_s1, fib_s2, fib_s3,
        atr_1, atr_2, atr_3, atr_4, atr_5, atr_6, atr_7, atr_8, atr_9, atr_10, atr_11, atr_12, atr_13'''
    
    placeholders = ','.join(['?' for _ in range(150)])
    sql = f'INSERT OR REPLACE INTO advanced_indicators ({adv_cols}) VALUES ({placeholders})'
    cursor.executemany(sql, advanced_data)
    
    # Insert FIBONACCI data
    print(f"    [{tf_key.upper()}] Inserting into fibonacci_data...")
    fib_data = []
    for i in range(n):
        fib_data.append((timestamps[i], tf_key, mt5_symbol,
            float(pivot_high[i]), float(pivot_low[i]),
            float(fib_levels['0000'][i]), float(fib_levels['0236'][i]), float(fib_levels['0382'][i]),
            float(fib_levels['0500'][i]), float(fib_levels['0618'][i]), float(fib_levels['0786'][i]),
            float(fib_levels['1000'][i]), float(fib_levels['1272'][i]), float(fib_levels['1618'][i]),
            float(fib_levels['2000'][i]), float(fib_levels['2618'][i]), float(fib_levels['3618'][i]),
            float(fib_levels['4236'][i]), fib_zone[i], int(in_golden[i]), float(zone_mult[i])))
    cursor.executemany('''INSERT OR REPLACE INTO fibonacci_data 
        (timestamp, timeframe, symbol, pivot_high, pivot_low,
         fib_level_0000, fib_level_0236, fib_level_0382, fib_level_0500, fib_level_0618, fib_level_0786,
         fib_level_1000, fib_level_1272, fib_level_1618, fib_level_2000, fib_level_2618, fib_level_3618,
         fib_level_4236, current_fib_zone, in_golden_zone, zone_multiplier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', fib_data)
    
    # Insert ATH data
    print(f"    [{tf_key.upper()}] Inserting into ath_tracking...")
    ath_data = [(timestamps[i], tf_key, mt5_symbol, float(ath[i]), float(closes[i]), 
                 float(ath_dist[i]), float(ath_mult[i]), ath_zone[i]) for i in range(n)]
    cursor.executemany('''INSERT OR REPLACE INTO ath_tracking 
        (timestamp, timeframe, symbol, current_ath, current_close, ath_distance_pct, ath_multiplier, ath_zone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', ath_data)
    
    conn.commit()
    print(f"    [{tf_key.upper()}] ✓ Complete - {n:,} rows")
    return n


def import_symbol(symbol_id: str, config: dict, clear_first: bool = True) -> Tuple[int, int]:
    """Import all data for one symbol"""
    mt5_symbol = config['mt5_symbol']
    db_path = config['db_path']
    name = config['name']
    
    print(f"\n{'='*60}")
    print(f"  {symbol_id}: {name}")
    print(f"  Database: {db_path}")
    print(f"{'='*60}")
    
    # Verify database exists
    if not os.path.exists(db_path):
        print(f"  ✗ Database not found: {db_path}")
        return 0, 0
    
    # Verify symbol
    if not verify_symbol(mt5_symbol):
        return 0, 0
    
    time.sleep(0.2)  # Brief pause for Market Watch
    
    # Clear existing data
    if clear_first:
        clear_tables(db_path)
    
    # Import data
    conn = sqlite3.connect(db_path)
    rows_1m = 0
    rows_15m = 0
    
    for tf_key, tf_mt5 in TIMEFRAMES.items():
        rows = import_timeframe(conn, symbol_id, mt5_symbol, tf_key, tf_mt5)
        if tf_key == '1m':
            rows_1m = rows
        else:
            rows_15m = rows
    
    # Update stats
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO collection_stats (timestamp, symbol, timeframe, bars_collected, indicators_calculated, status)
            VALUES (?, ?, 'all', ?, ?, 'completed')''', 
            (datetime.now().isoformat(), mt5_symbol, rows_1m + rows_15m, (rows_1m + rows_15m) * 176))
    except:
        pass
    
    conn.commit()
    conn.close()
    
    size = os.path.getsize(db_path) / 1024 / 1024
    print(f"\n  ✓ {symbol_id} Complete: {rows_1m + rows_15m:,} total rows, {size:.1f} MB")
    
    return rows_1m, rows_15m


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print("MT5 FULL IMPORT - All Symbols, All Timeframes")
    print("=" * 70)
    print(f"\nSymbols to import: {', '.join(SYMBOLS.keys())}")
    print(f"Timeframes: 1M, 15M")
    print(f"Bars per timeframe: {MAX_BARS:,}")
    
    # Check databases exist
    missing = []
    for sym_id, config in SYMBOLS.items():
        if not os.path.exists(config['db_path']):
            missing.append(f"  {sym_id}: {config['db_path']}")
    
    if missing:
        print(f"\n⚠️  Missing databases:")
        for m in missing:
            print(m)
        print("\nRun init_databases.py first to create them.")
    
    # Auto mode check
    auto_mode = '--auto' in sys.argv
    
    if not auto_mode:
        print("\nThis will DELETE existing data and import fresh from MT5.")
        confirm = input("Type 'IMPORT' to continue: ").strip().upper()
        if confirm != 'IMPORT':
            print("Aborted.")
            return
    
    # Connect to MT5
    if not connect_mt5():
        print("\n✗ Could not connect to MT5. Make sure terminal is running.")
        return
    
    start_time = datetime.now()
    results = {}
    
    # Import each symbol
    for sym_id, config in SYMBOLS.items():
        if os.path.exists(config['db_path']):
            rows_1m, rows_15m = import_symbol(sym_id, config)
            results[sym_id] = {'1m': rows_1m, '15m': rows_15m}
        else:
            results[sym_id] = {'1m': 0, '15m': 0, 'error': 'Database not found'}
    
    # Disconnect
    disconnect_mt5()
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"\n{'Symbol':<12} {'1M Bars':>12} {'15M Bars':>12} {'Status':<15}")
    print("-" * 55)
    
    total_rows = 0
    for sym_id, data in results.items():
        if 'error' in data:
            print(f"{sym_id:<12} {'-':>12} {'-':>12} {data['error']:<15}")
        else:
            print(f"{sym_id:<12} {data['1m']:>12,} {data['15m']:>12,} {'✓ Complete':<15}")
            total_rows += data['1m'] + data['15m']
    
    print("-" * 55)
    print(f"{'TOTAL':<12} {total_rows:>24,}")
    print(f"\nTime elapsed: {elapsed:.1f} seconds")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
