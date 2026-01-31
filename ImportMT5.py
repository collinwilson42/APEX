import MetaTrader5 as mt5
import sqlite3
import os
from datetime import datetime
import numpy as np
import sys
import logging
import traceback
import time

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('MT5_BACKFILL')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Corrected symbol names based on your project structure
SYMBOLS_TO_FILL = [
    {'symbol': 'XAUG26.sim', 'db': 'XAUG26_intelligence.db', 'name': 'Gold Futures'},
    {'symbol': 'BTCF26.sim', 'db': 'BTCZ25_intelligence.db', 'name': 'BTC Futures'},
    {'symbol': 'US500H26.sim', 'db': 'US500Z25_intelligence.db', 'name': 'S&P 500 Futures'},
    {'symbol': 'US100H26.sim', 'db': 'US100Z25_intelligence.db', 'name': 'NASDAQ 100 Futures'},
    {'symbol': 'US30H26.sim', 'db': 'US30Z25_intelligence.db', 'name': 'Dow Jones Futures'},
]

TIMEFRAMES = {
    '1m': mt5.TIMEFRAME_M1,
    '15m': mt5.TIMEFRAME_M15
}
MAX_BARS = 50000

# ============================================================================
# MT5 DEBUGGING FUNCTIONS
# ============================================================================

def debug_mt5_init():
    log.info("Attempting MT5 initialization...")
    # Add a path argument if your terminal is not in the default location
    # result = mt5.initialize(path="C:\\Program Files\\MetaTrader 5\\terminal64.exe")
    result = mt5.initialize()
    if not result:
        log.error("MT5 INITIALIZATION FAILED")
        log.error(f"Last Error: {mt5.last_error()}")
        log.info("TROUBLESHOOTING: Is MetaTrader 5 running and logged in? Is 'Allow algorithmic trading' enabled in Tools > Options?")
        return False
    log.info("MT5 INITIALIZATION SUCCESSFUL")
    return True

def debug_mt5_status():
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    if not terminal or not account:
        log.error("Could not get terminal/account info.")
        return
    log.info(f"Terminal: {terminal.name} (Build {terminal.build}) on {terminal.path}")
    log.info(f"Account: {account.name} on {account.server}")

def debug_symbol_info(symbol):
    log.info(f"--- Checking Symbol: {symbol} ---")
    info = mt5.symbol_info(symbol)
    if info is None:
        log.warning(f"Symbol '{symbol}' not found by broker.")
        log.warning(f"Last error: {mt5.last_error()}")
        all_symbols = mt5.symbols_get()
        if all_symbols:
            base = symbol.split('.')[0][:4] if '.' in symbol else symbol[:4]
            matches = [s.name for s in all_symbols if base.lower() in s.name.lower()]
            if matches:
                log.info(f"Did you mean one of these? {matches[:15]}")
        return False

    log.info(f"  Description: {info.description}")
    log.info(f"  Visible:     {info.visible}")

    if not info.visible:
        log.warning("Symbol not visible, attempting to select...")
        if not mt5.symbol_select(symbol, True):
            log.error(f"Failed to select symbol: {mt5.last_error()}")
            return False
        log.info("Symbol selected successfully.")
    return True

def debug_test_data_fetch(symbol, timeframe, tf_name):
    log.info(f"--- Test Fetch: 10 bars of {tf_name} for {symbol} ---")
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 10)
    if rates is None or len(rates) == 0:
        log.error("Test fetch FAILED. `copy_rates_from_pos` returned no data.")
        log.error(f"Last error: {mt5.last_error()}")
        return False

    log.info(f"SUCCESS: Fetched {len(rates)} bars for test.")
    return True

# ============================================================================
# INDICATOR CALCULATIONS (Consolidated from goldfill.py)
# ============================================================================
# This section now contains the full, correct calculation functions.

from goldfill import (
    calculate_atr, calculate_ema, calculate_sma, calculate_supertrend,
    calculate_rsi, calculate_cci, calculate_stochastic, calculate_williams_r,
    calculate_adx, calculate_momentum, calculate_bollinger_bands, calculate_macd,
    calculate_obv, calculate_roc, calculate_cmf, calculate_parabolic_sar,
    calculate_ichimoku, calculate_fibonacci_levels, calculate_ath_data
)

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def check_database_exists(db_path):
    if not os.path.exists(db_path):
        log.error(f"Database '{db_path}' not found. Run 'py -3.11 init_databases.py' first.")
        return False
    return True

