"""
COMPLETE FLASK API ENDPOINTS - ALL FEATURES
Includes: Profile Management, Import System, Export System
"""

from flask import Flask, jsonify, request, send_file
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess
from threading import Thread
import sqlite3

# ============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/api/files/counts', methods=['GET'])
def get_file_counts():
    """Get file counts for all folders"""
    try:
        folders = ['profiles', 'inputs', 'prompts', 'skills']
        counts = {}
        
        for folder in folders:
            folder_path = os.path.join(os.getcwd(), folder)
            if os.path.exists(folder_path):
                files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                counts[folder] = len(files)
            else:
                counts[folder] = 0
                
        return jsonify(counts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/list', methods=['GET'])
def list_files():
    """List files in a specific folder"""
    try:
        folder = request.args.get('folder', 'profiles')
        folder_path = os.path.join(os.getcwd(), secure_filename(folder))
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            return jsonify([])
        
        files = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                })
        
        return jsonify(files)
    except Exception as e:
        print(f"[ERROR] list_files: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/content', methods=['GET'])
def get_file_content():
    """Get content of a specific file"""
    try:
        folder = request.args.get('folder')
        filename = request.args.get('file')
        
        if not folder or not filename:
            return jsonify({'error': 'Missing folder or file parameter'}), 400
        
        file_path = os.path.join(os.getcwd(), secure_filename(folder), secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'filename': filename,
            'folder': folder,
            'content': content
        })
    except Exception as e:
        print(f"[ERROR] get_file_content: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/save', methods=['POST'])
def save_file():
    """Save or update a file"""
    try:
        data = request.json
        folder = data.get('folder')
        filename = data.get('filename')
        content = data.get('content')
        
        if not all([folder, filename, content]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        folder_path = os.path.join(os.getcwd(), secure_filename(folder))
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        file_path = os.path.join(folder_path, secure_filename(filename))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'message': f'File saved: {filename}'
        })
    except Exception as e:
        print(f"[ERROR] save_file: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    """Delete a file"""
    try:
        folder = request.args.get('folder')
        filename = request.args.get('file')
        
        if not folder or not filename:
            return jsonify({'error': 'Missing folder or file parameter'}), 400
        
        file_path = os.path.join(os.getcwd(), secure_filename(folder), secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': f'File deleted: {filename}'
        })
    except Exception as e:
        print(f"[ERROR] delete_file: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# RISK MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/api/risk/save', methods=['POST'])
def save_risk_settings():
    """Save risk management settings"""
    try:
        settings = request.json
        
        settings_path = os.path.join(os.getcwd(), 'risk_settings.json')
        
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Risk settings saved'
        })
    except Exception as e:
        print(f"[ERROR] save_risk_settings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/risk/load', methods=['GET'])
def load_risk_settings():
    """Load risk management settings"""
    try:
        settings_path = os.path.join(os.getcwd(), 'risk_settings.json')
        
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            return jsonify(settings)
        else:
            # Return defaults
            return jsonify({
                'riskRewardLevel': 50,
                'maxDrawdown': 3,
                'stopLoss': [1.5, 2.0, 2.5, 3.0, 1.0],
                'takeProfit': [1.5, 3.0, 5.0, 8.0, 1.5]
            })
    except Exception as e:
        print(f"[ERROR] load_risk_settings: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# IMPORT SYSTEM ENDPOINTS
# ============================================================================

# Global state for import tracking
import_state = {
    'importing': False,
    'progress': 0,
    'message': '',
    'complete': False,
    'error': None,
    'total_bars': 0,
    'timeframes': 0,
    'process': None
}

@app.route('/api/import/start', methods=['POST'])
def start_import():
    """Start historical data import"""
    global import_state
    
    try:
        if import_state['importing']:
            return jsonify({
                'success': False,
                'error': 'Import already in progress'
            }), 400
        
        data = request.json
        bars = data.get('bars', 50000)
        timeframes = data.get('timeframes', {'1m': True, '15m': True})
        clear_existing = data.get('clear_existing', False)
        
        if bars < 1000 or bars > 100000:
            return jsonify({
                'success': False,
                'error': 'Bar count must be between 1,000 and 100,000'
            }), 400
        
        # Reset state
        import_state = {
            'importing': True,
            'progress': 0,
            'message': 'Starting import...',
            'complete': False,
            'error': None,
            'total_bars': 0,
            'timeframes': 0,
            'process': None
        }
        
        # Build command for backfill script
        cmd = ['python', 'backfill_history.py']
        
        # Add bar counts based on selected timeframes
        if timeframes.get('1m') and timeframes.get('15m'):
            cmd.extend([str(bars), str(bars)])
        elif timeframes.get('1m'):
            cmd.extend([str(bars), '0'])
        elif timeframes.get('15m'):
            cmd.extend(['0', str(bars)])
        
        if clear_existing:
            cmd.append('--clear')
        
        # Start import in background thread
        def run_import():
            global import_state
            try:
                import_state['message'] = 'Connecting to MT5...'
                import_state['progress'] = 5
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                import_state['process'] = process
                
                total_expected = bars * len([t for t in timeframes.values() if t])
                bars_imported = 0
                
                for line in process.stdout:
                    if 'Imported' in line or 'bars' in line.lower():
                        try:
                            parts = line.split('/')
                            if len(parts) >= 2:
                                current = int(''.join(filter(str.isdigit, parts[0])))
                                bars_imported = current
                                progress = min(95, int((bars_imported / total_expected) * 100))
                                import_state['progress'] = progress
                                import_state['message'] = f'Imported {bars_imported:,} / {total_expected:,} bars'
                        except:
                            pass
                
                return_code = process.wait()
                
                if return_code == 0:
                    import_state['progress'] = 100
                    import_state['message'] = 'Import complete!'
                    import_state['complete'] = True
                    import_state['importing'] = False
                    import_state['total_bars'] = total_expected
                    import_state['timeframes'] = len([t for t in timeframes.values() if t])
                else:
                    stderr = process.stderr.read()
                    import_state['error'] = f'Import failed: {stderr}'
                    import_state['importing'] = False
                    import_state['complete'] = False
                
            except Exception as e:
                import_state['error'] = str(e)
                import_state['importing'] = False
                import_state['complete'] = False
        
        thread = Thread(target=run_import)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Import started',
            'bars': bars,
            'timeframes': timeframes
        })
        
    except Exception as e:
        print(f"[ERROR] start_import: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/import/status', methods=['GET'])
def import_status():
    """Get current import progress"""
    global import_state
    
    return jsonify({
        'importing': import_state['importing'],
        'progress': import_state['progress'],
        'message': import_state['message'],
        'complete': import_state['complete'],
        'error': import_state['error'],
        'total_bars': import_state['total_bars'],
        'timeframes': import_state['timeframes']
    })


@app.route('/api/import/cancel', methods=['POST'])
def cancel_import():
    """Cancel ongoing import"""
    global import_state
    
    try:
        if import_state['importing'] and import_state['process']:
            import_state['process'].terminate()
            import_state['importing'] = False
            import_state['message'] = 'Import cancelled'
            import_state['error'] = 'Cancelled by user'
            
            return jsonify({
                'success': True,
                'message': 'Import cancelled'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No import in progress'
            }), 400
            
    except Exception as e:
        print(f"[ERROR] cancel_import: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# EXPORT SYSTEM ENDPOINTS
# ============================================================================

@app.route('/api/export/core', methods=['GET'])
def export_core():
    """Export core market data as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        table_name = f'core_{timeframe}'
        
        conn = sqlite3.connect('mt5_data.db')
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 10000")
        rows = cursor.fetchall()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        conn.close()
        
        # Create CSV
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'core_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        print(f"[ERROR] export_core: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/basic', methods=['GET'])
def export_basic():
    """Export basic indicators as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        table_name = f'basic_{timeframe}'
        
        conn = sqlite3.connect('mt5_data.db')
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 10000")
        rows = cursor.fetchall()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        conn.close()
        
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'basic_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        print(f"[ERROR] export_basic: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/fibonacci', methods=['GET'])
def export_fibonacci():
    """Export Fibonacci data as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = sqlite3.connect('mt5_data.db')
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM fibonacci_data WHERE timeframe=? ORDER BY timestamp DESC LIMIT 10000", (timeframe,))
        rows = cursor.fetchall()
        
        cursor.execute("PRAGMA table_info(fibonacci_data)")
        columns = [col[1] for col in cursor.fetchall()]
        
        conn.close()
        
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'fibonacci_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        print(f"[ERROR] export_fibonacci: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/ath', methods=['GET'])
def export_ath():
    """Export ATH tracking data as CSV"""
    try:
        timeframe = request.args.get('timeframe', '15m')
        
        conn = sqlite3.connect('mt5_data.db')
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM ath_tracking WHERE timeframe=? ORDER BY timestamp DESC LIMIT 10000", (timeframe,))
        rows = cursor.fetchall()
        
        cursor.execute("PRAGMA table_info(ath_tracking)")
        columns = [col[1] for col in cursor.fetchall()]
        
        conn.close()
        
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'ath_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        print(f"[ERROR] export_ath: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# TRIGGER ENDPOINT (For Import Button in Header)
# ============================================================================

@app.route('/api/trigger', methods=['POST'])
def trigger_action():
    """Generic trigger endpoint for various actions"""
    try:
        data = request.json
        action = data.get('action')
        
        if action == 'import':
            # Redirect to import/start
            return start_import()
        else:
            return jsonify({'error': 'Unknown action'}), 400
            
    except Exception as e:
        print(f"[ERROR] trigger_action: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# END OF API ENDPOINTS
# ============================================================================
