"""
MT5 Live Position Sync Manager (SEED 10D)
==========================================
Synchronizes live MT5 positions to instance databases in real-time.

Features:
- Multi-instance support (one sync thread per active instance)
- Thread-safe position updates
- Automatic detection of externally closed positions
- Configurable poll interval

Usage:
    from mt5_live_position_sync import PositionSyncManager
    
    sync_manager = PositionSyncManager(instance_db)
    sync_manager.start_sync('instance_id', 'XAUJ26')
    ...
    sync_manager.stop_sync('instance_id')
    sync_manager.stop_all()
"""

import threading
import time
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[MT5Sync] MetaTrader5 not installed - sync disabled")


@dataclass
class SyncState:
    """State for a single instance sync thread"""
    instance_id: str
    symbol: str
    thread: Optional[threading.Thread] = None
    running: bool = False
    last_sync: Optional[str] = None
    position_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


class PositionSyncManager:
    """
    Manages live MT5 position synchronization for multiple instances.
    Each active instance gets its own polling thread.
    """
    
    def __init__(self, instance_db, poll_interval: float = 1.0):
        """
        Args:
            instance_db: InstanceDatabaseManager instance
            poll_interval: Seconds between MT5 polls (default 1.0)
        """
        self.db = instance_db
        self.poll_interval = poll_interval
        self._syncs: Dict[str, SyncState] = {}
        self._lock = threading.Lock()
        self._mt5_connected = False
        
        # Callbacks
        self.on_position_update: Optional[Callable[[str, dict], None]] = None
        self.on_position_closed: Optional[Callable[[str, int], None]] = None
        self.on_sync_error: Optional[Callable[[str, str], None]] = None
    
    def _ensure_mt5_connection(self) -> bool:
        """Ensure MT5 is connected, attempt reconnect if needed"""
        if not MT5_AVAILABLE:
            return False
        
        if self._mt5_connected and mt5.terminal_info() is not None:
            return True
        
        if mt5.initialize():
            self._mt5_connected = True
            print("[MT5Sync] Connected to MT5")
            return True
        
        self._mt5_connected = False
        return False
    
    def start_sync(self, instance_id: str, symbol: str) -> bool:
        """
        Start position sync for an instance.
        
        Args:
            instance_id: Instance to sync positions for
            symbol: MT5 symbol to filter positions (e.g., 'XAUJ26')
        
        Returns:
            True if sync started successfully
        """
        with self._lock:
            # Check if already running
            if instance_id in self._syncs and self._syncs[instance_id].running:
                print(f"[MT5Sync] Sync already running for {instance_id}")
                return True
            
            # Verify MT5 connection
            if not self._ensure_mt5_connection():
                print(f"[MT5Sync] Cannot start sync - MT5 not connected")
                return False
            
            # Create sync state
            state = SyncState(
                instance_id=instance_id,
                symbol=symbol.upper(),
                running=True
            )
            
            # Start thread
            state.thread = threading.Thread(
                target=self._sync_loop,
                args=(state,),
                daemon=True,
                name=f"MT5Sync-{instance_id[:12]}"
            )
            
            self._syncs[instance_id] = state
            state.thread.start()
            
            print(f"[MT5Sync] Started sync for {instance_id} ({symbol})")
            return True
    
    def stop_sync(self, instance_id: str) -> bool:
        """
        Stop position sync for an instance.
        
        Args:
            instance_id: Instance to stop syncing
        
        Returns:
            True if sync was stopped
        """
        with self._lock:
            if instance_id not in self._syncs:
                return False
            
            state = self._syncs[instance_id]
            state.running = False
            
            # Wait for thread to finish
            if state.thread and state.thread.is_alive():
                state.thread.join(timeout=2.0)
            
            del self._syncs[instance_id]
            print(f"[MT5Sync] Stopped sync for {instance_id}")
            return True
    
    def stop_all(self):
        """Stop all sync threads"""
        instance_ids = list(self._syncs.keys())
        for instance_id in instance_ids:
            self.stop_sync(instance_id)
        
        # Shutdown MT5 connection
        if self._mt5_connected:
            mt5.shutdown()
            self._mt5_connected = False
            print("[MT5Sync] Disconnected from MT5")
    
    def get_sync_status(self, instance_id: str) -> Optional[dict]:
        """Get sync status for an instance"""
        with self._lock:
            if instance_id not in self._syncs:
                return None
            
            state = self._syncs[instance_id]
            return {
                "instance_id": state.instance_id,
                "symbol": state.symbol,
                "running": state.running,
                "last_sync": state.last_sync,
                "position_count": state.position_count,
                "error_count": state.error_count,
                "last_error": state.last_error
            }
    
    def get_all_sync_statuses(self) -> List[dict]:
        """Get sync status for all active syncs"""
        with self._lock:
            return [
                {
                    "instance_id": s.instance_id,
                    "symbol": s.symbol,
                    "running": s.running,
                    "last_sync": s.last_sync,
                    "position_count": s.position_count,
                    "error_count": s.error_count
                }
                for s in self._syncs.values()
            ]
    
    def is_syncing(self, instance_id: str) -> bool:
        """Check if an instance is currently syncing"""
        with self._lock:
            return instance_id in self._syncs and self._syncs[instance_id].running
    
    def _sync_loop(self, state: SyncState):
        """
        Main sync loop for a single instance.
        Runs in its own thread, polls MT5 at configured interval.
        """
        print(f"[MT5Sync] Sync loop started for {state.instance_id}")
        
        while state.running:
            try:
                # Check MT5 connection
                if not self._ensure_mt5_connection():
                    state.last_error = "MT5 connection lost"
                    state.error_count += 1
                    if self.on_sync_error:
                        self.on_sync_error(state.instance_id, state.last_error)
                    time.sleep(5.0)  # Wait longer before retry
                    continue
                
                # Fetch positions from MT5
                positions = self._fetch_mt5_positions(state.symbol)
                
                # Get active ticket numbers
                active_tickets = [p['ticket'] for p in positions]
                
                # Sync each position to database
                for pos_data in positions:
                    try:
                        self.db.upsert_mt5_position(state.instance_id, pos_data)
                        
                        if self.on_position_update:
                            self.on_position_update(state.instance_id, pos_data)
                    
                    except Exception as e:
                        print(f"[MT5Sync] Error syncing position {pos_data.get('ticket')}: {e}")
                        state.error_count += 1
                
                # Mark closed positions
                closed_count = self.db.mark_positions_closed_by_mt5(
                    state.instance_id, 
                    active_tickets
                )
                
                if closed_count > 0 and self.on_position_closed:
                    self.on_position_closed(state.instance_id, closed_count)
                
                # Update state
                state.last_sync = datetime.utcnow().isoformat() + "Z"
                state.position_count = len(positions)
                state.last_error = None
                
            except Exception as e:
                state.last_error = str(e)
                state.error_count += 1
                print(f"[MT5Sync] Sync error for {state.instance_id}: {e}")
                
                if self.on_sync_error:
                    self.on_sync_error(state.instance_id, state.last_error)
            
            # Wait for next poll
            time.sleep(self.poll_interval)
        
        print(f"[MT5Sync] Sync loop ended for {state.instance_id}")
    
    def _fetch_mt5_positions(self, symbol: str) -> List[dict]:
        """
        Fetch open positions from MT5 for a specific symbol.
        
        Args:
            symbol: Symbol to filter (e.g., 'XAUJ26')
        
        Returns:
            List of position dicts with MT5 data
        """
        if not MT5_AVAILABLE or not self._mt5_connected:
            return []
        
        # Get all positions for symbol
        positions = mt5.positions_get(symbol=symbol)
        
        if positions is None:
            return []
        
        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': pos.type,  # 0=BUY, 1=SELL
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'swap': pos.swap,
                'commission': 0.0,  # MT5 positions don't have commission field directly
                'magic': pos.magic,
                'time': pos.time,
                'comment': pos.comment
            })
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON & HELPERS
# ═══════════════════════════════════════════════════════════════════════════

