"""
MT5 META AGENT V11.3 - CLEAN DATABASE VIEW
Only chart-data page - clean and focused

BUG CLEANUP PHASE 1 - API_FOUNDATION Implementation
Code-Nodes: BC-001 through BC-008
"""

import sys
import subprocess
import os

def check_and_install_dependencies():
    """Check for required packages and install if missing"""
    
    required_packages = {
        'MetaTrader5': 'MetaTrader5',
        'flask': 'Flask',
        'flask_cors': 'flask-cors',
        'numpy': 'numpy',
        'pandas': 'pandas',
    }
    
    missing_packages = []
    
    print("\n" + "="*70)
    print("DEPENDENCY CHECK")
    print("="*70)
    
    for import_name, pip_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✓ {pip_name:20s} - Installed")
        except ImportError:
            print(f"✗ {pip_name:20s} - Missing")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("\n" + "="*70)
        print(f"INSTALLING {len(missing_packages)} MISSING PACKAGES")
        print("="*70)
        
        for package in missing_packages:
            print(f"\n[INSTALL] {package}...")
            try:
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package,
                    '--quiet', '--disable-pip-version-check'
                ])
                print(f"✓ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to install {package}: {e}")
                return False
        
        print("\n" + "="*70)
        print("✓ ALL DEPENDENCIES INSTALLED")
        print("="*70)
    else:
        print("\n✓ All dependencies satisfied")
    
    print("="*70 + "\n")
    return True

if not check_and_install_dependencies():
    print("\n✗ Dependency installation failed")
    sys.exit(1)

# ============================================================================
# IMPORTS
# ============================================================================

from flask import Flask, render_template, jsonify, request, redirect
from flask_cors import CORS
import sqlite3
from datetime import datetime
import threading

try:
    from mt5_multi_collector import MT5MultiSymbolCollector
    MULTI_COLLECTOR_AVAILABLE = True
except ImportError:
    MULTI_COLLECTOR_AVAILABLE = False

try:
    from mt5_collector_v11_3 import MT5AdvancedCollector
    ADVANCED_COLLECTOR_AVAILABLE = True
except ImportError:
    ADVANCED_COLLECTOR_AVAILABLE = False

# Import symbol configuration from central config
from config import SYMBOL_DATABASES, DEFAULT_SYMBOL, COLLECTOR_TIMEFRAMES, COLLECTOR_ENABLED

# Legacy single-symbol variables (backward compatibility)
DB_PATH = SYMBOL_DATABASES[DEFAULT_SYMBOL]['db_path']

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mt5-meta-agent-v11-3-secret-key'
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ============================================================================
# DATABASE HELPERS (Legacy)
# ============================================================================

