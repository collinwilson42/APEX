"""
MT5 META AGENT - CALCULATION ENGINE WITH COUNTDOWN & WEBHOOK TRIGGER
Runs every 1 second, tracks countdown, triggers webhook when countdown hits 0
"""

import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import sys
import os

# Import your existing modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_init_base44_unified import (
    insert_position_state_row,
    get_latest_position_state,
    calculate_execution_countdown,
    get_execution_gate_config,
    is_agent_running,
    get_trade_statistics,
    DB_PATH
)

from webhook_writer import get_webhook_writer

# ============================================================================
# CONFIGURATION
# ============================================================================

UPDATE_INTERVAL_SEC = 1  # Update every 1 second for countdown
SCORE_RECALC_INTERVAL_SEC = 60  # Recalculate score every 60 seconds
SYMBOL = "XAUG26.sim"  # Updated to match mt5_collector_sqlite.py

# Global state for countdown tracking
class CountdownState:
    def __init__(self):
        self.current_score = 50.0
        self.peak_zone = 1
        self.peak_zone_timestamp = None
        self.countdown_sec = 60.0
        self.countdown_remaining_sec = 60.0
        self.last_score_calc = None
        self.last_webhook_trigger = None
        
countdown_state = CountdownState()

# ============================================================================
# LOT SIZE CALCULATION (FUTURES: 1.0 MINIMUM)
# ============================================================================

def calculate_lots_for_gate(gate: int, config: Dict[str, Any]) -> float:
    """
    Calculate lot size for given gate
    Respects futures minimum of 1.0 lot
    """
    base_qty = config.get('base_qty', 1.0)
    max_qty = config.get('max_qty', 5.0)
    num_gates = config.get('num_gates', 10)
    
    # Ensure minimums for futures
    if base_qty < 1.0:
        base_qty = 1.0
    
    # Calculate multiplier based on gate (1-10)
    multiplier = gate / num_gates
    
    # Linear scaling from base to max
    lots = base_qty + (max_qty - base_qty) * multiplier
    
    # Round to nearest 0.1 lot
    lots = round(lots, 1)
    
    # Enforce minimum
    lots = max(base_qty, lots)
    
    return lots


# ============================================================================
# CORE CALCULATION FUNCTIONS
# ============================================================================

