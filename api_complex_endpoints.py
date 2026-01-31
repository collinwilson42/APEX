"""
MT5 META AGENT - API COMPLEX ENDPOINTS
Flask routes for API Complex decision engine and screenshot analysis integration
"""

from flask import jsonify, request
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Optional

# Import vision analyzer
try:
    from vision_analyzer import VisionAnalyzer
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    print("⚠ vision_analyzer.py not found - screenshot analysis disabled")

# ============================================================================
# VISION ANALYSIS ENDPOINT
# ============================================================================

def register_api_complex_routes(app):
    """Register all API Complex routes with Flask app"""
    
    # Use global VISION_AVAILABLE, but create local variable for runtime status
    vision_analyzer = None
    vision_available_runtime = VISION_AVAILABLE
    
    if vision_available_runtime:
        try:
            vision_analyzer = VisionAnalyzer()
            print("✓ Vision Analyzer initialized")
        except Exception as e:
            print(f"✗ Vision Analyzer initialization failed: {e}")
            vision_available_runtime = False
    
    @app.route('/api/vision/analyze', methods=['POST'])
    def analyze_screenshot():
        """
        Analyze latest screenshot using Claude Vision
        
        Request JSON:
        {
            "module_id": 1,
            "screenshot_path": "optional/custom/path.png"
        }
        
        Returns:
        {
            "success": true,
            "analysis": {
                "directional_confidence": {...},
                "risk_assessment": {...},
                "key_levels": {...},
                "next_15m_prediction": {...},
                "pattern_recognition": {...},
                "market_context": {...},
                "snapshot_analysis": "..."
            },
            "metadata": {...}
        }
        """
        
        if not vision_available_runtime or not vision_analyzer:
            return jsonify({
                'success': False,
                'error': 'Vision analysis not available',
                'message': 'vision_analyzer.py not found or failed to initialize'
            }), 503
        
        try:
            data = request.get_json() or {}
            module_id = data.get('module_id', 1)
            custom_path = data.get('screenshot_path')
            
            # Find screenshot to analyze
            if custom_path:
                screenshot_path = Path(custom_path)
            else:
                # Find most recent screenshot
                screenshot_dir = Path("screenshots")
                
                if not screenshot_dir.exists():
                    return jsonify({
                        'success': False,
                        'error': 'Screenshot directory not found',
                        'message': 'screenshots/ folder does not exist'
                    }), 404
                
                screenshots = sorted(
                    screenshot_dir.glob("*.png"), 
                    key=lambda p: p.stat().st_mtime, 
                    reverse=True
                )
                
                if not screenshots:
                    return jsonify({
                        'success': False,
                        'error': 'No screenshots found',
                        'message': 'No .png files in screenshots/ folder'
                    }), 404
                
                screenshot_path = screenshots[0]
            
            # Perform analysis
            print(f"\n[API Complex] Analyzing screenshot for Module #{module_id}")
            print(f"Screenshot: {screenshot_path.name}")
            
            analysis = vision_analyzer.analyze_chart(str(screenshot_path))
            
            return jsonify({
                'success': True,
                'module_id': module_id,
                'screenshot': str(screenshot_path),
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
            
        except FileNotFoundError as e:
            return jsonify({
                'success': False,
                'error': 'Screenshot not found',
                'message': str(e)
            }), 404
            
        except Exception as e:
            print(f"[ERROR] Vision analysis failed: {e}")
            return jsonify({
                'success': False,
                'error': 'Analysis failed',
                'message': str(e)
            }), 500
    
    # ============================================================================
    # DECISION ENGINE EXECUTION ENDPOINT
    # ============================================================================
    
    @app.route('/api/complex/execute', methods=['POST'])
    def execute_decision():
        """
        Execute API Complex decision with full module state
        
        Request JSON:
        {
            "decision": "BULLISH|BEARISH|NEUTRAL",
            "confidence": 75.5,
            "modules": [
                {
                    "id": 1,
                    "name": "API #1",
                    "confidence": 65,
                    "weight": 1.0,
                    "enabled": true,
                    "use_screenshot": true,
                    "frequency": "every",
                    "vision_analysis": {...}  // Optional, if screenshot was analyzed
                },
                ...
            ],
            "execution_settings": {
                "base_interval": 180,
                "threshold": 10
            }
        }
        
        Returns:
        {
            "success": true,
            "execution_id": "exec_abc123",
            "decision": "BULLISH",
            "confidence": 75.5,
            "action": "BUY|SELL|HOLD",
            "timestamp": "..."
        }
        """
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
            
            # Extract decision data
            decision = data.get('decision', 'NEUTRAL')
            confidence = data.get('confidence', 0)
            modules = data.get('modules', [])
            settings = data.get('execution_settings', {})
            
            # Generate execution ID
            execution_id = f"exec_{int(datetime.now().timestamp())}"
            
            print("\n" + "="*70)
            print("API COMPLEX EXECUTION")
            print("="*70)
            print(f"Decision: {decision}")
            print(f"Confidence: {confidence}%")
            print(f"Active Modules: {len([m for m in modules if m.get('enabled', False)])}")
            
            # Log module states
            for module in modules:
                if module.get('enabled', False):
                    print(f"\n  Module #{module['id']}: {module.get('name', 'Unnamed')}")
                    print(f"    Confidence: {module.get('confidence', 0)}")
                    print(f"    Weight: {module.get('weight', 1.0)}")
                    print(f"    Screenshot: {module.get('use_screenshot', False)}")
                    
                    # If vision analysis included, show key metrics
                    if 'vision_analysis' in module:
                        va = module['vision_analysis']
                        if 'directional_confidence' in va:
                            dc = va['directional_confidence']
                            print(f"    Vision: {dc.get('primary_direction', 'N/A')} "
                                  f"(Bull:{dc.get('bullish', 0)} Bear:{dc.get('bearish', 0)})")
            
            # Determine action based on decision and threshold
            threshold = settings.get('threshold', 10)
            
            if decision == 'BULLISH' and confidence >= threshold:
                action = 'BUY'
            elif decision == 'BEARISH' and confidence >= threshold:
                action = 'SELL'
            else:
                action = 'HOLD'
            
            print(f"\n[ACTION] {action} (Threshold: {threshold})")
            print("="*70)
            
            # TODO: Integrate with actual MT5 execution logic here
            # For now, just return the decision
            
            response = {
                'success': True,
                'execution_id': execution_id,
                'decision': decision,
                'confidence': confidence,
                'action': action,
                'modules_processed': len(modules),
                'settings': settings,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save execution log (optional)
            try:
                log_dir = Path("execution_logs")
                log_dir.mkdir(exist_ok=True)
                
                log_file = log_dir / f"{execution_id}.json"
                with open(log_file, 'w') as f:
                    json.dump({
                        'request': data,
                        'response': response
                    }, f, indent=2)
                
                print(f"[LOG] Execution saved to {log_file}")
                
            except Exception as log_error:
                print(f"[WARNING] Failed to save execution log: {log_error}")
            
            return jsonify(response)
            
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            return jsonify({
                'success': False,
                'error': 'Execution failed',
                'message': str(e)
            }), 500
    
    # ============================================================================
    # MODULE MANAGEMENT ENDPOINTS
    # ============================================================================
    
    @app.route('/api/complex/modules', methods=['GET'])
    def get_modules():
        """
        Get all configured API modules
        
        Returns:
        {
            "success": true,
            "modules": [
                {"id": 1, "name": "API #1", "active": true, ...},
                ...
            ]
        }
        """
        
        # TODO: Load from database or config file
        # For now, return empty list (modules managed client-side)
        
        return jsonify({
            'success': True,
            'modules': [],
            'message': 'Module persistence not yet implemented'
        })
    
    @app.route('/api/complex/modules/<int:module_id>', methods=['POST'])
    def save_module(module_id):
        """
        Save/update module configuration
        
        Request JSON:
        {
            "name": "Custom API Name",
            "use_screenshot": true,
            "frequency": "15min",
            "weight": 1.5
        }
        """
        
        try:
            data = request.get_json()
            
            # TODO: Save to database or config file
            # For now, just acknowledge
            
            print(f"[API Complex] Module #{module_id} configuration updated")
            print(f"  Name: {data.get('name', 'Unnamed')}")
            print(f"  Screenshot: {data.get('use_screenshot', False)}")
            print(f"  Frequency: {data.get('frequency', 'every')}")
            
            return jsonify({
                'success': True,
                'module_id': module_id,
                'message': 'Module saved (persistence not yet implemented)'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ============================================================================
    # HEALTH CHECK
    # ============================================================================
    
    @app.route('/api/complex/health', methods=['GET'])
    def health_check():
        """Check API Complex system health"""
        
        return jsonify({
            'success': True,
            'vision_available': vision_available_runtime,
            'screenshot_dir_exists': Path("screenshots").exists(),
            'timestamp': datetime.now().isoformat()
        })
    
    print("\n✓ API Complex routes registered")
    print("  POST /api/vision/analyze - Screenshot analysis")
    print("  POST /api/complex/execute - Decision execution")
    print("  GET  /api/complex/modules - List modules")
    print("  POST /api/complex/modules/<id> - Save module")
    print("  GET  /api/complex/health - Health check")

# ============================================================================
# INTEGRATION INSTRUCTIONS
# ============================================================================

"""
TO INTEGRATE INTO startapp.py:

1. Import this module:
   from api_complex_endpoints import register_api_complex_routes

2. After creating Flask app, register routes:
   app = Flask(__name__)
   CORS(app)
   
   # Register API Complex routes
   register_api_complex_routes(app)

3. Ensure vision_analyzer.py is in the same directory

4. Screenshots should be in screenshots/ folder (created by screenshot_capture.py)

5. Frontend calls:
   
   // Analyze screenshot
   fetch('/api/vision/analyze', {
       method: 'POST',
       headers: {'Content-Type': 'application/json'},
       body: JSON.stringify({
           module_id: 1
       })
   })
   
   // Execute decision
   fetch('/api/complex/execute', {
       method: 'POST',
       headers: {'Content-Type': 'application/json'},
       body: JSON.stringify({
           decision: 'BULLISH',
           confidence: 75,
           modules: [...],
           execution_settings: {...}
       })
   })
"""