def get_db_connection():
    """Get SQLite database connection (legacy - uses default DB_PATH)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_exists():
    """Check if database file exists (legacy - uses default DB_PATH)"""
    return os.path.exists(DB_PATH)

# ============================================================================
# BC-003 | DATABASE_PATH_RESOLVER
# Logic to resolve *_intelligence.db file paths from symbol ID,
# check existence, and handle missing database files gracefully.
# STOIC Alignment: S↑ (error resilience)
# ============================================================================

def get_symbol_db_path(symbol_id):
    """
    Resolve database path for a given symbol ID.
    Returns (db_path, exists) tuple.
    """
    config = SYMBOL_DATABASES.get(symbol_id)
    if not config:
        return None, False
    
    db_path = config['db_path']
    exists = os.path.exists(db_path)
    return db_path, exists


def get_symbol_config(symbol_id):
    """
    Get full symbol configuration by ID.
    Returns config dict or None if not found.
    """
    return SYMBOL_DATABASES.get(symbol_id)


# ============================================================================
# BC-006 | DATABASE_CONNECTION_FACTORY
# Factory function to create SQLite connections to symbol-specific 
# databases with proper row_factory and error handling.
# STOIC Alignment: S↑ (consistent connection handling)
# ============================================================================

def get_symbol_db_connection(symbol_id):
    """
    Create SQLite connection to symbol-specific database.
    Returns (connection, error_message) tuple.
    Connection is None if error occurred.
    """
    db_path, exists = get_symbol_db_path(symbol_id)
    
    if db_path is None:
        return None, f"Unknown symbol: {symbol_id}"
    
    if not exists:
        return None, f"Database not found: {db_path}"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, None
    except Exception as e:
        return None, f"Connection error: {str(e)}"


# ============================================================================
# BC-004 | RECORD_COUNT_AGGREGATOR  
# SQL queries to count records in core_1m and core_15m tables per symbol.
# Must handle missing tables without crashing.
# STOIC Alignment: T↑ (measurable metrics per symbol)
# ============================================================================

def get_symbol_record_counts(symbol_id):
    """
    Get record counts for 1m and 15m timeframes from symbol database.
    Returns dict with records_1m and records_15m (0 if table missing).
    """
    conn, error = get_symbol_db_connection(symbol_id)
    
    if conn is None:
        return {'records_1m': 0, 'records_15m': 0, 'error': error}
    
    counts = {'records_1m': 0, 'records_15m': 0}
    
    try:
        cursor = conn.cursor()
        
        # Count 1m records - handle missing table gracefully
        try:
            cursor.execute("SELECT COUNT(*) as count FROM core_1m")
            result = cursor.fetchone()
            counts['records_1m'] = result['count'] if result else 0
        except sqlite3.OperationalError:
            # Table doesn't exist
            counts['records_1m'] = 0
        
        # Count 15m records - handle missing table gracefully
        try:
            cursor.execute("SELECT COUNT(*) as count FROM core_15m")
            result = cursor.fetchone()
            counts['records_15m'] = result['count'] if result else 0
        except sqlite3.OperationalError:
            # Table doesn't exist
            counts['records_15m'] = 0
        
        conn.close()
        
    except Exception as e:
        counts['error'] = str(e)
        try:
            conn.close()
        except:
            pass
    
    return counts


# ============================================================================
# GLOBAL COLLECTORS
# ============================================================================

multi_collector = None  # MT5MultiSymbolCollector instance
collectors = {}  # Legacy: Dictionary of symbol_id -> MT5AdvancedCollector
collector = None  # Legacy single collector reference

# ============================================================================
# ROUTES - ONLY CHART DATA
# ============================================================================

@app.route('/')
def index():
    """Redirect to chart-data"""
    return redirect('/chart-data')

@app.route('/chart-data')
def chart_data():
    """Intelligence Database page"""
    return render_template('chart_data.html')

@app.route('/tunity')
def tunity():
    """TUNITY Control Panel"""
    return render_template('tunity.html')

@app.route('/api/health')
def api_health():
    """Quick health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'V11.3 TUNITY',
        'database': db_exists()
    })


# ============================================================================
# BC-001 | API_SYMBOLS_ENDPOINT
# Flask route /api/symbols - returns 5 symbol databases with record counts,
# availability status, and active symbol designation.
# Critical blocker for all database UI functionality.
# STOIC Alignment: S↑ (foundation) + O↑ (unblocks everything)
# ============================================================================

@app.route('/api/symbols')
def api_symbols():
    """
    Get available symbol databases with record counts.
    
    Returns:
        - symbols: List of symbol objects with id, name, symbol, db_path, 
                   available, records_1m, records_15m
        - active_symbol: First available symbol ID (or default)
        - count: Total number of symbols
    """
    symbols = []
    
    for sym_id, config in SYMBOL_DATABASES.items():
        db_path = config['db_path']
        available = os.path.exists(db_path)
        
        # Get record counts using BC-004 aggregator
        counts = get_symbol_record_counts(sym_id) if available else {'records_1m': 0, 'records_15m': 0}
        
        symbols.append({
            'id': config['id'],
            'name': config['name'],
            'symbol': config['symbol'],
            'db_path': db_path,
            'available': available,
            'records_1m': counts.get('records_1m', 0),
            'records_15m': counts.get('records_15m', 0)
        })
    
    # Determine active symbol (first available or default)
    active_symbol = DEFAULT_SYMBOL
    for sym in symbols:
        if sym['available']:
            active_symbol = sym['id']
            break
    
    return jsonify({
        'success': True,
        'symbols': symbols,
        'active_symbol': active_symbol,
        'count': len(symbols)
    })


# ============================================================================
# BC-005 | CHART_DATA_SYMBOL_PARAM
# Modify /api/chart-data endpoint to accept symbol query parameter,
# route to correct database, and return symbol-specific OHLCV data.
# STOIC Alignment: O↑ (high-value unlock for multi-symbol support)
# ============================================================================

