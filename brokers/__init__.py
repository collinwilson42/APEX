"""
BROKERS PACKAGE
===============
Unified broker interface for SIM and LIVE trading.

Seed 14B - The Virtual Broker Implementation

Usage:
    from brokers import BrokerFactory
    
    # Create simulation broker
    broker = BrokerFactory.get_broker("instance_001", mode="SIM")
    
    # Feed price data
    broker.on_tick("XAUJ26", bid=2850.50, ask=2850.70)
    
    # Execute trades (same interface for SIM and LIVE)
    result = broker.buy("XAUJ26", 0.1, sl=2840, tp=2870)
    
    # Get state for API/frontend
    state = broker.get_state()
"""

from .base_broker import IBroker, BrokerMode, Position, OrderResult
from .virtual_broker import VirtualBroker
from .broker_factory import BrokerFactory

# LiveBroker imported conditionally (requires MT5)
try:
    from .live_broker import LiveBroker
except ImportError:
    LiveBroker = None

__all__ = [
    'IBroker', 
    'BrokerMode', 
    'Position', 
    'OrderResult',
    'VirtualBroker', 
    'LiveBroker', 
    'BrokerFactory'
]
