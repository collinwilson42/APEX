"""
TRADER ROUTES — Flask API for starting/stopping the TORRA Trader
=================================================================
Seed 19: Config-First Activation

Flow:
  1. Frontend double-taps "Active" on an algo instance
  2. JS calls POST /api/trader/start with {instance_id, api_key, model, trading_config}
  3. This route:
     a. VALIDATES config completeness (profile, weights, thresholds, API key)
     b. Upserts trading_config into the DB profiles table
     c. Links the profile to the instance
     d. Spawns torra_trader.py --instance-id <id> with API key as env var
  4. The API key NEVER touches the database — passed only as env var to subprocess

Routes:
  POST /api/trader/start     — Start trader for an instance
  POST /api/trader/stop      — Stop trader
  GET  /api/trader/status    — Get all trader statuses
  POST /api/trader/toggle    — Toggle on/off
"""

import os
import sys
import json
import signal
import subprocess
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG VALIDATION (Seed 19: Config-First Gate)
# ═══════════════════════════════════════════════════════════════════════════

def validate_start_request(data: dict) -> dict:
    """
    Validate all required fields before spawning a trader.
    Returns {'valid': True} or {'valid': False, 'errors': [...]}.
    """
    errors = []

    instance_id = data.get('instance_id', '').strip()
    api_key = data.get('api_key', '').strip()
    trading_config = data.get('trading_config', {})

    # Required fields
    if not instance_id:
        errors.append('instance_id is required')

    if not api_key:
        errors.append('api_key is required — configure in Profile Manager')

    # Instance must exist in DB — auto-create if missing (Seed 18: bridge localStorage ↔ DB)
    if instance_id:
        from instance_database import get_instance_db
        db = get_instance_db(os.path.join(BASE_DIR, 'apex_instances.db'))
        instance = db.get_instance(instance_id)
        if not instance:
            # Normalize symbol: strip .SIM suffix (Seed 20: Symbol Alignment)
            raw_symbol = data.get('symbol', '').upper() or 'UNKNOWN'
            symbol = raw_symbol[:-4] if raw_symbol.endswith('.SIM') else raw_symbol
            try:
                db.register_instance(
                    instance_id=instance_id,
                    symbol=symbol,
                    account_type='SIM',
                    display_name=f"{symbol} Trader",
                    profile_id=data.get('profile_id', '')
                )
                logger.info(f"[validate_start_config] Auto-registered instance: {instance_id} ({symbol})")
            except Exception as e:
                errors.append(f'Instance not found and auto-register failed: {e}')

    # Trading config validation
    if trading_config:
        sw = trading_config.get('sentiment_weights', {})
        if sw:
            w_sum = sum(float(v) for v in sw.values())
            if abs(w_sum - 1.0) > 0.05:
                errors.append(f'sentiment_weights sum to {w_sum:.3f}, expected ~1.0')
        else:
            errors.append('trading_config missing sentiment_weights')

        if not trading_config.get('thresholds'):
            errors.append('trading_config missing thresholds')

        if not trading_config.get('timeframe_weights'):
            errors.append('trading_config missing timeframe_weights')
    else:
        errors.append('trading_config is required')

    return {'valid': len(errors) == 0, 'errors': errors}


# ═══════════════════════════════════════════════════════════════════════════
# TRADER PROCESS MANAGER
# ═══════════════════════════════════════════════════════════════════════════

# Log directory for trader output
LOG_DIR = os.path.join(BASE_DIR, 'logs', 'traders')
os.makedirs(LOG_DIR, exist_ok=True)


class TraderProcess:
    """Wraps a torra_trader.py subprocess."""

    def __init__(self, instance_id: str, symbol: str, process: subprocess.Popen,
                 log_path: str = None):
        self.instance_id = instance_id
        self.symbol = symbol
        self.process = process
        self.pid = process.pid
        self.started_at = datetime.now()
        self.state = 'running'
        self.log_path = log_path
        self._log_file = None  # kept open for subprocess lifetime

    def is_alive(self) -> bool:
        if self.process.poll() is None:
            return True
        self.state = 'crashed' if self.process.returncode != 0 else 'stopped'
        # Close log file when process ends
        if self._log_file and not self._log_file.closed:
            self._log_file.close()
        return False

    def get_tail(self, lines: int = 50) -> str:
        """Read last N lines of the trader log file."""
        if not self.log_path or not os.path.exists(self.log_path):
            return ''
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception:
            return ''

    def to_dict(self) -> dict:
        alive = self.is_alive()
        d = {
            'instance_id': self.instance_id,
            'symbol': self.symbol,
            'pid': self.pid,
            'state': 'running' if alive else self.state,
            'started_at': self.started_at.isoformat(),
            'runtime_seconds': round((datetime.now() - self.started_at).total_seconds(), 1),
            'return_code': self.process.returncode,
            'log_path': self.log_path,
        }
        # Include last few log lines for crashed traders
        if not alive and self.state == 'crashed':
            d['last_output'] = self.get_tail(20)
        return d