@app.route('/api/chart-data')
def api_chart_data():
    """
    Get OHLCV chart data for specified symbol and timeframe.
    
    Query Parameters:
        - symbol: Symbol ID (default: XAUG26)
        - timeframe: '1m' or '15m' (default: 15m)
        - limit: Number of records (default: 200)
    
    Returns:
        - success: Boolean
        - symbol: Symbol ticker
        - timeframe: Requested timeframe
        - count: Number of records returned
        - data: List of OHLCV objects
    """
    symbol_id = request.args.get('symbol', DEFAULT_SYMBOL)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 200))
    
    # Validate timeframe
    if timeframe not in ['1m', '15m']:
        timeframe = '15m'
    
    # Get symbol config
    config = get_symbol_config(symbol_id)
    if not config:
        return jsonify({
            'success': False, 
            'error': f'Unknown symbol: {symbol_id}'
        }), 404
    
    # Get database connection using BC-006 factory
    conn, error = get_symbol_db_connection(symbol_id)
    if conn is None:
        return jsonify({
            'success': False, 
            'error': error
        }), 404
    
    try:
        cursor = conn.cursor()
        table_name = f'core_{timeframe}'
        
        # Query chart data
        cursor.execute(f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {table_name}
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order for charting
        data = [dict(row) for row in reversed(rows)]
        
        return jsonify({
            'success': True,
            'symbol': config['symbol'],
            'symbol_id': symbol_id,
            'symbol_name': config['name'],
            'timeframe': timeframe,
            'count': len(data),
            'data': data
        })
        
    except sqlite3.OperationalError as e:
        conn.close()
        return jsonify({
            'success': False,
            'error': f'Table {table_name} not found. Run database initialization.'
        }), 404
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500


# ============================================================================
# BC-007 | API_PROFILES_SYMBOL_FILTER
# Enhance /api/profiles to filter by symbol parameter,
# returning only profiles associated with selected database.
# STOIC Alignment: T↑ (profile-symbol relationship tracked)
# ============================================================================

@app.route('/api/profiles')
def api_profiles():
    """
    Get trading profiles, optionally filtered by symbol.
    
    Query Parameters:
        - symbol: Symbol ID to filter by (optional)
        - limit: Number of records (default: 50)
    
    Returns:
        - success: Boolean
        - profiles: List of profile objects
        - count: Number of profiles returned
    """
    symbol_id = request.args.get('symbol', None)
    limit = int(request.args.get('limit', 50))
    
    # If symbol specified, use symbol-specific database
    if symbol_id:
        conn, error = get_symbol_db_connection(symbol_id)
        if conn is None:
            # Fall back to default database if symbol DB not found
            if not db_exists():
                return jsonify({
                    'success': False,
                    'error': 'No database available'
                }), 404
            conn = get_db_connection()
    else:
        # Use default database
        if not db_exists():
            return jsonify({
                'success': False,
                'error': 'Database not found'
            }), 404
        conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Check if profiles table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='profiles'
        """)
        
        if not cursor.fetchone():
            conn.close()
            # Return empty list if table doesn't exist (not an error)
            return jsonify({
                'success': True,
                'profiles': [],
                'count': 0,
                'message': 'No profiles table found'
            })
        
        # Query profiles
        if symbol_id:
            cursor.execute("""
                SELECT * FROM profiles 
                WHERE symbol = ? OR symbol IS NULL
                ORDER BY created_at DESC
                LIMIT ?
            """, (symbol_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM profiles 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        profiles = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'profiles': profiles,
            'count': len(profiles),
            'symbol_filter': symbol_id
        })
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# BC-008 | API_HYPERSPHERES_ENDPOINT
# New endpoint /api/hyperspheres to retrieve hypersphere configurations 
# per symbol. Prerequisite for Hyperspheres tab in Database view.
# STOIC Alignment: C↑ (new variable exposure) + O↑ (Hypersphere integration)
# ============================================================================

@app.route('/api/hyperspheres')
def api_hyperspheres():
    """
    Get hypersphere configurations, optionally filtered by symbol.
    
    Query Parameters:
        - symbol: Symbol ID to filter by (optional)
        - limit: Number of records (default: 50)
    
    Returns:
        - success: Boolean
        - hyperspheres: List of hypersphere configuration objects
        - count: Number of hyperspheres returned
    """
    symbol_id = request.args.get('symbol', None)
    limit = int(request.args.get('limit', 50))
    
    # If symbol specified, use symbol-specific database
    if symbol_id:
        conn, error = get_symbol_db_connection(symbol_id)
        if conn is None:
            # Fall back to default database
            if not db_exists():
                return jsonify({
                    'success': False,
                    'error': 'No database available'
                }), 404
            conn = get_db_connection()
    else:
        if not db_exists():
            return jsonify({
                'success': False,
                'error': 'Database not found'
            }), 404
        conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Check if hyperspheres table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hyperspheres'
        """)
        
        if not cursor.fetchone():
            conn.close()
            # Return empty list with schema hint if table doesn't exist
            return jsonify({
                'success': True,
                'hyperspheres': [],
                'count': 0,
                'message': 'No hyperspheres table found. Table will be created when Hypersphere Complex is initialized.',
                'expected_schema': {
                    'id': 'INTEGER PRIMARY KEY',
                    'name': 'TEXT',
                    'symbol': 'TEXT',
                    'state_count': 'INTEGER',
                    'classifier_type': 'TEXT',
                    'accuracy': 'REAL',
                    'last_trained': 'TIMESTAMP',
                    'config_json': 'TEXT',
                    'created_at': 'TIMESTAMP'
                }
            })
        
        # Query hyperspheres
        if symbol_id:
            cursor.execute("""
                SELECT * FROM hyperspheres 
                WHERE symbol = ? OR symbol IS NULL
                ORDER BY created_at DESC
                LIMIT ?
            """, (symbol_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM hyperspheres 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        hyperspheres = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'hyperspheres': hyperspheres,
            'count': len(hyperspheres),
            'symbol_filter': symbol_id
        })
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# LEGACY API ENDPOINTS (Updated to support symbol parameter)
# ============================================================================