def clear_database_tables(db_path):
    log.info(f"Clearing all tables in {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        tables = ['core_15m', 'basic_15m', 'advanced_indicators', 'fibonacci_data', 'ath_tracking', 'collection_stats']
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                log.warning(f"  Table '{table}' not found, skipping.")
        conn.commit()
        conn.close()
        log.info("Tables cleared successfully.")
    except Exception as e:
        log.error(f"Failed to clear tables: {e}")

def backfill_timeframe(conn, symbol, tf_key, mt5_tf, max_bars):
    log.info(f"[{tf_key.upper()}] Fetching up to {max_bars:,} bars for {symbol}...")

    rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, max_bars)

    if rates is None or len(rates) == 0:
        log.error(f"[{tf_key.upper()}] FAILED TO FETCH DATA. `copy_rates_from_pos` returned no data.")
        log.error(f"Last MT5 error: {mt5.last_error()}")
        return 0

    n = len(rates)
    log.info(f"[{tf_key.upper()}] Fetched {n:,} bars. Processing all indicators...")

    timestamps = [datetime.fromtimestamp(r['time']).isoformat() for r in rates]
    opens = np.array([r['open'] for r in rates], dtype=np.float64)
    highs = np.array([r['high'] for r in rates], dtype=np.float64)
    lows = np.array([r['low'] for r in rates], dtype=np.float64)
    closes = np.array([r['close'] for r in rates], dtype=np.float64)
    volumes = np.array([r['tick_volume'] for r in rates], dtype=np.float64)

    # --- ALL INDICATOR CALCULATIONS ---
    # Basic
    atr_14 = calculate_atr(highs, lows, closes, 14)
    atr_50 = calculate_ema(atr_14, 50)
    ema_4 = calculate_ema(closes, 4)
    ema_22 = calculate_ema(closes, 22)
    _, st_dir = calculate_supertrend(highs, lows, closes, 10, 2.5)

    # Advanced
    rsi = {p: calculate_rsi(closes, p) for p in range(1, 15)}
    cci = {p: calculate_cci(highs, lows, closes, p) for p in range(1, 15)}
    stoch_k, stoch_d = {}, {}
    for p in range(1, 15): stoch_k[p], stoch_d[p] = calculate_stochastic(highs, lows, closes, p, 3)
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

    # --- DATA PREPARATION FOR INSERTION ---
    core_data, basic_data, advanced_data, fib_data, ath_data = [], [], [], [], []

    for i in range(n):
        core_data.append((timestamps[i], tf_key, symbol, float(opens[i]), float(highs[i]), float(lows[i]), float(closes[i]), int(volumes[i])))

        atr_ratio = atr_14[i] / atr_50[i] if atr_50[i] > 0 else 0
        ema_dist = ema_4[i] - ema_22[i]
        st_signal = 'BULL' if st_dir[i] == 1 else 'BEAR'
        basic_data.append((timestamps[i], tf_key, symbol, float(atr_14[i]), float(atr_50[i]), atr_ratio, float(ema_4[i]), float(ema_22[i]), ema_dist, st_signal))

        adv_row = [timestamps[i], tf_key, symbol] + [float(rsi[p][i]) for p in range(1, 15)] + [float(cci[p][i]) for p in range(1, 15)]
        for p in range(1,15): adv_row.extend([float(stoch_k[p][i]), float(stoch_d[p][i])])
        adv_row.extend([float(williams[p][i]) for p in range(1, 15)])
        adv_row.extend([float(adx[p][i]) for p in range(1, 15)])
        adv_row.extend([float(momentum[p][i]) for p in range(1, 15)])
        adv_row.extend([float(bb_upper[i]), float(bb_middle[i]), float(bb_lower[i]), float(bb_width[i]), float(bb_pct[i])])
        adv_row.extend([float(macd_line[i]), float(macd_signal[i]), float(macd_hist[i])])
        adv_row.extend([float(obv[i]), float(vol_ma[i]), float(volumes[i] / vol_ma[i] if vol_ma[i]>0 else 0), float(cmf[i])])
        adv_row.extend([float(sar[i]), 'UP' if sar_trend[i] == 1 else 'DOWN'])
        adv_row.extend([float(ich_tenkan[i]), float(ich_kijun[i]), float(ich_senkou_a[i]), float(ich_senkou_b[i])])
        adv_row.extend([float(roc[p][i]) for p in range(1, 15)])
        # Simplified pivots for this fix
        adv_row.extend([pivot_high[i], fib_levels['0618'][i], fib_levels['0786'][i], fib_levels['1000'][i], fib_levels['0382'][i], fib_levels['0236'][i], fib_levels['0000'][i]])
        adv_row.extend([float(atr_multi[p][i]) for p in range(1, 14)])
        advanced_data.append(tuple(adv_row))

        fib_data.append((timestamps[i], tf_key, symbol, float(pivot_high[i]), float(pivot_low[i]), *[float(fib_levels[k][i]) for k in sorted(fib_levels.keys())], fib_zone[i], int(in_golden[i]), float(zone_mult[i])))
        ath_data.append((timestamps[i], tf_key, symbol, float(ath[i]), float(closes[i]), float(ath_dist[i]), float(ath_mult[i]), ath_zone[i]))

    # --- DATABASE INSERTION ---
    cursor = conn.cursor()
    log.info(f"[{tf_key.upper()}] Inserting {n:,} rows into 5 tables...")

    cursor.executemany('INSERT OR REPLACE INTO core_15m (timestamp, timeframe, symbol, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', core_data)
    cursor.executemany('INSERT OR REPLACE INTO basic_15m (timestamp, timeframe, symbol, atr_14, atr_50_avg, atr_ratio, ema_short, ema_medium, ema_distance, supertrend) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', basic_data)

    adv_cols = 'timestamp, timeframe, symbol, rsi_1, rsi_2, rsi_3, rsi_4, rsi_5, rsi_6, rsi_7, rsi_8, rsi_9, rsi_10, rsi_11, rsi_12, rsi_13, rsi_14, cci_1, cci_2, cci_3, cci_4, cci_5, cci_6, cci_7, cci_8, cci_9, cci_10, cci_11, cci_12, cci_13, cci_14, stoch_k_1, stoch_d_1, stoch_k_2, stoch_d_2, stoch_k_3, stoch_d_3, stoch_k_4, stoch_d_4, stoch_k_5, stoch_d_5, stoch_k_6, stoch_d_6, stoch_k_7, stoch_d_7, stoch_k_8, stoch_d_8, stoch_k_9, stoch_d_9, stoch_k_10, stoch_d_10, stoch_k_11, stoch_d_11, stoch_k_12, stoch_d_12, stoch_k_13, stoch_d_13, stoch_k_14, stoch_d_14, williams_r_1, williams_r_2, williams_r_3, williams_r_4, williams_r_5, williams_r_6, williams_r_7, williams_r_8, williams_r_9, williams_r_10, williams_r_11, williams_r_12, williams_r_13, williams_r_14, adx_1, adx_2, adx_3, adx_4, adx_5, adx_6, adx_7, adx_8, adx_9, adx_10, adx_11, adx_12, adx_13, adx_14, momentum_1, momentum_2, momentum_3, momentum_4, momentum_5, momentum_6, momentum_7, momentum_8, momentum_9, momentum_10, momentum_11, momentum_12, momentum_13, momentum_14, bb_upper_20, bb_middle_20, bb_lower_20, bb_width_20, bb_pct_20, macd_line_12_26, macd_signal_12_26, macd_histogram_12_26, obv, volume_ma_20, volume_ratio, cmf_20, sar, sar_trend, ichimoku_tenkan, ichimoku_kijun, ichimoku_senkou_a, ichimoku_senkou_b, roc_1, roc_2, roc_3, roc_4, roc_5, roc_6, roc_7, roc_8, roc_9, roc_10, roc_11, roc_12, roc_13, roc_14, fib_pivot, fib_r1, fib_r2, fib_r3, fib_s1, fib_s2, fib_s3, atr_1, atr_2, atr_3, atr_4, atr_5, atr_6, atr_7, atr_8, atr_9, atr_10, atr_11, atr_12, atr_13'
    placeholders = ','.join(['?' for _ in range(150)])
    sql = f'INSERT OR REPLACE INTO advanced_indicators ({adv_cols}) VALUES ({placeholders})'
    cursor.executemany(sql, advanced_data)

    fib_cols = 'timestamp, timeframe, symbol, pivot_high, pivot_low, fib_level_0000, fib_level_0236, fib_level_0382, fib_level_0500, fib_level_0618, fib_level_0786, fib_level_1000, fib_level_1272, fib_level_1618, fib_level_2000, fib_level_2618, fib_level_3618, fib_level_4236, current_fib_zone, in_golden_zone, zone_multiplier'
    placeholders = ','.join(['?' for _ in range(21)])
    sql = f'INSERT OR REPLACE INTO fibonacci_data ({fib_cols}) VALUES ({placeholders})'
    cursor.executemany(sql, fib_data)

    ath_cols = 'timestamp, timeframe, symbol, current_ath, current_close, ath_distance_pct, ath_multiplier, ath_zone'
    placeholders = ','.join(['?' for _ in range(8)])
    sql = f'INSERT OR REPLACE INTO ath_tracking ({ath_cols}) VALUES ({placeholders})'
    cursor.executemany(sql, ath_data)

    conn.commit()
    log.info(f"[{tf_key.upper()}] All tables populated successfully.")
    return n

