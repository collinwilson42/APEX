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
import json
from flask import Flask, render_template, jsonify, request, redirect, send_from_directory
from flask_cors import CORS

from config import SYMBOL_DATABASES, DEFAULT_SYMBOL
from mt5_collector_v11_3 import MT5AdvancedCollector
from dataclasses import asdict

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
# INSTANCE DATABASE INTEGRATION
# ============================================================================

instance_db = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from instance_database import get_instance_db, AlgorithmInstance
    instance_db = get_instance_db(os.path.join(BASE_DIR, 'apex_instances.db'))
    print("✓ Instance database initialized")
except ImportError as e:
    print(f"⚠️  Instance database not available: {e}")
except Exception as e:
    print(f"✗ Failed to initialize instance database: {e}")

# ============================================================================
# SENTIMENT ENGINE INTEGRATION
# ============================================================================

sentiment_scheduler = None
DEFAULT_SENTIMENT_SYMBOLS = ['XAUJ26', 'US100', 'BTCUSD']

try:
    from sentiment_engine import (
        SentimentConfig, 
        SentimentScheduler, 
        SentimentDatabase,
        register_sentiment_routes
    )
    
    sentiment_config = SentimentConfig(
        api_key=os.getenv('ANTHROPIC_API_KEY', ''),
        db_path=os.path.join(BASE_DIR, 'sentiment_analysis.db')
    )
    
    sentiment_scheduler = SentimentScheduler(sentiment_config, DEFAULT_SENTIMENT_SYMBOLS)
    register_sentiment_routes(app, sentiment_scheduler)
    print("✓ Sentiment engine initialized")
except ImportError as e:
    print(f"⚠️  Sentiment engine not available: {e}")
except Exception as e:
    print(f"✗ Failed to initialize sentiment engine: {e}")

# Chart Health Check: run standalone via `python chart_health_check.py`
# (no Flask route registration — avoids circular import with init2)

# ============================================================================
# CYTOBASE SIMULATOR INTEGRATION
# ============================================================================

try:
    from cyto_routes import register_cyto_routes
    register_cyto_routes(app)
    print("✓ CytoBase data routes registered")
except ImportError as e:
    print(f"⚠️  CytoBase data routes not available: {e}")
except Exception as e:
    print(f"✗ Failed to register CytoBase data routes: {e}")

# ============================================================================
# INSTANCE PROCESS MANAGER (Seed 16 — Independent Instances)
# ============================================================================
# Replaces monolithic CytoSimulator with per-symbol subprocesses.
# Each instance runs as its own Python process (instance_runner.py).

try:
    from process_manager import register_process_routes, get_process_manager
    register_process_routes(app)
    
    # Clean up any orphan processes from previous unclean shutdown
    pm = get_process_manager()
    pm.cleanup_orphans()
except ImportError as e:
    print(f"⚠️  Process manager not available: {e}")
except Exception as e:
    print(f"✗ Failed to register process manager: {e}")

# ============================================================================
# TORRA TRADER ROUTES (Seed 17 — The First Run)
# ============================================================================
# API routes for starting/stopping torra_trader.py from the frontend.
# Bridges Profile Manager (API key) → Instance Browser (activation) → Trader subprocess.

try:
    from trader_routes import register_trader_routes
    register_trader_routes(app)
except ImportError as e:
    print(f"⚠️  Trader routes not available: {e}")
except Exception as e:
    print(f"✗ Failed to register trader routes: {e}")

# ============================================================================
# CHART CAPTURE ROUTES (Seed 23 — Headless Plotly Export)
# ============================================================================

try:
    from chart_capture import register_capture_routes
    register_capture_routes(app)
    print("✓ Chart capture routes registered")
except ImportError as e:
    print(f"⚠️  Chart capture not available: {e}")
except Exception as e:
    print(f"✗ Failed to register chart capture routes: {e}")

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

def ensure_symbol_database(db_path):
    """Create the intelligence database with all required tables if it doesn't exist."""
    if os.path.exists(db_path):
        return
    
    print(f"  Creating new database: {os.path.basename(db_path)}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Core OHLCV table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS core_15m (
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume INTEGER,
            PRIMARY KEY (timestamp, timeframe, symbol)
        )
    """)
    
    # Basic indicators
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS basic_15m (
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            atr_14 REAL, atr_50_avg REAL, atr_ratio REAL,
            ema_short REAL, ema_medium REAL, ema_distance REAL,
            supertrend TEXT,
            PRIMARY KEY (timestamp, timeframe, symbol)
        )
    """)
    
    # Advanced indicators — dynamic columns, create base structure
    # Full columns are created on first INSERT OR REPLACE via the dynamic SQL
    adv_cols = []
    for p in range(1, 15):
        adv_cols += [f'rsi_{p} REAL', f'cci_{p} REAL', f'stoch_k_{p} REAL', f'stoch_d_{p} REAL',
                     f'williams_r_{p} REAL', f'adx_{p} REAL', f'momentum_{p} REAL', f'roc_{p} REAL']
    for p in range(1, 14):
        adv_cols.append(f'atr_{p} REAL')
    adv_cols += [
        'bb_upper_20 REAL', 'bb_middle_20 REAL', 'bb_lower_20 REAL', 'bb_width_20 REAL', 'bb_pct_20 REAL',
        'macd_line_12_26 REAL', 'macd_signal_12_26 REAL', 'macd_histogram_12_26 REAL',
        'obv REAL', 'volume_ma_20 REAL', 'volume_ratio REAL', 'cmf_20 REAL',
        'sar REAL', 'sar_trend TEXT',
        'ichimoku_tenkan REAL', 'ichimoku_kijun REAL', 'ichimoku_senkou_a REAL', 'ichimoku_senkou_b REAL',
        'fib_pivot REAL', 'fib_r1 REAL', 'fib_r2 REAL', 'fib_r3 REAL',
        'fib_s1 REAL', 'fib_s2 REAL', 'fib_s3 REAL'
    ]
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS advanced_indicators (
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            {', '.join(adv_cols)},
            PRIMARY KEY (timestamp, timeframe, symbol)
        )
    """)
    
    # Fibonacci data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fibonacci_data (
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            pivot_high REAL, pivot_low REAL,
            fib_level_0000 REAL, fib_level_0236 REAL, fib_level_0382 REAL, fib_level_0500 REAL,
            fib_level_0618 REAL, fib_level_0786 REAL, fib_level_1000 REAL, fib_level_1272 REAL,
            fib_level_1618 REAL, fib_level_2000 REAL, fib_level_2618 REAL, fib_level_3618 REAL, fib_level_4236 REAL,
            current_fib_zone TEXT, in_golden_zone INTEGER, zone_multiplier REAL,
            PRIMARY KEY (timestamp, timeframe, symbol)
        )
    """)
    
    # ATH tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ath_tracking (
            timestamp TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            symbol TEXT NOT NULL,
            current_ath REAL, current_close REAL,
            ath_distance_pct REAL, ath_multiplier REAL, ath_zone TEXT,
            PRIMARY KEY (timestamp, timeframe, symbol)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"  ✓ Database created: {os.path.basename(db_path)}")