def get_latest_15m_snapshot() -> Optional[Dict[str, Any]]:
    """Get latest 15m data from your existing database"""
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
        """, (SYMBOL,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
        
    finally:
        cursor.close()
        conn.close()


def calculate_trade_score(snapshot: Dict[str, Any]) -> float:
    """
    Calculate trade score (0-100) based on your indicators
    """
    score = 50.0  # Start neutral
    
    # ATR Component (0-20 points)
    atr_ratio = snapshot.get('atr_ratio', 1.0)
    if atr_ratio > 1.2:
        score += 20
    elif atr_ratio > 1.0:
        score += 10
    elif atr_ratio < 0.8:
        score -= 10
    
    # Trend Component (0-30 points)
    supertrend = snapshot.get('supertrend', 'NEUTRAL')
    ema_distance = snapshot.get('ema_distance', 0)
    
    if supertrend == 'BULLISH':
        score += 15
        if ema_distance > 0:
            score += 15
    elif supertrend == 'BEARISH':
        score += 15
        if ema_distance < 0:
            score += 15
    
    # Fibonacci Zone Component (0-25 points)
    fib_zone = snapshot.get('current_fib_zone', 7)
    zone_multiplier = snapshot.get('zone_multiplier', 1.0)
    
    if 4 <= fib_zone <= 7:
        score += 15
    
    score += min(10, zone_multiplier * 5)
    
    # ATH Distance Component (0-25 points)
    ath_distance = snapshot.get('ath_distance_pct', 0)
    ath_multiplier = snapshot.get('ath_multiplier', 1.0)
    
    if ath_distance < 0.5:
        score += 20
    elif ath_distance < 1.0:
        score += 15
    elif ath_distance < 2.0:
        score += 10
    
    score += min(5, ath_multiplier * 2.5)
    
    return max(0, min(100, score))


def determine_trade_direction(snapshot: Dict[str, Any]) -> str:
    """
    Determine if signal should be BUY or SELL based on market conditions
    
    Returns: "BUY" or "SELL"
    """
    supertrend = snapshot.get('supertrend', 'NEUTRAL')
    ema_distance = snapshot.get('ema_distance', 0)
    
    # Primary: Use supertrend
    if supertrend == 'BULLISH':
        return 'BUY'
    elif supertrend == 'BEARISH':
        return 'SELL'
    
    # Fallback: Use EMA distance
    if ema_distance > 0:
        return 'BUY'
    else:
        return 'SELL'


def build_snapshot_preview(snapshot: Dict[str, Any]) -> str:
    """Create human-readable preview of market state"""
    supertrend = snapshot.get('supertrend', 'NEUTRAL')
    atr_ratio = snapshot.get('atr_ratio', 1.0)
    fib_zone = snapshot.get('current_fib_zone', 7)
    ath_dist = snapshot.get('ath_distance_pct', 0)
    
    volatility = "HIGH" if atr_ratio > 1.2 else "NORMAL" if atr_ratio > 0.9 else "LOW"
    
    return f"{supertrend} | Vol: {volatility} | Fib Z{fib_zone} | ATH: {ath_dist:.2f}%"


def get_active_position_state() -> Dict[str, Any]:
    """Get active position P&L from MT5 or your tracking system"""
    # TODO: Integrate with your MT5 position tracking
    return {
        "active_lots": 0.0,
        "active_pl": 0.0
    }


def send_webhook_signal(snapshot: Dict[str, Any], gate_zone: int, score: float):
    """
    Send webhook signal to MT5 EA
    Triggers BUY or SELL based on market conditions
    """
    try:
        writer = get_webhook_writer()
        
        # Determine direction
        direction = determine_trade_direction(snapshot)
        
        # Get ATR for TP/SL calculation
        atr = snapshot.get('atr_14', 1.0)
        current_price = snapshot.get('price_close', 2000.0)
        
        # Calculate TP/SL levels
        if direction == 'BUY':
            tp_levels = [
                current_price + (atr * 1.0),
                current_price + (atr * 1.5),
                current_price + (atr * 2.0),
                current_price + (atr * 2.5),
                current_price + (atr * 3.0)
            ]
            sl_level = current_price - (atr * 0.5)
            action = 'BUY'
        else:
            tp_levels = [
                current_price - (atr * 1.0),
                current_price - (atr * 1.5),
                current_price - (atr * 2.0),
                current_price - (atr * 2.5),
                current_price - (atr * 3.0)
            ]
            sl_level = current_price + (atr * 0.5)
            action = 'SELL'
        
        # Round to 2 decimals
        tp_levels = [round(tp, 2) for tp in tp_levels]
        sl_level = round(sl_level, 2)
        
        # Calculate lot size based on gate (1.0 - 5.0 lots)
        config = get_execution_gate_config()
        qty = calculate_lots_for_gate(gate_zone, config)
        
        # Send signal with dynamic lot sizing
        comment = f"Gate{gate_zone}_Score{int(score)}"
        
        success = writer.send_signal(
            action=action,
            symbol=SYMBOL,
            qty=qty,  # Dynamic lot sizing based on gate
            tp_levels=tp_levels,
            sl_level=sl_level,
            comment=comment,
            gate_zone=gate_zone
        )
        
        if success:
            print(f"\n{'='*70}")
            print(f"🔔 WEBHOOK SIGNAL SENT")
            print(f"{'='*70}")
            print(f"  Action: {action}")
            print(f"  Symbol: {SYMBOL}")
            print(f"  Qty: {qty} lot(s)  [Gate-scaled: 1.0-5.0]")
            print(f"  Gate Zone: {gate_zone}")
            print(f"  Score: {score:.1f}")
            print(f"  TPs: {tp_levels}")
            print(f"  SL: {sl_level}")
            print(f"  Comment: {comment}")
            print(f"{'='*70}\n")
        else:
            print(f"\n✗ Failed to send webhook signal")
        
        return success
        
    except Exception as e:
        print(f"\n✗ Error sending webhook signal: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_countdown_state(snapshot: Dict[str, Any], config: Dict[str, Any]):
    """
    Update countdown state based on current score
    Implements peak zone persistence logic
    """
    global countdown_state
    
    now = datetime.now()
    
    # Recalculate score if needed (every 60 seconds)
    if (countdown_state.last_score_calc is None or 
        (now - countdown_state.last_score_calc).total_seconds() >= SCORE_RECALC_INTERVAL_SEC):
        
        countdown_state.current_score = calculate_trade_score(snapshot)
        countdown_state.last_score_calc = now
        print(f"\n[{now.strftime('%H:%M:%S')}] Score recalculated: {countdown_state.current_score:.1f}/100")
    
    # Calculate gate from current score
    num_gates = config.get('num_gates', 10)
    base_interval = config.get('base_interval_sec', 60)
    peak_duration = config.get('peak_zone_duration_sec', 120)
    
    gate_size = 100.0 / num_gates
    current_gate = int(countdown_state.current_score / gate_size) + 1
    current_gate = max(1, min(num_gates, current_gate))
    
    # Peak zone logic: if new gate is higher, update peak
    if current_gate > countdown_state.peak_zone:
        countdown_state.peak_zone = current_gate
        countdown_state.peak_zone_timestamp = now
        print(f"  📈 Peak zone updated: {countdown_state.peak_zone}")
    
    # Check if peak zone should persist
    effective_gate = countdown_state.peak_zone
    if countdown_state.peak_zone_timestamp:
        time_in_peak = (now - countdown_state.peak_zone_timestamp).total_seconds()
        if time_in_peak > peak_duration:
            # Peak expired, use current gate
            effective_gate = current_gate
            countdown_state.peak_zone = current_gate
            countdown_state.peak_zone_timestamp = now
            print(f"  ⏰ Peak expired, using current gate: {effective_gate}")
    
    # Calculate countdown duration
    countdown_state.countdown_sec = base_interval / effective_gate
    
    return effective_gate


def update_position_state_row(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Build position state row with countdown info"""
    global countdown_state
    
    config = get_execution_gate_config()
    base_interval = config['base_interval_sec'] if config else 60
    
    # Update countdown state
    effective_gate = update_countdown_state(snapshot, config)
    
    # Get stats
    position = get_active_position_state()
    stats = get_trade_statistics()
    
    # Build row
    row = {
        "timestamp": datetime.now().isoformat(),
        "price_close": snapshot['price_close'],
        "base_interval_sec": base_interval,
        "trade_score": round(countdown_state.current_score, 2),
        "execution_gate": effective_gate,
        "estimated_lots": calculate_lots_for_gate(effective_gate, config),  # Fixed for 1.0 minimum
        "countdown_sec": round(countdown_state.countdown_sec, 2),
        "countdown_remaining_sec": round(countdown_state.countdown_remaining_sec, 2),
        "peak_zone": countdown_state.peak_zone,
        "peak_zone_timestamp": countdown_state.peak_zone_timestamp.isoformat() if countdown_state.peak_zone_timestamp else None,
        "active_lots": position['active_lots'],
        "active_pl": position['active_pl'],
        "net_profit_closed": stats['net_profit'],
        "profit_factor": stats['profit_factor'],
        "total_lots": position['active_lots'],
        "total_pl": position['active_pl'] + stats['net_profit'],
        "total_closed_trades": stats['total_trades'],
        "snapshot_15m_id": snapshot['id'],
        "snapshot_preview": build_snapshot_preview(snapshot)
    }
    
    return row


# ============================================================================
# MAIN COUNTDOWN LOOP
# ============================================================================

def run_countdown_cycle(snapshot: Dict[str, Any]) -> bool:
    """Single countdown tick - decrements countdown, checks for trigger"""
    global countdown_state
    
    try:
        now = datetime.now()
        
        # Decrement countdown
        countdown_state.countdown_remaining_sec -= UPDATE_INTERVAL_SEC
        
        # Check if countdown hit zero
        if countdown_state.countdown_remaining_sec <= 0:
            print(f"\n{'='*70}")
            print(f"⏰ COUNTDOWN HIT ZERO!")
            print(f"{'='*70}")
            print(f"  Gate Zone: {countdown_state.peak_zone}")
            print(f"  Score: {countdown_state.current_score:.1f}")
            
            # Send webhook signal
            send_webhook_signal(
                snapshot=snapshot,
                gate_zone=countdown_state.peak_zone,
                score=countdown_state.current_score
            )
            
            # Reset countdown
            countdown_state.countdown_remaining_sec = countdown_state.countdown_sec
            countdown_state.last_webhook_trigger = now
            
            print(f"  ✓ Countdown reset to {countdown_state.countdown_sec:.1f}s")
            print(f"{'='*70}\n")
        
        # Update database every second
        row = update_position_state_row(snapshot)
        insert_position_state_row(row)
        
        # Show countdown progress (every 10 seconds)
        if int(countdown_state.countdown_remaining_sec) % 10 == 0:
            print(f"[{now.strftime('%H:%M:%S')}] Countdown: {countdown_state.countdown_remaining_sec:.1f}s | Gate: {countdown_state.peak_zone} | Score: {countdown_state.current_score:.1f}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error in countdown cycle: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main loop - runs every second"""
    global countdown_state
    
    print("="*70)
    print("MT5 META AGENT - CALCULATION ENGINE WITH COUNTDOWN")
    print("="*70)
    print(f"Database: {DB_PATH}")
    print(f"Update Interval: {UPDATE_INTERVAL_SEC}s")
    print(f"Score Recalc: {SCORE_RECALC_INTERVAL_SEC}s")
    print(f"Symbol: {SYMBOL}")
    print("="*70)
    
    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"\n✗ Database not found: {DB_PATH}")
        return
    
    print("\n✓ Database connected")
    
    # Get initial snapshot
    print("✓ Getting initial 15m snapshot...")
    snapshot = get_latest_15m_snapshot()
    if not snapshot:
        print("✗ No 15m data available. Run mt5_collector.py first!")
        return
    
    print(f"✓ Snapshot loaded: {snapshot['timestamp']}")
    print(f"  Price: ${snapshot['price_close']:.2f}")
    
    # Initialize countdown state
    config = get_execution_gate_config()
    countdown_state.current_score = calculate_trade_score(snapshot)
    countdown_state.peak_zone = max(1, int(countdown_state.current_score / 10) + 1)
    countdown_state.peak_zone_timestamp = datetime.now()
    countdown_state.countdown_sec = (config['base_interval_sec'] if config else 60) / countdown_state.peak_zone
    countdown_state.countdown_remaining_sec = countdown_state.countdown_sec
    countdown_state.last_score_calc = datetime.now()
    
    print(f"\n✓ Initial state:")
    print(f"  Score: {countdown_state.current_score:.1f}/100")
    print(f"  Peak Zone: {countdown_state.peak_zone}")
    print(f"  Countdown: {countdown_state.countdown_sec:.1f}s")
    
    print("\n✓ Starting countdown loop...")
    print("\nPress Ctrl+C to stop\n")
    
    cycle_count = 0
    last_snapshot_update = datetime.now()
    
    try:
        while True:
            cycle_count += 1
            
            # Update snapshot every 60 seconds
            if (datetime.now() - last_snapshot_update).total_seconds() >= 60:
                snapshot = get_latest_15m_snapshot()
                last_snapshot_update = datetime.now()
            
            # Run countdown cycle
            run_countdown_cycle(snapshot)
            
            # Wait for next tick
            time.sleep(UPDATE_INTERVAL_SEC)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("✓ CALCULATION ENGINE STOPPED")
        print("="*70)
        print(f"Total cycles: {cycle_count}")
        print(f"Final score: {countdown_state.current_score:.1f}")
        print(f"Final gate: {countdown_state.peak_zone}")
        print("="*70)


if __name__ == "__main__":
    main()
