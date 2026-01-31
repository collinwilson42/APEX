"""
WIZAUDE API ENDPOINTS
Flask routes for Trinity Core + Markov integration
Add these to flask_app.py or import as blueprint
"""

from flask import Blueprint, jsonify, request
from datetime import datetime

# Import Wizaude
from wizaude_core import get_wizaude_engine

wizaude_bp = Blueprint('wizaude', __name__)


@wizaude_bp.route('/api/wizaude/status')
def wizaude_status():
    """Get Wizaude engine status"""
    try:
        engine = get_wizaude_engine()
        status = engine.get_status()
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@wizaude_bp.route('/api/wizaude/signal')
def wizaude_signal():
    """Get current Wizaude signal"""
    try:
        engine = get_wizaude_engine()
        
        if engine.last_signal:
            return jsonify({
                'success': True,
                'signal': engine.last_signal,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': True,
                'signal': None,
                'message': 'No signal generated yet'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@wizaude_bp.route('/api/wizaude/regime')
def wizaude_regime():
    """Get current regime and distribution"""
    try:
        engine = get_wizaude_engine()
        
        return jsonify({
            'success': True,
            'current_regime': engine.markov.get_regime(),
            'persistence': round(engine.markov.get_persistence(), 3),
            'distribution': engine.get_regime_distribution(),
            'state_history_length': len(engine.markov.state_history),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@wizaude_bp.route('/api/wizaude/trinity')
def wizaude_trinity():
    """Get Trinity Core state"""
    try:
        engine = get_wizaude_engine()
        trinity = engine.trinity
        
        return jsonify({
            'success': True,
            'memory_core': {
                'dmsn': trinity.memory.state.dmsn,
                'reflection': trinity.memory.state.reflection,
                'regime': trinity.memory.state.regime,
                'version': trinity.memory.state.version,
                'anchor_pf': trinity.memory.anchor_pf,
                'anchor_np': trinity.memory.anchor_np
            },
            'active_core': {
                'current_pf': trinity.active.current_pf,
                'current_np': trinity.active.current_np,
                'signal': trinity.active.signal,
                'confidence': trinity.active.confidence
            },
            'heatmap_core': {
                'percentile': round(trinity.heatmap.percentile, 1),
                'color': trinity.heatmap.hex_color,
                'history_length': len(trinity.heatmap.performance_history)
            },
            'stability': trinity.validate_stability(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@wizaude_bp.route('/api/wizaude/process', methods=['POST'])
def wizaude_process():
    """
    Process data through Wizaude manually.
    
    POST body:
    {
        "market_data": {
            "supertrend": "BULL",
            "atr_ratio": 1.2,
            "ema_distance": 0.5,
            "momentum": 25
        },
        "trade_data": {
            "pf": 1.5,
            "np": 250
        }
    }
    """
    try:
        engine = get_wizaude_engine()
        data = request.get_json()
        
        result = {}
        
        # Process market data if provided
        if 'market_data' in data:
            markov_result = engine.process_market_data(data['market_data'])
            result['markov'] = markov_result
        
        # Process trade data if provided
        if 'trade_data' in data:
            td = data['trade_data']
            signal = engine.process_trade_data(
                pf=td.get('pf', 1.0),
                np_value=td.get('np', 0.0)
            )
            result['signal'] = signal
        
        return jsonify({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@wizaude_bp.route('/api/wizaude/stoic')
def wizaude_stoic():
    """Get STOIC validation status"""
    try:
        engine = get_wizaude_engine()
        trinity = engine.trinity
        markov = engine.markov
        
        stability = trinity.validate_stability()
        
        # Calculate STOIC factors
        stoic = {
            'S': {
                'name': 'Stability',
                'value': stability['condition_number'],
                'threshold': 1.1,
                'passed': stability['condition_number'] < 1.1,
                'component': 'Orthogonal weight matrices'
            },
            'T': {
                'name': 'Tuning',
                'value': trinity.north_star(trinity.active.current_pf, 
                                           trinity.normalize_profit(trinity.active.current_np)),
                'target': 1.0,
                'component': 'North Star equation'
            },
            'O': {
                'name': 'Opportunity',
                'value': trinity.active.confidence,
                'component': 'Gate zone priority'
            },
            'I': {
                'name': 'Intuitivity',
                'value': markov.get_persistence(),
                'threshold': 0.3,
                'passed': markov.get_persistence() > 0.3,
                'component': 'Markov regime detection'
            },
            'C': {
                'name': 'Creativity',
                'value': len(markov.state_history),
                'component': 'Pattern learning'
            }
        }
        
        # Overall validation
        all_passed = stoic['S']['passed'] and stoic['I']['passed']
        
        return jsonify({
            'success': True,
            'stoic': stoic,
            'all_passed': all_passed,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# REGISTRATION HELPER
# ============================================================================

def register_wizaude_routes(app):
    """Register Wizaude blueprint with Flask app"""
    app.register_blueprint(wizaude_bp)
    print("[OK] Wizaude API endpoints registered")
