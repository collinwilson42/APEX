"""
V6 Intelligence Database - Unified Webhook Server
Receives TradingView alerts and Pine Logs bulk imports
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import threading
import os

app = Flask(__name__)

# Super permissive CORS - allows everything
CORS(app, 
     resources={r"/*": {
         "origins": "*",
         "methods": ["GET", "POST", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization"],
         "supports_credentials": True
     }})

# Add OPTIONS handler for preflight
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# Database configuration
DB_PATH = 'v6_intelligence.db'
DB_LOCK = threading.Lock()

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_database():
    """Initialize SQLite database with new schema matching Google Sheet template"""
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create 15m baseline table (updated schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bulk_analysis_15m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL UNIQUE,
                symbol TEXT DEFAULT 'MGC',
                
                -- CORE OHLCV
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                
                -- TRADINGVIEW PERFORMANCE
                tv_trades INTEGER,
                tv_wr REAL,
                tv_pf REAL,
                tv_netprofit REAL,
                
                -- SUPERTREND
                st_entry REAL,
                st_exit REAL,
                st_dir TEXT,
                st_dist REAL,
                bars_since_st INTEGER,
                
                -- EMA MOMENTUM
                ema_short REAL,
                ema_medium REAL,
                ema_align TEXT,
                ema_align_bars INTEGER,
                ema_align_strength REAL,
                ema_dist REAL,
                ema_mult REAL,
                
                -- RSI SYSTEM
                rsi REAL,
                rsi_ob INTEGER,
                rsi_os INTEGER,
                rsi_bull_div INTEGER,
                rsi_bear_div INTEGER,
                rsi_div_strength REAL,
                
                -- BULLISH SPIKE
                spike_bull_tier TEXT,
                bull_quality REAL,
                bull_magnitude REAL,
                bull_consistency REAL,
                bull_acceleration REAL,
                bull_vol_conf REAL,
                
                -- BEARISH SPIKE
                spike_bear_tier TEXT,
                bear_quality REAL,
                bear_consistency REAL,
                
                -- ATR VOLATILITY
                atr REAL,
                atr_zone TEXT,
                atr_50_avg REAL,
                atr_ratio REAL,
                atr_expanding INTEGER,
                
                -- PRICE VELOCITY
                velocity_change REAL,
                velocity_lookback INTEGER,
                accelerating INTEGER,
                
                -- FIBONACCI
                fib_zone INTEGER,
                fib_mult REAL,
                golden_zone INTEGER,
                fib_high REAL,
                fib_low REAL,
                
                -- ATH DISTANCE
                ath_value REAL,
                ath_dist REAL,
                ath_mult REAL,
                
                -- MARKET CONTEXT
                session TEXT,
                dow TEXT,
                session_mult REAL,
                dow_mult REAL,
                
                -- SPIKE QUALITY MOMENTUM
                sqm_pct REAL,
                sqm_mult REAL,
                sqm_lookback INTEGER,
                
                -- FINAL MULTIPLIERS
                total_mult REAL,
                min_threshold REAL,
                pending_exit_mult REAL,
                lb24_mult REAL,
                lb48_mult REAL,
                
                -- ADDITIONAL CONTEXT
                consol_bars INTEGER,
                range_breakout INTEGER,
                range_width REAL,
                vol_div TEXT,
                vol_div_strength REAL,
                vol_surge INTEGER,
                
                -- METADATA
                received_at TEXT DEFAULT CURRENT_TIMESTAMP,
                data_source TEXT DEFAULT 'pine_logs'
            )
        ''')
        
        # Create index on timestamp for fast queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON bulk_analysis_15m(timestamp DESC)
        ''')
        
        # Create 1m recalibration table (for future use)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recalibration_1m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL UNIQUE,
                symbol TEXT DEFAULT 'MGC',
                close REAL,
                ema_short REAL,
                ema_medium REAL,
                ema_alignment TEXT,
                distance_to_st_entry REAL,
                short_medium_distance REAL,
                short_medium_multiplier REAL,
                atr_14 REAL,
                atr_zone TEXT,
                atr_ratio REAL,
                fibonacci_zone INTEGER,
                fibonacci_multiplier REAL,
                rsi_14 REAL,
                rsi_overbought INTEGER,
                rsi_oversold INTEGER,
                spike_bull_quality_score REAL,
                spike_bull_consistency REAL,
                spike_bear_quality_score REAL,
                spike_bear_consistency REAL,
                price_velocity_pct REAL,
                velocity_accelerating INTEGER,
                volume_surge_active INTEGER,
                volume_surge_ratio REAL,
                range_breakout_active INTEGER,
                range_width_pct REAL,
                total_multiplier REAL,
                received_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"[DB] Initialized database: {DB_PATH}")

# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.route('/webhook/15m', methods=['POST'])
def webhook_15m():
    """
    Receive 15-minute full analysis alerts from TradingView
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data or 'timestamp' not in data:
            return jsonify({'status': 'error', 'message': 'Missing timestamp'}), 400
        
        # Insert into database
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO bulk_analysis_15m (
                    timestamp, symbol, open, high, low, close, volume,
                    tv_trades, tv_wr, tv_pf, tv_netprofit,
                    st_entry, st_exit, st_dir, st_dist, bars_since_st,
                    ema_short, ema_medium, ema_align, ema_align_bars, ema_align_strength, ema_dist, ema_mult,
                    rsi, rsi_ob, rsi_os, rsi_bull_div, rsi_bear_div, rsi_div_strength,
                    spike_bull_tier, bull_quality, bull_magnitude, bull_consistency, bull_acceleration, bull_vol_conf,
                    spike_bear_tier, bear_quality, bear_consistency,
                    atr, atr_zone, atr_50_avg, atr_ratio, atr_expanding,
                    velocity_change, velocity_lookback, accelerating,
                    fib_zone, fib_mult, golden_zone, fib_high, fib_low,
                    ath_value, ath_dist, ath_mult,
                    session, dow, session_mult, dow_mult,
                    sqm_pct, sqm_mult, sqm_lookback,
                    total_mult, min_threshold, pending_exit_mult, lb24_mult, lb48_mult,
                    consol_bars, range_breakout, range_width,
                    vol_div, vol_div_strength, vol_surge,
                    data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('symbol', 'MGC'),
                data.get('open'),
                data.get('high'),
                data.get('low'),
                data.get('close'),
                data.get('volume'),
                data.get('tv_trades'),
                data.get('tv_wr'),
                data.get('tv_pf'),
                data.get('tv_netprofit'),
                data.get('st_entry_line'),
                data.get('st_exit_line'),
                data.get('st_direction'),
                data.get('distance_to_entry'),
                data.get('bars_since_st_cross'),
                data.get('ema_short'),
                data.get('ema_medium'),
                data.get('ema_alignment'),
                data.get('ema_alignment_bars'),
                data.get('ema_alignment_strength'),
                data.get('short_medium_distance'),
                data.get('short_medium_multiplier'),
                data.get('rsi_14'),
                data.get('rsi_overbought', 0),
                data.get('rsi_oversold', 0),
                data.get('rsi_bull_divergence', 0),
                data.get('rsi_bear_divergence', 0),
                data.get('rsi_divergence_strength'),
                data.get('spike_bull_tier'),
                data.get('spike_bull_quality_score'),
                data.get('spike_bull_magnitude'),
                data.get('spike_bull_consistency'),
                data.get('spike_bull_acceleration'),
                data.get('spike_bull_volume_conf'),
                data.get('spike_bear_tier'),
                data.get('spike_bear_quality_score'),
                data.get('spike_bear_consistency'),
                data.get('atr_14'),
                data.get('atr_zone'),
                data.get('atr_50_avg'),
                data.get('atr_ratio'),
                data.get('atr_expanding', 0),
                data.get('price_velocity_pct'),
                data.get('velocity_lookback'),
                data.get('velocity_accelerating', 0),
                data.get('fibonacci_zone'),
                data.get('fibonacci_multiplier'),
                data.get('in_golden_zone', 0),
                data.get('fib_pivot_high'),
                data.get('fib_pivot_low'),
                data.get('ath_value'),
                data.get('ath_distance_pct'),
                data.get('ath_multiplier'),
                data.get('session'),
                data.get('day_of_week'),
                data.get('session_multiplier'),
                data.get('dow_multiplier'),
                data.get('sqm_quality_pct'),
                data.get('sqm_multiplier'),
                data.get('sqm_optimal_lookback'),
                data.get('total_multiplier'),
                data.get('minimum_threshold'),
                data.get('pending_exit_mult'),
                data.get('lb24_mult'),
                data.get('lb48_mult'),
                data.get('consol_bars'),
                data.get('range_breakout', 0),
                data.get('range_width'),
                data.get('volume_divergence'),
                data.get('volume_div_strength'),
                data.get('volume_surge_active', 0),
                'webhook'
            ))
            
            conn.commit()
            conn.close()
        
        return jsonify({'status': 'success', 'timestamp': data.get('timestamp')}), 200
        
    except Exception as e:
        print(f"[ERROR] 15m webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook/1m', methods=['POST'])
def webhook_1m():
    """
    Receive 1-minute recalibration alerts from TradingView
    """
    try:
        data = request.json
        
        if not data or 'timestamp' not in data:
            return jsonify({'status': 'error', 'message': 'Missing timestamp'}), 400
        
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO recalibration_1m (
                    timestamp, symbol, close, ema_short, ema_medium, ema_alignment,
                    distance_to_st_entry, short_medium_distance, short_medium_multiplier,
                    atr_14, atr_zone, atr_ratio, fibonacci_zone, fibonacci_multiplier,
                    rsi_14, rsi_overbought, rsi_oversold,
                    spike_bull_quality_score, spike_bull_consistency,
                    spike_bear_quality_score, spike_bear_consistency,
                    price_velocity_pct, velocity_accelerating,
                    volume_surge_active, volume_surge_ratio,
                    range_breakout_active, range_width_pct,
                    total_multiplier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('symbol', 'MGC'),
                data.get('close'),
                data.get('ema_short'),
                data.get('ema_medium'),
                data.get('ema_alignment'),
                data.get('distance_to_entry'),
                data.get('short_medium_distance'),
                data.get('short_medium_multiplier'),
                data.get('atr_14'),
                data.get('atr_zone'),
                data.get('atr_ratio'),
                data.get('fibonacci_zone'),
                data.get('fibonacci_multiplier'),
                data.get('rsi_14'),
                data.get('rsi_overbought', 0),
                data.get('rsi_oversold', 0),
                data.get('spike_bull_quality_score'),
                data.get('spike_bull_consistency'),
                data.get('spike_bear_quality_score'),
                data.get('spike_bear_consistency'),
                data.get('price_velocity_pct'),
                data.get('velocity_accelerating', 0),
                data.get('volume_surge_active', 0),
                data.get('volume_surge_ratio'),
                data.get('range_breakout_active', 0),
                data.get('range_width_pct'),
                data.get('total_multiplier')
            ))
            
            conn.commit()
            conn.close()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"[ERROR] 1m webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/bulk-import', methods=['POST'])
