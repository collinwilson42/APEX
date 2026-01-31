"""
MT5 META AGENT V11.3 - UNIFIED STARTUP & INITIALIZATION
============================================================
TUNITY UNIFIED EDITION - Single Entry Point
MULTI-SYMBOL DATABASE SUPPORT

This unified init.py:
1. Creates/repairs database with correct schema
2. Initializes all tables (core, basic, advanced, fibonacci, ath, apex v2.0)
3. Starts the Flask application with all endpoints
4. Supports multiple symbol databases selectable from APEX dropdown
5. Runs the data collector

Usage: py -3.11 init.py
"""

import sys
import subprocess
import os
import sqlite3
from datetime import datetime
import threading
import atexit

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

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
    
    print("="*70 + "\n")
    return True

if not check_and_install_dependencies():
    print("\n✗ Dependency installation failed")
    sys.exit(1)

# ============================================================================
# NOW IMPORT EVERYTHING
# ============================================================================

from flask import Flask, render_template, jsonify, request, redirect, send_from_directory
from flask_cors import CORS
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default database (legacy support)
DB_PATH = 'mt5_intelligence.db'

# Multi-symbol database configuration (5 symbol DBs + 1 analytics DB)
SYMBOL_DATABASES = {
    'XAUG26': {
        'db': 'XAUG26_intelligence.db',
        'symbol': 'XAUG26.sim',
        'name': 'Gold Futures',
        'description': 'Gold Futures (XAUG26)'
    },
    'BTCZ25': {
        'db': 'BTCZ25_intelligence.db',
        'symbol': 'BTCZ25.sim',
        'name': 'BTC Futures',
        'description': 'Bitcoin Futures (BTCZ25)'
    },
    'US500Z25': {
        'db': 'US500Z25_intelligence.db',
        'symbol': 'US500Z25.sim',
        'name': 'S&P 500 Futures',
        'description': 'S&P 500 Index Futures'
    },
    'US100Z25': {
        'db': 'US100Z25_intelligence.db',
        'symbol': 'US100Z25.sim',
        'name': 'NASDAQ 100 Futures',
        'description': 'NASDAQ 100 Index Futures'
    },
    'US30Z25': {
        'db': 'US30Z25_intelligence.db',
        'symbol': 'US30Z25.sim',
        'name': 'Dow Jones Futures',
        'description': 'Dow Jones Industrial Average Futures'
    },
}

# Analytics database (stores cross-symbol analysis)
ANALYTICS_DB = {
    'db': 'analytics_intelligence.db',
    'name': 'Analytics Database',
    'description': 'Cross-Symbol Analysis'
}

# Currently active database (can be changed at runtime)
ACTIVE_SYMBOL = 'XAUG26'  # Default to Gold

COLLECTOR_ENABLED = True
COLLECTOR_TIMEFRAMES = ['1m', '15m']

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_active_db_path():
    """Get the path to the currently active symbol database"""
    global ACTIVE_SYMBOL
    
    if ACTIVE_SYMBOL in SYMBOL_DATABASES:
        db_path = SYMBOL_DATABASES[ACTIVE_SYMBOL]['db']
        if os.path.exists(db_path):
            return db_path
    
    # Fallback to legacy database
    return DB_PATH

def get_db_connection(db_path=None):
    """Get SQLite database connection"""
    if db_path is None:
        db_path = get_active_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def db_exists(db_path=None):
    """Check if database file exists"""
    if db_path is None:
        db_path = get_active_db_path()
    return os.path.exists(db_path)

def safe_query(query, params=(), fetch_one=False, db_path=None):
    """Execute query with error handling"""
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch_one:
            result = cursor.fetchone()
            result = dict(result) if result else None
        else:
            result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result
    except Exception as e:
        print(f"Query error: {e}")
        return None if fetch_one else []

# ============================================================================
# DATABASE INITIALIZATION & REPAIR
# ============================================================================

