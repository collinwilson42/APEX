#!/usr/bin/env python3
"""
MT5 META AGENT V3.2 - Flask Application
Serves Control Panel and all web interfaces
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)

# Configuration
DATABASE_PATH = 'mt5_intelligence.db'

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    """Execute database query"""
    try:
        conn = get_db_connection()
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.close()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"Database query error: {e}")
        return None if one else []

# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard/homepage"""
    return render_template('dashboard.html')

@app.route('/control-panel')
def control_panel():
    """V3.2 Control Panel - NEW!"""
    return render_template('control_panel.html')

@app.route('/chart-data')
@app.route('/database')
def chart_data():
    """V6 Intelligence Database view"""
    return render_template('chart_data.html')

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/markov')
@app.route('/wizaude')
def markov_panel():
    """Markov Matrix Control Panel"""
    return render_template('markov_panel.html')

@app.route('/tunity')
def tunity():
    """Tunity Control Panel"""
    return render_template('tunity.html')

# ============================================================================
# API ENDPOINTS - HEALTH & STATUS
# ============================================================================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'flask_app',
        'timestamp': datetime.now().isoformat(),
        'version': 'v3.2'
    })

@app.route('/api/status')
def status():
    """System status endpoint"""
    try:
        # Check database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM core_15m")
        core_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'operational',
            'database': 'connected',
            'records': core_count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================================================
# API ENDPOINTS - CONTROL PANEL (V3.2)
# ============================================================================

@app.route('/api/profiles/list')
def list_profiles():
    """Get list of all profiles"""
    # Mock data for now - replace with actual database query
    profiles = [
        {
            'id': 'claude_elite_v1_0',
            'name': 'Claude_Elite_v1.0',
            'trading_class': 'Scalping',
            'north_star_metric': 13454,
            'rank': 8,
            'is_active': False,
            'created_date': '2024-11-15'
        },
        {
            'id': 'claude_elite_v1_4',
            'name': 'Claude_Elite_v1.4',
            'trading_class': 'Scalping',
            'north_star_metric': 33545,
            'rank': 4,
            'is_active': True,
            'created_date': '2024-12-01'
        },
        {
            'id': 'claude_elite_v1_5',
            'name': 'Claude_Elite_v1.5',
            'trading_class': 'Scalping',
            'north_star_metric': 28900,
            'rank': 5,
            'is_active': False,
            'created_date': '2024-12-03'
        }
    ]
    
    return jsonify(profiles)

@app.route('/api/profiles/get/<profile_id>')
def get_profile(profile_id):
    """Get detailed profile data"""
    # Mock data - replace with database query
    profile = {
        'id': profile_id,
        'name': 'Claude_Elite_v1.4',
        'trading_class': 'Scalping',
        'north_star_metric': 33545,
        'rank': 4,
        'settings': {
            'timeframe': '1m',
            'position_size': 0.10,
            'stop_loss': 15,
            'take_profit': 30,
            'max_trades': 25,
            'leverage': '1:50',
            'max_drawdown': 5,
            'pyramiding': True
        },
        'assigned_files': {
            'skills': ['advanced_momentum_v2.1', 'volatility_filter_v1.3'],
            'prompts': ['claude_elite_prompt_v4'],
            'inputs': ['MGC_1m_recalibration']
        },
        'is_active': True,
        'last_modified': '2 hours ago'
    }
    
    return jsonify(profile)

@app.route('/api/profiles/search')
def search_profiles():
    """Search profiles by name/class"""
    query = request.args.get('q', '').lower()
    
    # Mock search results
    all_profiles = [
        {'name': 'Claude_Elite_v1.0', 'metric': 13454, 'class': 'Scalping'},
        {'name': 'Claude_Elite_v1.1', 'metric': 13454, 'class': 'Scalping'},
        {'name': 'Claude_Elite_v1.2', 'metric': 16789, 'class': 'Scalping'},
        {'name': 'Claude_Elite_v1.3', 'metric': 23456, 'class': 'Scalping'},
        {'name': 'Claude_Elite_v1.4', 'metric': 33545, 'class': 'Scalping'},
        {'name': 'Claude_Elite_v1.5', 'metric': 28900, 'class': 'Scalping'}
    ]
    
    results = [p for p in all_profiles if query in p['name'].lower()]
    
    return jsonify(results)

