"""
═══════════════════════════════════════════════════════════════════════════════
APEX Flask Server
Family F: SYSTEM_INFRASTRUCTURE_BRIDGE | PC-251 Flask Static Serving
═══════════════════════════════════════════════════════════════════════════════

Lightweight Flask server for APEX UI.
Serves static files and the main template.
Includes sentiment engine integration.
"""

from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

# Enable CORS for development
CORS(app)

# ═══════════════════════════════════════════════════════════════════════════════
# SENTIMENT ENGINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

sentiment_scheduler = None

try:
    from sentiment_engine import (
        SentimentConfig, 
        SentimentScheduler, 
        SentimentDatabase,
        register_sentiment_routes
    )
    
    # Initialize sentiment engine
    sentiment_config = SentimentConfig(
        api_key=os.getenv('ANTHROPIC_API_KEY', ''),
        db_path=os.path.join(BASE_DIR, 'sentiment_analysis.db')
    )
    
    # Default symbols - can be configured
    DEFAULT_SYMBOLS = ['XAUJ26', 'US100H26', 'BTCF26']
    
    sentiment_scheduler = SentimentScheduler(sentiment_config, DEFAULT_SYMBOLS)
    
    # Register sentiment API routes
    register_sentiment_routes(app, sentiment_scheduler)
    
    logger.info("Sentiment engine initialized")
    
except ImportError as e:
    logger.warning(f"Sentiment engine not available: {e}")
