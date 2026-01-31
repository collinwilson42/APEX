"""
FLASK API ENDPOINTS - IMPORT/EXPORT FUNCTIONALITY
Add these endpoints to your flask_app_sqlite.py

Individual table exports + import triggering
"""

# Add these imports at the top of flask_app_sqlite.py:
import subprocess
import csv
import io
from flask import send_file

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