@app.route('/api/profiles/activate/<profile_id>', methods=['POST'])
def activate_profile(profile_id):
    """Activate a profile"""
    # TODO: Update database with activation
    return jsonify({
        'success': True,
        'profile_id': profile_id,
        'message': f'Profile {profile_id} activated',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/profiles/update/<profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """Update profile settings"""
    data = request.get_json()
    
    # TODO: Save to database
    return jsonify({
        'success': True,
        'profile_id': profile_id,
        'message': 'Profile updated successfully'
    })

@app.route('/api/leaderboard/rankings')
def leaderboard_rankings():
    """Get leaderboard rankings"""
    # Mock leaderboard data
    rankings = []
    for i in range(1, 100):
        rankings.append({
            'rank': i,
            'profile_name': f'Profile_{i}',
            'north_star_metric': 50000 - (i * 500),
            'trading_class': 'Scalping' if i % 2 == 0 else 'Swing'
        })
    
    return jsonify(rankings)

@app.route('/api/leaderboard/get-by-rank/<int:rank>')
def get_by_rank(rank):
    """Get profile at specific rank"""
    # Mock data
    profile = {
        'rank': rank,
        'profile_id': f'profile_{rank}',
        'profile_name': f'Claude_Elite_v1.{rank}',
        'north_star_metric': 50000 - (rank * 500),
        'trading_class': 'Scalping'
    }
    
    return jsonify(profile)

# ============================================================================
# API ENDPOINTS - DATA RETRIEVAL (Chart Data Page)
# ============================================================================

@app.route('/api/core')
def get_core_data():
    """Get core market data (OHLCV)"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    query = """
        SELECT timestamp, symbol, open, high, low, close, volume
        FROM core_15m 
        WHERE timeframe = ?
        ORDER BY timestamp DESC 
        LIMIT ?
    """
    
    rows = query_db(query, (timeframe, limit))
    data = [dict(row) for row in rows] if rows else []
    
    return jsonify({'success': True, 'data': data})


@app.route('/api/basic')
def get_basic_data():
    """Get basic indicators"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    query = """
        SELECT timestamp, atr_14, atr_50_avg, atr_ratio, 
               ema_short, ema_medium, ema_distance, supertrend
        FROM basic_15m 
        WHERE timeframe = ?
        ORDER BY timestamp DESC 
        LIMIT ?
    """
    
    rows = query_db(query, (timeframe, limit))
    data = [dict(row) for row in rows] if rows else []
    
    return jsonify({'success': True, 'data': data})


@app.route('/api/advanced')
def get_advanced_data():
    """Get advanced indicators"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    query = """
        SELECT * FROM advanced_indicators 
        WHERE timeframe = ?
        ORDER BY timestamp DESC 
        LIMIT ?
    """
    
    rows = query_db(query, (timeframe, limit))
    data = [dict(row) for row in rows] if rows else []
    
    return jsonify({'success': True, 'data': data})


@app.route('/api/fibonacci')
def get_fibonacci_data_api():
    """Get Fibonacci zone data"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    query = """
        SELECT * FROM fibonacci_data
        WHERE timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    
    rows = query_db(query, (timeframe, limit))
    data = [dict(row) for row in rows] if rows else []
    
    return jsonify({'success': True, 'data': data})


@app.route('/api/ath')
def get_ath_data_api():
    """Get ATH tracking data"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    query = """
        SELECT * FROM ath_tracking
        WHERE timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    
    rows = query_db(query, (timeframe, limit))
    data = [dict(row) for row in rows] if rows else []
    
    return jsonify({'success': True, 'data': data})


# ============================================================================
# API ENDPOINTS - APEX V2.0 (Indicator Management)
# ============================================================================

@app.route('/api/group-summary')
def get_group_summary():
    """Get indicator group summary"""
    query = """
        SELECT 
            ig.id,
            ig.name as group_name,
            ig.description,
            ig.is_active,
            COUNT(ic.id) as total_indicators,
            SUM(CASE WHEN ic.is_active = 1 THEN 1 ELSE 0 END) as active_indicators
        FROM indicator_groups ig
        LEFT JOIN indicator_configs ic ON ig.id = ic.group_id
        GROUP BY ig.id
        ORDER BY ig.display_order
    """
    
    rows = query_db(query)
    if rows:
        data = [dict(row) for row in rows]
    else:
        # Return mock data if table doesn't exist
        data = [
            {'id': 1, 'group_name': 'Trend', 'description': 'Trend indicators', 'is_active': 1, 'total_indicators': 5, 'active_indicators': 5},
            {'id': 2, 'group_name': 'Momentum', 'description': 'Momentum indicators', 'is_active': 1, 'total_indicators': 8, 'active_indicators': 8},
            {'id': 3, 'group_name': 'Volatility', 'description': 'Volatility indicators', 'is_active': 1, 'total_indicators': 4, 'active_indicators': 4},
            {'id': 4, 'group_name': 'Volume', 'description': 'Volume indicators', 'is_active': 1, 'total_indicators': 2, 'active_indicators': 2},
        ]
    
    return jsonify({'success': True, 'data': data})


@app.route('/api/indicator-groups')
def get_indicator_groups():
    """Get all indicator groups"""
    query = "SELECT * FROM indicator_groups ORDER BY display_order"
    
    rows = query_db(query)
    if rows:
        data = [dict(row) for row in rows]
    else:
        data = [
            {'id': 1, 'name': 'Trend', 'description': 'Trend-following indicators', 'is_active': 1, 'display_order': 1, 'created_at': '2024-12-01'},
            {'id': 2, 'name': 'Momentum', 'description': 'Momentum oscillators', 'is_active': 1, 'display_order': 2, 'created_at': '2024-12-01'},
            {'id': 3, 'name': 'Volatility', 'description': 'Volatility measures', 'is_active': 1, 'display_order': 3, 'created_at': '2024-12-01'},
            {'id': 4, 'name': 'Volume', 'description': 'Volume analysis', 'is_active': 1, 'display_order': 4, 'created_at': '2024-12-01'},
        ]
    
    return jsonify({'success': True, 'data': data})


@app.route('/api/indicators')
def get_indicators():
    """Get all indicators"""
    group_id = request.args.get('group_id')
    
    query = "SELECT * FROM indicators"
    args = ()
    
    if group_id:
        query += " WHERE default_group_id = ?"
        args = (group_id,)
    
    query += " ORDER BY id"
    
    rows = query_db(query, args)
    if rows:
        data = [dict(row) for row in rows]
    else:
        data = [
            {'id': 1, 'name': 'supertrend', 'display_name': 'SuperTrend', 'description': 'Trend direction', 'logic_base_id': 1, 'default_group_id': 1, 'created_at': '2024-12-01'},
            {'id': 2, 'name': 'ema_distance', 'display_name': 'EMA Distance', 'description': 'Distance from EMA', 'logic_base_id': 1, 'default_group_id': 1, 'created_at': '2024-12-01'},
            {'id': 3, 'name': 'rsi', 'display_name': 'RSI', 'description': 'Relative Strength Index', 'logic_base_id': 2, 'default_group_id': 2, 'created_at': '2024-12-01'},
            {'id': 4, 'name': 'atr', 'display_name': 'ATR', 'description': 'Average True Range', 'logic_base_id': 3, 'default_group_id': 3, 'created_at': '2024-12-01'},
        ]
    
    return jsonify({'success': True, 'data': data, 'count': len(data)})


@app.route('/api/indicator-configs')
def get_indicator_configs():
    """Get indicator configurations"""
    group_id = request.args.get('group_id')
    active_only = request.args.get('active_only')
    limit = int(request.args.get('limit', 200))
    
    query = """
        SELECT ic.*, i.name as indicator_name, ig.name as group_name
        FROM indicator_configs ic
        LEFT JOIN indicators i ON ic.indicator_id = i.id
        LEFT JOIN indicator_groups ig ON ic.group_id = ig.id
        WHERE 1=1
    """
    args = []
    
    if group_id:
        query += " AND ic.group_id = ?"
        args.append(group_id)
    
    if active_only == 'true':
        query += " AND ic.is_active = 1"
    
    query += f" ORDER BY ic.display_order LIMIT {limit}"
    
    rows = query_db(query, tuple(args))
    if rows:
        data = [dict(row) for row in rows]
    else:
        data = [
            {'id': 1, 'indicator_name': 'supertrend', 'display_name': 'SuperTrend', 'scope': '15m', 'is_active': 1, 'group_name': 'Trend', 'display_order': 1, 'logic_base_id': 1, 'last_updated_at': '2024-12-01'},
            {'id': 2, 'indicator_name': 'ema_distance', 'display_name': 'EMA Distance', 'scope': '15m', 'is_active': 1, 'group_name': 'Trend', 'display_order': 2, 'logic_base_id': 1, 'last_updated_at': '2024-12-01'},
            {'id': 3, 'indicator_name': 'rsi', 'display_name': 'RSI 14', 'scope': '15m', 'is_active': 1, 'group_name': 'Momentum', 'display_order': 3, 'logic_base_id': 2, 'last_updated_at': '2024-12-01'},
            {'id': 4, 'indicator_name': 'atr', 'display_name': 'ATR 14', 'scope': '15m', 'is_active': 1, 'group_name': 'Volatility', 'display_order': 4, 'logic_base_id': 3, 'last_updated_at': '2024-12-01'},
        ]
    
    return jsonify({'success': True, 'data': data, 'count': len(data)})


@app.route('/api/evaluation-settings')
def get_evaluation_settings():
    """Get evaluation settings"""
    query = "SELECT * FROM evaluation_settings WHERE id = 1"
    
    row = query_db(query, one=True)
    if row:
        data = dict(row)
    else:
        data = {
            'bar_interval_mode': 'time_window',
            'time_window_minutes': 15,
            'last_evaluation_at': None,
            'created_at': '2024-12-01',
            'updated_at': '2024-12-01'
        }
    
    return jsonify({'success': True, 'data': data})


@app.route('/api/ai-analysis-results')
def get_ai_analysis_results():
    """Get AI analysis results"""
    limit = int(request.args.get('limit', 20))
    
    query = f"SELECT * FROM ai_analysis_results ORDER BY timestamp DESC LIMIT {limit}"
    
    rows = query_db(query)
    data = [dict(row) for row in rows] if rows else []
    
    return jsonify({'success': True, 'data': data, 'count': len(data)})


@app.route('/api/data/15m')
def get_15m_data():
    """Get 15-minute chart data"""
    symbol = request.args.get('symbol', 'MGC')
    limit = int(request.args.get('limit', 100))
    
    query = """
        SELECT timestamp, symbol, open, high, low, close, volume
        FROM core_15m 
        WHERE timeframe = '15m' AND symbol = ?
        ORDER BY timestamp DESC 
        LIMIT ?
    """
    
    rows = query_db(query, (symbol, limit))
    
    data = []
    for row in rows:
        data.append({
            'timestamp': row['timestamp'],
            'symbol': row['symbol'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        })
    
    return jsonify(data)

@app.route('/api/data/1m')
def get_1m_data():
    """Get 1-minute chart data"""
    symbol = request.args.get('symbol', 'MGC')
    limit = int(request.args.get('limit', 250))
    
    query = """
        SELECT timestamp, symbol, open, high, low, close, volume
        FROM core_15m 
        WHERE timeframe = '1m' AND symbol = ?
        ORDER BY timestamp DESC 
        LIMIT ?
    """
    
    rows = query_db(query, (symbol, limit))
    
    data = []
    for row in rows:
        data.append({
            'timestamp': row['timestamp'],
            'symbol': row['symbol'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        })
    
    return jsonify(data)

@app.route('/api/data/fibonacci')
def get_fibonacci_data():
    """Get Fibonacci zone data"""
    symbol = request.args.get('symbol', 'MGC')
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 100))
    
    query = """
        SELECT * FROM fibonacci_data
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    
    rows = query_db(query, (symbol, timeframe, limit))
    
    data = []
    for row in rows:
        data.append(dict(row))
    
    return jsonify(data)

@app.route('/api/data/ath')
def get_ath_data():
    """Get ATH tracking data"""
    symbol = request.args.get('symbol', 'MGC')
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 100))
    
    query = """
        SELECT * FROM ath_tracking
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    
    rows = query_db(query, (symbol, timeframe, limit))
    
    data = []
    for row in rows:
        data.append(dict(row))
    
    return jsonify(data)

# ============================================================================
# STATIC FILE SERVING
# ============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """404 handler"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500 handler"""
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

# ============================================================================
# WIZAUDE INTEGRATION
# ============================================================================

try:
    from wizaude_api import register_wizaude_routes
    register_wizaude_routes(app)
    WIZAUDE_ENABLED = True
except ImportError as e:
    print(f"[WARN] Wizaude not available: {e}")
    WIZAUDE_ENABLED = False

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("="*60)
    print("MT5 META AGENT V3.2 - Flask Application")
    if WIZAUDE_ENABLED:
        print("[WIZAUDE CORE INTEGRATED]")
    print("="*60)
    print("\nStarting Flask server...")
    print(f"Database: {DATABASE_PATH}")
    print("\nAvailable routes:")
    print("  - http://localhost:5000/              (Dashboard)")
    print("  - http://localhost:5000/control-panel (Control Panel)")
    print("  - http://localhost:5000/database      (V6 Database)")
    print("  - http://localhost:5000/settings      (Settings)")
    print("\nAPI endpoints:")
    print("  - /api/health")
    print("  - /api/profiles/*")
    print("  - /api/leaderboard/*")
    print("  - /api/data/*")
    if WIZAUDE_ENABLED:
        print("\nWizaude endpoints:")
        print("  - /api/wizaude/status")
        print("  - /api/wizaude/signal")
        print("  - /api/wizaude/regime")
        print("  - /api/wizaude/trinity")
        print("  - /api/wizaude/stoic")
    print("="*60)
    print()
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