@app.route('/api/core')
def api_core():
    """Get core market data (OHLCV) - supports symbol parameter"""
    symbol_id = request.args.get('symbol', None)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    # Use symbol-specific or default database
    if symbol_id:
        conn, error = get_symbol_db_connection(symbol_id)
        if conn is None:
            return jsonify({'success': False, 'error': error}), 404
    else:
        if not db_exists():
            return jsonify({'error': 'Database not found'}), 404
        conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        table_name = f'core_{timeframe}' if timeframe in ['1m', '15m'] else 'core_15m'
        
        cursor.execute(f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {table_name}
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'count': len(data),
            'data': data,
            'symbol': symbol_id
        })
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/basic')
def api_basic():
    """Get basic indicators data - supports symbol parameter"""
    symbol_id = request.args.get('symbol', None)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    if symbol_id:
        conn, error = get_symbol_db_connection(symbol_id)
        if conn is None:
            return jsonify({'success': False, 'error': error}), 404
    else:
        if not db_exists():
            return jsonify({'error': 'Database not found'}), 404
        conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        table_name = f'basic_{timeframe}' if timeframe in ['1m', '15m'] else 'basic_15m'
        
        cursor.execute(f"""
            SELECT timestamp, atr_14, atr_50_avg, atr_ratio,
                   ema_short, ema_medium, ema_distance, supertrend
            FROM {table_name}
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'count': len(data),
            'data': data,
            'symbol': symbol_id
        })
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/advanced')
def api_advanced():
    """Get advanced indicators data (V11.3) - supports symbol parameter"""
    symbol_id = request.args.get('symbol', None)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    if symbol_id:
        conn, error = get_symbol_db_connection(symbol_id)
        if conn is None:
            return jsonify({'success': False, 'error': error}), 404
    else:
        if not db_exists():
            return jsonify({'error': 'Database not found'}), 404
        conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Check if advanced_indicators table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='advanced_indicators'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Advanced indicators table not found. Run: python init_v11_3_advanced.py'
            }), 404
        
        cursor.execute("""
            SELECT * FROM advanced_indicators
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
            'data': data,
            'version': 'V11.3',
            'symbol': symbol_id
        })
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fibonacci')
def api_fibonacci():
    """Get Fibonacci zone data - supports symbol parameter"""
    symbol_id = request.args.get('symbol', None)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    if symbol_id:
        conn, error = get_symbol_db_connection(symbol_id)
        if conn is None:
            return jsonify({'success': False, 'error': error}), 404
    else:
        if not db_exists():
            return jsonify({'error': 'Database not found'}), 404
        conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, current_fib_zone, in_golden_zone, zone_multiplier,
                   pivot_high, pivot_low, fib_level_0382, fib_level_0618,
                   fib_level_0786, distance_to_next_level
            FROM fibonacci_data
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
            'data': data,
            'symbol': symbol_id
        })
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ath')
def api_ath():
    """Get ATH tracking data - supports symbol parameter"""
    symbol_id = request.args.get('symbol', None)
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 10))
    
    if symbol_id:
        conn, error = get_symbol_db_connection(symbol_id)
        if conn is None:
            return jsonify({'success': False, 'error': error}), 404
    else:
        if not db_exists():
            return jsonify({'error': 'Database not found'}), 404
        conn = get_db_connection()
    
    try:
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
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'count': len(data),
            'data': data,
            'symbol': symbol_id
        })
        
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# APEX V2.0 API ENDPOINTS
# ============================================================================

