"""
BROKER FACTORY - Create the Right Broker
=========================================
Factory pattern to instantiate VirtualBroker or LiveBroker
based on mode configuration.

Seed 14B - The Virtual Broker Implementation
"""

from typing import Dict, Optional

from .base_broker import IBroker, BrokerMode
from .virtual_broker import VirtualBroker

# Conditional LiveBroker import
try:
    from .live_broker import LiveBroker, MT5_AVAILABLE
except ImportError:
    LiveBroker = None
    MT5_AVAILABLE = False


class BrokerFactory:
    """
    Broker Factory
    --------------
    Creates and manages broker instances per instance_id.
    Implements singleton pattern per instance to prevent duplicates.
    
    Usage:
        # Get a simulation broker
        broker = BrokerFactory.get_broker("instance_001", mode="SIM")
        
        # Get a live broker (requires MT5)
        broker = BrokerFactory.get_broker("instance_002", mode="LIVE")
        
        # Get existing broker (returns same instance)
        broker = BrokerFactory.get_broker("instance_001")
    """
    
    # Singleton registry: instance_id -> broker
    _brokers: Dict[str, IBroker] = {}
    
    @classmethod
    def get_broker(cls, 
                   instance_id: str, 
                   mode: str = "SIM",
                   initial_balance: float = 10000.0,
                   force_new: bool = False,
                   db_manager=None) -> IBroker:
        """
        Get or create a broker for the given instance.
        
        Args:
            instance_id: Unique instance identifier
            mode: "SIM" for VirtualBroker, "LIVE" for LiveBroker
            initial_balance: Starting balance for SIM mode
            force_new: If True, replace existing broker
            db_manager: Optional database manager for persistence
            
        Returns:
            IBroker instance (VirtualBroker or LiveBroker)
            
        Raises:
            ValueError: If LIVE mode requested but MT5 not available
        """
        # Return existing broker if not forcing new
        if not force_new and instance_id in cls._brokers:
            existing = cls._brokers[instance_id]
            # Warn if mode mismatch
            if existing.mode.value != mode:
                print(f"[BrokerFactory] Warning: Existing broker for {instance_id} "
                      f"is {existing.mode.value}, requested {mode}")
            return existing
        
        # Create new broker based on mode
        broker_mode = BrokerMode(mode.upper())
        
        if broker_mode == BrokerMode.SIM:
            broker = VirtualBroker(instance_id, initial_balance, db_manager=db_manager)
        
        elif broker_mode == BrokerMode.LIVE:
            if not MT5_AVAILABLE or LiveBroker is None:
                raise ValueError(
                    "LIVE mode requires MetaTrader5 package. "
                    "Install with: pip install MetaTrader5"
                )
            broker = LiveBroker(instance_id)
            if not broker.connect():
                raise ValueError(
                    "Failed to connect to MT5. Ensure terminal is running."
                )
        
        else:
            raise ValueError(f"Unknown broker mode: {mode}")
        
        # Register and return
        cls._brokers[instance_id] = broker
        print(f"[BrokerFactory] Created {mode} broker for {instance_id}")
        
        return broker
    
    @classmethod
    def get_existing(cls, instance_id: str) -> Optional[IBroker]:
        """Get existing broker without creating new one"""
        return cls._brokers.get(instance_id)
    
    @classmethod
    def remove_broker(cls, instance_id: str) -> bool:
        """
        Remove and cleanup broker for instance.
        
        Args:
            instance_id: Instance to remove
            
        Returns:
            True if broker was removed, False if not found
        """
        if instance_id not in cls._brokers:
            return False
        
        broker = cls._brokers.pop(instance_id)
        
        # Cleanup for LiveBroker
        if hasattr(broker, 'disconnect'):
            broker.disconnect()
        
        print(f"[BrokerFactory] Removed broker for {instance_id}")
        return True
    
    @classmethod
    def get_all_brokers(cls) -> Dict[str, IBroker]:
        """Get all registered brokers"""
        return dict(cls._brokers)
    
    @classmethod
    def get_all_states(cls) -> Dict[str, dict]:
        """Get state dict for all brokers (for API response)"""
        return {
            instance_id: broker.get_state()
            for instance_id, broker in cls._brokers.items()
        }
    
    @classmethod
    def broadcast_tick(cls, symbol: str, bid: float, ask: float) -> None:
        """
        Broadcast price tick to all brokers.
        Called by the central data collector (Hub pattern).
        
        Args:
            symbol: Symbol that ticked
            bid: Current bid price
            ask: Current ask price
        """
        for broker in cls._brokers.values():
            broker.on_tick(symbol, bid, ask)
    
    @classmethod
    def clear_all(cls) -> None:
        """Remove all brokers (for testing/reset)"""
        for instance_id in list(cls._brokers.keys()):
            cls.remove_broker(instance_id)
        print("[BrokerFactory] Cleared all brokers")