def get_symbol_db_path(symbol_id):
    return SYMBOL_DATABASES.get(symbol_id.upper(), {}).get('db_path')

def resolve_symbol_id(raw_id):
    """Resolve a symbol ID to a valid SYMBOL_DATABASES key.
    Handles: exact match, .sim suffix, case insensitivity, tr_ prefixes.
    Returns (resolved_id, config) or (None, None) if not found."""
    if not raw_id:
        return None, None
    
    sid = raw_id.strip().upper()
    
    # Strip .sim/.SIM suffix
    if sid.endswith('.SIM'):
        sid = sid[:-4]
    
    # Direct lookup
    config = SYMBOL_DATABASES.get(sid)
    if config:
        return sid, config
    
    # Try without any suffix after last dot
    if '.' in sid:
        base = sid.rsplit('.', 1)[0]
        config = SYMBOL_DATABASES.get(base)
        if config:
            return base, config
    
    return None, None


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
    """Get record counts for each timeframe. SEED 13: Now tracks 15m and 1h."""
    conn, error = get_symbol_db_connection(symbol_id)
    if conn is None:
        return {'records_15m': 0, 'records_1h': 0}
    counts = {'records_15m': 0, 'records_1h': 0}
    try:
        cursor = conn.cursor()
        for tf in ['15m', '1h']:
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

def full_backfill_timeframe(symbol, db_path, timeframe_str, mt5_timeframe, db_symbol=None):
    """Full backfill. symbol=MT5 symbol for data fetch, db_symbol=symbol stored in DB."""
    db_symbol = db_symbol or symbol
    print(f"      [{timeframe_str}] Fetching {BACKFILL_MAX_BARS:,} bars from MT5 symbol '{symbol}'...")
    
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, BACKFILL_MAX_BARS)
    if rates is None or len(rates) == 0:
        error = mt5.last_error()
        print(f"      [{timeframe_str}] ✗ No data from MT5! Error: {error}")
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
            insert_bar(cursor, db_symbol, timeframe_str, latest, history, close_price, highs, lows)
            inserted += 1
            
            if inserted % 5000 == 0:
                conn.commit()
                pct = (inserted / (total - ATH_LOOKBACK)) * 100
                print(f"      [{timeframe_str}] ... {inserted:,} / {total - ATH_LOOKBACK:,} ({pct:.1f}%)")
        except Exception as e:
            if inserted == 0:
                print(f"      [{timeframe_str}] First insert error: {e}")
            pass
    
    conn.commit()
    conn.close()
    print(f"      [{timeframe_str}] ✓ Completed: {inserted:,} bars")
    return inserted


# ============================================================================
# GAP-ONLY FILL (for databases with sufficient data)
# ============================================================================

def fill_gaps_only(symbol, db_path, timeframe_str, mt5_timeframe, existing_timestamps, db_symbol=None):
    """Fill ONLY the missing bars. symbol=MT5 symbol, db_symbol=symbol stored in DB."""
    db_symbol = db_symbol or symbol
    
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
            insert_bar(cursor, db_symbol, timeframe_str, latest, history, close_price, highs, lows)
            filled += 1
        except Exception as e:
            if filled == 0:
                print(f"      Gap fill first error: {e}")
            pass
    
    conn.commit()
    conn.close()
    print(f"      ✓ Filled {filled} gaps")
    return filled


# ============================================================================
# MAIN BACKFILL CHECK
# ============================================================================

def resolve_mt5_symbol(config_symbol):
    """Resolve a config symbol to an actual MT5 symbol.
    Tries: exact match, without .sim, base symbol.
    Returns (mt5_symbol, success) tuple."""
    candidates = [config_symbol]
    
    # Strip .sim/.SIM suffix
    if config_symbol.lower().endswith('.sim'):
        base = config_symbol[:-4]
        candidates.append(base)
        candidates.append(base + '.SIM')
    
    for candidate in candidates:
        info = mt5.symbol_info(candidate)
        if info is not None:
            if mt5.symbol_select(candidate, True):
                return candidate, True
    
    return config_symbol, False