except Exception as e:
    logger.error(f"Failed to initialize sentiment engine: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# INSTANCE DATABASE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

instance_db = None

try:
    from instance_database import get_instance_db, AlgorithmInstance
    from dataclasses import asdict
    
    instance_db = get_instance_db(os.path.join(BASE_DIR, 'apex_instances.db'))
    logger.info("Instance database initialized")
    
except ImportError as e:
    logger.warning(f"Instance database not available: {e}")
except Exception as e:
    logger.error(f"Failed to initialize instance database: {e}")


# Instance API Routes
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
    
    # Convert to dicts — flat array for frontend .filter() compatibility
    active_list = [asdict(i) for i in grouped["active"]]
    archived_list = [asdict(i) for i in grouped["archived"]]
    all_instances = active_list + archived_list
    
    return jsonify({
        "success": True, 
        "instances": all_instances,
        "active": active_list,
        "archived": archived_list
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
        logger.error(f"Failed to create instance: {e}")
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


@app.route('/api/instance/<instance_id>/initialize', methods=['POST'])
def api_initialize_instance(instance_id):
    """
    Initialize database tables for a localStorage algorithm instance.
    Called when user selects an algorithm in the Instance Browser.
    Creates the 4 linked tables: positions, sentiments, transitions, matrices
    """
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    data = request.get_json() or {}
    symbol = data.get('symbol', 'UNKNOWN').upper()
    display_name = data.get('name', f'{symbol} Algorithm')
    
    try:
        # Check if instance already exists in backend
        existing = instance_db.get_instance(instance_id)
        
        if existing:
            # Already initialized
            return jsonify({
                "success": True,
                "message": "Instance already initialized",
                "instance_id": instance_id,
                "tables_created": []
            })
        
        # Create new instance with all 4 tables
        instance = instance_db.create_instance(
            symbol=symbol,
            display_name=display_name,
            account_type='SIM'  # Default to SIM for algorithm instances
        )
        
        # The create_instance method already creates:
        # - positions_{safe_id}
        # - sentiment_{safe_id}
        # - state_transitions_{safe_id}
        # - markov_matrices_{safe_id}
        
        safe_id = instance_id.replace("-", "_").replace(".", "_").lower()
        
        logger.info(f"[APEX] Initialized instance tables for: {instance_id}")
        
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
        logger.error(f"Failed to initialize instance {instance_id}: {e}")
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
    for tf in ['1m', '15m']:
        matrix = instance_db.get_markov_matrix(instance_id, tf)
        if matrix:
            matrices.append(matrix)
    return jsonify({"success": True, "data": matrices})


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE API - Test Connection
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/profile/test', methods=['POST'])
def api_test_profile_connection():
    """
    Test API connection for a profile.
    Supports Anthropic, Google (Gemini), and OpenAI.
    """
    import time
    
    data = request.get_json() or {}
    provider = data.get('provider', 'google')
    api_key = data.get('apiKey', '')
    model = data.get('model', '')
    
    if not api_key:
        return jsonify({"success": False, "error": "No API key provided"})
    
    start_time = time.time()
    
    try:
        if provider == 'anthropic':
            # Test Anthropic API
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
            # Test Google Gemini API
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            gen_model = genai.GenerativeModel(model or 'gemini-2.0-flash')
            response = gen_model.generate_content("Say 'connected' in one word.")
            latency = int((time.time() - start_time) * 1000)
            return jsonify({"success": True, "latency": latency, "provider": "Google"})
            
        elif provider == 'openai':
            # Test OpenAI API
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
        # Clean up common error messages
        if "invalid api key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Invalid API key"
        elif "rate limit" in error_msg.lower():
            error_msg = "Rate limited - try again later"
        elif "quota" in error_msg.lower():
            error_msg = "API quota exceeded"
        return jsonify({"success": False, "error": error_msg})


# ═══════════════════════════════════════════════════════════════════════════════
# TRADER ROUTES INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from trader_routes import register_trader_routes
    register_trader_routes(app)
except ImportError as e:
    logger.warning(f"Trader routes not available: {e}")
except Exception as e:
    logger.error(f"Failed to register trader routes: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MISSION CONTROL API — Endpoints for /debug dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/profile/list', methods=['GET'])
def api_profile_list():
    """Get all profiles for Mission Control display"""
    if not instance_db:
        return jsonify({"success": False, "profiles": [], "error": "Database not available"})
    
    try:
        profiles = instance_db.get_all_profiles()
        profile_dicts = [asdict(p) for p in profiles]
        return jsonify({"success": True, "profiles": profile_dicts, "count": len(profile_dicts)})
    except Exception as e:
        logger.error(f"Profile list failed: {e}")
        return jsonify({"success": False, "profiles": [], "error": str(e)})


@app.route('/api/instance/<instance_id>/sentiments/latest', methods=['GET'])
def api_instance_sentiments_latest(instance_id):
    """Get latest sentiment for each timeframe — used by Mission Control"""
    if not instance_db:
        return jsonify({"success": False, "error": "Database not available"}), 500
    
    result = {"success": True, "instance_id": instance_id, "15m": None, "1h": None}
    
    for tf in ["15m", "1h"]:
        try:
            reading = instance_db.get_latest_sentiment(instance_id, tf)
            result[tf] = reading
        except Exception as e:
            result[tf] = None
            result[f"{tf}_error"] = str(e)
    
    return jsonify(result)


@app.route('/api/debug/health', methods=['GET'])
def api_debug_health():
    """Comprehensive health check for Mission Control diagnostics"""
    import sqlite3
    
    checks = {
        "flask": True,
        "instance_db": instance_db is not None,
        "sentiment_engine": sentiment_scheduler is not None,
        "trader_routes": False,
        "endpoints": {},
        "databases": {},
        "errors": []
    }
    
    # Check trader routes
    try:
        from trader_routes import get_trader_manager
        tm = get_trader_manager()
        checks["trader_routes"] = True
        checks["trader_manager"] = {
            "running_count": sum(1 for t in tm._traders.values() if t.is_alive()),
            "total_tracked": len(tm._traders)
        }
    except Exception as e:
        checks["errors"].append(f"trader_routes: {e}")
    
    # Check instance database tables
    if instance_db:
        try:
            conn = instance_db._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            checks["databases"]["apex_instances"] = {
                "tables": tables,
                "table_count": len(tables)
            }
            
            # Count instances and profiles
            try:
                cursor.execute("SELECT COUNT(*) FROM algorithm_instances WHERE status = 'ACTIVE'")
                checks["databases"]["active_instances"] = cursor.fetchone()[0]
            except Exception:
                checks["databases"]["active_instances"] = 0
            
            try:
                cursor.execute("SELECT COUNT(*) FROM profiles WHERE status != 'ARCHIVED'")
                checks["databases"]["active_profiles"] = cursor.fetchone()[0]
            except Exception:
                checks["databases"]["active_profiles"] = 0
            
            # Count sentiment tables and their row counts
            sentiment_tables = [t for t in tables if t.startswith('sentiment_')]
            checks["databases"]["sentiment_tables"] = {}
            for st in sentiment_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {st}")
                    checks["databases"]["sentiment_tables"][st] = cursor.fetchone()[0]
                except Exception:
                    checks["databases"]["sentiment_tables"][st] = -1
            
            conn.close()
        except Exception as e:
            checks["errors"].append(f"database scan: {e}")
    
    # Check intelligence databases
    try:
        from config import SYMBOL_DATABASES
        for sym_id, config in SYMBOL_DATABASES.items():
            db_path = config.get('db_path', '')
            checks["databases"][f"intel_{sym_id}"] = {
                "path": db_path,
                "exists": os.path.exists(db_path)
            }
    except Exception:
        pass
    
    # Check key endpoints exist
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static' and '/api/' in rule.rule:
            checks["endpoints"][rule.rule] = list(rule.methods - {'OPTIONS', 'HEAD'})
    
    return jsonify(checks)


# ═══════════════════════════════════════════════════════════════════════════════
# SEED 22: AGENT FRAMEWORK DEBUG
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/debug/agents', methods=['GET'])
def api_debug_agents():
    """Agent framework diagnostics for Mission Control"""
    import json as _json

    result = {
        "framework_available": False,
        "config_available": False,
        "imports": {},
        "agent_roster": [],
        "profiles_with_agents": [],
        "latest_deliberations": [],
        "errors": []
    }

    # Check imports
    try:
        from agent_framework import run_debate, build_memory_context
        result["framework_available"] = True
        result["imports"]["agent_framework"] = True
    except ImportError as e:
        result["imports"]["agent_framework"] = False
        result["errors"].append(f"agent_framework import failed: {e}")

    try:
        from agent_config import AGENT_ROSTER, MODE_PRESETS, DEFAULT_AGENT_CONFIG, resolve_agent_config
        result["config_available"] = True
        result["imports"]["agent_config"] = True
        result["default_config"] = DEFAULT_AGENT_CONFIG
        result["mode_presets"] = {k: v.get("active_agents", []) for k, v in MODE_PRESETS.items()}
        result["agent_roster"] = [
            {"id": aid, "role": info.get("role"), "tier": info.get("tier"),
             "vectors": info.get("primary_vectors", [])}
            for aid, info in AGENT_ROSTER.items()
        ]
    except ImportError as e:
        result["imports"]["agent_config"] = False
        result["errors"].append(f"agent_config import failed: {e}")

    # Check each agent module
    agent_modules = [
        ("agents.technical_agent", "run_technical_agent"),
        ("agents.bull_researcher", "run_bull_researcher"),
        ("agents.bear_researcher", "run_bear_researcher"),
        ("agents.risk_gate", "run_risk_gate"),
        ("agents.key_levels_agent", "run_key_levels_agent"),
        ("agents.momentum_agent", "run_momentum_agent"),
        ("agents.sentiment_agent", "run_sentiment_agent"),
        ("agents.news_agent", "run_news_agent"),
    ]
    for mod_name, fn_name in agent_modules:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            result["imports"][mod_name] = True
        except ImportError:
            result["imports"][mod_name] = False

    # Check which profiles have agents configured
    if instance_db:
        try:
            profiles = instance_db.get_all_profiles()
            for p in profiles:
                try:
                    tc = _json.loads(p.trading_config) if isinstance(p.trading_config, str) else (p.trading_config or {})
                except Exception:
                    tc = {}
                agent_cfg = tc.get("agents", {})
                if agent_cfg:
                    result["profiles_with_agents"].append({
                        "profile_id": p.id[:16],
                        "profile_name": p.name,
                        "enabled": agent_cfg.get("enabled", True),
                        "mode": agent_cfg.get("mode", "budget"),
                        "timeout": agent_cfg.get("timeout_seconds", 15),
                        "debate_rounds": agent_cfg.get("debate_rounds", 1),
                        "markov": agent_cfg.get("include_markov_context", True),
                    })
        except Exception as e:
            result["errors"].append(f"profile scan: {e}")

        # Pull latest agent_deliberation rows from sentiment tables
        try:
            conn = instance_db._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sentiment_%'")
            tables = [row[0] for row in cursor.fetchall()]

            for tbl in tables[:10]:
                try:
                    # Check if column exists
                    cursor.execute(f"PRAGMA table_info({tbl})")
                    cols = [c[1] for c in cursor.fetchall()]
                    if "agent_deliberation" not in cols:
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
                            delib = {"raw": str(row[8])[:200]}

                        entry = {
                            "table": tbl,
                            "timestamp": row[0],
                            "timeframe": row[1],
                            "source_type": row[2],
                            "processing_ms": row[3],
                            "composite": row[4],
                            "consensus": row[5],
                            "signal": row[6],
                            "met": bool(row[7]),
                        }
                        if delib:
                            entry["mode"] = delib.get("mode", "?")
                            entry["active_agents"] = delib.get("active_agents", [])
                            entry["timing"] = delib.get("timing", {})
                            entry["final_adjustments"] = delib.get("final_adjustments", {})
                            entry["analyst_consensus"] = delib.get("analyst_consensus", {})

                            # Extract key info from sub-results
                            bull = delib.get("bull_result", {})
                            bear = delib.get("bear_result", {})
                            risk = delib.get("risk_result", {})
                            entry["bull"] = {
                                "confidence": bull.get("confidence"),
                                "strongest": bull.get("strongest_vector"),
                                "flags": bull.get("flags", []),
                            }
                            entry["bear"] = {
                                "confidence": bear.get("confidence"),
                                "weakest": bear.get("weakest_vector"),
                                "flags": bear.get("flags", []),
                            }
                            entry["risk"] = {
                                "level": risk.get("overall_risk_level"),
                                "veto": risk.get("veto", False),
                                "multipliers": risk.get("multipliers", {}),
                                "flags": risk.get("flags", []),
                            }

                            # Analyst summaries
                            analysts = delib.get("analyst_reports", [])
                            entry["analysts"] = [
                                {
                                    "id": a.get("agent_id"),
                                    "confidence": a.get("confidence"),
                                    "flags": a.get("flags", []),
                                    "adjustments": a.get("adjustments", {}),
                                } for a in analysts
                            ]

                        result["latest_deliberations"].append(entry)
                except Exception as e:
                    result["errors"].append(f"{tbl}: {e}")

            conn.close()
        except Exception as e:
            result["errors"].append(f"deliberation scan: {e}")

    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """
    Main APEX page - serves apex.html template
    """
    return render_template('apex.html')


@app.route('/debug')
def debug_page():
    """
    Mission Control — Seed 18: The Nervous System
    Diagnostic dashboard for trader processes, sentiments, and system health.
    """
    return render_template('debug.html')


@app.route('/api/health')
def health_check():
    """
    Health check endpoint (PC-268)
    Returns app status for monitoring
    """
    return jsonify({
        'status': 'healthy',
        'app': 'APEX',
        'version': '11.0.0',
        'phase': 'Phase 1 - Quad Run E+F+C+J'
    })


@app.route('/api/state')
def get_state():
    """
    Debug endpoint - returns current server state
    """
    return jsonify({
        'status': 'ok',
        'message': 'State is managed client-side in localStorage'
    })


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f'Server error: {e}')
    return jsonify({'error': 'Internal server error'}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('═══════════════════════════════════════════════════════════════')
    print('  APEX Flask Server')
    print('  http://localhost:5000')
    print('═══════════════════════════════════════════════════════════════')
    
    # Start sentiment scheduler if available
    if sentiment_scheduler:
        sentiment_scheduler.start()
        print('  Sentiment Engine: ACTIVE')
    else:
        print('  Sentiment Engine: DISABLED')
    
    print('═══════════════════════════════════════════════════════════════')
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            threaded=True
        )
    finally:
        if sentiment_scheduler:
            sentiment_scheduler.stop()
