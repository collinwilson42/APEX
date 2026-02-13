"""
CHART HEALTH CHECK — Re-render Last N Bars from MT5
====================================================
Self-contained — no init2 import to avoid circular dependency.
Uses the same indicator math as init2 but standalone.

Usage:
    python chart_health_check.py                              # Diagnose all
    python chart_health_check.py --repair --symbol XAUJ26     # Fix gold 15m
    python chart_health_check.py --repair --symbol XAUJ26 --timeframe 1h
    python chart_health_check.py --repair --symbol USOILH26 --bars 200
"""

import sqlite3
import sys
import os
import argparse
from datetime import datetime
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import SYMBOL_DATABASES
import MetaTrader5 as mt5

# Import calculators (same as init2)
try:
    from fibonacci_calculator import calculate_fibonacci_data
    from ath_calculator import calculate_ath_data
    CALCULATORS_AVAILABLE = True
except ImportError:
    CALCULATORS_AVAILABLE = False
    print("[WARN] Fibonacci/ATH calculators not found — OHLCV + basic only")

TIMEFRAME_MAP = {
    '15m': mt5.TIMEFRAME_M15,
    '1h': mt5.TIMEFRAME_H1
}

ALL_TABLES = ['core_15m', 'basic_15m', 'advanced_indicators', 'fibonacci_data', 'ath_tracking']
ATH_LOOKBACK = 500
FIB_LOOKBACK = 120


def resolve_symbol(raw):
    """Resolve symbol input to a SYMBOL_DATABASES key. Handles .sim suffix, case."""
    if not raw:
        return None, None
    sid = raw.strip().upper()
    if sid.endswith('.SIM'):
        sid = sid[:-4]
    if '.' in sid:
        sid = sid.rsplit('.', 1)[0]
    config = SYMBOL_DATABASES.get(sid)
    return (sid, config) if config else (None, None)


# ============================================================================
# INDICATOR CALCULATION (copied from init2 to avoid circular import)
# ============================================================================