def init_database():
    """Initialize/repair the complete database schema"""
    
    print("\n" + "="*70)
    print("DATABASE INITIALIZATION & REPAIR")
    print("="*70)
    
    # Check for symbol-specific databases
    available_dbs = []
    for key, config in SYMBOL_DATABASES.items():
        if os.path.exists(config['db']):
            size_mb = os.path.getsize(config['db']) / (1024*1024)
            available_dbs.append(f"  ✓ {config['name']:20s} ({config['db']}) - {size_mb:.1f} MB")
        else:
            available_dbs.append(f"  ✗ {config['name']:20s} ({config['db']}) - NOT FOUND")
    
    print("\nSymbol Databases:")
    for db_info in available_dbs:
        print(db_info)
    
    # Initialize legacy database if no symbol databases exist
    any_symbol_db = any(os.path.exists(c['db']) for c in SYMBOL_DATABASES.values())
    
    if not any_symbol_db:
        print("\n⚠ No symbol databases found. Initializing legacy database...")
        return init_legacy_database()
    
    print("\n✓ Symbol databases detected. Using multi-symbol mode.")
    return True

def init_legacy_database():
    """Initialize legacy single database (fallback)"""
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Core tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_15m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, timeframe, symbol)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_timestamp ON core_15m(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_timeframe ON core_15m(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_symbol ON core_15m(symbol)")
        
        # Basic indicators
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS basic_15m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                symbol TEXT NOT NULL,
                atr_14 REAL NOT NULL,
                atr_50_avg REAL NOT NULL,
                atr_ratio REAL NOT NULL,
                ema_short REAL NOT NULL,
                ema_medium REAL NOT NULL,
                ema_distance REAL NOT NULL,
                supertrend TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, timeframe, symbol)
            )
        """)
        
        # Collection stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timeframe TEXT NOT NULL UNIQUE,
                total_collections INTEGER DEFAULT 0,
                successful_collections INTEGER DEFAULT 0,
                failed_collections INTEGER DEFAULT 0,
                last_collection TEXT,
                last_error TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO collection_stats (timeframe, total_collections) 
            VALUES ('1m', 0), ('15m', 0)
        """)
        
        # APEX instances
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apex_instances (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT,
                instance_type TEXT NOT NULL DEFAULT 'database',
                signals_today INTEGER DEFAULT 0,
                trend REAL DEFAULT 0,
                pf REAL DEFAULT 0,
                np REAL DEFAULT 0,
                regime TEXT,
                confidence INTEGER DEFAULT 0,
                settings TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✓ Legacy database initialized: {DB_PATH}")
        return True
        
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        return False

# ============================================================================
# FLASK APPLICATION
# ============================================================================

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'mt5-meta-agent-v11-3-tunity-unified'
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Global collector reference
collector = None

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """APEX Dashboard - Main Homepage"""
    return render_template('apex.html')

@app.route('/apex')
def apex():
    """APEX Dashboard - Explicit Route"""
    return render_template('apex.html')

@app.route('/chart-data')
@app.route('/database')
def chart_data():
    """Intelligence Database page"""
    return render_template('chart_data.html')

@app.route('/tunity')
def tunity():
    """TUNITY Control Panel page"""
    return render_template('tunity.html')

@app.route('/fingerprint')
def fingerprint():
    """Fingerprint System - 2D Radial with Fibonacci Rings"""
    return render_template('fingerprint.html')

# ============================================================================
# API ENDPOINTS - SYMBOL DATABASE MANAGEMENT
# ============================================================================

@app.route('/api/symbols')
def api_symbols():
    """Get list of available symbol databases"""
    symbols = []
    
    for key, config in SYMBOL_DATABASES.items():
        exists = os.path.exists(config['db'])
        size_mb = os.path.getsize(config['db']) / (1024*1024) if exists else 0
        
        # Get record counts if database exists
        records_1m = 0
        records_15m = 0
        if exists:
            try:
                data = safe_query("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='1m'", 
                                  db_path=config['db'], fetch_one=True)
                records_1m = data['count'] if data else 0
                
                data = safe_query("SELECT COUNT(*) as count FROM core_15m WHERE timeframe='15m'", 
                                  db_path=config['db'], fetch_one=True)
                records_15m = data['count'] if data else 0
            except:
                pass
        
        symbols.append({
            'id': key,
            'symbol': config['symbol'],
            'name': config['name'],
            'description': config['description'],
            'db': config['db'],
            'available': exists,
            'size_mb': round(size_mb, 2),
            'records_1m': records_1m,
            'records_15m': records_15m,
            'active': key == ACTIVE_SYMBOL
        })
    
    return jsonify({
        'success': True,
        'active_symbol': ACTIVE_SYMBOL,
        'count': len(symbols),
        'symbols': symbols
    })

@app.route('/api/symbols/active', methods=['GET', 'POST'])
def api_active_symbol():
    """Get or set the active symbol database"""
    global ACTIVE_SYMBOL
    
    if request.method == 'POST':
        data = request.get_json()
        symbol_id = data.get('symbol_id', '').upper()
        
        if symbol_id not in SYMBOL_DATABASES:
            return jsonify({'success': False, 'error': f'Unknown symbol: {symbol_id}'}), 400
        
        if not os.path.exists(SYMBOL_DATABASES[symbol_id]['db']):
            return jsonify({'success': False, 'error': f'Database not found for {symbol_id}. Run fillall.py first.'}), 400
        
        ACTIVE_SYMBOL = symbol_id
        config = SYMBOL_DATABASES[symbol_id]
        
        return jsonify({
            'success': True,
            'active_symbol': ACTIVE_SYMBOL,
            'name': config['name'],
            'symbol': config['symbol'],
            'db': config['db']
        })
    
    # GET request
    config = SYMBOL_DATABASES.get(ACTIVE_SYMBOL, {})
    return jsonify({
        'success': True,
        'active_symbol': ACTIVE_SYMBOL,
        'name': config.get('name', 'Unknown'),
        'symbol': config.get('symbol', ''),
        'db': config.get('db', DB_PATH)
    })

# ============================================================================
# API ENDPOINTS - CORE DATA (Multi-Symbol Aware)
# ============================================================================

@app.route('/api/core')
def api_core():
    """Get core OHLCV data from active symbol database"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 50))
    symbol_id = request.args.get('symbol', None)
    
    # Use specified symbol or active symbol
    if symbol_id and symbol_id.upper() in SYMBOL_DATABASES:
        db_path = SYMBOL_DATABASES[symbol_id.upper()]['db']
    else:
        db_path = get_active_db_path()
    
    if not os.path.exists(db_path):
        return jsonify({'success': False, 'error': 'Database not found', 'data': []}), 200
    
    try:
        data = safe_query("""
            SELECT timestamp, symbol, open, high, low, close, volume
            FROM core_15m
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit), db_path=db_path)
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'database': os.path.basename(db_path),
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []}), 200