def bulk_import():
    """
    Bulk import Pine Logs data from Tampermonkey script
    Accepts array of parsed CSV records
    """
    try:
        data = request.json
        records = data.get('records', [])
        
        if not records:
            return jsonify({'status': 'error', 'message': 'No records provided'}), 400
        
        success_count = 0
        error_count = 0
        
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            for record in records:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO bulk_analysis_15m (
                            timestamp, symbol, open, high, low, close, volume,
                            tv_trades, tv_wr, tv_pf, tv_netprofit,
                            st_entry, st_exit, st_dir, st_dist, bars_since_st,
                            ema_short, ema_medium, ema_align, ema_align_bars, ema_align_strength, ema_dist, ema_mult,
                            rsi, rsi_ob, rsi_os, rsi_bull_div, rsi_bear_div, rsi_div_strength,
                            spike_bull_tier, bull_quality, bull_magnitude, bull_consistency, bull_acceleration, bull_vol_conf,
                            spike_bear_tier, bear_quality, bear_consistency,
                            atr, atr_zone, atr_50_avg, atr_ratio, atr_expanding,
                            velocity_change, velocity_lookback, accelerating,
                            fib_zone, fib_mult, golden_zone, fib_high, fib_low,
                            ath_value, ath_dist, ath_mult,
                            session, dow, session_mult, dow_mult,
                            sqm_pct, sqm_mult, sqm_lookback,
                            total_mult, min_threshold, pending_exit_mult, lb24_mult, lb48_mult,
                            consol_bars, range_breakout, range_width,
                            vol_div, vol_div_strength, vol_surge,
                            data_source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record.get('timestamp'),
                        record.get('symbol', 'MGC'),
                        record.get('open'),
                        record.get('high'),
                        record.get('low'),
                        record.get('close'),
                        record.get('volume'),
                        record.get('tv_trades'),
                        record.get('tv_wr'),
                        record.get('tv_pf'),
                        record.get('tv_netprofit'),
                        record.get('st_entry'),
                        record.get('st_exit'),
                        record.get('st_dir'),
                        record.get('st_dist'),
                        record.get('bars_since_st'),
                        record.get('ema_short'),
                        record.get('ema_medium'),
                        record.get('ema_align'),
                        record.get('ema_align_bars'),
                        record.get('ema_align_strength'),
                        record.get('ema_dist'),
                        record.get('ema_mult'),
                        record.get('rsi'),
                        1 if record.get('rsi_ob') else 0,
                        1 if record.get('rsi_os') else 0,
                        1 if record.get('rsi_bull_div') else 0,
                        1 if record.get('rsi_bear_div') else 0,
                        record.get('rsi_div_strength'),
                        record.get('spike_bull_tier'),
                        record.get('bull_quality'),
                        record.get('bull_magnitude'),
                        record.get('bull_consistency'),
                        record.get('bull_acceleration'),
                        record.get('bull_vol_conf'),
                        record.get('spike_bear_tier'),
                        record.get('bear_quality'),
                        record.get('bear_consistency'),
                        record.get('atr'),
                        record.get('atr_zone'),
                        record.get('atr_50_avg'),
                        record.get('atr_ratio'),
                        1 if record.get('atr_expanding') else 0,
                        record.get('velocity_change'),
                        record.get('velocity_lookback'),
                        1 if record.get('accelerating') else 0,
                        record.get('fib_zone'),
                        record.get('fib_mult'),
                        1 if record.get('golden_zone') else 0,
                        record.get('fib_high'),
                        record.get('fib_low'),
                        record.get('ath_value'),
                        record.get('ath_dist'),
                        record.get('ath_mult'),
                        record.get('session'),
                        record.get('dow'),
                        record.get('session_mult'),
                        record.get('dow_mult'),
                        record.get('sqm_pct'),
                        record.get('sqm_mult'),
                        record.get('sqm_lookback'),
                        record.get('total_mult'),
                        record.get('min_threshold'),
                        record.get('pending_exit_mult'),
                        record.get('lb24_mult'),
                        record.get('lb48_mult'),
                        record.get('consol_bars'),
                        1 if record.get('range_breakout') else 0,
                        record.get('range_width'),
                        record.get('vol_div'),
                        record.get('vol_div_strength'),
                        1 if record.get('vol_surge') else 0,
                        'pine_logs'
                    ))
                    success_count += 1
                except Exception as e:
                    print(f"[ERROR] Failed to insert record: {str(e)}")
                    error_count += 1
            
            conn.commit()
            conn.close()
        
        return jsonify({
            'status': 'success',
            'inserted': success_count,
            'errors': error_count,
            'total': len(records)
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Bulk import: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# API QUERY ENDPOINTS
# ============================================================================

@app.route('/api/15m/latest', methods=['GET'])
def get_15m_latest():
    """Get latest 15m baseline records"""
    try:
        limit = request.args.get('limit', 25, type=int)
        
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM bulk_analysis_15m
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to list of dicts
            data = [dict(row) for row in rows]
            
            return jsonify({
                'status': 'success',
                'count': len(data),
                'data': data
            }), 200
            
    except Exception as e:
        print(f"[ERROR] Get 15m latest: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/15m/count', methods=['GET'])
def get_15m_count():
    """Get total count of 15m records"""
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM bulk_analysis_15m')
            count = cursor.fetchone()[0]
            
            conn.close()
            
            return jsonify({
                'status': 'success',
                'count': count
            }), 200
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'unified_webhook_server',
        'database': DB_PATH,
        'timestamp': datetime.now().isoformat()
    }), 200

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  V6 INTELLIGENCE DATABASE - UNIFIED WEBHOOK SERVER       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    # Initialize database
    init_database()
    
    print()
    print("[START] Server starting on http://0.0.0.0:5001")
    print()
    print("Webhook endpoints:")
    print("  - 15m Full Analysis:  POST http://localhost:5001/webhook/15m")
    print("  - 1m Recalibration:   POST http://localhost:5001/webhook/1m")
    print("  - Pine Logs Import:   POST http://localhost:5001/api/bulk-import")
    print()
    print("Query endpoints:")
    print("  - Get Latest 15m:     GET  http://localhost:5001/api/15m/latest?limit=25")
    print("  - Get Record Count:   GET  http://localhost:5001/api/15m/count")
    print("  - Health Check:       GET  http://localhost:5001/api/health")
    print()
    print("Press Ctrl+C to stop")
    print("═" * 62)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5001)