@app.route('/api/indicator-groups')
def api_indicator_groups():
    """Get indicator groups (Apex V2.0)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, is_active, display_order, created_at
            FROM indicator_groups
            ORDER BY display_order ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data,
            'version': 'Apex V2.0'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/indicators')
def api_indicators():
    """Get indicators catalog (Apex V2.0)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        group_id = request.args.get('group_id', None)
        limit = int(request.args.get('limit', 200))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if group_id:
            cursor.execute("""
                SELECT i.id, i.name, i.display_name, i.description, 
                       i.logic_base_id, i.default_group_id, i.created_at,
                       ig.name as group_name
                FROM indicators i
                LEFT JOIN indicator_groups ig ON i.default_group_id = ig.id
                WHERE i.default_group_id = ?
                ORDER BY i.id ASC
                LIMIT ?
            """, (group_id, limit))
        else:
            cursor.execute("""
                SELECT i.id, i.name, i.display_name, i.description, 
                       i.logic_base_id, i.default_group_id, i.created_at,
                       ig.name as group_name
                FROM indicators i
                LEFT JOIN indicator_groups ig ON i.default_group_id = ig.id
                ORDER BY i.default_group_id, i.id ASC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data,
            'version': 'Apex V2.0'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/indicator-configs')
def api_indicator_configs():
    """Get indicator configs with full details (Apex V2.0)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        group_id = request.args.get('group_id', None)
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 200))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT ic.id, ic.indicator_id, ic.scope, ic.is_active, 
                   ic.group_id, ic.display_order, ic.last_updated_at,
                   i.name as indicator_name, i.display_name, i.logic_base_id,
                   ig.name as group_name
            FROM indicator_configs ic
            JOIN indicators i ON ic.indicator_id = i.id
            JOIN indicator_groups ig ON ic.group_id = ig.id
            WHERE 1=1
        """
        params = []
        
        if group_id:
            query += " AND ic.group_id = ?"
            params.append(group_id)
        
        if active_only:
            query += " AND ic.is_active = 1"
        
        query += " ORDER BY ic.group_id, ic.display_order ASC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data,
            'version': 'Apex V2.0'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation-settings')
def api_evaluation_settings():
    """Get evaluation settings (Apex V2.0)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, bar_interval_mode, time_window_minutes, 
                   last_evaluation_at, created_at, updated_at
            FROM evaluation_settings
            WHERE id = 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            return jsonify({
                'success': True,
                'data': data,
                'version': 'Apex V2.0'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No evaluation settings found'
            }), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai-analysis-results')