def backfill_symbol(symbol_config):
    db_path = symbol_config['db']
    symbol = symbol_config['symbol']
    name = symbol_config['name']

    log.info("=" * 70)
    log.info(f"PROCESSING: {name} ({symbol})")
    log.info(f"Database: {db_path}")
    log.info("=" * 70)

    if not check_database_exists(db_path): return False
    if not debug_symbol_info(symbol): return False
    if not debug_test_data_fetch(symbol, mt5.TIMEFRAME_M15, '15m'): return False

    clear_database_tables(db_path)

    conn = sqlite3.connect(db_path)
    total_bars = 0
    start_time = datetime.now()

    for tf_key, tf_mt5 in TIMEFRAMES.items():
        total_bars += backfill_timeframe(conn, symbol, tf_key, tf_mt5, MAX_BARS)

    conn.close()

    elapsed = (datetime.now() - start_time).total_seconds()
    size_mb = os.path.getsize(db_path) / 1024 / 1024

    log.info(f"COMPLETED for {name}: {total_bars:,} total bars in {elapsed:.1f}s. DB size: {size_mb:.1f} MB")
    return True

# ============================================================================
# MAIN
# ============================================================================

def main():
    log.info("=" * 70)
    log.info("MT5 UNIFIED DATABASE BACKFILL WIZARD (V2 - FIXED)")
    log.info("=" * 70)

    if not debug_mt5_init():
        return
    debug_mt5_status()

    log.info("\nChecking databases and symbols...")
    valid_symbols_to_fill = []
    for config in SYMBOLS_TO_FILL:
        if check_database_exists(config['db']) and debug_symbol_info(config['symbol']):
            valid_symbols_to_fill.append(config)
        else:
            log.error(f"Skipping {config['name']} due to setup issues.")

    if not valid_symbols_to_fill:
        log.error("No valid databases or symbols found. Please run init_databases.py and check symbol names.")
        mt5.shutdown()
        return

    log.info("\n" + "=" * 70)
    log.info("Ready to fill the following databases:")
    for config in valid_symbols_to_fill:
        log.info(f"  - {config['name']} ({config['db']})")
    log.info(f"This will fill {MAX_BARS:,} bars for 1m and 15m timeframes.")
    log.info("This will DELETE ALL EXISTING DATA in these files.")
    log.info("This process may take 5-15 minutes per database.")

    confirm = input("\nType 'FILL ALL' to begin: ").strip()
    if confirm != 'FILL ALL':
        log.warning("Confirmation failed. Exiting.")
        mt5.shutdown()
        return

    log.info("\n--- STARTING BACKFILL ---")
    start_time = datetime.now()

    for config in valid_symbols_to_fill:
        backfill_symbol(config)

    elapsed = (datetime.now() - start_time).total_seconds()
    log.info("\n" + "=" * 70)
    log.info(f"ALL BACKFILLS COMPLETE in {elapsed/60:.1f} minutes.")
    log.info("=" * 70)

    mt5.shutdown()

if __name__ == '__main__':
    if not os.path.exists('goldfill.py'):
        print("ERROR: 'goldfill.py' is missing. It's required for its calculation functions.")
    else:
        main()