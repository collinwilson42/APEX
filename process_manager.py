"""
PROCESS MANAGER — Instance Orchestrator
========================================
Manages independent Python subprocesses for each trading instance.
Each symbol gets its own process (instance_runner.py) with full isolation.

Seed 16 — The Independent Instances

Usage:
    from process_manager import ProcessManager
    pm = ProcessManager(base_dir='/path/to/codebase')
    pm.start_instance('BTC', mode='SIM')
    pm.start_instance('GOLD', mode='SIM')
    pm.stop_instance('BTC')
    pm.get_status()  # {'BTC': {'state': 'stopped'}, 'GOLD': {'state': 'running', 'pid': 12347}}
"""

import os
import sys
import json
import signal
import subprocess
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ASSET CLASS REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

ASSET_CLASSES = {
    'BTC': {
        'symbol': 'BTCF26',
        'name': 'Bitcoin Futures',
        'volatility': 0.12,
        'trade_frequency': 0.25,
        'pnl_scale': 500.0,
        'trend_bias': 0.02,
    },
    'OIL': {
        'symbol': 'USOILH26',
        'name': 'Crude Oil Futures',
        'volatility': 0.08,
        'trade_frequency': 0.30,
        'pnl_scale': 200.0,
        'trend_bias': -0.01,
    },
    'GOLD': {
        'symbol': 'XAUJ26',
        'name': 'Gold Futures',
        'volatility': 0.06,
        'trade_frequency': 0.28,
        'pnl_scale': 300.0,
        'trend_bias': 0.015,
    },
    'US100': {
        'symbol': 'US100H26',
        'name': 'Nasdaq 100 Futures',
        'volatility': 0.09,
        'trade_frequency': 0.22,
        'pnl_scale': 250.0,
        'trend_bias': 0.025,
    },
    'US30': {
        'symbol': 'US30H26',
        'name': 'Dow 30 Futures',
        'volatility': 0.07,
        'trade_frequency': 0.24,
        'pnl_scale': 220.0,
        'trend_bias': 0.02,
    },
    'US500': {
        'symbol': 'US500H26',
        'name': 'S&P 500 Futures',
        'volatility': 0.065,
        'trade_frequency': 0.26,
        'pnl_scale': 230.0,
        'trend_bias': 0.018,
    },
}


class InstanceProcess:
    """Wraps a subprocess.Popen with metadata."""
    
    def __init__(self, symbol: str, mode: str, process: subprocess.Popen):
        self.symbol = symbol
        self.mode = mode
        self.process = process
        self.pid = process.pid
        self.started_at = datetime.now()
        self.state = 'running'
    
    def is_alive(self) -> bool:
        """Check if the process is still running."""
        if self.process.poll() is None:
            return True
        self.state = 'crashed' if self.process.returncode != 0 else 'stopped'
        return False
    
    def to_dict(self) -> dict:
        """Serialize to dict for API responses."""
        alive = self.is_alive()
        return {
            'symbol': self.symbol,
            'mode': self.mode,
            'pid': self.pid,
            'state': 'running' if alive else self.state,
            'started_at': self.started_at.isoformat(),
            'runtime_seconds': round((datetime.now() - self.started_at).total_seconds(), 1),
            'return_code': self.process.returncode,
        }


class ProcessManager:
    """
    Orchestrates independent instance_runner.py subprocesses.
    One process per symbol. Singleton per symbol enforced.
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.runner_path = os.path.join(self.base_dir, 'instance_runner.py')
        self.python_exe = sys.executable
        self._processes: Dict[str, InstanceProcess] = {}
        self._lock = threading.Lock()
        
        logger.info(f"[ProcessManager] Initialized. Runner: {self.runner_path}")
    
    def start_instance(self, symbol: str, mode: str = 'SIM', 
                       interval: int = 900, speed: float = 1.0) -> dict:
        """
        Start an instance_runner.py process for the given symbol.
        """
        symbol = symbol.upper()
        
        if symbol not in ASSET_CLASSES:
            return {
                'success': False,
                'error': f'Unknown symbol: {symbol}. Valid: {list(ASSET_CLASSES.keys())}'
            }
        
        with self._lock:
            if symbol in self._processes:
                existing = self._processes[symbol]
                if existing.is_alive():
                    return {
                        'success': False,
                        'error': f'{symbol} is already running (PID {existing.pid})',
                        'instance': existing.to_dict()
                    }
                else:
                    del self._processes[symbol]
            
            if not os.path.exists(self.runner_path):
                return {
                    'success': False,
                    'error': f'instance_runner.py not found at {self.runner_path}'
                }
            
            cmd = [
                self.python_exe,
                self.runner_path,
                '--symbol', symbol,
                '--mode', mode,
                '--interval', str(interval),
                '--speed', str(speed),
                '--base-dir', self.base_dir,
            ]
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.base_dir,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                )
                
                time.sleep(0.5)
                if process.poll() is not None:
                    stdout, stderr = process.communicate(timeout=2)
                    return {
                        'success': False,
                        'error': f'{symbol} process exited immediately',
                        'stdout': stdout[-500:] if stdout else '',
                        'stderr': stderr[-500:] if stderr else '',
                    }
                
                instance = InstanceProcess(symbol, mode, process)
                self._processes[symbol] = instance
                
                logger.info(f"[ProcessManager] ✓ Started {symbol} ({mode}) — PID {process.pid}")
                print(f"[ProcessManager] ✓ Started {symbol} ({mode}) — PID {process.pid}")
                
                return {
                    'success': True,
                    'message': f'{symbol} instance started',
                    'instance': instance.to_dict()
                }
                
            except Exception as e:
                logger.error(f"[ProcessManager] ✗ Failed to start {symbol}: {e}")
                return {'success': False, 'error': str(e)}
    
    def stop_instance(self, symbol: str, timeout: float = 5.0) -> dict:
        """Stop a running instance process gracefully."""
        symbol = symbol.upper()
        
        with self._lock:
            if symbol not in self._processes:
                return {'success': False, 'error': f'{symbol} is not running'}
            
            instance = self._processes[symbol]
            
            if not instance.is_alive():
                del self._processes[symbol]
                return {'success': True, 'message': f'{symbol} was already stopped', 'state': instance.state}
            
            try:
                if os.name == 'nt':
                    os.kill(instance.pid, signal.CTRL_BREAK_EVENT)
                else:
                    instance.process.terminate()
                
                try:
                    instance.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(f"[ProcessManager] {symbol} didn't stop gracefully, killing...")
                    instance.process.kill()
                    instance.process.wait(timeout=2)
                
                instance.state = 'stopped'
                del self._processes[symbol]
                
                logger.info(f"[ProcessManager] ✓ Stopped {symbol} (was PID {instance.pid})")
                print(f"[ProcessManager] ✓ Stopped {symbol} (was PID {instance.pid})")
                
                return {'success': True, 'message': f'{symbol} instance stopped'}
                
            except Exception as e:
                logger.error(f"[ProcessManager] ✗ Error stopping {symbol}: {e}")
                return {'success': False, 'error': str(e)}
    
    def restart_instance(self, symbol: str, mode: str = None, 
                         interval: int = 900, speed: float = 1.0) -> dict:
        """Stop then start an instance."""
        symbol = symbol.upper()
        if mode is None and symbol in self._processes:
            mode = self._processes[symbol].mode
        mode = mode or 'SIM'
        
        stop_result = self.stop_instance(symbol)
        time.sleep(0.5)
        start_result = self.start_instance(symbol, mode, interval, speed)
        
        return {'success': start_result['success'], 'stop': stop_result, 'start': start_result}
    
    def get_status(self) -> dict:
        """Get status of all known instances."""
        status = {}
        
        with self._lock:
            for symbol, instance in self._processes.items():
                status[symbol] = instance.to_dict()
        
        for symbol in ASSET_CLASSES:
            if symbol not in status:
                status[symbol] = {
                    'symbol': symbol, 'mode': None, 'pid': None,
                    'state': 'idle', 'started_at': None,
                    'runtime_seconds': 0, 'return_code': None,
                }
        
        return {
            'instances': status,
            'running_count': sum(1 for s in status.values() if s['state'] == 'running'),
            'total_count': len(ASSET_CLASSES),
        }
    
    def stop_all(self) -> dict:
        """Stop all running instances."""
        results = {}
        symbols = list(self._processes.keys())
        for symbol in symbols:
            results[symbol] = self.stop_instance(symbol)
        return results
    
    def cleanup_orphans(self) -> dict:
        """Clean up dead processes from previous sessions."""
        cleaned = []
        with self._lock:
            dead = [s for s, i in self._processes.items() if not i.is_alive()]
            for symbol in dead:
                cleaned.append(symbol)
                del self._processes[symbol]
        if cleaned:
            logger.info(f"[ProcessManager] Cleaned up orphans: {cleaned}")
        return {'cleaned': cleaned}


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_manager: Optional[ProcessManager] = None

def get_process_manager(base_dir: str = None) -> ProcessManager:
    """Get or create the global ProcessManager singleton."""
    global _manager
    if _manager is None:
        _manager = ProcessManager(base_dir)
    return _manager


# ═══════════════════════════════════════════════════════════════════════════
# FLASK ROUTE REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════

def register_process_routes(app):
    """Register Flask API routes for instance process management."""
    from flask import jsonify, request
    
    @app.route('/api/instance/status', methods=['GET'])
    def instance_process_status():
        pm = get_process_manager()
        return jsonify(pm.get_status())
    
    @app.route('/api/instance/<symbol>/start', methods=['POST'])
    def instance_process_start(symbol):
        pm = get_process_manager()
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', 'SIM')
        interval = data.get('interval', 900)
        speed = data.get('speed', 1.0)
        result = pm.start_instance(symbol, mode, interval, speed)
        return jsonify(result), 200 if result['success'] else 409
    
    @app.route('/api/instance/<symbol>/stop', methods=['POST'])
    def instance_process_stop(symbol):
        pm = get_process_manager()
        result = pm.stop_instance(symbol)
        return jsonify(result), 200 if result['success'] else 404
    
    @app.route('/api/instance/<symbol>/restart', methods=['POST'])
    def instance_process_restart(symbol):
        pm = get_process_manager()
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', None)
        result = pm.restart_instance(symbol, mode)
        return jsonify(result)
    
    @app.route('/api/instance/<symbol>/toggle', methods=['POST'])
    def instance_process_toggle(symbol):
        pm = get_process_manager()
        status = pm.get_status()
        instance_state = status['instances'].get(symbol.upper(), {}).get('state', 'idle')
        
        if instance_state == 'running':
            result = pm.stop_instance(symbol)
        else:
            data = request.get_json(silent=True) or {}
            mode = data.get('mode', 'SIM')
            speed = data.get('speed', 1.0)
            result = pm.start_instance(symbol, mode, speed=speed)
        
        return jsonify(result)
    
    @app.route('/api/instance/stop-all', methods=['POST'])
    def instance_process_stop_all():
        pm = get_process_manager()
        result = pm.stop_all()
        return jsonify({'success': True, 'results': result})
    
    # Shutdown handler
    import atexit
    def shutdown_instances():
        pm = get_process_manager()
        pm.stop_all()
        logger.info("[ProcessManager] All instances stopped on shutdown.")
    atexit.register(shutdown_instances)
    
    print("✓ Instance process management routes registered")
    print("  Routes: /api/instance/status, /api/instance/<symbol>/start|stop|toggle")
