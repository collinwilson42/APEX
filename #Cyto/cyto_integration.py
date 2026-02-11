"""
CYTO INTEGRATION BRIDGE
=======================
Connects the CytoBase to the existing Apex systems:
- Sentiment Engine → 6 sentiment vectors
- Virtual Broker → Trade data (P/L, direction)
- Instance Database → Instance metadata

This bridge:
1. Listens to sentiment readings and extracts vector scores
2. Listens to trade closures and captures P/L data
3. Combines both into geometric nodes for the CytoBase

SEED 15A - Phase 5: Integration Layer
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import CytoBase components
from cyto_schema import init_db, DB_PATH
from cyto_manager import CytoManager


class CytoIntegration:
    """
    Bridge between Apex systems and CytoBase.
    
    Usage:
        # Initialize once at startup
        cyto = CytoIntegration()
        
        # Register with sentiment engine
        sentiment_scheduler.add_callback(cyto.on_sentiment_reading)
        
        # Register with virtual broker
        broker.set_trade_callback(cyto.on_trade_close)
        
        # Or manually feed data
        cyto.record_bar(
            instance_id="XAUJ26_SIM_001",
            timestamp=datetime.now(),
            sentiment_data={...},
            trade_data={...}  # Optional
        )
    """
    
    def __init__(self, db_path: str = None):
        """Initialize the Cyto integration bridge."""
        self.db_path = db_path or DB_PATH
        
        # Initialize schema if needed
        init_db()
        
        # Create manager
        self.manager = CytoManager(self.db_path)
        
        # Track active instances
        self._active_instances: Dict[str, dict] = {}
        
        # Last 1H sentiment cache (sticky until next 1H bar)
        self._last_1h_sentiment: Dict[str, dict] = {}  # instance_id -> sentiment data
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        print(f"✓ CytoIntegration initialized: {self.db_path}")
    
    # ========================================
    # INSTANCE MANAGEMENT
    # ========================================
    
    def register_instance(
        self,
        instance_id: str,
        symbol: str,
        profile_name: str = None,
        config: Dict = None
    ) -> str:
        """
        Register a simulation instance with CytoBase.
        Call this when starting a new simulation run.
        """
        with self._lock:
            # Check if already exists
            existing = self.manager.get_instance(instance_id)
            if existing:
                # Load P/L history for accurate percentile calculations
                self.manager.load_pnl_history(instance_id)
                self._active_instances[instance_id] = {
                    'symbol': symbol,
                    'profile_name': profile_name,
                    'started_at': existing['created_at']
                }
                print(f"[Cyto] Instance restored: {instance_id}")
                return instance_id
            
            # Create new instance
            self.manager.create_instance(
                instance_id=instance_id,
                symbol=symbol,
                profile_name=profile_name,
                config=config
            )
            
            self._active_instances[instance_id] = {
                'symbol': symbol,
                'profile_name': profile_name,
                'started_at': datetime.now().isoformat()
            }
            
            print(f"[Cyto] Instance registered: {instance_id}")
            return instance_id
    
    def complete_instance(self, instance_id: str):
        """Mark an instance as completed."""
        stats = self.manager.get_instance_stats(instance_id)
        self.manager.update_instance_status(
            instance_id,
            status='completed',
            total_trades=stats.get('total_trades', 0),
            total_pnl=stats.get('total_pnl', 0.0),
            win_rate=stats.get('win_rate')
        )
        
        if instance_id in self._active_instances:
            del self._active_instances[instance_id]
        
        print(f"[Cyto] Instance completed: {instance_id}")
    
    # ========================================
    # SENTIMENT VECTOR EXTRACTION
    # ========================================
    
    def extract_vectors_from_reading(self, reading: Dict) -> Dict[str, float]:
        """
        Extract 6 sentiment vectors from a sentiment reading.
        
        Maps the 5 narrative categories + composite to our 6 vectors:
        v1: price_action_score
        v2: key_levels_score
        v3: momentum_score
        v4: volume_score
        v5: structure_score
        v6: composite_score (overall bias)
        """
        return {
            'v1': reading.get('price_action_score', 0.0),
            'v2': reading.get('key_levels_score', 0.0),
            'v3': reading.get('momentum_score', 0.0),
            'v4': reading.get('volume_score', 0.0),
            'v5': reading.get('structure_score', 0.0),
            'v6': reading.get('composite_score', 0.0)
        }
    
    def calc_weighted_average(self, vectors: Dict[str, float]) -> float:
        """
        Calculate weighted average of 6 vectors.
        
        Weights (can be tuned):
        - v1 (price_action): 0.20
        - v2 (key_levels): 0.15
        - v3 (momentum): 0.20
        - v4 (volume): 0.15
        - v5 (structure): 0.15
        - v6 (composite): 0.15
        """
        weights = {
            'v1': 0.20,  # Price Action
            'v2': 0.15,  # Key Levels
            'v3': 0.20,  # Momentum
            'v4': 0.15,  # Volume
            'v5': 0.15,  # Structure
            'v6': 0.15   # Composite
        }
        
        total = 0.0
        for key, weight in weights.items():
            total += vectors.get(key, 0.0) * weight
        
        return round(total, 4)
    
    # ========================================
    # DATA INGESTION - SENTIMENT
    # ========================================
    
    def on_sentiment_reading(
        self,
        instance_id: str,
        reading: Dict,
        timeframe: str = '15m'
    ):
        """
        Callback for new sentiment readings.
        
        Args:
            instance_id: The trading instance ID
            reading: Dict containing sentiment scores and narratives
            timeframe: '15m' or '1h'
        """
        with self._lock:
            # Extract vectors
            vectors = self.extract_vectors_from_reading(reading)
            weighted = self.calc_weighted_average(vectors)
            
            # Update 1H cache if this is a 1H reading
            if timeframe == '1h':
                self._last_1h_sentiment[instance_id] = {
                    'vectors': vectors,
                    'weighted': weighted,
                    'timestamp': reading.get('timestamp', datetime.now().isoformat())
                }
                print(f"[Cyto] 1H sentiment cached for {instance_id}: {weighted:.3f}")
            
            # For 15m readings, we create a node
            elif timeframe == '15m':
                # Get sticky 1H sentiment
                cached_1h = self._last_1h_sentiment.get(instance_id, {})
                weighted_1h = cached_1h.get('weighted', weighted)  # Fallback to 15m if no 1H yet
                
                # Calculate final blend (70% 15m, 30% 1H for responsiveness)
                weighted_final = (weighted * 0.7) + (weighted_1h * 0.3)
                
                # Parse timestamp
                ts_str = reading.get('timestamp')
                if isinstance(ts_str, str):
                    try:
                        timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()
                
                # Store for later node creation (trade may close on this bar)
                if instance_id not in self._active_instances:
                    return
                
                self._active_instances[instance_id]['pending_bar'] = {
                    'timestamp': timestamp,
                    'vectors_15m': vectors,
                    'weighted_15m': weighted,
                    'weighted_1h': weighted_1h,
                    'weighted_final': weighted_final
                }
                
                print(f"[Cyto] 15m sentiment stored for {instance_id}: final={weighted_final:.3f}")
    
    # ========================================
    # DATA INGESTION - TRADES
    # ========================================
    
    def on_trade_close(
        self,
        instance_id: str,
        trade_data: Dict
    ):
        """
        Callback for trade closures.
        
        Args:
            instance_id: The trading instance ID
            trade_data: Dict with trade details:
                - ticket: Trade ticket number
                - direction: 'long' or 'short'
                - entry_price: Entry price
                - exit_price: Exit price
                - volume/lots: Position size
                - pnl: Realized P/L (raw)
                - pnl_normalized: P/L normalized to 1 lot (optional)
                - entry_time: Entry timestamp
                - exit_time: Exit timestamp
        """
        with self._lock:
            if instance_id not in self._active_instances:
                print(f"[Cyto] Warning: Trade for unknown instance {instance_id}")
                return
            
            instance = self._active_instances[instance_id]
            pending = instance.get('pending_bar')
            
            # Get exit timestamp
            exit_time = trade_data.get('exit_time')
            if isinstance(exit_time, str):
                try:
                    exit_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                except:
                    exit_time = datetime.now()
            elif exit_time is None:
                exit_time = datetime.now()
            
            # Build trade data for node
            trade_for_node = {
                'pnl_raw': trade_data.get('pnl', 0.0),
                'pnl_normalized': trade_data.get('pnl_normalized', trade_data.get('pnl', 0.0)),
                'direction': trade_data.get('direction', 'long')
            }
            
            # Create node with trade
            if pending:
                # Use pending bar data
                node_id = self.manager.add_node(
                    instance_id=instance_id,
                    timestamp=pending['timestamp'],
                    vectors_15m=pending['vectors_15m'],
                    weighted_15m=pending['weighted_15m'],
                    weighted_1h=pending['weighted_1h'],
                    weighted_final=pending['weighted_final'],
                    trade_data=trade_for_node
                )
                
                # Clear pending bar
                instance['pending_bar'] = None
            else:
                # No pending bar - create minimal node with just trade data
                node_id = self.manager.add_node(
                    instance_id=instance_id,
                    timestamp=exit_time,
                    trade_data=trade_for_node
                )
            
            # Add detailed trade record
            entry_time = trade_data.get('entry_time')
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                except:
                    entry_time = exit_time
            elif entry_time is None:
                entry_time = exit_time
            
            self.manager.add_trade(
                node_id=node_id,
                instance_id=instance_id,
                entry_time=entry_time,
                exit_time=exit_time,
                entry_price=trade_data.get('entry_price', 0.0),
                exit_price=trade_data.get('exit_price', 0.0),
                lots=trade_data.get('volume', trade_data.get('lots', 0.01)),
                direction=trade_data.get('direction', 'long'),
                pnl_raw=trade_data.get('pnl', 0.0),
                pnl_normalized=trade_data.get('pnl_normalized', trade_data.get('pnl', 0.0))
            )
            
            pnl = trade_data.get('pnl', 0.0)
            print(f"[Cyto] Trade recorded for {instance_id}: ${pnl:+.2f} (node {node_id})")
    
    # ========================================
    # MANUAL BAR RECORDING
    # ========================================
    
    def record_bar(
        self,
        instance_id: str,
        timestamp: datetime,
        sentiment_data: Dict = None,
        trade_data: Dict = None
    ) -> int:
        """
        Manually record a bar to CytoBase.
        
        Args:
            instance_id: Instance identifier
            timestamp: Bar timestamp
            sentiment_data: Dict with sentiment readings (optional)
            trade_data: Dict with trade details if trade closed (optional)
            
        Returns:
            The created node_id
        """
        with self._lock:
            vectors = None
            weighted_15m = None
            weighted_1h = None
            weighted_final = None
            
            if sentiment_data:
                vectors = self.extract_vectors_from_reading(sentiment_data)
                weighted_15m = self.calc_weighted_average(vectors)
                
                # Get cached 1H
                cached_1h = self._last_1h_sentiment.get(instance_id, {})
                weighted_1h = cached_1h.get('weighted', weighted_15m)
                
                weighted_final = (weighted_15m * 0.7) + (weighted_1h * 0.3)
            
            # Format trade data if present
            trade_for_node = None
            if trade_data:
                trade_for_node = {
                    'pnl_raw': trade_data.get('pnl', trade_data.get('pnl_raw', 0.0)),
                    'pnl_normalized': trade_data.get('pnl_normalized', trade_data.get('pnl', 0.0)),
                    'direction': trade_data.get('direction', 'long')
                }
            
            node_id = self.manager.add_node(
                instance_id=instance_id,
                timestamp=timestamp,
                vectors_15m=vectors,
                weighted_15m=weighted_15m,
                weighted_1h=weighted_1h,
                weighted_final=weighted_final,
                trade_data=trade_for_node
            )
            
            return node_id
    
    # ========================================
    # FLUSH PENDING DATA
    # ========================================
    
    def flush_pending_bars(self):
        """
        Flush any pending bar data that hasn't been saved yet.
        Call this periodically or at end of session.
        """
        with self._lock:
            for instance_id, instance in self._active_instances.items():
                pending = instance.get('pending_bar')
                if pending:
                    self.manager.add_node(
                        instance_id=instance_id,
                        timestamp=pending['timestamp'],
                        vectors_15m=pending['vectors_15m'],
                        weighted_15m=pending['weighted_15m'],
                        weighted_1h=pending['weighted_1h'],
                        weighted_final=pending['weighted_final'],
                        trade_data=None
                    )
                    instance['pending_bar'] = None
            
            print(f"[Cyto] Flushed pending bars")
    
    # ========================================
    # QUERY SHORTCUTS
    # ========================================
    
    def get_instance_stats(self, instance_id: str) -> Dict:
        """Get stats for an instance."""
        return self.manager.get_instance_stats(instance_id)
    
    def get_epoch_data(self, instance_id: str, cycle_index: int = None) -> list:
        """Get nodes for an epoch (defaults to current cycle)."""
        if cycle_index is None:
            cycle_index = self.manager.get_current_cycle()
        return self.manager.get_epoch_nodes(instance_id, cycle_index)
    
    def get_all_trades(self, instance_id: str) -> list:
        """Get all trade nodes for an instance."""
        return self.manager.get_nodes_with_trades(instance_id)


# ============================================
# GLOBAL INSTANCE (for easy access)
# ============================================

_cyto_integration: Optional[CytoIntegration] = None

def get_cyto_integration() -> CytoIntegration:
    """Get or create the global CytoIntegration instance."""
    global _cyto_integration
    if _cyto_integration is None:
        _cyto_integration = CytoIntegration()
    return _cyto_integration


# ============================================
# MAIN - Testing
# ============================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("CytoIntegration Test")
    print("=" * 50)
    
    # Create integration
    cyto = CytoIntegration()
    
    # Register test instance
    instance_id = cyto.register_instance(
        instance_id="TEST_CYTO_001",
        symbol="XAUJ26",
        profile_name="FLASH_2.0",
        config={"version": "test"}
    )
    
    # Simulate some sentiment readings
    for i in range(5):
        # 1H reading (every 4 bars)
        if i % 4 == 0:
            cyto.on_sentiment_reading(
                instance_id=instance_id,
                reading={
                    'timestamp': datetime.now().isoformat(),
                    'price_action_score': 0.6,
                    'key_levels_score': 0.3,
                    'momentum_score': 0.5,
                    'volume_score': 0.2,
                    'structure_score': 0.4,
                    'composite_score': 0.45
                },
                timeframe='1h'
            )
        
        # 15m reading
        cyto.on_sentiment_reading(
            instance_id=instance_id,
            reading={
                'timestamp': datetime.now().isoformat(),
                'price_action_score': 0.5 + i*0.1,
                'key_levels_score': 0.2,
                'momentum_score': 0.4,
                'volume_score': 0.3,
                'structure_score': 0.3,
                'composite_score': 0.35 + i*0.05
            },
            timeframe='15m'
        )
        
        # Simulate trade on bar 2
        if i == 2:
            cyto.on_trade_close(
                instance_id=instance_id,
                trade_data={
                    'ticket': 1001,
                    'direction': 'long',
                    'entry_price': 2850.50,
                    'exit_price': 2865.00,
                    'volume': 0.1,
                    'pnl': 145.00,
                    'entry_time': datetime.now().isoformat(),
                    'exit_time': datetime.now().isoformat()
                }
            )
    
    # Flush remaining
    cyto.flush_pending_bars()
    
    # Get stats
    stats = cyto.get_instance_stats(instance_id)
    print(f"\n📈 Instance stats:")
    print(f"   Total nodes: {stats.get('total_nodes', 0)}")
    print(f"   Total trades: {stats.get('total_trades', 0)}")
    print(f"   Total P/L: ${stats.get('total_pnl', 0):.2f}")
    print(f"   Win rate: {stats.get('win_rate', 0)*100:.1f}%" if stats.get('win_rate') else "   Win rate: N/A")
    
    # Get trade nodes
    trades = cyto.get_all_trades(instance_id)
    print(f"\n📊 Trade nodes: {len(trades)}")
    for t in trades:
        print(f"   Node {t['node_id']}: ${t['raw_pnl']:.2f} @ slot {t['theta_slot']}")
    
    print("\n" + "=" * 50)
    print("✓ CytoIntegration test complete")
    print("=" * 50 + "\n")