@app.route('/api/basic')
def api_basic():
    """Get basic indicators from active symbol database"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 50))
    symbol_id = request.args.get('symbol', None)
    
    if symbol_id and symbol_id.upper() in SYMBOL_DATABASES:
        db_path = SYMBOL_DATABASES[symbol_id.upper()]['db']
    else:
        db_path = get_active_db_path()
    
    if not os.path.exists(db_path):
        return jsonify({'success': False, 'error': 'Database not found', 'data': []}), 200
    
    try:
        data = safe_query("""
            SELECT timestamp, atr_14, atr_50_avg, atr_ratio, 
                   ema_short, ema_medium, ema_distance, supertrend
            FROM basic_15m
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit), db_path=db_path)
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'database': os.path.basename(db_path),
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []}), 200

@app.route('/api/advanced')
def api_advanced():
    """Get advanced indicators from active symbol database"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 50))
    symbol_id = request.args.get('symbol', None)
    
    if symbol_id and symbol_id.upper() in SYMBOL_DATABASES:
        db_path = SYMBOL_DATABASES[symbol_id.upper()]['db']
    else:
        db_path = get_active_db_path()
    
    if not os.path.exists(db_path):
        return jsonify({'success': False, 'error': 'Database not found', 'data': []}), 200
    
    try:
        data = safe_query("""
            SELECT *
            FROM advanced_indicators
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit), db_path=db_path)
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'database': os.path.basename(db_path),
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []}), 200

