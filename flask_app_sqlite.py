"""
MT5 META AGENT V10 - Flask Application (SQLite Edition)
Complete dashboard + database interface with real-time data
V2.032 - Includes ATH tracking
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import json
import subprocess
import csv
import io

# Base44 imports
try:
    from database_init_base44_unified import (
        get_latest_position_state,
        get_position_state_history,
        get_trade_statistics,
        get_execution_gate_config,
        update_execution_gate_config,
        is_agent_running,
        start_agent,
        stop_agent,
        get_agent_status,
        get_webhook_signal_history
    )
    BASE44_AVAILABLE = True
except ImportError:
    BASE44_AVAILABLE = False
    print("⚠ Base44 functions not available - some endpoints will be disabled")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mt5-meta-agent-v10-secret-key'
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "allow_headers": "*",
        "expose_headers": "*"
    }
})

# Database configuration
DB_PATH = 'mt5_intelligence.db'

# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def db_exists():
    """Check if database file exists"""
    return os.path.exists(DB_PATH)

# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/chart-data')
def chart_data():
    """Intelligence Database page"""
    return render_template('chart_data.html')

# ============================================================================
# API ENDPOINTS - CORE DATA
# ============================================================================

@app.route('/api/core')
def api_core():
    """Get core market data (OHLCV)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 10))
        
        print(f"[API] /api/core requested: timeframe={timeframe}, limit={limit}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, symbol, open, high, low, close, volume
            FROM core_15m
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        if len(data) > 0:
            print(f"[API] Returning {len(data)} records. First timestamp: {data[0]['timestamp']}")
        else:
            print(f"[API] No data found for timeframe={timeframe}")
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/basic')
def api_basic():
    """Get basic indicators data"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 10))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, atr_14, atr_50_avg, atr_ratio,
                   ema_short, ema_medium, ema_distance, supertrend
            FROM basic_15m
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fibonacci')
def api_fibonacci():
    """Get Fibonacci zone data (V2.021)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 10))
        
        print(f"[API] /api/fibonacci requested: timeframe={timeframe}, limit={limit}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, current_fib_zone, in_golden_zone, zone_multiplier,
                   pivot_high, pivot_low, fib_range, lookback_bars,
                   fib_level_0000, fib_level_0236, fib_level_0382, fib_level_0500,
                   fib_level_0618, fib_level_0786, fib_level_1000,
                   distance_to_next_level
            FROM fibonacci_data
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        if len(data) > 0:
            print(f"[API] Returning {len(data)} Fibonacci records. First timestamp: {data[0]['timestamp']}")
        else:
            print(f"[API] No Fibonacci data found for timeframe={timeframe}")
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        print(f"[API] Fibonacci error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ath')
def api_ath():
    """Get All-Time High tracking data (V2.032)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 10))
        
        print(f"[API] /api/ath requested: timeframe={timeframe}, limit={limit}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, current_ath, current_close,
                   ath_distance_points, ath_distance_pct,
                   ath_multiplier, ath_zone, distance_from_ath_percentile
            FROM ath_tracking
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        if len(data) > 0:
            print(f"[API] Returning {len(data)} ATH records. First timestamp: {data[0]['timestamp']}")
        else:
            print(f"[API] No ATH data found for timeframe={timeframe}")
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        print(f"[API] ATH error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# BASE44 STATE TRACKING ENDPOINTS
# ============================================================================

@app.route('/api/state/current')
def api_state_current():
    """Get current position state with countdown"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        state = get_latest_position_state()
        
        if state is None:
            return jsonify({
                'success': False,
                'message': 'No state data available. Is calculation engine running?'
            }), 404
        
        return jsonify({
            'success': True,
            'data': state
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/state/history')
def api_state_history():
    """Get position state history"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        limit = int(request.args.get('limit', 100))
        history = get_position_state_history(limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(history),
            'data': history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/state/stats')
def api_state_stats():
    """Get trade statistics"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        stats = get_trade_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# EXECUTION GATE CONFIGURATION ENDPOINTS
# ============================================================================

@app.route('/api/config/gates', methods=['GET'])
def api_config_gates_get():
    """Get execution gate configuration"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        config = get_execution_gate_config()
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/gates', methods=['POST'])
def api_config_gates_update():
    """Update execution gate configuration"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Update configuration
        update_execution_gate_config(data)
        
        # Return updated config
        config = get_execution_gate_config()
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated',
            'data': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# AGENT CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/agent/status')
def api_agent_status():
    """Get agent status"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        status = get_agent_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/agent/start', methods=['POST'])
def api_agent_start():
    """Start the agent"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        if is_agent_running():
            return jsonify({
                'success': False,
                'message': 'Agent is already running'
            }), 400
        
        start_agent()
        
        return jsonify({
            'success': True,
            'message': 'Agent started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/agent/stop', methods=['POST'])
def api_agent_stop():
    """Stop the agent"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        if not is_agent_running():
            return jsonify({
                'success': False,
                'message': 'Agent is not running'
            }), 400
        
        stop_agent()
        
        return jsonify({
            'success': True,
            'message': 'Agent stopped'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# WEBHOOK SIGNAL LOGGING ENDPOINTS
# ============================================================================

@app.route('/api/webhooks/history')
def api_webhooks_history():
    """Get webhook signal history"""
    if not BASE44_AVAILABLE:
        return jsonify({'error': 'Base44 not initialized'}), 503
    
    try:
        limit = int(request.args.get('limit', 100))
        history = get_webhook_signal_history(limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(history),
            'data': history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        

@app.route('/api/nodes')
def api_nodes():
    """Get nodes data for 3D visualization"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        limit = int(request.args.get('limit', 1000))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get data from core and basic tables to create nodes
        cursor.execute("""
            SELECT c.timestamp, c.close, b.atr_ratio, b.ema_distance,
                   b.supertrend, c.volume
            FROM core_15m c
            LEFT JOIN basic_15m b ON c.timestamp = b.timestamp
            WHERE c.timeframe = '15m'
            ORDER BY c.timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Transform to node format
        nodes = []
        for i, row in enumerate(rows):
            nodes.append({
                'node_id': f'node_{i}',
                'x': float(row['ema_distance'] or 0),
                'y': float(row['close'] or 0),
                'z': float(row['atr_ratio'] or 0),
                'sample_count': int(row['volume'] or 0),
                'confidence': 0.8,
                'cluster_id': 'cluster_1',
                'trigger_class': row['supertrend'] or 'neutral',
                'profile_family': 'default'
            })
        
        return jsonify({
            'success': True,
            'count': len(nodes),
            'data': nodes
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get collection statistics"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get stats for this timeframe
        cursor.execute("""
            SELECT total_collections, successful_collections, 
                   failed_collections, last_collection, last_error
            FROM collection_stats
            WHERE timeframe = ?
        """, (timeframe,))
        
        row = cursor.fetchone()
        
        # Get total records count
        cursor.execute("""
            SELECT COUNT(*) as count FROM core_15m WHERE timeframe = ?
        """, (timeframe,))
        
        count_row = cursor.fetchone()
        conn.close()
        
        if row:
            stats = dict(row)
            stats['total_records'] = count_row['count'] if count_row else 0
            
            return jsonify({
                'success': True,
                'timeframe': timeframe,
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No stats found for timeframe'
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def api_status():
    """Check system status"""
    status = {
        'database_connected': db_exists(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'V10'
    }
    
    if db_exists():
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get record counts
            cursor.execute("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='1m'")
            count_1m = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='15m'")
            count_15m = cursor.fetchone()['count']
            
            # Get latest collection time
            cursor.execute("""
                SELECT MAX(last_collection) as latest 
                FROM collection_stats
            """)
            latest_row = cursor.fetchone()
            
            conn.close()
            
            status['records_1m'] = count_1m
            status['records_15m'] = count_15m
            status['last_collection'] = latest_row['latest'] if latest_row else None
            status['collector_running'] = check_collector_running(latest_row['latest'])
            
        except Exception as e:
            status['database_error'] = str(e)
    
    return jsonify(status)

def check_collector_running(last_collection):
    """Check if collector is running based on last collection time"""
    if not last_collection:
        return False
    
    try:
        last_time = datetime.strptime(last_collection, '%Y-%m-%d %H:%M:%S')
        time_diff = (datetime.now() - last_time).total_seconds()
        
        # Consider collector running if last collection was within 5 minutes
        return time_diff < 300
    except:
        return False

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# API ENDPOINTS - IMPORT/EXPORT
# ============================================================================

@app.route('/api/import/trigger', methods=['POST'])
def api_import_trigger():
    """
    Trigger historical data backfill
    Accepts JSON: {"bars_1m": 50000, "bars_15m": 50000}
    """
    try:
        data = request.get_json() or {}
        bars_1m = data.get('bars_1m', 50000)
        bars_15m = data.get('bars_15m', 50000)
        
        print(f"[API] Import triggered: 1m={bars_1m}, 15m={bars_15m}")
        
        # Run backfill script in background
        process = subprocess.Popen(
            ['python', 'backfill_history.py', str(bars_1m), str(bars_15m)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return jsonify({
            'success': True,
            'message': f'Import started: {bars_1m:,} bars (1m), {bars_15m:,} bars (15m)',
            'pid': process.pid,
            'bars_1m': bars_1m,
            'bars_15m': bars_15m
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/import/status')
def api_import_status():
    """Check if import is currently running"""
    try:
        # Check if backfill process is running
        try:
            import psutil
            running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and 'backfill_history.py' in ' '.join(cmdline):
                        running = True
                        break
                except:
                    continue
            
            return jsonify({
                'success': True,
                'import_running': running
            })
        except ImportError:
            # psutil not available, return unknown status
            return jsonify({
                'success': True,
                'import_running': False,
                'note': 'Install psutil for accurate status: pip install psutil'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/export/core')
def api_export_core():
    """Export core_15m table as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, symbol, open, high, low, close, volume
            FROM core_15m
            WHERE timeframe = ?
            ORDER BY timestamp DESC
        """, (timeframe,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) == 0:
            return jsonify({'error': 'No data to export'}), 404
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
        
        # Write data
        for row in rows:
            writer.writerow([row['timestamp'], row['symbol'], row['open'], 
                           row['high'], row['low'], row['close'], row['volume']])
        
        # Prepare file for download
        output.seek(0)
        filename = f'core_data_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/basic')
def api_export_basic():
    """Export basic_15m table as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, atr_14, atr_50_avg, atr_ratio,
                   ema_short, ema_medium, ema_distance, supertrend
            FROM basic_15m
            WHERE timeframe = ?
            ORDER BY timestamp DESC
        """, (timeframe,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) == 0:
            return jsonify({'error': 'No data to export'}), 404
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['timestamp', 'atr_14', 'atr_50_avg', 'atr_ratio',
                        'ema_short', 'ema_medium', 'ema_distance', 'supertrend'])
        
        for row in rows:
            writer.writerow([row['timestamp'], row['atr_14'], row['atr_50_avg'], 
                           row['atr_ratio'], row['ema_short'], row['ema_medium'],
                           row['ema_distance'], row['supertrend']])
        
        output.seek(0)
        filename = f'basic_indicators_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/fibonacci')
def api_export_fibonacci():
    """Export fibonacci_data table as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, current_fib_zone, in_golden_zone, zone_multiplier,
                   pivot_high, pivot_low, fib_range, lookback_bars,
                   fib_level_0000, fib_level_0236, fib_level_0382, fib_level_0500,
                   fib_level_0618, fib_level_0786, fib_level_1000,
                   distance_to_next_level
            FROM fibonacci_data
            WHERE timeframe = ?
            ORDER BY timestamp DESC
        """, (timeframe,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) == 0:
            return jsonify({'error': 'No data to export'}), 404
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['timestamp', 'current_fib_zone', 'in_golden_zone', 'zone_multiplier',
                        'pivot_high', 'pivot_low', 'fib_range', 'lookback_bars',
                        'fib_0000', 'fib_0236', 'fib_0382', 'fib_0500',
                        'fib_0618', 'fib_0786', 'fib_1000', 'distance_to_next'])
        
        for row in rows:
            writer.writerow([row['timestamp'], row['current_fib_zone'], row['in_golden_zone'],
                           row['zone_multiplier'], row['pivot_high'], row['pivot_low'],
                           row['fib_range'], row['lookback_bars'],
                           row['fib_level_0000'], row['fib_level_0236'], row['fib_level_0382'],
                           row['fib_level_0500'], row['fib_level_0618'], row['fib_level_0786'],
                           row['fib_level_1000'], row['distance_to_next_level']])
        
        output.seek(0)
        filename = f'fibonacci_data_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/ath')
def api_export_ath():
    """Export ath_tracking table as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, current_ath, current_close,
                   ath_distance_points, ath_distance_pct,
                   ath_multiplier, ath_zone, distance_from_ath_percentile
            FROM ath_tracking
            WHERE timeframe = ?
            ORDER BY timestamp DESC
        """, (timeframe,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) == 0:
            return jsonify({'error': 'No data to export'}), 404
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['timestamp', 'current_ath', 'current_close',
                        'ath_distance_points', 'ath_distance_pct',
                        'ath_multiplier', 'ath_zone', 'distance_from_ath_percentile'])
        
        for row in rows:
            writer.writerow([row['timestamp'], row['current_ath'], row['current_close'],
                           row['ath_distance_points'], row['ath_distance_pct'],
                           row['ath_multiplier'], row['ath_zone'], 
                           row['distance_from_ath_percentile']])
        
        output.seek(0)
        filename = f'ath_tracking_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/all')
def api_export_all():
    """Export all tables as JSON (complete database dump)"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        export_data = {
            'metadata': {
                'timeframe': timeframe,
                'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': 'V10'
            },
            'tables': {}
        }
        
        # Export core_15m
        cursor.execute("""
            SELECT * FROM core_15m WHERE timeframe = ? ORDER BY timestamp DESC
        """, (timeframe,))
        export_data['tables']['core_15m'] = [dict(row) for row in cursor.fetchall()]
        
        # Export basic_15m
        cursor.execute("""
            SELECT * FROM basic_15m WHERE timeframe = ? ORDER BY timestamp DESC
        """, (timeframe,))
        export_data['tables']['basic_15m'] = [dict(row) for row in cursor.fetchall()]
        
        # Export fibonacci_data
        cursor.execute("""
            SELECT * FROM fibonacci_data WHERE timeframe = ? ORDER BY timestamp DESC
        """, (timeframe,))
        export_data['tables']['fibonacci_data'] = [dict(row) for row in cursor.fetchall()]
        
        # Export ath_tracking
        cursor.execute("""
            SELECT * FROM ath_tracking WHERE timeframe = ? ORDER BY timestamp DESC
        """, (timeframe,))
        export_data['tables']['ath_tracking'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Create JSON file
        json_str = json.dumps(export_data, indent=2)
        filename = f'complete_export_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        return send_file(
            io.BytesIO(json_str.encode()),
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# TEMPLATE FILTERS
# ============================================================================

@app.template_filter('format_timestamp')
def format_timestamp(value):
    """Format timestamp for display"""
    try:
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%m/%d %H:%M')
    except:
        return value

@app.template_filter('format_number')
def format_number(value, decimals=2):
    """Format number with specific decimal places"""
    try:
        return f"{float(value):.{decimals}f}"
    except:
        return value

# ============================================================================
# STARTUP CHECKS
# ============================================================================

def startup_checks():
    """Run startup checks"""
    print("\n" + "="*70)
    print("MT5 META AGENT V10 - FLASK APPLICATION")
    print("="*70)
    
    # Check database
    if db_exists():
        print(f"✓ Database found: {DB_PATH}")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='1m'")
            count_1m = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='15m'")
            count_15m = cursor.fetchone()['count']
            
            conn.close()
            
            print(f"  Records (1m): {count_1m}")
            print(f"  Records (15m): {count_15m}")
            
        except Exception as e:
            print(f"✗ Database error: {e}")
    else:
        print(f"✗ Database not found: {DB_PATH}")
        print("  Run: py -3.11 database_init_sqlite.py")
    
    # Check templates
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if os.path.exists(templates_dir):
        print(f"✓ Templates directory found")
    else:
        print(f"✗ Templates directory not found")
    
    print("="*70)
    print("Starting Flask server...")
    print("Dashboard: http://localhost:5000")
    print("Database: http://localhost:5000/chart-data")
    print("API Status: http://localhost:5000/api/status")
    print("="*70 + "\n")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    startup_checks()
    
    # Run Flask development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