def calculate_indicators_for_fill(history_rates):
    closes = np.array([float(r['close']) for r in history_rates])
    highs = np.array([float(r['high']) for r in history_rates])
    lows = np.array([float(r['low']) for r in history_rates])
    volumes = np.array([float(r['tick_volume']) for r in history_rates])
    n = len(closes)

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

    adv = {}
    deltas = np.diff(closes) if n > 1 else np.array([0.0])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    for p in range(1, 15):
        if len(gains) >= p:
            ag, al = float(np.mean(gains[-p:])), float(np.mean(losses[-p:]))
            rsi = 100.0 - (100.0 / (1.0 + ag / al)) if al > 0 else (100.0 if ag > 0 else 50.0)
        else:
            rsi = 50.0
        adv[f'rsi_{p}'] = round(float(rsi), 2)

        if n >= p:
            tp = (highs[-p:] + lows[-p:] + closes[-p:]) / 3.0
            sma_tp = float(np.mean(tp))
            mad = float(np.mean(np.abs(tp - sma_tp)))
            adv[f'cci_{p}'] = round((float(tp[-1]) - sma_tp) / (0.015 * mad) if mad != 0 else 0.0, 2)
        else:
            adv[f'cci_{p}'] = 0.0

        if n >= p:
            l_min, h_max = float(np.min(lows[-p:])), float(np.max(highs[-p:]))
            k = (float(closes[-1]) - l_min) / (h_max - l_min) * 100.0 if h_max != l_min else 50.0
            adv[f'stoch_k_{p}'] = round(float(k), 2)
            adv[f'stoch_d_{p}'] = round(float(k) * 0.9, 2)
        else:
            adv[f'stoch_k_{p}'] = 50.0
            adv[f'stoch_d_{p}'] = 50.0

        if n >= p:
            h_max, l_min = float(np.max(highs[-p:])), float(np.min(lows[-p:]))
            adv[f'williams_r_{p}'] = round((h_max - float(closes[-1])) / (h_max - l_min) * -100.0 if h_max != l_min else -50.0, 2)
        else:
            adv[f'williams_r_{p}'] = -50.0

        adv[f'adx_{p}'] = round(25.0 + float(p % 10), 2)
        adv[f'momentum_{p}'] = round(float(closes[-1]) - float(closes[-p-1]) if n > p else 0.0, 5)

        if n > p and closes[-p-1] != 0:
            adv[f'roc_{p}'] = round((float(closes[-1]) - float(closes[-p-1])) / float(closes[-p-1]) * 100.0, 4)
        else:
            adv[f'roc_{p}'] = 0.0

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

    ema12, ema26 = ema(closes, 12), ema(closes, 26)
    macd = ema12 - ema26
    adv['macd_line_12_26'] = round(float(macd), 5)
    adv['macd_signal_12_26'] = round(float(macd) * 0.9, 5)
    adv['macd_histogram_12_26'] = round(float(macd) * 0.1, 5)

    obv = 0.0
    for i in range(1, n):
        if closes[i] > closes[i-1]: obv += float(volumes[i])
        elif closes[i] < closes[i-1]: obv -= float(volumes[i])
    adv['obv'] = round(obv, 0)

    vol_ma = float(np.mean(volumes[-20:])) if n >= 20 else float(np.mean(volumes))
    adv['volume_ma_20'] = round(vol_ma, 0)
    adv['volume_ratio'] = round(float(volumes[-1]) / vol_ma if vol_ma > 0 else 1.0, 4)

    if n >= 20:
        hl = highs[-20:] - lows[-20:]
        hl = np.where(hl == 0, 0.0001, hl)
        mfv = ((closes[-20:] - lows[-20:]) - (highs[-20:] - closes[-20:])) / hl * volumes[-20:]
        adv['cmf_20'] = round(float(np.sum(mfv)) / (float(np.sum(volumes[-20:])) + 0.0001), 4)
    else:
        adv['cmf_20'] = 0.0

    adv['sar'] = round(float(closes[-1]) * 0.98, 5)
    adv['sar_trend'] = "UP" if n > 1 and closes[-1] > closes[-2] else "DOWN"

    adv['ichimoku_tenkan'] = round((float(np.max(highs[-9:])) + float(np.min(lows[-9:]))) / 2.0, 5) if n >= 9 else round(float(closes[-1]), 5)
    adv['ichimoku_kijun'] = round((float(np.max(highs[-26:])) + float(np.min(lows[-26:]))) / 2.0, 5) if n >= 26 else round(float(closes[-1]), 5)
    adv['ichimoku_senkou_a'] = round((adv['ichimoku_tenkan'] + adv['ichimoku_kijun']) / 2.0, 5)
    adv['ichimoku_senkou_b'] = round((float(np.max(highs[-52:])) + float(np.min(lows[-52:]))) / 2.0, 5) if n >= 52 else round(float(closes[-1]), 5)

    pivot = (float(highs[-1]) + float(lows[-1]) + float(closes[-1])) / 3.0
    fr = float(highs[-1]) - float(lows[-1])
    adv['fib_pivot'] = round(pivot, 5)
    adv['fib_r1'] = round(pivot + 0.382 * fr, 5)
    adv['fib_r2'] = round(pivot + 0.618 * fr, 5)
    adv['fib_r3'] = round(pivot + fr, 5)
    adv['fib_s1'] = round(pivot - 0.382 * fr, 5)
    adv['fib_s2'] = round(pivot - 0.618 * fr, 5)
    adv['fib_s3'] = round(pivot - fr, 5)

    for p in range(1, 14):
        adv[f'atr_{p}'] = round(float(np.mean(tr[-p:])) if n >= p else 0.0, 5)

    return basic, adv


def insert_bar(cursor, symbol, timeframe_str, latest, history, close_price, highs, lows):
    """Insert a single bar with all indicators — same logic as init2.insert_bar()."""
    timestamp = datetime.fromtimestamp(latest['time']).strftime('%Y-%m-%d %H:%M:%S')
    basic, adv = calculate_indicators_for_fill(history)

    # Core
    cursor.execute("""
        INSERT OR REPLACE INTO core_15m
        (timestamp, timeframe, symbol, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, timeframe_str, symbol,
          float(latest['open']), float(latest['high']),
          float(latest['low']), float(latest['close']),
          int(latest['tick_volume'])))

    # Basic
    cursor.execute("""
        INSERT OR REPLACE INTO basic_15m
        (timestamp, timeframe, symbol, atr_14, atr_50_avg, atr_ratio,
         ema_short, ema_medium, ema_distance, supertrend)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, timeframe_str, symbol,
          basic['atr_14'], basic['atr_50_avg'], basic['atr_ratio'],
          basic['ema_short'], basic['ema_medium'], basic['ema_distance'],
          basic['supertrend']))

    # Advanced
    adv_cols = list(adv.keys())
    adv_vals = [adv[k] for k in adv_cols]
    cols_str = ','.join(['timestamp', 'timeframe', 'symbol'] + adv_cols)
    placeholders = ','.join(['?' for _ in range(len(adv_cols) + 3)])
    cursor.execute(f"INSERT OR REPLACE INTO advanced_indicators ({cols_str}) VALUES ({placeholders})",
                   [timestamp, timeframe_str, symbol] + adv_vals)

    # Fibonacci
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
                  fib_data.get('fib_level_0236', 0), fib_data['fib_level_0382'],
                  fib_data.get('fib_level_0500', 0), fib_data['fib_level_0618'],
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
        except:
            pass

    # ATH
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


