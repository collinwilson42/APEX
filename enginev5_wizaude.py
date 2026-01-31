"""
MT5 META AGENT V5 - WIZAUDE INTEGRATION ENGINE
Trinity Core + Markov Regime Detection + Real MT5 Data Flow
"""

import time
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import anthropic
import base64

# Import configuration
import config

# Import modules
from mt5_position_tracker import get_position_tracker

# Import database functions
from database_init_base44_unified import (
    insert_position_state_row,
    get_latest_position_state,
    get_execution_gate_config,
    get_trade_statistics,
    DB_PATH
)

# Import Wizaude Core
from wizaude_core import get_wizaude_engine, WizaudeEngine


# ============================================================================
# GLOBAL STATE
# ============================================================================

class EngineState:
    """Global engine state"""
    def __init__(self):
        self.current_score = 50.0
        self.peak_zone = 1
        self.peak_zone_timestamp = None
        self.countdown_sec = 60.0
        self.countdown_remaining_sec = 60.0
        self.last_score_calc = None
        self.last_full_analysis = None
        self.last_lightweight_update = None
        self.last_webhook_trigger = None
        self.cycle_count = 0
        
engine_state = EngineState()


# ============================================================================
# DATABASE QUERIES
# ============================================================================

def get_latest_15m_snapshot() -> Optional[Dict[str, Any]]:
    """Get latest 15m data from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                c.id,
                c.timestamp,
                c.close as price_close,
                b.atr_14,
                b.atr_ratio,
                b.ema_distance,
                b.supertrend,
                f.current_fib_zone,
                f.zone_multiplier,
                a.ath_distance_pct,
                a.ath_multiplier
            FROM core_15m c
            LEFT JOIN basic_15m b ON c.timestamp = b.timestamp AND c.timeframe = b.timeframe
            LEFT JOIN fibonacci_data f ON c.timestamp = f.timestamp AND c.timeframe = f.timeframe
            LEFT JOIN ath_tracking a ON c.timestamp = a.timestamp AND c.timeframe = a.timeframe
            WHERE c.timeframe = '15m' AND c.symbol = ?
            ORDER BY c.timestamp DESC
            LIMIT 1
        """, (config.SYMBOL,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
        
    finally:
        cursor.close()
        conn.close()


def get_latest_1m_snapshot() -> Optional[Dict[str, Any]]:
    """Get latest 1m data from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                c.timestamp,
                c.close as price_close,
                b.atr_14,
                b.supertrend
            FROM core_15m c
            LEFT JOIN basic_15m b ON c.timestamp = b.timestamp AND c.timeframe = b.timeframe
            WHERE c.timeframe = '1m' AND c.symbol = ?
            ORDER BY c.timestamp DESC
            LIMIT 1
        """, (config.SYMBOL,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
        
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# TRADE SCORE CALCULATION (Original + Wizaude Enhancement)
# ============================================================================

def calculate_trade_score(snapshot: Dict[str, Any], wizaude: WizaudeEngine) -> float:
    """
    Calculate trade score (0-100) based on indicators.
    Enhanced with Wizaude regime detection.
    """
    score = 50.0
    
    # ATR ratio scoring
    atr_ratio = snapshot.get('atr_ratio', 1.0)
    if atr_ratio > 1.2:
        score += 20
    elif atr_ratio > 1.0:
        score += 10
    elif atr_ratio < 0.8:
        score -= 10
    
    # Supertrend + EMA alignment
    supertrend = snapshot.get('supertrend', 'NEUTRAL')
    ema_distance = snapshot.get('ema_distance', 0)
    
    if supertrend == 'BULL':
        score += 15
        if ema_distance > 0:
            score += 15
    elif supertrend == 'BEAR':
        score += 15
        if ema_distance < 0:
            score += 15
    
    # Fibonacci zone scoring
    fib_zone = snapshot.get('current_fib_zone', 7)
    zone_multiplier = snapshot.get('zone_multiplier', 1.0)
    
    if 4 <= fib_zone <= 7:
        score += 15
    
    score += min(10, zone_multiplier * 5)
    
    # ATH distance scoring
    ath_distance = snapshot.get('ath_distance_pct', 0)
    ath_multiplier = snapshot.get('ath_multiplier', 1.0)
    
    if ath_distance < 0.5:
        score += 20
    elif ath_distance < 1.0:
        score += 15
    elif ath_distance < 2.0:
        score += 10
    
    score += min(5, ath_multiplier * 2.5)
    
    # Update Wizaude with market data
    wizaude.process_market_data({
        'supertrend': supertrend,
        'atr_ratio': atr_ratio,
        'ema_distance': ema_distance,
        'momentum': score - 50  # Use score deviation as momentum proxy
    })
    
    # Apply regime-based adjustment
    regime = wizaude.markov.get_regime()
    persistence = wizaude.markov.get_persistence()
    
    if regime == 'volatile':
        score *= 0.8  # Reduce confidence in volatile regime
    elif regime in ['bullish', 'bearish']:
        score *= (1.0 + persistence * 0.1)  # Boost in trending regimes
    elif regime == 'breakout_pending':
        score *= 0.9  # Slightly cautious before breakout
    
    return max(0, min(100, score))


# ============================================================================
# WEBHOOK WRITER
# ============================================================================

class WebhookWriter:
    """Writes webhook signals"""
    
    def __init__(self, file_path: str = "webhook_signals.txt"):
        self.file_path = file_path
        self.signals_sent = 0
        
    def send_trade(self, action: str, symbol: str, qty: float, tp: float = None, sl: float = None) -> bool:
        signal = {"action": action, "symbol": symbol, "qty": qty}
        if tp:
            signal["tp"] = tp
        if sl:
            signal["sl"] = sl
        return self._write_signal(signal)
    
    def send_close(self, symbol: str) -> bool:
        return self._write_signal({"action": "CLOSE", "symbol": symbol})
    
    def _write_signal(self, signal: Dict[str, Any]) -> bool:
        try:
            json_str = json.dumps(signal, separators=(',', ':'))
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            self.signals_sent += 1
            print(f"[OK] Webhook #{self.signals_sent}: {json_str}")
            return True
        except Exception as e:
            print(f"[FAIL] Webhook error: {e}")
            return False


# ============================================================================
# MAIN ENGINE CYCLE
# ============================================================================

def run_engine_cycle(
    snapshot_15m: Dict[str, Any],
    snapshot_1m: Dict[str, Any],
    gate_config: Dict[str, Any],
    wizaude: WizaudeEngine,
    tracker: Any,
    writer: WebhookWriter
) -> bool:
    """Single engine cycle with Wizaude integration"""
    global engine_state
    
    try:
        now = datetime.now()
        engine_state.cycle_count += 1
        
        # Calculate trade score with Wizaude enhancement
        engine_state.current_score = calculate_trade_score(snapshot_15m, wizaude)
        
        # Get trade statistics for Wizaude
        stats = get_trade_statistics()
        pf = stats.get('profit_factor', 1.0)
        np_value = stats.get('net_profit', 0.0)
        
        # Process through Wizaude Trinity Core
        wizaude_signal = wizaude.process_trade_data(pf, np_value)
        
        # Update gate/countdown
        num_gates = gate_config.get('num_gates', 10)
        base_interval = gate_config.get('base_interval_sec', 60)
        
        gate_size = 100.0 / num_gates
        current_gate = int(engine_state.current_score / gate_size) + 1
        current_gate = max(1, min(num_gates, current_gate))
        
        if current_gate > engine_state.peak_zone:
            engine_state.peak_zone = current_gate
            engine_state.peak_zone_timestamp = now
        
        engine_state.countdown_sec = base_interval / engine_state.peak_zone
        engine_state.countdown_remaining_sec -= 1.0
        
        # Display status
        regime = wizaude_signal.get('regime', 'unknown')
        ns = wizaude_signal.get('north_star', 0)
        trinity_signal = wizaude_signal.get('signal', 'HOLD')
        confidence = wizaude_signal.get('confidence', 50)
        
        if config.SHOW_COUNTDOWN and engine_state.cycle_count % 5 == 0:
            print(f"[{now.strftime('%H:%M:%S')}] "
                  f"Score: {engine_state.current_score:.0f} | "
                  f"Gate: {engine_state.peak_zone} | "
                  f"CD: {engine_state.countdown_remaining_sec:.0f}s | "
                  f"Regime: {regime} | "
                  f"Trinity: {trinity_signal} ({confidence}%) | "
                  f"NS: {ns:.3f}")
        
        # Countdown trigger
        if engine_state.countdown_remaining_sec <= 0:
            print(f"\n{'='*70}")
            print(f"⏰ COUNTDOWN ZERO - SIGNAL TRIGGER")
            print(f"{'='*70}")
            print(f"  Score: {engine_state.current_score:.0f}")
            print(f"  Gate: {engine_state.peak_zone}")
            print(f"  Regime: {regime}")
            print(f"  Trinity Signal: {trinity_signal} ({confidence}%)")
            print(f"  North Star: {ns:.4f}")
            print(f"{'='*70}\n")
            
            # Write bridge signal
            bridge_signal = {
                "timestamp": now.isoformat(),
                "action": trinity_signal,
                "symbol": config.SYMBOL,
                "qty": config.BASE_LOT_SIZE,
                "confidence": confidence,
                "regime": regime,
                "north_star": ns
            }
            
            try:
                with open("bridge.txt", "w", encoding='utf-8') as f:
                    f.write(json.dumps(bridge_signal))
                print(f"[OK] Bridge signal written")
            except Exception as e:
                print(f"[FAIL] Bridge write failed: {e}")
            
            # Reset countdown
            engine_state.countdown_remaining_sec = engine_state.countdown_sec
            engine_state.last_webhook_trigger = now
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Engine cycle error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main engine loop with Wizaude integration"""
    global engine_state
    
    print("="*70)
    print("MT5 META AGENT V5 - WIZAUDE INTEGRATION ENGINE")
    print("Trinity Core + Markov Regime Detection")
    print("="*70)
    
    # Print config
    if hasattr(config, 'print_config'):
        config.print_config()
    else:
        print(f"\n[CONFIG]")
        print(f"  Symbol: {config.SYMBOL}")
        print(f"  Risk Level: {config.RISK_REWARD_LEVEL}")
    
    # Check database
    if not os.path.exists(DB_PATH):
        print(f"\n[FAIL] Database not found: {DB_PATH}")
        return
    print("\n[OK] Database connected")
    
    # Initialize Wizaude Engine
    print("\n[INIT] Initializing Wizaude Core...")
    wizaude = get_wizaude_engine(DB_PATH)
    
    # Initialize other components
    writer = WebhookWriter(config.WEBHOOK_FILE_PATH)
    print("[OK] Webhook writer initialized")
    
    tracker = get_position_tracker(config.SYMBOL)
    if not tracker.connect():
        print("[WARN] MT5 connection failed - running in data-only mode")
    else:
        print("[OK] MT5 position tracker connected")
    
    # Get initial data
    print("\n[OK] Getting initial market data...")
    snapshot_15m = get_latest_15m_snapshot()
    snapshot_1m = get_latest_1m_snapshot()
    
    if not snapshot_15m:
        print("[FAIL] No 15m data available")
        return
    
    print(f"[OK] 15m: {snapshot_15m.get('timestamp', 'N/A')} | ${snapshot_15m.get('price_close', 0):.2f}")
    
    # Initialize state
    gate_config = get_execution_gate_config() or {'num_gates': 10, 'base_interval_sec': 60}
    engine_state.current_score = calculate_trade_score(snapshot_15m, wizaude)
    engine_state.peak_zone = max(1, int(engine_state.current_score / 10) + 1)
    engine_state.peak_zone_timestamp = datetime.now()
    engine_state.countdown_sec = gate_config['base_interval_sec'] / engine_state.peak_zone
    engine_state.countdown_remaining_sec = engine_state.countdown_sec
    
    print(f"\n[OK] Initial state:")
    print(f"  Score: {engine_state.current_score:.1f}/100")
    print(f"  Peak Zone: {engine_state.peak_zone}")
    print(f"  Countdown: {engine_state.countdown_sec:.1f}s")
    print(f"  Regime: {wizaude.markov.get_regime()}")
    
    # Show Wizaude status
    status = wizaude.get_status()
    print(f"\n[WIZAUDE STATUS]")
    print(f"  Stability: {status['stability']}")
    print(f"  Condition: {status['condition_number']}")
    
    print("\n[OK] Starting engine...")
    print("Press Ctrl+C to stop\n")
    print("="*70 + "\n")
    
    last_snapshot_update = datetime.now()
    
    try:
        while True:
            # Update snapshots every 60s
            if (datetime.now() - last_snapshot_update).total_seconds() >= 60:
                snapshot_15m = get_latest_15m_snapshot()
                snapshot_1m = get_latest_1m_snapshot()
                last_snapshot_update = datetime.now()
            
            # Run cycle
            run_engine_cycle(
                snapshot_15m=snapshot_15m,
                snapshot_1m=snapshot_1m,
                gate_config=gate_config,
                wizaude=wizaude,
                tracker=tracker,
                writer=writer
            )
            
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("[OK] ENGINE STOPPED")
        print("="*70)
        print(f"Total cycles: {engine_state.cycle_count}")
        print(f"Final score: {engine_state.current_score:.1f}")
        
        # Wizaude final status
        status = wizaude.get_status()
        print(f"\n[WIZAUDE FINAL STATUS]")
        print(f"  Regime: {status['regime']}")
        print(f"  Persistence: {status['persistence']}")
        print(f"  Memory Version: {status['memory_version']}")
        
        # Regime distribution
        dist = wizaude.get_regime_distribution()
        print(f"\n[REGIME DISTRIBUTION]")
        for regime, pct in sorted(dist.items(), key=lambda x: -x[1]):
            if pct > 0:
                print(f"  {regime}: {pct:.1f}%")
        
        print("="*70)
        
        if tracker:
            tracker.disconnect()


if __name__ == "__main__":
    main()