_sync_manager = None

def get_sync_manager(instance_db=None) -> Optional[PositionSyncManager]:
    """
    Get singleton sync manager instance.
    Must provide instance_db on first call.
    """
    global _sync_manager
    
    if _sync_manager is None:
        if instance_db is None:
            return None
        _sync_manager = PositionSyncManager(instance_db)
    
    return _sync_manager


# ═══════════════════════════════════════════════════════════════════════════
# CLI FOR TESTING
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MT5 Position Sync Manager")
    parser.add_argument('--instance', required=True, help='Instance ID to sync')
    parser.add_argument('--symbol', required=True, help='Symbol to sync (e.g., XAUJ26)')
    parser.add_argument('--interval', type=float, default=1.0, help='Poll interval in seconds')
    parser.add_argument('--duration', type=int, default=60, help='Run for N seconds')
    
    args = parser.parse_args()
    
    # Import instance database
    from instance_database import get_instance_db
    db = get_instance_db()
    
    # Create sync manager
    manager = PositionSyncManager(db, poll_interval=args.interval)
    
    # Set up callbacks for logging
    def on_update(instance_id, pos):
        print(f"  Position update: {pos['symbol']} {pos['ticket']} P&L: ${pos['profit']:.2f}")
    
    def on_closed(instance_id, count):
        print(f"  {count} position(s) closed externally")
    
    manager.on_position_update = on_update
    manager.on_position_closed = on_closed
    
    # Start sync
    print(f"Starting sync for {args.instance} ({args.symbol})")
    print(f"Running for {args.duration} seconds...")
    
    if manager.start_sync(args.instance, args.symbol):
        try:
            for i in range(args.duration):
                time.sleep(1)
                status = manager.get_sync_status(args.instance)
                if status and i % 10 == 0:
                    print(f"[{i}s] Positions: {status['position_count']}, Errors: {status['error_count']}")
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            manager.stop_all()
            print("Sync stopped")
    else:
        print("Failed to start sync")