@app.route('/api/fibonacci')
def api_fibonacci():
    """Get Fibonacci data from active symbol database"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 50))
    symbol_id = request.args.get('symbol', None)
    
    if symbol_id and symbol_id.upper() in SYMBOL_DATABASES:
        db_path = SYMBOL_DATABASES[symbol_id.upper()]['db']
    else:
        db_path = get_active_db_path()
    
    if not os.path.exists(db_path):
        return jsonify({'success': False, 'error': 'Database not found', 'data': []}), 200
    
    try:
        data = safe_query("""
            SELECT *
            FROM fibonacci_data
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit), db_path=db_path)
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'database': os.path.basename(db_path),
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []}), 200

@app.route('/api/ath')
def api_ath():
    """Get ATH tracking data from active symbol database"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 50))
    symbol_id = request.args.get('symbol', None)
    
    if symbol_id and symbol_id.upper() in SYMBOL_DATABASES:
        db_path = SYMBOL_DATABASES[symbol_id.upper()]['db']
    else:
        db_path = get_active_db_path()
    
    if not os.path.exists(db_path):
        return jsonify({'success': False, 'error': 'Database not found', 'data': []}), 200
    
    try:
        data = safe_query("""
            SELECT *
            FROM ath_tracking
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit), db_path=db_path)
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'database': os.path.basename(db_path),
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []}), 200

