"""
BASE BROKER - IBroker Interface
===============================
Abstract interface that both VirtualBroker and LiveBroker implement.
Strategy code calls broker.buy() without knowing if it's SIM or LIVE.

Seed 14B - The Virtual Broker Implementation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class BrokerMode(Enum):
    """Broker execution mode"""
    SIM = "SIM"      # Virtual/Paper trading
    LIVE = "LIVE"    # Real MT5 execution


@dataclass
class Position:
    """
    Unified position representation.
    Same structure whether from VirtualBroker or MT5.
    """
    ticket: int                     # Unique position ID
    symbol: str                     # e.g., "XAUJ26"
    direction: str                  # "BUY" or "SELL"
    volume: float                   # Lot size
    open_price: float               # Entry price
    open_time: datetime             # When opened
    sl: Optional[float] = None      # Stop loss
    tp: Optional[float] = None      # Take profit
    current_price: Optional[float] = None  # Latest price (for PnL calc)
    pnl: float = 0.0                # Unrealized P&L
    comment: str = ""               # Order comment/tag
    
    def calculate_pnl(self, current_price: float, point_value: float = 1.0) -> float:
        """Calculate unrealized PnL based on current price"""
        if self.direction == "BUY":
            self.pnl = (current_price - self.open_price) * self.volume * point_value
        else:  # SELL
            self.pnl = (self.open_price - current_price) * self.volume * point_value
        self.current_price = current_price
        return self.pnl


@dataclass
class OrderResult:
    """Result of a trade operation"""
    success: bool
    ticket: Optional[int] = None    # Position ticket if opened
    message: str = ""               # Success/error message
    price: Optional[float] = None   # Execution price
    timestamp: datetime = field(default_factory=datetime.now)


class IBroker(ABC):
    """
    Abstract Broker Interface
    -------------------------
    Both VirtualBroker and LiveBroker implement this interface.
    The strategy layer only sees these methods - complete decoupling.
    
    Pattern: Dependency Injection / Strategy Pattern
    """
    
    def __init__(self, instance_id: str, mode: BrokerMode):
        self.instance_id = instance_id
        self.mode = mode
    
    @abstractmethod
    def buy(self, symbol: str, volume: float, 
            sl: Optional[float] = None, 
            tp: Optional[float] = None,
            comment: str = "") -> OrderResult:
        """
        Open a BUY position.
        
        Args:
            symbol: Trading symbol (e.g., "XAUJ26")
            volume: Lot size
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            comment: Order comment/tag
            
        Returns:
            OrderResult with success status and ticket
        """
        pass
    
    @abstractmethod
    def sell(self, symbol: str, volume: float,
             sl: Optional[float] = None,
             tp: Optional[float] = None,
             comment: str = "") -> OrderResult:
        """
        Open a SELL position.
        
        Args:
            symbol: Trading symbol
            volume: Lot size
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            comment: Order comment/tag
            
        Returns:
            OrderResult with success status and ticket
        """
        pass
    
    @abstractmethod
    def close(self, ticket: int) -> OrderResult:
        """
        Close a specific position by ticket.
        
        Args:
            ticket: Position ticket ID
            
        Returns:
            OrderResult with success status
        """
        pass
    
    @abstractmethod
    def close_all(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """
        Close all positions, optionally filtered by symbol.
        
        Args:
            symbol: If provided, only close positions for this symbol
            
        Returns:
            List of OrderResults for each closed position
        """
        pass
    
    @abstractmethod
    def modify(self, ticket: int, 
               sl: Optional[float] = None,
               tp: Optional[float] = None) -> OrderResult:
        """
        Modify SL/TP of an existing position.
        
        Args:
            ticket: Position ticket ID
            sl: New stop loss (None = don't change)
            tp: New take profit (None = don't change)
            
        Returns:
            OrderResult with success status
        """
        pass
    
    @abstractmethod
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get all open positions.
        
        Args:
            symbol: If provided, filter by symbol
            
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    def get_position(self, ticket: int) -> Optional[Position]:
        """
        Get a specific position by ticket.
        
        Args:
            ticket: Position ticket ID
            
        Returns:
            Position if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_pnl(self) -> float:
        """
        Get total unrealized P&L across all positions.
        
        Returns:
            Total unrealized profit/loss
        """
        pass
    
    @abstractmethod
    def on_tick(self, symbol: str, bid: float, ask: float) -> None:
        """
        Called by the engine when new price data arrives.
        Allows broker to update position PnL without external calls.
        
        Args:
            symbol: Symbol that ticked
            bid: Current bid price
            ask: Current ask price
        """
        pass
    
    @abstractmethod
    def get_state(self) -> dict:
        """
        Get broker state for database persistence / API response.
        
        Returns:
            Dict with positions, PnL, and metadata
        """
        pass
