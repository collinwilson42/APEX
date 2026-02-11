"""
CYTO API ROUTES
===============
Flask routes for CytoBase data access.
Register these with the main Flask app.

Usage:
    from cyto_routes import register_cyto_routes
    register_cyto_routes(app)
"""

from flask import jsonify, request
from datetime import datetime
import os
import sys

# Add Cyto directory to path
CYTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '#Cyto')
if CYTO_DIR not in sys.path:
    sys.path.insert(0, CYTO_DIR)


def register_cyto_routes(app, cyto_integration=None):
    """
    Register Cyto API routes with a Flask app.
    
    Args:
        app: Flask application
        cyto_integration: Optional CytoIntegration instance (will create if None)
    """
    
    # Lazy load integration
    _cyto = None
    
    def get_cyto():
        nonlocal _cyto
        if _cyto is None:
            if cyto_integration:
                _cyto = cyto_integration
            else:
                from cyto_integration import get_cyto_integration
                _cyto = get_cyto_integration()
        return _cyto
    
    # ========================================
    # INSTANCE ROUTES
    # ========================================
    
    @app.route('/api/cyto/instances', methods=['GET'])
    def cyto_get_instances():
        """Get all Cyto instances."""
        try:
            cyto = get_cyto()
            instances = cyto.manager.get_all_instances()
            return jsonify({
                'success': True,
                'instances': instances,
                'count': len(instances)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/cyto/instances/<instance_id>', methods=['GET'])
    def cyto_get_instance(instance_id):
        """Get a single Cyto instance."""
        try:
            cyto = get_cyto()
            instance = cyto.manager.get_instance(instance_id)
            if not instance:
                return jsonify({'success': False, 'error': 'Instance not found'}), 404
            return jsonify({'success': True, 'instance': instance})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/cyto/instances/<instance_id>/stats', methods=['GET'])
    def cyto_get_instance_stats(instance_id):
        """Get aggregated stats for a Cyto instance."""
        try:
            cyto = get_cyto()
            stats = cyto.get_instance_stats(instance_id)
            return jsonify({'success': True, 'stats': stats})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/cyto/instances', methods=['POST'])
    def cyto_create_instance():
        """Create/register a new Cyto instance."""
        try:
            cyto = get_cyto()
            data = request.get_json() or {}
            
            instance_id = data.get('instance_id')
            symbol = data.get('symbol', 'UNKNOWN')
            profile_name = data.get('profile_name')
            config = data.get('config')
            
            if not instance_id:
                # Auto-generate ID
                instance_id = f"{symbol}_SIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            cyto.register_instance(
                instance_id=instance_id,
                symbol=symbol,
                profile_name=profile_name,
                config=config
            )
            
            return jsonify({
                'success': True,
                'instance_id': instance_id
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========================================
    # NODE ROUTES
    # ========================================
    
    @app.route('/api/cyto/instances/<instance_id>/nodes', methods=['GET'])
    def cyto_get_nodes(instance_id):
        """
        Get nodes for an instance.
        
        Query params:
            cycle: Specific cycle index (default: current)
            trades_only: If 'true', only return nodes with trades
        """
        try:
            cyto = get_cyto()
            
            cycle = request.args.get('cycle', type=int)
            trades_only = request.args.get('trades_only', '').lower() == 'true'
            
            if trades_only:
                nodes = cyto.manager.get_nodes_with_trades(instance_id, cycle)
            else:
                if cycle is None:
                    cycle = cyto.manager.get_current_cycle()
                nodes = cyto.manager.get_epoch_nodes(instance_id, cycle)
            
            return jsonify({
                'success': True,
                'cycle': cycle,
                'nodes': nodes,
                'count': len(nodes)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/cyto/instances/<instance_id>/cycles', methods=['GET'])
    def cyto_get_cycles(instance_id):
        """Get list of cycles that have data for an instance."""
        try:
            cyto = get_cyto()
            cycles = cyto.manager.get_instance_cycles(instance_id)
            current = cyto.manager.get_current_cycle()
            return jsonify({
                'success': True,
                'cycles': cycles,
                'current_cycle': current
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========================================
    # VISUALIZATION DATA
    # ========================================
    
    @app.route('/api/cyto/instances/<instance_id>/radial', methods=['GET'])
    def cyto_get_radial_data(instance_id):
        """
        Get data formatted for radial visualization.
        
        Query params:
            cycle: Specific cycle index (default: current)
        
        Returns nodes with pre-calculated visualization properties:
            - theta (angle in degrees)
            - radius (0.618 to 1.618)
            - size, hue, saturation
        """
        try:
            cyto = get_cyto()
            
            cycle = request.args.get('cycle', type=int)
            if cycle is None:
                cycle = cyto.manager.get_current_cycle()
            
            nodes = cyto.manager.get_epoch_nodes(instance_id, cycle)
            
            # Transform for visualization
            viz_nodes = []
            for node in nodes:
                viz_nodes.append({
                    'node_id': node['node_id'],
                    'theta': cyto.manager.slot_to_angle(node['theta_slot']),
                    'theta_slot': node['theta_slot'],
                    'radius': node['radius'] if node['radius'] else 1.0,  # Default to median
                    'size': node['node_size'] or 8,
                    'hue': node['node_hue'] or 'neutral',
                    'saturation': node['node_saturation'] or 0.5,
                    'has_trade': bool(node['has_trade']),
                    'pnl': node['raw_pnl'],
                    'weighted_final': node['weighted_final'],
                    'agreement': node['agreement_score'],
                    'timestamp': node['timestamp']
                })
            
            # Also get cycle bounds
            start, end = cyto.manager.get_cycle_bounds(cycle)
            
            return jsonify({
                'success': True,
                'cycle': cycle,
                'cycle_start': start.isoformat(),
                'cycle_end': end.isoformat(),
                'nodes': viz_nodes,
                'count': len(viz_nodes)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/cyto/instances/<instance_id>/node/<int:node_id>/vectors', methods=['GET'])
    def cyto_get_node_vectors(instance_id, node_id):
        """
        Get detailed vector data for a specific node.
        Used for hover tooltips (radar/bar display).
        """
        try:
            cyto = get_cyto()
            
            # Get the node
            from cyto_schema import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cyto_nodes WHERE node_id = ? AND instance_id = ?
            """, (node_id, instance_id))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return jsonify({'success': False, 'error': 'Node not found'}), 404
            
            node = dict(row)
            
            # Parse vectors JSON
            import json
            vectors = json.loads(node['vectors_15m']) if node['vectors_15m'] else {}
            
            # Format for visualization
            radar_data = [
                {'axis': 'Price Action', 'value': vectors.get('v1', 0)},
                {'axis': 'Key Levels', 'value': vectors.get('v2', 0)},
                {'axis': 'Momentum', 'value': vectors.get('v3', 0)},
                {'axis': 'Volume', 'value': vectors.get('v4', 0)},
                {'axis': 'Structure', 'value': vectors.get('v5', 0)},
                {'axis': 'Composite', 'value': vectors.get('v6', 0)}
            ]
            
            return jsonify({
                'success': True,
                'node_id': node_id,
                'vectors': vectors,
                'radar_data': radar_data,
                'weighted_15m': node['weighted_15m'],
                'weighted_1h': node['weighted_1h'],
                'weighted_final': node['weighted_final'],
                'agreement_score': node['agreement_score']
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========================================
    # TRADE ROUTES
    # ========================================
    
    @app.route('/api/cyto/instances/<instance_id>/trades', methods=['GET'])
    def cyto_get_trades(instance_id):
        """Get all trades for an instance."""
        try:
            cyto = get_cyto()
            
            from cyto_schema import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cyto_trades WHERE instance_id = ?
                ORDER BY exit_time DESC
            """, (instance_id,))
            trades = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return jsonify({
                'success': True,
                'trades': trades,
                'count': len(trades)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========================================
    # HEALTH CHECK
    # ========================================
    
    @app.route('/api/cyto/health', methods=['GET'])
    def cyto_health():
        """Check Cyto system health."""
        try:
            cyto = get_cyto()
            
            # Get basic stats
            instances = cyto.manager.get_all_instances()
            active = [i for i in instances if i.get('status') == 'running']
            
            from cyto_schema import get_schema_info
            schema = get_schema_info()
            
            return jsonify({
                'success': True,
                'status': 'healthy',
                'db_path': cyto.db_path,
                'total_instances': len(instances),
                'active_instances': len(active),
                'tables': {name: data['row_count'] for name, data in schema.items()}
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    print("✓ Cyto API routes registered")
