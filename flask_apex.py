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
    
    # Convert to dicts
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
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """
    Main APEX page - serves apex.html template
    """
    return render_template('apex.html')


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