def run_backfill_check():
    if not MT5_AVAILABLE or not BACKFILL_ENABLED:
        print("[BACKFILL] Skipped")
        return
    
    print("\n" + "="*70)
    print("BACKFILL CHECK")
    print("="*70)
    
    if not mt5.initialize():
        print("[BACKFILL] ✗ MT5 connection failed")
        # Diagnostic: show MT5 error
        error = mt5.last_error()
        if error:
            print(f"[BACKFILL]   Error: {error}")
        return
    
    print(f"[BACKFILL] ✓ Connected to MT5")
    
    # Show available symbols for diagnostics
    all_symbols = mt5.symbols_get()
    if all_symbols:
        symbol_names = [s.name for s in all_symbols]
        # Show which config symbols are available in MT5
        for symbol_id, config in SYMBOL_DATABASES.items():
            base = config['symbol'].replace('.sim', '').replace('.SIM', '')
            matches = [s for s in symbol_names if base.lower() in s.lower()]
            if matches:
                print(f"  [{symbol_id}] MT5 matches: {matches[:5]}")
            else:
                print(f"  [{symbol_id}] ⚠ No MT5 match for '{config['symbol']}' or '{base}'")
    
    # SEED 13: Migrated from 1m/15m to 15m/1h
    timeframes = {'15m': mt5.TIMEFRAME_M15, '1h': mt5.TIMEFRAME_H1}
    total_filled = 0
    
    for symbol_id, config in SYMBOL_DATABASES.items():
        db_path = config['db_path']
        config_symbol = config['symbol']
        
        # Auto-create database if it doesn't exist
        ensure_symbol_database(db_path)
        
        # Resolve the actual MT5 symbol (handles .sim suffix mismatch)
        symbol, selected = resolve_mt5_symbol(config_symbol)
        if not selected:
            print(f"\n  [{symbol_id}] ✗ MT5 symbol not found: tried '{config_symbol}' and variants")
            error = mt5.last_error()
            if error:
                print(f"    Last error: {error}")
            continue
        
        if symbol != config_symbol:
            print(f"\n  [{symbol_id}] Resolved '{config_symbol}' → '{symbol}'")
        
        print(f"\n  [{symbol_id}] {config['name']}")
        
        for tf_str, tf_mt5 in timeframes.items():
            current = get_db_record_count(db_path, tf_str)
            print(f"    [{tf_str}] {current:,} bars")
            
            if current < BACKFILL_MIN_BARS_THRESHOLD:
                print(f"    [{tf_str}] FULL backfill needed...")
                filled = full_backfill_timeframe(symbol, db_path, tf_str, tf_mt5, db_symbol=config_symbol)
                total_filled += filled
            else:
                # Get existing timestamps — try BOTH config_symbol and resolved symbol
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                existing = set()
                for sym_variant in set([config_symbol, symbol]):
                    cursor.execute("SELECT timestamp FROM core_15m WHERE symbol = ? AND timeframe = ?", (sym_variant, tf_str))
                    existing.update(row[0] for row in cursor.fetchall())
                conn.close()
                
                if not existing and current > 0:
                    # DB has records but symbol column doesn't match — diagnose
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT symbol FROM core_15m WHERE timeframe = ? LIMIT 5", (tf_str,))
                    db_symbols = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    print(f"    [{tf_str}] ⚠ Symbol mismatch! DB has: {db_symbols}, looking for: {config_symbol} or {symbol}")
                
                # Check for gaps using MT5 data
                rates = mt5.copy_rates_from_pos(symbol, tf_mt5, 0, 5000)
                if rates is not None:
                    missing = sum(1 for r in rates if datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S') not in existing)
                    
                    if missing > 0:
                        print(f"    [{tf_str}] {missing} gaps found")
                        filled = fill_gaps_only(symbol, db_path, tf_str, tf_mt5, existing, db_symbol=config_symbol)
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
def metatron(): return send_from_directory('templates', 'cytobase.html')

@app.route('/cytobase')
def cytobase(): return send_from_directory('templates', 'cytobase.html')

@app.route('/debug')
def debug_page(): return render_template('debug.html')

@app.route('/api/debug/health', methods=['GET'])
def api_debug_health():
    """Comprehensive system diagnostics for Mission Control."""
    import sqlite3 as _sql
    result = {
        'flask': True,
        'instance_db': instance_db is not None,
        'sentiment_engine': sentiment_scheduler is not None,
        'trader_routes': False,
        'endpoints': {},
        'databases': {},
        'errors': []
    }
    
    # Check trader routes
    try:
        from trader_routes import get_trader_manager
        tm = get_trader_manager()
        result['trader_routes'] = True
        status = tm.get_status()
        result['trader_manager'] = {
            'running_count': status.get('running_count', 0),
            'total_tracked': len(status.get('traders', {}))
        }
    except Exception as e:
        result['errors'].append(f'trader_routes: {e}')
    
    # Scan instance database
    if instance_db:
        try:
            all_inst = instance_db.get_all_instances()
            active_count = len(all_inst.get('active', []))
            archived_count = len(all_inst.get('archived', []))
            result['databases']['active_instances'] = active_count
            result['databases']['archived_instances'] = archived_count
            
            profiles = instance_db.get_all_profiles()
            result['databases']['active_profiles'] = len([p for p in profiles if p.status != 'ARCHIVED'])
            
            # Count sentiment tables
            try:
                conn = instance_db._get_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sentiment_%'")
                sentiment_tables = {}
                for row in cursor.fetchall():
                    tname = row[0]
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM [{tname}]")
                        sentiment_tables[tname] = cursor.fetchone()[0]
                    except:
                        sentiment_tables[tname] = -1
                result['databases']['sentiment_tables'] = sentiment_tables
            except Exception as e:
                result['errors'].append(f'sentiment scan: {e}')
        except Exception as e:
            result['errors'].append(f'instance_db scan: {e}')
    
    # List registered endpoints
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api/'):
            methods = sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')])
            result['endpoints'][rule.rule] = methods
    
    return jsonify(result)


@app.route('/api/debug/agents', methods=['GET'])
def api_debug_agents():
    """Seed 22: Agent framework diagnostics for Mission Control."""
    import json as _json

    result = {
        'framework_available': False,
        'config_available': False,
        'imports': {},
        'agent_roster': [],
        'profiles_with_agents': [],
        'latest_deliberations': [],
        'errors': []
    }

    # Check core imports
    try:
        from agent_framework import run_debate, build_memory_context
        result['framework_available'] = True
        result['imports']['agent_framework'] = True
    except ImportError as e:
        result['imports']['agent_framework'] = False
        result['errors'].append(f'agent_framework import: {e}')

    try:
        from agent_config import AGENT_ROSTER, MODE_PRESETS, DEFAULT_AGENT_CONFIG, resolve_agent_config
        result['config_available'] = True
        result['imports']['agent_config'] = True
        result['default_config'] = DEFAULT_AGENT_CONFIG
        result['mode_presets'] = {k: v.get('active_agents', []) for k, v in MODE_PRESETS.items()}
        result['agent_roster'] = [
            {'id': aid, 'role': info.get('role'), 'tier': info.get('tier'),
             'vectors': info.get('primary_vectors', [])}
            for aid, info in AGENT_ROSTER.items()
        ]
    except ImportError as e:
        result['imports']['agent_config'] = False
        result['errors'].append(f'agent_config import: {e}')

    # Check each agent module
    for mod_name, fn_name in [
        ('agents.technical_agent', 'run_technical_agent'),
        ('agents.bull_researcher', 'run_bull_researcher'),
        ('agents.bear_researcher', 'run_bear_researcher'),
        ('agents.risk_gate', 'run_risk_gate'),
        ('agents.key_levels_agent', 'run_key_levels_agent'),
        ('agents.momentum_agent', 'run_momentum_agent'),
        ('agents.sentiment_agent', 'run_sentiment_agent'),
        ('agents.news_agent', 'run_news_agent'),
    ]:
        try:
            __import__(mod_name, fromlist=[fn_name])
            result['imports'][mod_name] = True
        except ImportError:
            result['imports'][mod_name] = False

    # Profiles with agent config
    if instance_db:
        try:
            profiles = instance_db.get_all_profiles()
            for p in profiles:
                try:
                    tc = _json.loads(p.trading_config) if isinstance(p.trading_config, str) else (p.trading_config or {})
                except Exception:
                    tc = {}
                agent_cfg = tc.get('agents', {})
                if agent_cfg:
                    result['profiles_with_agents'].append({
                        'profile_id': p.id[:16],
                        'profile_name': p.name,
                        'enabled': agent_cfg.get('enabled', True),
                        'mode': agent_cfg.get('mode', 'budget'),
                        'timeout': agent_cfg.get('timeout_seconds', 15),
                        'debate_rounds': agent_cfg.get('debate_rounds', 1),
                        'markov': agent_cfg.get('include_markov_context', True),
                    })
        except Exception as e:
            result['errors'].append(f'profile scan: {e}')

        # Pull latest agent_deliberation from sentiment tables
        try:
            conn = instance_db._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sentiment_%'")
            tables = [row[0] for row in cursor.fetchall()]

            for tbl in tables[:10]:
                try:
                    cursor.execute(f'PRAGMA table_info({tbl})')
                    cols = [c[1] for c in cursor.fetchall()]
                    if 'agent_deliberation' not in cols:
                        continue

                    cursor.execute(f"""
                        SELECT timestamp, timeframe, source_type, processing_time_ms,
                               composite_score, consensus_score, signal_direction,
                               meets_threshold, agent_deliberation
                        FROM {tbl}
                        WHERE agent_deliberation IS NOT NULL AND agent_deliberation != ''
                        ORDER BY timestamp DESC LIMIT 3
                    """)
                    for row in cursor.fetchall():
                        delib = None
                        try:
                            delib = _json.loads(row[8]) if row[8] else None
                        except Exception:
                            delib = {'raw': str(row[8])[:200]}

                        entry = {
                            'table': tbl, 'timestamp': row[0], 'timeframe': row[1],
                            'source_type': row[2], 'processing_ms': row[3],
                            'composite': row[4], 'consensus': row[5],
                            'signal': row[6], 'met': bool(row[7]),
                        }
                        if delib and isinstance(delib, dict) and 'raw' not in delib:
                            entry['mode'] = delib.get('mode', '?')
                            entry['active_agents'] = delib.get('active_agents', [])
                            entry['timing'] = delib.get('timing', {})
                            entry['final_adjustments'] = delib.get('final_adjustments', {})
                            entry['analyst_consensus'] = delib.get('analyst_consensus', {})

                            bull = delib.get('bull_result', {})
                            bear = delib.get('bear_result', {})
                            risk = delib.get('risk_result', {})
                            entry['bull'] = {
                                'confidence': bull.get('confidence'),
                                'strongest': bull.get('strongest_vector'),
                                'flags': bull.get('flags', []),
                            }
                            entry['bear'] = {
                                'confidence': bear.get('confidence'),
                                'weakest': bear.get('weakest_vector'),
                                'flags': bear.get('flags', []),
                            }
                            entry['risk'] = {
                                'level': risk.get('overall_risk_level'),
                                'veto': risk.get('veto', False),
                                'multipliers': risk.get('multipliers', {}),
                                'flags': risk.get('flags', []),
                            }
                            analysts = delib.get('analyst_reports', [])
                            entry['analysts'] = [
                                {'id': a.get('agent_id'), 'confidence': a.get('confidence'),
                                 'flags': a.get('flags', []), 'adjustments': a.get('adjustments', {})}
                                for a in analysts
                            ]

                        result['latest_deliberations'].append(entry)
                except Exception as e:
                    result['errors'].append(f'{tbl}: {e}')

            conn.close()
        except Exception as e:
            result['errors'].append(f'deliberation scan: {e}')

    return jsonify(result)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/health')
def api_health():
    return jsonify({'status': 'healthy', 'active_symbol': ACTIVE_SYMBOL})

@app.route('/api/symbols')
def api_symbols():
    """List all symbols with record counts. SEED 13: Now shows 15m and 1h counts."""
    symbols = []
    for sym_id, config in SYMBOL_DATABASES.items():
        available = os.path.exists(config['db_path'])
        counts = get_symbol_record_counts(sym_id) if available else {}
        symbols.append({
            'id': config['id'], 'name': config['name'], 'symbol': config['symbol'],
            'available': available, 
            'records_15m': counts.get('records_15m', 0),
            'records_1h': counts.get('records_1h', 0)
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
    raw_symbol = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 300))
    
    # Resolve symbol through robust lookup (handles .sim suffix, tr_ prefix, case)
    symbol_id, config = resolve_symbol_id(raw_symbol)
    if not config:
        # Only fall back to active symbol if the raw input was empty or a tr_ ID
        if not raw_symbol or raw_symbol.startswith('tr_'):
            symbol_id, config = resolve_symbol_id(ACTIVE_SYMBOL)
        if not config:
            return jsonify({'success': False, 'error': f'Unknown symbol: {raw_symbol}'}), 404
    
    conn, error = get_symbol_db_connection(symbol_id)
    if conn is None: 
        return jsonify({'success': False, 'error': error}), 404
    try:
        cursor = conn.cursor()
        symbol_name = config['symbol']
        cursor.execute("SELECT timestamp, open, high, low, close, volume FROM core_15m WHERE timeframe = ? AND symbol = ? ORDER BY timestamp DESC LIMIT ?", (timeframe, symbol_name, limit))
        data = [dict(row) for row in reversed(cursor.fetchall())]
        conn.close()
        return jsonify({'success': True, 'symbol': config['symbol'], 'data': data})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/basic')
def api_basic():
    raw_symbol = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '1m')
    limit = int(request.args.get('limit', 300))
    
    symbol_id, config = resolve_symbol_id(raw_symbol)
    if not config:
        symbol_id, config = resolve_symbol_id(ACTIVE_SYMBOL)
    if not config:
        return jsonify({'success': False, 'error': f'Unknown symbol: {raw_symbol}'}), 404
    
    symbol_name = config['symbol']
    conn, error = get_symbol_db_connection(symbol_id)
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
    raw_symbol = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 300))
    
    symbol_id, config = resolve_symbol_id(raw_symbol)
    if not config:
        symbol_id, config = resolve_symbol_id(ACTIVE_SYMBOL)
    if not config:
        return jsonify({'success': False, 'error': f'Unknown symbol: {raw_symbol}'}), 404
    
    symbol_name = config['symbol']
    conn, error = get_symbol_db_connection(symbol_id)
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
    raw_symbol = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 300))
    
    symbol_id, config = resolve_symbol_id(raw_symbol)
    if not config:
        symbol_id, config = resolve_symbol_id(ACTIVE_SYMBOL)
    if not config:
        return jsonify({'success': False, 'error': f'Unknown symbol: {raw_symbol}'}), 404
    
    symbol_name = config['symbol']
    conn, error = get_symbol_db_connection(symbol_id)
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
    raw_symbol = request.args.get('symbol', ACTIVE_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 300))
    
    symbol_id, config = resolve_symbol_id(raw_symbol)
    if not config:
        symbol_id, config = resolve_symbol_id(ACTIVE_SYMBOL)
    if not config:
        return jsonify({'success': False, 'error': f'Unknown symbol: {raw_symbol}'}), 404
    
    symbol_name = config['symbol']
    conn, error = get_symbol_db_connection(symbol_id)
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
def api_profiles_legacy():
    """Legacy route — queries per-symbol DB. Kept for backward compat."""
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