def api_ai_analysis_results():
    """Get AI analysis results (Apex V2.0)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        symbol = request.args.get('symbol', None)
        timeframe = request.args.get('timeframe', None)
        limit = int(request.args.get('limit', 20))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM ai_analysis_results WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data,
            'version': 'Apex V2.0'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/group-summary')
def api_group_summary():
    """Get summary of indicators per group (Apex V2.0)"""
    if not db_exists():
        return jsonify({'error': 'Database not found'}), 404
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ig.id as group_id,
                ig.name as group_name,
                ig.description,
                ig.is_active,
                ig.display_order,
                COUNT(ic.id) as total_indicators,
                SUM(CASE WHEN ic.is_active = 1 THEN 1 ELSE 0 END) as active_indicators
            FROM indicator_groups ig
            LEFT JOIN indicator_configs ic ON ic.group_id = ig.id
            GROUP BY ig.id, ig.name, ig.description, ig.is_active, ig.display_order
            ORDER BY ig.display_order
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data,
            'version': 'Apex V2.0'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """Check system status - enhanced with symbol database info"""
    global collector, collectors, multi_collector
    
    # Determine collector status
    if multi_collector:
        collector_running = multi_collector.running
        collector_type = 'multi'
        collector_stats = multi_collector.get_stats() if multi_collector.running else None
    elif collectors:
        collector_running = any(c.running for c in collectors.values())
        collector_type = 'legacy_multi'
        collector_stats = None
    elif collector:
        collector_running = collector.running
        collector_type = 'legacy_single'
        collector_stats = None
    else:
        collector_running = False
        collector_type = 'none'
        collector_stats = None
    
    status = {
        'database_connected': db_exists(),
        'collector_running': collector_running,
        'collector_type': collector_type,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'V11.3',
        'multi_collector_available': MULTI_COLLECTOR_AVAILABLE,
        'advanced_collector': ADVANCED_COLLECTOR_AVAILABLE
    }
    
    if collector_stats:
        status['collector_stats'] = collector_stats
    
    # Add symbol database status
    symbol_status = {}
    for sym_id, config in SYMBOL_DATABASES.items():
        db_path = config['db_path']
        exists = os.path.exists(db_path)
        counts = get_symbol_record_counts(sym_id) if exists else {'records_1m': 0, 'records_15m': 0}
        symbol_status[sym_id] = {
            'name': config['name'],
            'available': exists,
            'records_1m': counts.get('records_1m', 0),
            'records_15m': counts.get('records_15m', 0)
        }
    status['symbol_databases'] = symbol_status
    
    if db_exists():
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='1m'")
            count_1m = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='15m'")
            count_15m = cursor.fetchone()['count']
            
            # Check for advanced indicators table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='advanced_indicators'
            """)
            has_advanced = cursor.fetchone() is not None
            
            if has_advanced:
                cursor.execute("SELECT COUNT(*) as count FROM advanced_indicators WHERE timeframe='1m'")
                adv_count_1m = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM advanced_indicators WHERE timeframe='15m'")
                adv_count_15m = cursor.fetchone()['count']
            else:
                adv_count_1m = 0
                adv_count_15m = 0
            
            conn.close()
            
            status['records_1m'] = count_1m
            status['records_15m'] = count_15m
            status['advanced_indicators_table'] = has_advanced
            status['advanced_records_1m'] = adv_count_1m
            status['advanced_records_15m'] = adv_count_15m
            
            # Add collector stats (multi-collector aware)
            if collectors:
                collector_stats = {}
                for sym_id, coll in collectors.items():
                    collector_stats[sym_id] = {
                        'running': coll.running,
                        'collection_counts': coll.collection_counts,
                        'error_count': coll.error_count
                    }
                status['collector_stats'] = collector_stats
            elif collector:
                status['collection_counts'] = collector.collection_counts
                status['error_count'] = collector.error_count
            
        except Exception as e:
            status['database_error'] = str(e)
    
    return jsonify(status)


# ============================================================================
# STARTUP
# ============================================================================