# ============================================================================
# DIAGNOSE
# ============================================================================

def diagnose(db_path, symbol_name, timeframe, bar_count=100):
    if not os.path.exists(db_path):
        return f"  ✗ DB not found: {db_path}"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT timestamp, open, high, low, close, volume
        FROM core_15m WHERE timeframe=? AND symbol=?
        ORDER BY timestamp DESC LIMIT ?
    """, (timeframe, symbol_name, bar_count))
    bars = [dict(r) for r in reversed(c.fetchall())]

    if not bars:
        conn.close()
        return "  ✗ No bars in core_15m"

    issues = []

    # Table count mismatches
    ts_first, ts_last = bars[0]['timestamp'], bars[-1]['timestamp']
    core_count = len(bars)
    for table in ALL_TABLES:
        try:
            c.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE timeframe=? AND symbol=? AND timestamp>=? AND timestamp<=?
            """, (timeframe, symbol_name, ts_first, ts_last))
            cnt = c.fetchone()[0]
            if cnt != core_count:
                issues.append(f"{table}: {cnt} rows (core has {core_count})")
        except:
            pass

    # Timestamp gaps
    expected_sec = 900 if timeframe == '15m' else 3600
    parsed = [datetime.strptime(b['timestamp'], '%Y-%m-%d %H:%M:%S') for b in bars]
    gaps = 0
    for i in range(1, len(parsed)):
        delta = (parsed[i] - parsed[i-1]).total_seconds()
        if delta > expected_sec * 1.5 and delta < 48 * 3600:
            if not (parsed[i-1].weekday() == 4 and parsed[i].weekday() in [0, 6]):
                gaps += 1

    if gaps:
        issues.append(f"{gaps} timestamp gaps")

    # Bad OHLC
    bad = sum(1 for b in bars if b['high'] < b['low'] or
              b['high'] < b['open'] or b['high'] < b['close'] or
              b['low'] > b['open'] or b['low'] > b['close'] or
              any(v in (None, 0) for v in (b['open'], b['high'], b['low'], b['close'])))
    if bad:
        issues.append(f"{bad} bars with bad OHLC")

    # Stale
    stale = sum(1 for i in range(1, len(bars))
                if bars[i]['open'] == bars[i-1]['open'] and
                   bars[i]['close'] == bars[i-1]['close'] and
                   bars[i]['high'] == bars[i-1]['high'] and
                   bars[i]['low'] == bars[i-1]['low'])
    if stale > 2:
        issues.append(f"{stale} identical consecutive bars")

    conn.close()

    if issues:
        return f"  ⚠️  {len(bars)} bars, {len(issues)} issue(s): " + " | ".join(issues)
    return f"  ✅ {len(bars)} bars — healthy"


# ============================================================================
# REPAIR
# ============================================================================

def repair(symbol_id, timeframe='15m', bar_count=100):
    config = SYMBOL_DATABASES.get(symbol_id.upper())
    if not config:
        print(f"✗ Unknown symbol: {symbol_id}")
        return False

    symbol_name = config['symbol']
    db_path = config['db_path']
    mt5_tf = TIMEFRAME_MAP.get(timeframe)

    print(f"\n{'='*60}")
    print(f"  REPAIR: {symbol_id} [{timeframe}] — last {bar_count} bars")
    print(f"{'='*60}")

    # 1. Init MT5
    print(f"\n[1/5] Connecting to MT5...")
    if not mt5.initialize():
        print(f"  ✗ MT5 init failed: {mt5.last_error()}")
        return False
    if not mt5.symbol_select(symbol_name, True):
        print(f"  ✗ Symbol not found: {symbol_name}")
        mt5.shutdown()
        return False
    print(f"  ✓ Connected — {symbol_name}")

    # 2. Find timestamps to delete
    print(f"\n[2/5] Reading last {bar_count} bar timestamps...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp FROM core_15m
        WHERE timeframe=? AND symbol=?
        ORDER BY timestamp DESC LIMIT ?
    """, (timeframe, symbol_name, bar_count))
    rows = cursor.fetchall()

    if not rows:
        print("  ✗ No bars found to replace")
        conn.close()
        mt5.shutdown()
        return False

    oldest = rows[-1][0]
    newest = rows[0][0]
    print(f"  {len(rows)} bars: {oldest} → {newest}")

    # 3. Delete from ALL tables
    print(f"\n[3/5] Deleting from all tables...")
    for table in ALL_TABLES:
        try:
            cursor.execute(f"""
                DELETE FROM {table}
                WHERE timeframe=? AND symbol=? AND timestamp>=? AND timestamp<=?
            """, (timeframe, symbol_name, oldest, newest))
            print(f"  {table}: {cursor.rowcount} deleted")
        except Exception as e:
            print(f"  {table}: skip ({e})")
    conn.commit()

    # 4. Fetch fresh from MT5
    fetch_count = bar_count + ATH_LOOKBACK + 50
    print(f"\n[4/5] Fetching {fetch_count} bars from MT5...")
    rates = mt5.copy_rates_from_pos(symbol_name, mt5_tf, 0, fetch_count)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print(f"  ✗ MT5 returned nothing")
        conn.close()
        return False
    print(f"  ✓ Got {len(rates)} bars")

    # 5. Re-insert with full indicators
    print(f"\n[5/5] Re-inserting with full indicator calculation...")
    inserted = 0
    errors = 0
    start_idx = max(ATH_LOOKBACK, len(rates) - bar_count)

    for i in range(start_idx, len(rates)):
        history = rates[max(0, i - ATH_LOOKBACK):i + 1]
        latest = history[-1]
        ts = datetime.fromtimestamp(latest['time']).strftime('%Y-%m-%d %H:%M:%S')

        if ts < oldest:
            continue

        close_price = float(latest['close'])
        highs_arr = np.array([float(r['high']) for r in history])
        lows_arr = np.array([float(r['low']) for r in history])

        try:
            insert_bar(cursor, symbol_name, timeframe, latest, history, close_price, highs_arr, lows_arr)
            inserted += 1
            if inserted % 25 == 0:
                conn.commit()
                print(f"  ... {inserted} bars")
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  ERROR at {ts}: {e}")

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  ✓ DONE — {inserted} bars re-inserted, {errors} errors")
    print(f"{'='*60}")

    # Post-repair check
    print(f"\nPost-repair diagnosis:")
    print(diagnose(db_path, symbol_name, timeframe, bar_count))
    return True


# ============================================================================
# CLI
# ============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Chart Health Check')
    parser.add_argument('--symbol', type=str, default='')
    parser.add_argument('--timeframe', type=str, default='15m')
    parser.add_argument('--bars', type=int, default=100)
    parser.add_argument('--repair', action='store_true')
    args = parser.parse_args()

    # Resolve symbol (handles .sim suffix)
    if args.symbol:
        resolved_id, resolved_config = resolve_symbol(args.symbol)
        if not resolved_config:
            print(f"✗ Unknown symbol: {args.symbol}")
            print(f"  Available: {', '.join(SYMBOL_DATABASES.keys())}")
            sys.exit(1)
        args.symbol = resolved_id

    if args.repair:
        if not args.symbol:
            print("--repair requires --symbol (e.g., --symbol XAUJ26)")
            sys.exit(1)
        repair(args.symbol, args.timeframe, args.bars)
    else:
        print(f"\nCHART HEALTH CHECK — Diagnosing last {args.bars} bars\n")
        if args.symbol:
            config = SYMBOL_DATABASES[args.symbol]
            for tf in ['15m', '1h']:
                print(f"{args.symbol} [{tf}]:")
                print(diagnose(config['db_path'], config['symbol'], tf, args.bars))
        else:
            for sym_id, config in SYMBOL_DATABASES.items():
                print(f"{sym_id}:")
                for tf in ['15m', '1h']:
                    print(f"  [{tf}] {diagnose(config['db_path'], config['symbol'], tf, args.bars)}")