class TraderManager:
    """Manages torra_trader.py subprocesses. One per instance."""

    def __init__(self):
        self._traders: Dict[str, TraderProcess] = {}
        self._lock = threading.Lock()
        self.trader_path = os.path.join(BASE_DIR, 'torra_trader.py')
        self.python_exe = sys.executable

    def start_trader(self, instance_id: str, symbol: str,
                     api_key: str, provider: str = 'anthropic',
                     model: str = None) -> dict:
        """
        Spawn torra_trader.py for an instance.
        API key is passed ONLY as env var — never stored in DB.
        """
        with self._lock:
            # Check if already running
            if instance_id in self._traders:
                existing = self._traders[instance_id]
                if existing.is_alive():
                    return {
                        'success': False,
                        'error': f'Trader already running (PID {existing.pid})',
                        'trader': existing.to_dict()
                    }
                del self._traders[instance_id]

            if not os.path.exists(self.trader_path):
                return {'success': False, 'error': 'torra_trader.py not found'}

            # Build environment with API key (never touches DB)
            env = os.environ.copy()

            if provider == 'anthropic':
                env['ANTHROPIC_API_KEY'] = api_key
            elif provider == 'google':
                env['GOOGLE_API_KEY'] = api_key
            elif provider == 'openai':
                env['OPENAI_API_KEY'] = api_key

            env['TORRA_API_KEY'] = api_key
            env['TORRA_PROVIDER'] = provider
            env['PYTHONIOENCODING'] = 'utf-8'  # Critical: prevents emoji crash in log files
            if model:
                env['TORRA_MODEL'] = model

            cmd = [
                self.python_exe,
                '-u',  # Unbuffered output — critical for log file flushing
                self.trader_path,
                '--instance-id', instance_id,
                '--run-now',  # Seed 18: immediate first tick on activation
            ]

            try:
                # ── Log file instead of PIPE (prevents buffer deadlock) ──
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_id = instance_id.replace('-', '_')[:24]
                log_filename = f"trader_{safe_id}_{timestamp_str}.log"
                log_path = os.path.join(LOG_DIR, log_filename)
                log_file = open(log_path, 'w', encoding='utf-8', buffering=1)

                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,  # merge stderr into stdout log
                    text=True,
                    cwd=BASE_DIR,
                    env=env,
                    creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP
                                   if os.name == 'nt' else 0),
                )

                time.sleep(0.5)
                if process.poll() is not None:
                    log_file.close()
                    # Read what the process wrote before dying
                    try:
                        with open(log_path, 'r', encoding='utf-8') as f:
                            crash_output = f.read()[-1000:]
                    except Exception:
                        crash_output = ''
                    return {
                        'success': False,
                        'error': 'Trader exited immediately — check profile config',
                        'output': crash_output,
                        'log_path': log_path,
                    }

                trader = TraderProcess(instance_id, symbol, process, log_path=log_path)
                trader._log_file = log_file  # keep reference so it stays open
                self._traders[instance_id] = trader

                logger.info(f"[TraderManager] ✓ Started trader for {instance_id} — PID {process.pid}")
                print(f"[TraderManager] ✓ Started trader for {instance_id} — PID {process.pid}")

                return {
                    'success': True,
                    'message': f'Trader started for {symbol}',
                    'trader': trader.to_dict()
                }

            except Exception as e:
                logger.error(f"[TraderManager] ✗ Failed: {e}")
                return {'success': False, 'error': str(e)}

    def stop_trader(self, instance_id: str, timeout: float = 5.0) -> dict:
        with self._lock:
            if instance_id not in self._traders:
                return {'success': False, 'error': 'Trader not running'}

            trader = self._traders[instance_id]
            if not trader.is_alive():
                del self._traders[instance_id]
                return {'success': True, 'message': 'Already stopped'}

            try:
                if os.name == 'nt':
                    os.kill(trader.pid, signal.CTRL_BREAK_EVENT)
                else:
                    trader.process.terminate()

                try:
                    trader.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    trader.process.kill()
                    trader.process.wait(timeout=2)

                del self._traders[instance_id]
                print(f"[TraderManager] ✓ Stopped trader for {instance_id}")
                return {'success': True, 'message': 'Trader stopped'}

            except Exception as e:
                return {'success': False, 'error': str(e)}

    def get_status(self) -> dict:
        statuses = {}
        with self._lock:
            for iid, trader in list(self._traders.items()):
                statuses[iid] = trader.to_dict()
        return {
            'traders': statuses,
            'running_count': sum(1 for t in statuses.values() if t['state'] == 'running'),
        }

    def is_running(self, instance_id: str) -> bool:
        with self._lock:
            if instance_id in self._traders:
                return self._traders[instance_id].is_alive()
        return False

    def stop_all(self):
        for iid in list(self._traders.keys()):
            self.stop_trader(iid)


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_trader_manager: Optional[TraderManager] = None

def get_trader_manager() -> TraderManager:
    global _trader_manager
    if _trader_manager is None:
        _trader_manager = TraderManager()
    return _trader_manager


# ═══════════════════════════════════════════════════════════════════════════
# PROFILE CONFIG SYNC — Frontend tradingConfig → DB profiles table
# ═══════════════════════════════════════════════════════════════════════════

def upsert_trading_config(instance_id: str, trading_config: dict,
                          model: str = None) -> str:
    """
    Save/update trading config into the DB profiles table.
    Links the profile to the instance.
    Returns the profile_id.
    """
    from instance_database import get_instance_db
    import uuid

    db = get_instance_db(os.path.join(BASE_DIR, 'apex_instances.db'))
    instance = db.get_instance(instance_id)
    if not instance:
        raise ValueError(f"Instance not found: {instance_id}")

    # Extract config sections
    sw = trading_config.get('sentiment_weights', {
        'price_action': 0.30, 'key_levels': 0.15,
        'momentum': 0.25, 'ath': 0.10, 'structure': 0.20
    })
    tw = trading_config.get('timeframe_weights', {'15m': 0.40, '1h': 0.60})
    thresholds = trading_config.get('thresholds', {
        'buy': 0.55, 'sell': -0.55, 'dead_zone': 0.25, 'gut_veto': 0.30
    })
    risk = trading_config.get('risk', {
        'base_lots': 1.0, 'max_lots': 1.0,
        'stop_loss_points': 80, 'take_profit_points': 200,
        'max_signals_per_hour': 3, 'cooldown_seconds': 300,
        'consecutive_loss_halt': 2, 'sentiment_exit': True
    })

    conn = db._get_conn()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"

    profile_id = instance.profile_id

    entry_rules = json.dumps({
        'timeframe_weights': tw,
        'gut_check_veto_threshold': thresholds.get('gut_veto', 0.30),
        'dead_zone_low': -thresholds.get('dead_zone', 0.25),
        'dead_zone_high': thresholds.get('dead_zone', 0.25),
    })
    exit_rules = json.dumps({
        'stop_loss_points': risk.get('stop_loss_points', 80),
        'take_profit_points': risk.get('take_profit_points', 200),
        'sentiment_exit_enabled': risk.get('sentiment_exit', True),
        'max_signals_per_hour': risk.get('max_signals_per_hour', 3),
        'cooldown_seconds': risk.get('cooldown_seconds', 300),
        'consecutive_loss_halt': risk.get('consecutive_loss_halt', 2),
    })
    position_sizing = json.dumps({
        'base_lots': risk.get('base_lots', 1.0),
        'max_lots': risk.get('max_lots', 1.0),
    })

    trading_config_json = json.dumps(trading_config)

    if profile_id:
        cursor.execute("""
            UPDATE profiles SET
                trading_config = ?,
                sentiment_weights = ?,
                sentiment_model = ?,
                sentiment_threshold = ?,
                position_sizing = ?,
                entry_rules = ?,
                exit_rules = ?,
                risk_config = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            trading_config_json,
            json.dumps(sw),
            model or 'claude-sonnet-4-20250514',
            abs(thresholds.get('buy', 0.55)),
            position_sizing,
            entry_rules,
            exit_rules,
            json.dumps(risk),
            now,
            profile_id
        ))
        print(f"[TraderRoutes] Updated profile {profile_id}")
    else:
        profile_id = str(uuid.uuid4())[:12]
        cursor.execute("""
            INSERT INTO profiles (
                id, name, symbol, status,
                trading_config,
                sentiment_weights, sentiment_model, sentiment_threshold,
                position_sizing, risk_config, entry_rules, exit_rules,
                created_at, updated_at
            ) VALUES (?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            f"{instance.symbol} Trading Profile",
            instance.symbol,
            trading_config_json,
            json.dumps(sw),
            model or 'claude-sonnet-4-20250514',
            abs(thresholds.get('buy', 0.55)),
            position_sizing,
            json.dumps(risk),
            entry_rules,
            exit_rules,
            now, now
        ))
        cursor.execute("""
            UPDATE algorithm_instances SET profile_id = ? WHERE id = ?
        """, (profile_id, instance_id))
        print(f"[TraderRoutes] Created profile {profile_id} → linked to {instance_id}")

    conn.commit()
    conn.close()
    return profile_id


# ═══════════════════════════════════════════════════════════════════════════
# FLASK ROUTE REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════

def register_trader_routes(app):
    """Register Flask API routes for TORRA trader management."""
    from flask import jsonify, request
    import atexit

    @app.route('/api/trader/start', methods=['POST'])
    def api_trader_start():
        """
        Start the TORRA trader for an instance.
        
        Seed 19: Config-first validation gate.
        Validates profile, weights, thresholds, and API key BEFORE spawning.
        """
        data = request.get_json() or {}

        # ── Config-first validation gate ──
        validation = validate_start_request(data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'error': 'Config validation failed',
                'validation_errors': validation['errors']
            }), 400

        instance_id = data.get('instance_id')
        api_key = data.get('api_key', '').strip()
        provider = data.get('provider', 'anthropic')
        model = data.get('model')
        trading_config = data.get('trading_config', {})
        symbol = data.get('symbol', '')

        # 1. Save trading config to DB profile (API key is NOT saved)
        try:
            profile_id = upsert_trading_config(instance_id, trading_config, model)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 404
        except Exception as e:
            logger.error(f"Profile upsert failed: {e}")
            return jsonify({'success': False, 'error': f'Profile save failed: {e}'}), 500

        # 2. Spawn torra_trader.py with API key as env var
        tm = get_trader_manager()
        result = tm.start_trader(instance_id, symbol, api_key, provider, model)

        if result['success']:
            result['profile_id'] = profile_id

        return jsonify(result), 200 if result['success'] else 409

    @app.route('/api/trader/stop', methods=['POST'])
    def api_trader_stop():
        data = request.get_json() or {}
        instance_id = data.get('instance_id')
        if not instance_id:
            return jsonify({'success': False, 'error': 'instance_id required'}), 400

        tm = get_trader_manager()
        result = tm.stop_trader(instance_id)
        return jsonify(result), 200 if result['success'] else 404

    @app.route('/api/trader/status', methods=['GET'])
    def api_trader_status():
        tm = get_trader_manager()
        return jsonify(tm.get_status())

    @app.route('/api/trader/<instance_id>/status', methods=['GET'])
    def api_trader_instance_status(instance_id):
        tm = get_trader_manager()
        running = tm.is_running(instance_id)
        return jsonify({'instance_id': instance_id, 'running': running})

    @app.route('/api/trader/toggle', methods=['POST'])
    def api_trader_toggle():
        """Toggle trader on/off. Frontend calls this on double-tap Active."""
        data = request.get_json() or {}
        instance_id = data.get('instance_id')
        if not instance_id:
            return jsonify({'success': False, 'error': 'instance_id required'}), 400

        tm = get_trader_manager()
        if tm.is_running(instance_id):
            result = tm.stop_trader(instance_id)
        else:
            # ── Config-first validation gate ──
            validation = validate_start_request(data)
            if not validation['valid']:
                return jsonify({
                    'success': False,
                    'error': 'Config validation failed',
                    'validation_errors': validation['errors']
                }), 400

            api_key = data.get('api_key', '').strip()
            provider = data.get('provider', 'anthropic')
            model = data.get('model')
            trading_config = data.get('trading_config', {})
            symbol = data.get('symbol', '')

            try:
                upsert_trading_config(instance_id, trading_config, model)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

            result = tm.start_trader(instance_id, symbol, api_key, provider, model)

        return jsonify(result)

    @app.route('/api/trader/<instance_id>/log', methods=['GET'])
    def api_trader_log(instance_id):
        """Read trader log file — tail N lines (default 100)."""
        tm = get_trader_manager()
        lines = int(request.args.get('lines', 100))
        
        with tm._lock:
            trader = tm._traders.get(instance_id)
        
        if not trader:
            return jsonify({'success': False, 'error': 'Trader not found'}), 404
        
        log_text = trader.get_tail(lines)
        return jsonify({
            'success': True,
            'instance_id': instance_id,
            'log_path': trader.log_path,
            'state': 'running' if trader.is_alive() else trader.state,
            'lines': lines,
            'output': log_text
        })

    @app.route('/api/trader/logs', methods=['GET'])
    def api_trader_logs_list():
        """List all trader log files."""
        logs = []
        if os.path.isdir(LOG_DIR):
            for fname in sorted(os.listdir(LOG_DIR), reverse=True):
                if fname.endswith('.log'):
                    fpath = os.path.join(LOG_DIR, fname)
                    size = os.path.getsize(fpath)
                    logs.append({'filename': fname, 'size': size, 'path': fpath})
        return jsonify({'success': True, 'logs': logs[:50]})

    # Clean up on shutdown
    def shutdown_traders():
        tm = get_trader_manager()
        tm.stop_all()
        logger.info("[TraderManager] All traders stopped on shutdown.")
    atexit.register(shutdown_traders)

    print("✓ TORRA trader routes registered (v2.0 — Config-First)")
    print("  Routes: /api/trader/start, /api/trader/stop, /api/trader/status, /api/trader/toggle, /api/trader/<id>/log")