def startup_checks():
    """Run startup checks"""
    global collector
    
    print("\n" + "="*70)
    print("MT5 META AGENT V11.3 - APEX BUG CLEANUP PHASE 1")
    print("API_FOUNDATION: BC-001 through BC-008 IMPLEMENTED")
    print("="*70)
    
    # Check symbol databases
    print("\nSYMBOL DATABASES:")
    for sym_id, config in SYMBOL_DATABASES.items():
        db_path = config['db_path']
        exists = os.path.exists(db_path)
        status = "✓ FOUND" if exists else "✗ NOT FOUND"
        if exists:
            counts = get_symbol_record_counts(sym_id)
            print(f"  {sym_id:12s} {status:12s} | 1m: {counts['records_1m']:>6} | 15m: {counts['records_15m']:>6}")
        else:
            print(f"  {sym_id:12s} {status}")
    
    print()
    
    if db_exists():
        print(f"✓ Default database found: {DB_PATH}")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='15m'")
            count_15m = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='advanced_indicators'
            """)
            has_advanced = cursor.fetchone() is not None
            
            if has_advanced:
                cursor.execute("SELECT COUNT(*) as count FROM advanced_indicators WHERE timeframe='15m'")
                adv_count_15m = cursor.fetchone()['count']
                print(f"✓ Advanced Indicators Table: PRESENT")
                print(f"  Records (15m): {adv_count_15m}")
            else:
                print(f"⚠️  Advanced Indicators Table: NOT FOUND")
                print(f"  Run: python init_v11_3_advanced.py")
            
            print(f"  Core Records (15m): {count_15m}")
            
            conn.close()
            
        except Exception as e:
            print(f"✗ Database error: {e}")
    else:
        print(f"✗ Default database not found: {DB_PATH}")
        print("  Run: python init.py")
    
    if COLLECTOR_ENABLED and MULTI_COLLECTOR_AVAILABLE:
        print(f"\n[STARTUP] Initializing multi-symbol collector...")
        
        # Build config for available databases
        valid_symbols = {}
        for sym_id, config in SYMBOL_DATABASES.items():
            db_path = config['db_path']
            if os.path.exists(db_path):
                valid_symbols[sym_id] = config
                print(f"  ✓ {sym_id}: {config['name']}")
            else:
                print(f"  ⚠️  {sym_id}: database not found")
        
        if valid_symbols:
            multi_collector = MT5MultiSymbolCollector(
                symbols_config=valid_symbols,
                timeframes=COLLECTOR_TIMEFRAMES
            )
            
            if multi_collector.connect_mt5():
                thread = threading.Thread(
                    target=multi_collector.run,
                    kwargs={'interval': 30},
                    daemon=True,
                    name='multi_collector'
                )
                thread.start()
                print(f"\n✓ Multi-symbol collector started ({len(valid_symbols)} symbols)")
            else:
                print("\n✗ Multi-symbol collector failed to connect to MT5")
                multi_collector = None
        else:
            print("\n✗ No databases found - collector not started")
    elif COLLECTOR_ENABLED and ADVANCED_COLLECTOR_AVAILABLE:
        # Fallback to legacy single-symbol collector
        print(f"\n[STARTUP] Initializing legacy collector (multi-collector not available)...")
        
        for sym_id, config in SYMBOL_DATABASES.items():
            db_path = config['db_path']
            mt5_symbol = config['symbol']
            
            if not os.path.exists(db_path):
                continue
            
            try:
                coll = MT5AdvancedCollector(
                    symbol=mt5_symbol,
                    db_path=db_path,
                    timeframes=COLLECTOR_TIMEFRAMES
                )
                
                if coll.connect_mt5():
                    coll.running = True
                    thread = threading.Thread(target=coll.run, daemon=True, name=f"collector_{sym_id}")
                    thread.start()
                    collectors[sym_id] = coll
                    print(f"  ✓ Started collector for {sym_id}")
                    break  # Only start one in legacy mode
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        if collectors:
            collector = list(collectors.values())[0]
            print(f"\n✓ Legacy collector started")
        else:
            print("\n✗ Legacy collector failed to start")
    else:
        print("\n⚠️  Collectors disabled")
    
    print("\n" + "="*70)
    print("NEW API ENDPOINTS (Bug Cleanup Phase 1):")
    print("  /api/symbols          - List all symbol databases")
    print("  /api/chart-data       - OHLCV data (now supports ?symbol=)")
    print("  /api/profiles         - Trading profiles (now supports ?symbol=)")
    print("  /api/hyperspheres     - Hypersphere configurations")
    print("="*70)
    print("Starting Flask server...")
    print("Database View:    http://localhost:5000/chart-data")
    print("TUNITY Control:   http://localhost:5000/tunity")
    print("API Symbols:      http://localhost:5000/api/symbols")
    print("API Status:       http://localhost:5000/api/status")
    print("="*70 + "\n")


def shutdown():
    """Cleanup on shutdown"""
    global collector, collectors, multi_collector
    
    if multi_collector and multi_collector.running:
        print("\nShutting down multi-symbol collector...")
        multi_collector.stop()
        multi_collector.disconnect_mt5()
    elif collectors:
        print(f"\nShutting down {len(collectors)} collector(s)...")
        for sym_id, coll in collectors.items():
            if coll.running:
                coll.running = False
                print(f"  Stopped: {sym_id}")
    elif collector and collector.running:
        print("\nShutting down collector...")
        collector.running = False

import atexit
atexit.register(shutdown)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    startup_checks()
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )
