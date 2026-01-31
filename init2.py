# init2.py (Version 2.4 - Smart Gap Fill)
"""
MT5 META AGENT V11.3 - UNIFIED STARTUP & INITIALIZATION
- Full 50K backfill for empty databases
- Gap-only fill for databases with sufficient data (FAST)
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta
import threading
import atexit
import time
import numpy as np
from flask import Flask, render_template, jsonify, request, redirect, send_from_directory
from flask_cors import CORS

from config import SYMBOL_DATABASES, DEFAULT_SYMBOL
from mt5_collector_v11_3 import MT5AdvancedCollector

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️  MetaTrader5 not installed - backfill disabled")

try:
    from fibonacci_calculator import calculate_fibonacci_data
    from ath_calculator import calculate_ath_data
    CALCULATORS_AVAILABLE = True
except ImportError:
    CALCULATORS_AVAILABLE = False
    print("⚠️  Fibonacci/ATH calculators not found")

# ============================================================================
# CONFIGURATION
# ============================================================================

ACTIVE_SYMBOL = DEFAULT_SYMBOL
BACKFILL_ENABLED = True
BACKFILL_MAX_BARS = 50000
BACKFILL_MIN_BARS_THRESHOLD = 1000
ATH_LOOKBACK = 500
FIB_LOOKBACK = 100

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
collector_threads = {}


# ============================================================================
# INDICATOR CALCULATION
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
        if closes[i] > closes[i-1]:
            obv += float(volumes[i])
        elif closes[i] < closes[i-1]:
            obv -= float(volumes[i])
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


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_symbol_db_path(symbol_id):
    return SYMBOL_DATABASES.get(symbol_id.upper(), {}).get('db_path')

def get_symbol_db_connection(symbol_id):
    db_path = get_symbol_db_path(symbol_id)
    if not db_path or not os.path.exists(db_path):
        return None, f"Database for {symbol_id} not found."
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn, None
    except Exception as e:
        return None, str(e)

def get_db_record_count(db_path, timeframe):
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM core_15m WHERE timeframe = ?", (timeframe,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_symbol_record_counts(symbol_id):
    conn, error = get_symbol_db_connection(symbol_id)
    if conn is None:
        return {'records_1m': 0, 'records_15m': 0}
    counts = {'records_1m': 0, 'records_15m': 0}
    try:
        cursor = conn.cursor()
        for tf in ['1m', '15m']:
            cursor.execute(f"SELECT COUNT(*) FROM core_15m WHERE timeframe=?", (tf,))
            counts[f'records_{tf}'] = cursor.fetchone()[0]
        conn.close()
    except:
        pass
    return counts


# ============================================================================
# INSERT SINGLE BAR (shared by both fill functions)
# ============================================================================

def insert_bar(cursor, symbol, timeframe_str, latest, history, close_price, highs, lows):
    """Insert a single bar with all indicators."""
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
                  fib_data['fib_level_0786'], fib_data.get('fib_level_1000', fib_data['pivot_high']),
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
# FULL BACKFILL (for empty databases)
# ============================================================================

def full_backfill_timeframe(symbol, db_path, timeframe_str, mt5_timeframe):
    print(f"      [{timeframe_str}] Fetching {BACKFILL_MAX_BARS:,} bars...")
    
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, BACKFILL_MAX_BARS)
    if rates is None or len(rates) == 0:
        print(f"      [{timeframe_str}] ✗ No data!")
        return 0
    
    total = len(rates)
    print(f"      [{timeframe_str}] Got {total:,} bars, processing...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    inserted = 0
    
    for i in range(ATH_LOOKBACK, total):
        history = rates[max(0, i - ATH_LOOKBACK):i + 1]
        latest = history[-1]
        close_price = float(latest['close'])
        highs = np.array([float(r['high']) for r in history])
        lows = np.array([float(r['low']) for r in history])
        
        try:
            insert_bar(cursor, symbol, timeframe_str, latest, history, close_price, highs, lows)
            inserted += 1
            
            if inserted % 5000 == 0:
                conn.commit()
                pct = (inserted / (total - ATH_LOOKBACK)) * 100
                print(f"      [{timeframe_str}] ... {inserted:,} / {total - ATH_LOOKBACK:,} ({pct:.1f}%)")
        except:
            pass
    
    conn.commit()
    conn.close()
    print(f"      [{timeframe_str}] ✓ Completed: {inserted:,} bars")
    return inserted


# ============================================================================
# GAP-ONLY FILL (for databases with sufficient data)
# ============================================================================

def fill_gaps_only(symbol, db_path, timeframe_str, mt5_timeframe, existing_timestamps):
    """Fill ONLY the missing bars - not a full backfill."""
    
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 5000)
    if rates is None or len(rates) == 0:
        return 0
    
    # Find missing indices
    missing_indices = []
    for i, rate in enumerate(rates):
        ts = datetime.fromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S')
        if ts not in existing_timestamps:
            missing_indices.append(i)
    
    if not missing_indices:
        return 0
    
    print(f"      Filling {len(missing_indices)} gaps...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    filled = 0
    
    for i in missing_indices:
        if i < ATH_LOOKBACK:
            continue
        
        history = rates[max(0, i - ATH_LOOKBACK):i + 1]
        latest = history[-1]
        close_price = float(latest['close'])
        highs = np.array([float(r['high']) for r in history])
        lows = np.array([float(r['low']) for r in history])
        
        try:
            insert_bar(cursor, symbol, timeframe_str, latest, history, close_price, highs, lows)
            filled += 1
        except:
            pass
    
    conn.commit()
    conn.close()
    print(f"      ✓ Filled {filled} gaps")
    return filled


# ============================================================================
# MAIN BACKFILL CHECK
# ============================================================================

def run_backfill_check():
    if not MT5_AVAILABLE or not BACKFILL_ENABLED:
        print("[BACKFILL] Skipped")
        return
    
    print("\n" + "="*70)
    print("BACKFILL CHECK")
    print("="*70)
    
    if not mt5.initialize():
        print("[BACKFILL] ✗ MT5 connection failed")
        return
    
    print(f"[BACKFILL] ✓ Connected to MT5")
    
    timeframes = {'1m': mt5.TIMEFRAME_M1, '15m': mt5.TIMEFRAME_M15}
    total_filled = 0
    
    for symbol_id, config in SYMBOL_DATABASES.items():
        db_path = config['db_path']
        symbol = config['symbol']
        
        if not os.path.exists(db_path):
            print(f"\n  [{symbol_id}] DB not found - skip")
            continue
        
        if not mt5.symbol_select(symbol, True):
            print(f"\n  [{symbol_id}] MT5 symbol error - skip")
            continue
        
        print(f"\n  [{symbol_id}] {config['name']}")
        
        for tf_str, tf_mt5 in timeframes.items():
            current = get_db_record_count(db_path, tf_str)
            print(f"    [{tf_str}] {current:,} bars")
            
            if current < BACKFILL_MIN_BARS_THRESHOLD:
                print(f"    [{tf_str}] FULL backfill needed...")
                filled = full_backfill_timeframe(symbol, db_path, tf_str, tf_mt5)
                total_filled += filled
            else:
                # Get existing timestamps
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp FROM core_15m WHERE symbol = ? AND timeframe = ?", (symbol, tf_str))
                existing = set(row[0] for row in cursor.fetchall())
                conn.close()
                
                # Check for gaps
                rates = mt5.copy_rates_from_pos(symbol, tf_mt5, 0, 5000)
                if rates is not None:
                    missing = sum(1 for r in rates if datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S') not in existing)
                    
                    if missing > 0:
                        print(f"    [{tf_str}] {missing} gaps found")
                        filled = fill_gaps_only(symbol, db_path, tf_str, tf_mt5, existing)
                        total_filled += filled
                    else:
                        print(f"    [{tf_str}] ✓ No gaps")
    
    mt5.shutdown()
    print(f"\n[BACKFILL] Done - {total_filled:,} bars filled")


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index(): return render_template('apex.html')
@app.route('/apex')
def apex(): return render_template('apex.html')
@app.route('/chart-data')
def chart_data(): return render_template('chart_data.html')
@app.route('/tunity')
def tunity(): return render_template('tunity.html')
@app.route('/fingerprint')
def fingerprint(): return render_template('fingerprint_medium.html')
@app.route('/metatron')
def metatron(): return send_from_directory('templates', 'metatron_radial.html')


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/health')
def api_health():
    return jsonify({'status': 'healthy', 'active_symbol': ACTIVE_SYMBOL})

@app.route('/api/symbols')
def api_symbols():
    symbols = []
    for sym_id, config in SYMBOL_DATABASES.items():
        available = os.path.exists(config['db_path'])
        counts = get_symbol_record_counts(sym_id) if available else {}
        symbols.append({
            'id': config['id'], 'name': config['name'], 'symbol': config['symbol'],
            'available': available, 'records_1m': counts.get('records_1m', 0),
            'records_15m': counts.get('records_15m', 0)
        })
    return jsonify({'success': True, 'symbols': symbols, 'active_symbol': ACTIVE_SYMBOL})

@app.route('/api/symbols/active', methods=['GET', 'POST'])
def api_active_symbol():
    global ACTIVE_SYMBOL
    if request.method == 'POST':
        data = request.get_json()
        symbol_id = data.get('symbol_id', '').upper()
        if symbol_id in SYMBOL_DATABASES and os.path.exists(get_symbol_db_path(symbol_id)):
            ACTIVE_SYMBOL = symbol_id
    return jsonify({'success': True, 'active_symbol': ACTIVE_SYMBOL})

@app.route('/api/chart-data')
def api_chart_data():
    symbol_id = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 200))
    
    # Handle trading instance IDs (tr_xxx) - fall back to active symbol
    if symbol_id.startswith('tr_'):
        symbol_id = ACTIVE_SYMBOL
    
    # Try uppercase lookup
    config = SYMBOL_DATABASES.get(symbol_id.upper())
    if not config:
        # Fall back to active symbol if not found
        config = SYMBOL_DATABASES.get(ACTIVE_SYMBOL)
        if not config:
            return jsonify({'success': False, 'error': 'Unknown symbol'}), 404
        symbol_id = ACTIVE_SYMBOL
    
    conn, error = get_symbol_db_connection(symbol_id.upper())
    if conn is None: 
        return jsonify({'success': False, 'error': error}), 404
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, open, high, low, close, volume FROM core_15m WHERE timeframe = ? ORDER BY timestamp DESC LIMIT ?", (timeframe, limit))
        data = [dict(row) for row in reversed(cursor.fetchall())]
        conn.close()
        return jsonify({'success': True, 'symbol': config['symbol'], 'data': data})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/basic')
def api_basic():
    symbol_id = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '1m')
    limit = int(request.args.get('limit', 100))
    
    # Handle trading instance IDs (tr_xxx) - fall back to active symbol
    if symbol_id.startswith('tr_'):
        symbol_id = ACTIVE_SYMBOL
    
    config = SYMBOL_DATABASES.get(symbol_id.upper())
    if not config:
        config = SYMBOL_DATABASES.get(ACTIVE_SYMBOL)
        symbol_id = ACTIVE_SYMBOL
    
    symbol_name = config['symbol'] if config else symbol_id
    conn, error = get_symbol_db_connection(symbol_id.upper() if not symbol_id.startswith('tr_') else ACTIVE_SYMBOL)
    if conn is None: return jsonify({'success': False, 'error': error}), 404
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, atr_14, atr_50_avg, atr_ratio, ema_short, ema_medium, ema_distance, supertrend FROM basic_15m WHERE timeframe = ? AND symbol = ? ORDER BY timestamp DESC LIMIT ?", (timeframe, symbol_name, limit))
        data = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data, 'count': len(data)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/advanced')
def api_advanced():
    symbol_id = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 100))
    
    # Handle trading instance IDs (tr_xxx) - fall back to active symbol
    if symbol_id.startswith('tr_'):
        symbol_id = ACTIVE_SYMBOL
    
    config = SYMBOL_DATABASES.get(symbol_id.upper())
    if not config:
        config = SYMBOL_DATABASES.get(ACTIVE_SYMBOL)
        symbol_id = ACTIVE_SYMBOL
    
    symbol_name = config['symbol'] if config else symbol_id
    conn, error = get_symbol_db_connection(symbol_id.upper())
    if conn is None: return jsonify({'success': False, 'error': error}), 404
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM advanced_indicators WHERE timeframe = ? AND symbol = ? ORDER BY timestamp DESC LIMIT ?", (timeframe, symbol_name, limit))
        data = [{k: (v.decode() if isinstance(v, bytes) else v) for k, v in dict(row).items()} for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data, 'count': len(data)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/fibonacci')
def api_fibonacci():
    symbol_id = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 100))
    
    # Handle trading instance IDs (tr_xxx) - fall back to active symbol
    if symbol_id.startswith('tr_'):
        symbol_id = ACTIVE_SYMBOL
    
    config = SYMBOL_DATABASES.get(symbol_id.upper())
    if not config:
        config = SYMBOL_DATABASES.get(ACTIVE_SYMBOL)
        symbol_id = ACTIVE_SYMBOL
    
    symbol_name = config['symbol'] if config else symbol_id
    conn, error = get_symbol_db_connection(symbol_id.upper())
    if conn is None: return jsonify({'success': False, 'error': error}), 404
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fibonacci_data WHERE timeframe = ? AND symbol = ? ORDER BY timestamp DESC LIMIT ?", (timeframe, symbol_name, limit))
        data = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data, 'count': len(data)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/ath')
def api_ath():
    symbol_id = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 100))
    
    # Handle trading instance IDs (tr_xxx) - fall back to active symbol
    if symbol_id.startswith('tr_'):
        symbol_id = ACTIVE_SYMBOL
    
    config = SYMBOL_DATABASES.get(symbol_id.upper())
    if not config:
        config = SYMBOL_DATABASES.get(ACTIVE_SYMBOL)
        symbol_id = ACTIVE_SYMBOL
    
    symbol_name = config['symbol'] if config else symbol_id
    conn, error = get_symbol_db_connection(symbol_id.upper())
    if conn is None: return jsonify({'success': False, 'error': error}), 404
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ath_tracking WHERE timeframe = ? AND symbol = ? ORDER BY timestamp DESC LIMIT ?", (timeframe, symbol_name, limit))
        data = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data, 'count': len(data)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/profiles')
def api_profiles():
    symbol_id = request.args.get('symbol')
    if not symbol_id: return jsonify({'success': False, 'error': 'Symbol required'}), 400
    conn, error = get_symbol_db_connection(symbol_id)
    if conn is None: return jsonify({'success': True, 'profiles': []})
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'")
        if not cursor.fetchone(): return jsonify({'success': True, 'profiles': []})
        cursor.execute("SELECT * FROM profiles LIMIT 50")
        return jsonify({'success': True, 'profiles': [dict(row) for row in cursor.fetchall()]})
    finally:
        conn.close()

@app.route('/api/hyperspheres')
def api_hyperspheres():
    symbol_id = request.args.get('symbol')
    if not symbol_id: return jsonify({'success': False, 'error': 'Symbol required'}), 400
    conn, error = get_symbol_db_connection(symbol_id)
    if conn is None: return jsonify({'success': True, 'hyperspheres': []})
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hyperspheres'")
        if not cursor.fetchone(): return jsonify({'success': True, 'hyperspheres': []})
        cursor.execute("SELECT * FROM hyperspheres LIMIT 50")
        return jsonify({'success': True, 'hyperspheres': [dict(row) for row in cursor.fetchall()]})
    finally:
        conn.close()


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

def startup():
    print("\n" + "="*70)
    print("MT5 META AGENT V11.3 - STARTUP")
    print("="*70)
    
    run_backfill_check()
    
    print("\n[STARTUP] Starting collectors...")
    for symbol_id, config in SYMBOL_DATABASES.items():
        if os.path.exists(config['db_path']):
            collector = MT5AdvancedCollector(symbol=config['symbol'], db_path=config['db_path'])
            if collector.connect_mt5():
                thread = threading.Thread(target=collector.run, daemon=True)
                thread.start()
                collector_threads[symbol_id] = {'collector': collector, 'thread': thread}
                print(f"  ✓ {symbol_id} collector running")
            else:
                print(f"  ✗ {symbol_id} MT5 failed")

    print("\n" + "="*70)
    print("FLASK SERVER: http://localhost:5000/")
    print("="*70)

def shutdown():
    print("\nShutting down collectors...")
    for data in collector_threads.values():
        data['collector'].running = False
    time.sleep(1)

atexit.register(shutdown)

if __name__ == '__main__':
    startup()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