@app.route('/api/chart-data')
def api_chart_data():
    """Get OHLCV data for charts from active symbol database"""
    timeframe = request.args.get('timeframe', '15m')
    limit = int(request.args.get('limit', 200))
    symbol_id = request.args.get('symbol', None)
    
    if symbol_id and symbol_id.upper() in SYMBOL_DATABASES:
        db_path = SYMBOL_DATABASES[symbol_id.upper()]['db']
        symbol_name = SYMBOL_DATABASES[symbol_id.upper()]['symbol']
    else:
        db_path = get_active_db_path()
        symbol_name = SYMBOL_DATABASES.get(ACTIVE_SYMBOL, {}).get('symbol', 'UNKNOWN')
    
    if not os.path.exists(db_path):
        return jsonify({'success': False, 'error': 'Database not found', 'data': []}), 200
    
    try:
        data = safe_query("""
            SELECT timestamp, open, high, low, close, volume
            FROM core_15m
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit), db_path=db_path)
        
        # Reverse to chronological order
        if data:
            data = list(reversed(data))
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'symbol': symbol_name,
            'database': os.path.basename(db_path),
            'count': len(data) if data else 0,
            'data': data or []
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []})

# ============================================================================
# API ENDPOINTS - APEX INSTANCES
# ============================================================================

@app.route('/api/apex/instances', methods=['GET'])
def api_apex_instances():
    """Get APEX instances for tab dropdown"""
    instance_type = request.args.get('type', 'database')
    
    # Build instances from available symbol databases
    if instance_type == 'database':
        instances = []
        for key, config in SYMBOL_DATABASES.items():
            if os.path.exists(config['db']):
                # Get latest data stats
                try:
                    core_data = safe_query(
                        "SELECT COUNT(*) as cnt FROM core_15m WHERE timeframe='15m'",
                        db_path=config['db'], fetch_one=True
                    )
                    record_count = core_data['cnt'] if core_data else 0
                except:
                    record_count = 0
                
                instances.append({
                    'id': f'db_{key.lower()}',
                    'name': config['name'],
                    'symbol': config['symbol'],
                    'signals_today': record_count,
                    'trend': 0,
                    'pf': 0,
                    'np': 0,
                    'db_key': key
                })
        
        return jsonify({
            'success': True,
            'type': instance_type,
            'count': len(instances),
            'instances': instances
        })
    
    # Trading instances
    instances = []
    for key, config in SYMBOL_DATABASES.items():
        if os.path.exists(config['db']):
            instances.append({
                'id': f'tr_{key.lower()}',
                'name': f"{config['name']} Trading",
                'symbol': config['symbol'],
                'regime': 'N',
                'confidence': 50,
                'db_key': key
            })
    
    return jsonify({
        'success': True,
        'type': instance_type,
        'count': len(instances),
        'instances': instances
    })

@app.route('/api/apex/instances', methods=['POST'])
def api_apex_create_instance():
    """Create a new APEX instance"""
    try:
        data = request.get_json()
        instance_type = data.get('type', 'database')
        name = data.get('name', '').strip()
        symbol = data.get('symbol', '').strip() or None
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        prefix = 'db_' if instance_type == 'database' else 'tr_'
        instance_id = prefix + datetime.now().strftime('%Y%m%d%H%M%S')
        
        return jsonify({
            'success': True,
            'instance': {
                'id': instance_id,
                'name': name,
                'symbol': symbol,
                'instance_type': instance_type
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# API ENDPOINTS - STATUS & HEALTH
# ============================================================================

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'APEX',
        'version': 'V11.3',
        'active_symbol': ACTIVE_SYMBOL,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/status')
def api_status():
    """Check system status"""
    global collector
    
    status = {
        'database_connected': db_exists(),
        'collector_running': collector.running if collector else False,
        'active_symbol': ACTIVE_SYMBOL,
        'active_db': get_active_db_path(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'V11.3 TUNITY Multi-Symbol'
    }
    
    # Check all symbol databases
    status['symbol_databases'] = {}
    for key, config in SYMBOL_DATABASES.items():
        exists = os.path.exists(config['db'])
        status['symbol_databases'][key] = {
            'available': exists,
            'db': config['db'],
            'name': config['name']
        }
        if exists:
            try:
                data = safe_query("SELECT COUNT(*) as cnt FROM core_15m WHERE timeframe='15m'", 
                                  db_path=config['db'], fetch_one=True)
                status['symbol_databases'][key]['records_15m'] = data['cnt'] if data else 0
            except:
                status['symbol_databases'][key]['records_15m'] = 0
    
    return jsonify(status)

# ============================================================================
# STARTUP
# ============================================================================

def startup():
    """Main startup sequence"""
    global collector
    
    print("\n" + "="*70)
    print("MT5 META AGENT V11.3 - TUNITY UNIFIED EDITION")
    print("MULTI-SYMBOL DATABASE SUPPORT")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Initialize database
    if not init_database():
        print("\n⚠ Database initialization warning - continuing anyway")
    
    # Try to start collector
    try:
        from mt5_collector_v11_3 import MT5AdvancedCollector
        
        print("\n" + "="*70)
        print("STARTING MT5 COLLECTOR")
        print("="*70)
        
        collector = MT5AdvancedCollector()
        
        if collector.connect_mt5():
            collector.running = True
            collector_thread = threading.Thread(target=collector.run, daemon=True)
            collector_thread.start()
            print("✓ Advanced collector started")
        else:
            print("⚠️  MT5 connection failed - collector disabled")
            collector = None
    except ImportError:
        print("\n⚠️  MT5 collector not available")
        collector = None
    except Exception as e:
        print(f"\n⚠️  Collector error: {e}")
        collector = None
    
    print("\n" + "="*70)
    print("FLASK SERVER STARTING")
    print("="*70)
    print(f"\n🏠 APEX Dashboard:        http://localhost:5000/")
    print(f"📊 Intelligence Database: http://localhost:5000/chart-data")
    print(f"🎛️  TUNITY Control Panel: http://localhost:5000/tunity")
    print(f"\n📡 API Endpoints:")
    print(f"   /api/symbols          - List available symbol databases")
    print(f"   /api/symbols/active   - Get/set active symbol")
    print(f"   /api/chart-data       - OHLCV data for charts")
    print(f"   /api/status           - System status")
    print(f"   /api/health           - Health check")
    print(f"\n🎯 Active Symbol: {ACTIVE_SYMBOL} ({SYMBOL_DATABASES[ACTIVE_SYMBOL]['name']})")
    print("\n" + "="*70 + "\n")

def shutdown():
    """Cleanup on shutdown"""
    global collector
    if collector and hasattr(collector, 'running') and collector.running:
        print("\nShutting down collector...")
        collector.running = False

atexit.register(shutdown)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    startup()
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )
