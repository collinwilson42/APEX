"""
VIRTUAL BROKER - Simulation Implementation
==========================================
In-memory paper trading with full position tracking.
Implements IBroker interface - strategy code doesn't know the difference.

Seed 14B - The Virtual Broker Implementation
- Now with database persistence for recovery
"""

from typing import Optional, List, Dict, Callable
from datetime import datetime
import threading

from .base_broker import IBroker, BrokerMode, Position, OrderResult


class VirtualBroker(IBroker):
    """
    Paper Trading Broker
    --------------------
    - Tracks positions in memory
    - Calculates PnL based on tick data
    - Simulates order execution (instant fill at current price)
    - Thread-safe for multi-instance use
    - Optional database persistence for recovery
    
    Usage:
        broker = VirtualBroker("instance_001")
        broker.on_tick("XAUJ26", bid=2850.50, ask=2850.70)
        result = broker.buy("XAUJ26", 0.1, sl=2840, tp=2870)
        
    With persistence:
        from instance_database import get_instance_db
        db = get_instance_db()
        broker = VirtualBroker("instance_001", db_manager=db)
    """
    
    def __init__(self, instance_id: str, initial_balance: float = 10000.0,
                 db_manager=None):
        super().__init__(instance_id, BrokerMode.SIM)
        
        # Database manager (optional)
        self._db = db_manager
        
        # Position tracking
        self._positions: Dict[int, Position] = {}  # ticket -> Position
        self._next_ticket = 1000  # Start tickets at 1000
        self._lock = threading.Lock()
        
        # Price cache (updated via on_tick)
        self._prices: Dict[str, dict] = {}  # symbol -> {bid, ask}
        
        # Account state
        self.initial_balance = initial_balance
        self.realized_pnl = 0.0  # Closed position profits
        
        # Trade history (for analysis)
        self._closed_positions: List[Position] = []
        
        # Event callbacks (for external integration)
        self._on_trade_callback: Optional[Callable] = None
        
        # Initialize DB state if available
        if self._db:
            self._init_from_db()
    
    def _init_from_db(self):
        """Initialize/restore state from database"""
        try:
            # Initialize broker state in DB
            state = self._db.init_broker_state(
                self.instance_id, 
                mode="SIM",
                initial_balance=self.initial_balance
            )
            
            # Restore values from DB
            self.initial_balance = state.get('initial_balance', self.initial_balance)
            self.realized_pnl = state.get('realized_pnl', 0.0)
            
            # Get highest ticket number to prevent collisions
            positions = self._db.restore_broker_positions(self.instance_id)
            if positions:
                max_ticket = max(p.get('ticket', 0) for p in positions)
                self._next_ticket = max(self._next_ticket, max_ticket + 1)
                
                # Restore open positions
                for p in positions:
                    pos = Position(
                        ticket=p['ticket'],
                        symbol=p['symbol'],
                        direction=p['direction'],
                        volume=p['volume'],
                        open_price=p['open_price'],
                        open_time=datetime.fromisoformat(p['open_time'].replace('Z', '+00:00')) if p.get('open_time') else datetime.now(),
                        sl=p.get('sl'),
                        tp=p.get('tp'),
                        current_price=p.get('current_price', p['open_price']),
                        pnl=p.get('unrealized_pnl', 0),
                        comment=p.get('comment', '')
                    )
                    self._positions[pos.ticket] = pos
                
                print(f"[VirtualBroker] Restored {len(positions)} positions for {self.instance_id}")
        except Exception as e:
            print(f"[VirtualBroker] DB init failed (continuing without persistence): {e}")
            self._db = None
    
    def set_trade_callback(self, callback: Callable):
        """Set callback for trade events (for external integration)"""
        self._on_trade_callback = callback
    
    def _persist_position(self, position: Position, status: str = 'OPEN', 
                          close_price: float = None, close_reason: str = None):
        """Persist position to database"""
        if not self._db:
            return
        
        try:
            pos_dict = {
                'ticket': position.ticket,
                'symbol': position.symbol,
                'direction': position.direction,
                'volume': position.volume,
                'open_price': position.open_price,
                'open_time': position.open_time.isoformat() + "Z" if position.open_time else None,
                'current_price': position.current_price,
                'unrealized_pnl': position.pnl,
                'sl': position.sl,
                'tp': position.tp,
                'status': status,
                'comment': position.comment
            }
            
            if status == 'CLOSED':
                pos_dict['close_price'] = close_price
                pos_dict['close_reason'] = close_reason
                pos_dict['realized_pnl'] = position.pnl
            
            self._db.save_broker_position(self.instance_id, pos_dict)
        except Exception as e:
            print(f"[VirtualBroker] Failed to persist position: {e}")
    
    def _persist_trade(self, trade_type: str, position: Position, 
                       result: OrderResult, pnl: float = None):
        """Log trade event to database"""
        if not self._db:
            return
        
        try:
            self._db.log_broker_trade(self.instance_id, {
                'trade_type': trade_type,
                'position_ticket': position.ticket,
                'symbol': position.symbol,
                'direction': position.direction,
                'volume': position.volume,
                'price': result.price,
                'sl': position.sl,
                'tp': position.tp,
                'pnl': pnl,
                'success': result.success,
                'message': result.message
            })
        except Exception as e:
            print(f"[VirtualBroker] Failed to log trade: {e}")
    
    def _update_broker_state(self):
        """Update broker state in database"""
        if not self._db:
            return
        
        try:
            self._db.update_broker_state(
                self.instance_id,
                realized_pnl=self.realized_pnl,
                last_equity=self.get_equity(),
                last_unrealized_pnl=self.get_pnl(),
                position_count=len(self._positions)
            )
        except Exception as e:
            print(f"[VirtualBroker] Failed to update state: {e}")
    
    def _get_price(self, symbol: str, direction: str) -> Optional[float]:
        """Get execution price (ask for BUY, bid for SELL)"""
        if symbol not in self._prices:
            return None
        if direction == "BUY":
            return self._prices[symbol].get('ask')
        return self._prices[symbol].get('bid')
    
    def _generate_ticket(self) -> int:
        """Generate unique ticket ID"""
        ticket = self._next_ticket
        self._next_ticket += 1
        return ticket
    
    def on_tick(self, symbol: str, bid: float, ask: float) -> None:
        """
        Update price cache and recalculate position PnL.
        Called by the engine's data loop.
        """
        with self._lock:
            self._prices[symbol] = {'bid': bid, 'ask': ask}
            
            # Update PnL for all positions with this symbol
            for pos in list(self._positions.values()):  # List copy for safe iteration
                if pos.symbol == symbol:
                    # Use bid for long positions (what we'd get if we closed)
                    # Use ask for short positions
                    close_price = bid if pos.direction == "BUY" else ask
                    pos.calculate_pnl(close_price)
                    
                    # Check SL/TP (auto-close simulation)
                    self._check_sl_tp(pos, bid, ask)
    
    def _check_sl_tp(self, pos: Position, bid: float, ask: float) -> None:
        """Check if position hit SL or TP"""
        if pos.direction == "BUY":
            # Long position: SL hit if bid <= sl, TP hit if bid >= tp
            if pos.sl and bid <= pos.sl:
                self._close_position(pos.ticket, bid, "SL_HIT")
            elif pos.tp and bid >= pos.tp:
                self._close_position(pos.ticket, bid, "TP_HIT")
        else:
            # Short position: SL hit if ask >= sl, TP hit if ask <= tp
            if pos.sl and ask >= pos.sl:
                self._close_position(pos.ticket, ask, "SL_HIT")
            elif pos.tp and ask <= pos.tp:
                self._close_position(pos.ticket, ask, "TP_HIT")
    
    def buy(self, symbol: str, volume: float,
            sl: Optional[float] = None,
            tp: Optional[float] = None,
            comment: str = "") -> OrderResult:
        """Open a BUY position at current ask price"""
        with self._lock:
            price = self._get_price(symbol, "BUY")
            if price is None:
                return OrderResult(
                    success=False,
                    message=f"No price data for {symbol}. Call on_tick first."
                )
            
            ticket = self._generate_ticket()
            position = Position(
                ticket=ticket,
                symbol=symbol,
                direction="BUY",
                volume=volume,
                open_price=price,
                open_time=datetime.now(),
                sl=sl,
                tp=tp,
                current_price=price,
                pnl=0.0,
                comment=comment
            )
            
            self._positions[ticket] = position
            
            result = OrderResult(
                success=True,
                ticket=ticket,
                price=price,
                message=f"BUY {volume} {symbol} @ {price}"
            )
            
            # Persist
            self._persist_position(position)
            self._persist_trade('OPEN', position, result)
            self._update_broker_state()
            
            # Callback
            if self._on_trade_callback:
                self._on_trade_callback('OPEN', position, result)
            
            return result
    
    def sell(self, symbol: str, volume: float,
             sl: Optional[float] = None,
             tp: Optional[float] = None,
             comment: str = "") -> OrderResult:
        """Open a SELL position at current bid price"""
        with self._lock:
            price = self._get_price(symbol, "SELL")
            if price is None:
                return OrderResult(
                    success=False,
                    message=f"No price data for {symbol}. Call on_tick first."
                )
            
            ticket = self._generate_ticket()
            position = Position(
                ticket=ticket,
                symbol=symbol,
                direction="SELL",
                volume=volume,
                open_price=price,
                open_time=datetime.now(),
                sl=sl,
                tp=tp,
                current_price=price,
                pnl=0.0,
                comment=comment
            )
            
            self._positions[ticket] = position
            
            result = OrderResult(
                success=True,
                ticket=ticket,
                price=price,
                message=f"SELL {volume} {symbol} @ {price}"
            )
            
            # Persist
            self._persist_position(position)
            self._persist_trade('OPEN', position, result)
            self._update_broker_state()
            
            # Callback
            if self._on_trade_callback:
                self._on_trade_callback('OPEN', position, result)
            
            return result
    
    def _close_position(self, ticket: int, close_price: float, reason: str = "MANUAL") -> OrderResult:
        """Internal close (used by SL/TP and manual close)"""
        if ticket not in self._positions:
            return OrderResult(success=False, message=f"Position {ticket} not found")
        
        pos = self._positions.pop(ticket)
        pos.calculate_pnl(close_price)
        
        # Add to realized PnL
        self.realized_pnl += pos.pnl
        
        # Archive for history
        self._closed_positions.append(pos)
        
        result = OrderResult(
            success=True,
            ticket=ticket,
            price=close_price,
            message=f"Closed {pos.direction} {pos.volume} {pos.symbol} @ {close_price} | PnL: {pos.pnl:.2f} | {reason}"
        )
        
        # Persist
        self._persist_position(pos, status='CLOSED', close_price=close_price, close_reason=reason)
        self._persist_trade('CLOSE', pos, result, pnl=pos.pnl)
        self._update_broker_state()
        
        # Callback
        if self._on_trade_callback:
            self._on_trade_callback('CLOSE', pos, result)
        
        print(f"[VirtualBroker] {result.message}")
        
        return result
    
    def close(self, ticket: int) -> OrderResult:
        """Close a specific position"""
        with self._lock:
            if ticket not in self._positions:
                return OrderResult(success=False, message=f"Position {ticket} not found")
            
            pos = self._positions[ticket]
            close_price = self._get_price(pos.symbol, "SELL" if pos.direction == "BUY" else "BUY")
            
            if close_price is None:
                return OrderResult(success=False, message=f"No price data for {pos.symbol}")
            
            return self._close_position(ticket, close_price, "MANUAL")
    
    def close_all(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """Close all positions, optionally filtered by symbol"""
        with self._lock:
            results = []
            tickets_to_close = [
                t for t, p in self._positions.items()
                if symbol is None or p.symbol == symbol
            ]
            
            for ticket in tickets_to_close:
                pos = self._positions[ticket]
                close_price = self._get_price(pos.symbol, "SELL" if pos.direction == "BUY" else "BUY")
                if close_price:
                    results.append(self._close_position(ticket, close_price, "CLOSE_ALL"))
            
            return results
    
    def modify(self, ticket: int,
               sl: Optional[float] = None,
               tp: Optional[float] = None) -> OrderResult:
        """Modify SL/TP of existing position"""
        with self._lock:
            if ticket not in self._positions:
                return OrderResult(success=False, message=f"Position {ticket} not found")
            
            pos = self._positions[ticket]
            old_sl, old_tp = pos.sl, pos.tp
            
            if sl is not None:
                pos.sl = sl
            if tp is not None:
                pos.tp = tp
            
            result = OrderResult(
                success=True,
                ticket=ticket,
                message=f"Modified {ticket}: SL={pos.sl}, TP={pos.tp}"
            )
            
            # Persist
            self._persist_position(pos)
            self._persist_trade('MODIFY', pos, result)
            
            return result
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get all open positions"""
        with self._lock:
            if symbol:
                return [p for p in self._positions.values() if p.symbol == symbol]
            return list(self._positions.values())
    
    def get_position(self, ticket: int) -> Optional[Position]:
        """Get specific position by ticket"""
        with self._lock:
            return self._positions.get(ticket)
    
    def get_pnl(self) -> float:
        """Get total unrealized PnL"""
        with self._lock:
            return sum(p.pnl for p in self._positions.values())
    
    def get_equity(self) -> float:
        """Get current equity (balance + unrealized PnL)"""
        return self.initial_balance + self.realized_pnl + self.get_pnl()
    
    def get_state(self) -> dict:
        """Get full broker state for API/database"""
        with self._lock:
            return {
                'instance_id': self.instance_id,
                'mode': self.mode.value,
                'initial_balance': self.initial_balance,
                'realized_pnl': self.realized_pnl,
                'unrealized_pnl': self.get_pnl(),
                'equity': self.get_equity(),
                'position_count': len(self._positions),
                'positions': [
                    {
                        'ticket': p.ticket,
                        'symbol': p.symbol,
                        'direction': p.direction,
                        'volume': p.volume,
                        'open_price': p.open_price,
                        'open_time': p.open_time.isoformat() if p.open_time else None,
                        'current_price': p.current_price,
                        'pnl': p.pnl,
                        'sl': p.sl,
                        'tp': p.tp,
                        'comment': p.comment
                    }
                    for p in self._positions.values()
                ],
                'closed_count': len(self._closed_positions),
                'prices': dict(self._prices)
            }
    
    def get_stats(self) -> dict:
        """Get trading statistics"""
        if self._db:
            return self._db.get_broker_stats(self.instance_id)
        
        # Calculate from memory
        total = len(self._closed_positions)
        wins = sum(1 for p in self._closed_positions if p.pnl > 0)
        total_pnl = sum(p.pnl for p in self._closed_positions)
        
        return {
            'total_trades': total,
            'winning_trades': wins,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'total_pnl': total_pnl,
            'realized_pnl': self.realized_pnl
        }