# ============================================================================
# PROFILE CRUD API (Persistent profiles in apex_instances.db)
# ============================================================================

@app.route('/api/profile/list', methods=['GET'])
def api_profile_list():
    """Get all profiles. Optional ?symbol= filter."""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    symbol = request.args.get('symbol')
    try:
        if symbol:
            profiles = instance_db.get_profiles_by_symbol(symbol)
        else:
            profiles = instance_db.get_all_profiles()
        
        return jsonify({
            "success": True,
            "profiles": [asdict(p) for p in profiles]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/profile/<profile_id>', methods=['GET'])
def api_profile_get(profile_id):
    """Get a single profile by ID."""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    profile = instance_db.get_profile(profile_id)
    if not profile:
        return jsonify({"success": False, "error": "Profile not found"}), 404
    
    return jsonify({"success": True, "profile": asdict(profile)})


@app.route('/api/profile/create', methods=['POST'])
def api_profile_create():
    """Create a new profile."""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    data = request.get_json() or {}
    name = data.get('name', 'New Profile')
    symbol = data.get('symbol', 'XAUJ26')
    
    kwargs = {}
    for field in ['provider', 'image_path', 'trading_config',
                  'sentiment_model', 'sentiment_weights',
                  'sentiment_threshold', 'position_sizing', 'risk_config',
                  'entry_rules', 'exit_rules']:
        if field in data:
            val = data[field]
            # JSON-encode dicts/lists for TEXT columns
            kwargs[field] = json.dumps(val) if isinstance(val, (dict, list)) else val
    
    # Auto-populate default trading_config if not provided
    if 'trading_config' not in kwargs:
        from instance_database import InstanceDatabaseManager
        kwargs['trading_config'] = json.dumps(InstanceDatabaseManager.DEFAULT_TRADING_CONFIG)
    
    try:
        profile = instance_db.create_profile(name=name, symbol=symbol, **kwargs)
        return jsonify({"success": True, "profile": asdict(profile)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/profile/<profile_id>', methods=['PUT', 'PATCH'])
def api_profile_update(profile_id):
    """Update an existing profile."""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    data = request.get_json() or {}
    
    # JSON-encode any dict/list values before passing to update
    updates = {}
    for k, v in data.items():
        if isinstance(v, (dict, list)):
            updates[k] = json.dumps(v)
        else:
            updates[k] = v
    
    try:
        profile = instance_db.update_profile(profile_id, updates)
        if not profile:
            return jsonify({"success": False, "error": "Profile not found"}), 404
        return jsonify({"success": True, "profile": asdict(profile)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/profile/<profile_id>', methods=['DELETE'])
def api_profile_delete(profile_id):
    """Delete a profile."""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    try:
        deleted = instance_db.delete_profile(profile_id)
        if not deleted:
            return jsonify({"success": False, "error": "Profile not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
# INSTANCE API ROUTES (migrated from flask_apex.py)
# ============================================================================

@app.route('/api/instances', methods=['GET'])
def api_get_instances():
    """Get all instances, optionally filtered by symbol"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    symbol = request.args.get('symbol')
    
    if symbol:
        grouped = instance_db.get_instances_by_symbol(symbol)
    else:
        grouped = instance_db.get_all_instances()
    
    return jsonify({
        "success": True, 
        "instances": {
            "active": [asdict(i) for i in grouped["active"]],
            "archived": [asdict(i) for i in grouped["archived"]]
        }
    })


@app.route('/api/instances', methods=['POST'])
def api_create_instance():
    """Create a new algorithm instance with all tables"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    data = request.get_json() or {}
    symbol = data.get('symbol', 'XAUJ26').upper()
    display_name = data.get('display_name')
    account_type = data.get('account_type', 'SIM')
    profile_id = data.get('profile_id')
    
    try:
        instance = instance_db.create_instance(
            symbol=symbol,
            display_name=display_name,
            account_type=account_type,
            profile_id=profile_id
        )
        return jsonify({"success": True, "instance": asdict(instance)})
    except Exception as e:
        print(f"Failed to create instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/instances/<instance_id>', methods=['GET'])
def api_get_instance(instance_id):
    """Get a single instance by ID"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    instance = instance_db.get_instance(instance_id)
    if not instance:
        return jsonify({"success": False, "error": "Instance not found"}), 404
    return jsonify({"success": True, "instance": asdict(instance)})


@app.route('/api/instances/<instance_id>/archive', methods=['POST'])
def api_archive_instance(instance_id):
    """Archive an instance (move to archived section)"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    success = instance_db.archive_instance(instance_id)
    return jsonify({"success": success})


@app.route('/api/instances/<instance_id>/restore', methods=['POST'])
def api_restore_instance(instance_id):
    """Restore an archived instance"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    success = instance_db.restore_instance(instance_id)
    return jsonify({"success": success})


def normalize_symbol(raw_symbol):
    """Strip .SIM/.sim suffix and normalize to base symbol.
    XAUJ26.SIM → XAUJ26, btcf26.sim → BTCF26, XAUJ26 → XAUJ26"""
    s = raw_symbol.strip().upper()
    if s.endswith('.SIM'):
        s = s[:-4]
    return s


@app.route('/api/instance/<instance_id>/initialize', methods=['POST'])
def api_initialize_instance(instance_id):
    """
    Initialize database tables for a localStorage algorithm instance.
    Called when user selects an algorithm in the Instance Browser.
    
    Seed 20: Symbol Alignment — normalizes .SIM suffix and reuses existing
    instances for the same symbol to prevent orphan duplicates.
    """
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    data = request.get_json() or {}
    raw_symbol = data.get('symbol', 'UNKNOWN').upper()
    symbol = normalize_symbol(raw_symbol)
    display_name = data.get('name', f'{symbol} Algorithm')
    
    try:
        # 1. Check if THIS exact instance_id already exists
        existing = instance_db.get_instance(instance_id)
        if existing:
            return jsonify({
                "success": True,
                "message": "Instance already initialized",
                "instance_id": instance_id,
                "tables_created": []
            })
        
        # 2. Check if an active instance for this symbol already exists (from a previous session)
        #    Reuse it instead of creating an orphan duplicate.
        #    Prefer instances with a linked profile (trader instances) over empty ones.
        all_instances = instance_db.get_all_instances()
        candidates = []
        for inst in all_instances.get('active', []):
            inst_symbol = normalize_symbol(inst.symbol)
            if inst_symbol == symbol and inst.id != instance_id:
                candidates.append(inst)
        
        if candidates:
            # Prefer instance with a profile_id (= has been used with trader)
            best = next((c for c in candidates if c.profile_id and c.profile_id.strip()), candidates[0])
            print(f"[APEX] Reusing existing instance {best.id} for {symbol} (frontend asked for {instance_id})")
            return jsonify({
                "success": True,
                "message": "Reusing existing instance for this symbol",
                "instance_id": best.id,
                "reused": True,
                "tables_created": []
            })
        
        # 3. No existing instance — create new one with normalized symbol
        instance = instance_db.register_instance(
            instance_id=instance_id,
            symbol=symbol,
            display_name=display_name,
            account_type='SIM'
        )
        
        safe_id = instance_id.replace("-", "_").replace(".", "_").lower()
        
        print(f"[APEX] Initialized instance tables for: {instance_id} ({symbol})")
        
        return jsonify({
            "success": True,
            "message": "Instance tables created",
            "instance_id": instance.id,
            "tables_created": [
                f"positions_{safe_id}",
                f"sentiment_{safe_id}",
                f"state_transitions_{safe_id}",
                f"markov_matrices_{safe_id}"
            ]
        })
        
    except Exception as e:
        print(f"Failed to initialize instance {instance_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/instance/<instance_id>/positions', methods=['GET'])
def api_get_positions(instance_id):
    """Get positions for an instance"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    limit = int(request.args.get('limit', 50))
    positions = instance_db.get_position_history(instance_id, limit=limit)
    return jsonify({"success": True, "data": positions})


@app.route('/api/instance/<instance_id>/sentiments', methods=['GET'])
def api_get_sentiments(instance_id):
    """Get sentiment readings for an instance"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 50))
    readings = instance_db.get_sentiment_history(instance_id, timeframe, limit=limit)
    return jsonify({"success": True, "data": readings})


@app.route('/api/instance/<instance_id>/transitions', methods=['GET'])
def api_get_transitions(instance_id):
    """Get state transitions for an instance"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 50))
    transitions = instance_db.get_state_transitions(instance_id, timeframe, limit=limit)
    return jsonify({"success": True, "data": transitions})


@app.route('/api/instance/<instance_id>/matrices', methods=['GET'])
def api_get_matrices(instance_id):
    """Get Markov matrices for an instance"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    matrices = []
    for tf in ['15m', '1h']:  # SEED 13: Changed from 1m/15m to 15m/1h
        matrix = instance_db.get_markov_matrix(instance_id, tf)
        if matrix:
            matrices.append(matrix)
    return jsonify({"success": True, "data": matrices})


# ============================================================================
# SEED 10D: DUAL-TIMEFRAME SENTIMENT ROUTES & LIVE POSITION SYNC
# ============================================================================

# Lazy-load sync manager
_sync_manager = None

def get_sync_manager():
    """Get or create the position sync manager"""
    global _sync_manager
    if _sync_manager is None:
        try:
            from mt5_live_position_sync import PositionSyncManager
            if instance_db:
                _sync_manager = PositionSyncManager(instance_db)
                print("\u2713 Position sync manager initialized")
        except ImportError as e:
            print(f"\u26a0\ufe0f Position sync not available: {e}")
    return _sync_manager


@app.route('/api/instance/<instance_id>/sentiments/<timeframe>', methods=['GET'])
def api_get_sentiments_by_timeframe(instance_id, timeframe):
    """
    SEED 10D: Get sentiments for a specific timeframe.
    Supports 15m and 1h tabs in the Instance Browser.
    """
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    # Validate timeframe
    if timeframe not in ['15m', '1h']:
        return jsonify({"success": False, "error": f"Invalid timeframe: {timeframe}"}), 400
    
    limit = int(request.args.get('limit', 50))
    
    try:
        sentiments = instance_db.get_sentiment_history(instance_id, timeframe, limit=limit)
        return jsonify({
            "success": True, 
            "timeframe": timeframe,
            "data": sentiments,
            "count": len(sentiments)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/instance/<instance_id>/sentiments/latest', methods=['GET'])
def api_get_latest_sentiments(instance_id):
    """
    SEED 10D: Get the latest sentiment reading for BOTH timeframes.
    Useful for dashboard widgets that need to show current state.
    """
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    try:
        latest_15m = instance_db.get_latest_sentiment(instance_id, '15m')
        latest_1h = instance_db.get_latest_sentiment(instance_id, '1h')
        
        return jsonify({
            "success": True,
            "15m": latest_15m,
            "1h": latest_1h
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/instance/<instance_id>/positions/live', methods=['GET'])
def api_get_live_positions(instance_id):
    """
    SEED 10D: Get positions with MT5 sync status.
    Returns positions with real-time P&L and sync indicators.
    """
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    limit = int(request.args.get('limit', 50))
    
    try:
        # Get positions with sync status
        positions = instance_db.get_positions_with_sync_status(instance_id, limit=limit)
        
        # Get sync status
        sync_manager = get_sync_manager()
        sync_status = None
        if sync_manager:
            sync_status = sync_manager.get_sync_status(instance_id)
        
        return jsonify({
            "success": True,
            "sync_active": sync_status.get('running', False) if sync_status else False,
            "last_sync": sync_status.get('last_sync') if sync_status else None,
            "positions": positions,
            "count": len(positions)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/instance/<instance_id>/sync/status', methods=['GET'])
def api_get_sync_status(instance_id):
    """
    SEED 10D: Get the current sync status for an instance.
    Used by frontend to show live/offline indicator.
    """
    sync_manager = get_sync_manager()
    
    if not sync_manager:
        return jsonify({
            "success": True,
            "data": {
                "running": False,
                "error": "Sync manager not available"
            }
        })
    
    status = sync_manager.get_sync_status(instance_id)
    
    return jsonify({
        "success": True,
        "data": status or {"running": False}
    })


@app.route('/api/instance/<instance_id>/sync/start', methods=['POST'])
def api_start_sync(instance_id):
    """
    SEED 10D: Start MT5 position sync for an instance.
    Requires symbol in request body.
    """
    sync_manager = get_sync_manager()
    
    if not sync_manager:
        return jsonify({
            "success": False, 
            "error": "Position sync not available (MT5 library not installed)"
        }), 503
    
    data = request.get_json() or {}
    symbol = data.get('symbol')
    
    if not symbol:
        # Try to get symbol from instance
        if instance_db:
            instance = instance_db.get_instance(instance_id)
            if instance:
                symbol = instance.symbol
    
    if not symbol:
        return jsonify({"success": False, "error": "Symbol required"}), 400
    
    try:
        success = sync_manager.start_sync(instance_id, symbol)
        return jsonify({
            "success": success,
            "message": f"Sync started for {symbol}" if success else "Failed to start sync"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/instance/<instance_id>/sync/stop', methods=['POST'])
def api_stop_sync(instance_id):
    """
    SEED 10D: Stop MT5 position sync for an instance.
    """
    sync_manager = get_sync_manager()
    
    if not sync_manager:
        return jsonify({"success": False, "error": "Sync manager not available"}), 503
    
    try:
        success = sync_manager.stop_sync(instance_id)
        return jsonify({
            "success": success,
            "message": "Sync stopped" if success else "No active sync to stop"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sync/all', methods=['GET'])
def api_get_all_sync_statuses():
    """
    SEED 10D: Get sync status for all active instances.
    Useful for showing which instances have live data.
    """
    sync_manager = get_sync_manager()
    
    if not sync_manager:
        return jsonify({"success": True, "data": []})
    
    statuses = sync_manager.get_all_sync_statuses()
    return jsonify({"success": True, "data": statuses})


# ============================================================================
# PROFILE API (migrated from flask_apex.py)
# ============================================================================

@app.route('/api/profile/upload-image', methods=['POST'])
def api_upload_profile_image():
    """
    Upload a profile image.
    Saves to static/img/profiles/ directory.
    """
    import re
    from werkzeug.utils import secure_filename
    
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image file provided"})
    
    file = request.files['image']
    profile_id = request.form.get('profile_id', 'unknown')
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"})
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"success": False, "error": f"Invalid file type: {ext}"})
    
    # Validate file size (2MB max)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to start
    if size > 2 * 1024 * 1024:
        return jsonify({"success": False, "error": "File too large (max 2MB)"})
    
    # Create directory if it doesn't exist
    upload_dir = os.path.join(BASE_DIR, 'static', 'img', 'profiles')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate safe filename
    safe_profile_id = re.sub(r'[^a-zA-Z0-9_-]', '', profile_id)
    timestamp = int(time.time())
    filename = f"{safe_profile_id}_{timestamp}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    try:
        file.save(filepath)
        # Return the URL path (not filesystem path)
        image_path = f"/static/img/profiles/{filename}"
        print(f"[PROFILE] Image saved: {filepath}")
        return jsonify({"success": True, "imagePath": image_path})
    except Exception as e:
        print(f"[PROFILE] Image upload failed: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/profile/test', methods=['POST'])
def api_test_profile_connection():
    """
    Test API connection for a profile.
    Supports Anthropic, Google (Gemini), and OpenAI.
    """
    data = request.get_json() or {}
    provider = data.get('provider', 'google')
    api_key = data.get('apiKey', '')
    model = data.get('model', '')
    
    if not api_key:
        return jsonify({"success": False, "error": "No API key provided"})
    
    start_time = time.time()
    
    try:
        if provider == 'anthropic':
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model or "claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'connected' in one word."}]
            )
            latency = int((time.time() - start_time) * 1000)
            return jsonify({"success": True, "latency": latency, "provider": "Anthropic"})
            
        elif provider == 'google':
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            gen_model = genai.GenerativeModel(model or 'gemini-2.0-flash')
            response = gen_model.generate_content("Say 'connected' in one word.")
            latency = int((time.time() - start_time) * 1000)
            return jsonify({"success": True, "latency": latency, "provider": "Google"})
            
        elif provider == 'openai':
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'connected' in one word."}]
            )
            latency = int((time.time() - start_time) * 1000)
            return jsonify({"success": True, "latency": latency, "provider": "OpenAI"})
            
        else:
            return jsonify({"success": False, "error": f"Unknown provider: {provider}"})
            
    except ImportError as e:
        return jsonify({"success": False, "error": f"Missing library: {str(e)}"})
    except Exception as e:
        error_msg = str(e)
        if "invalid api key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Invalid API key"
        elif "rate limit" in error_msg.lower():
            error_msg = "Rate limited - try again later"
        elif "quota" in error_msg.lower():
            error_msg = "API quota exceeded"
        return jsonify({"success": False, "error": error_msg})


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

def startup():
    """
    SEED 13: The Great Migration
    - Now collecting 15m and 1h data (abandoned 1m)
    - Collectors use 2-bar snapshot for gap-free data
    """
    print("\n" + "="*70)
    print("MT5 META AGENT V11.4 - STARTUP (15m/1h Migration)")
    print("="*70)
    
    run_backfill_check()
    
    print("\n[STARTUP] Starting collectors (15m + 1h)...")
    for symbol_id, config in SYMBOL_DATABASES.items():
        ensure_symbol_database(config['db_path'])
        if os.path.exists(config['db_path']):
            # Resolve MT5 symbol (same logic as backfill)
            mt5_symbol = config['symbol']
            if MT5_AVAILABLE and mt5.initialize():
                resolved, ok = resolve_mt5_symbol(config['symbol'])
                if ok:
                    mt5_symbol = resolved
                    if resolved != config['symbol']:
                        print(f"  [{symbol_id}] Collector using resolved symbol: {resolved}")
            
            # SEED 13: Explicitly pass 15m/1h timeframes
            collector = MT5AdvancedCollector(
                symbol=mt5_symbol, 
                db_path=config['db_path'],
                timeframes=['15m', '1h']  # New timeframe config
            )
            if collector.connect_mt5():
                thread = threading.Thread(target=collector.run, daemon=True)
                thread.start()
                collector_threads[symbol_id] = {'collector': collector, 'thread': thread}
                print(f"  ✓ {symbol_id} collector running (15m, 1h) [{mt5_symbol}]")
            else:
                print(f"  ✗ {symbol_id} MT5 failed for '{mt5_symbol}'")

    # Start sentiment scheduler if available
    if sentiment_scheduler:
        sentiment_scheduler.start()
        print("  ✓ Sentiment scheduler started")
    
    print("\n" + "="*70)
    print("FLASK SERVER: http://localhost:5000/")
    print("="*70)

def shutdown():
    print("\nShutting down...")
    
    # Stop sentiment scheduler
    if sentiment_scheduler:
        sentiment_scheduler.stop()
        print("  ✓ Sentiment scheduler stopped")
    
    # Stop collectors
    for data in collector_threads.values():
        data['collector'].running = False
    print("  ✓ Collectors stopped")
    
    time.sleep(1)

atexit.register(shutdown)

if __name__ == '__main__':
    startup()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
