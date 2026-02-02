"""
LIVE BROKER - MT5 Implementation
================================
Wraps the existing trade.py MT5 logic into the IBroker interface.
Real money execution - same interface as VirtualBroker.

Seed 14B - The Virtual Broker Implementation
"""

from typing import Optional, List, Dict
from datetime import datetime
import threading

from .base_broker import IBroker, BrokerMode, Position, OrderResult

# Conditional MT5 import (not available on all systems)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class LiveBroker(IBroker):
    """
    Live MT5 Trading Broker
    -----------------------
    Executes real trades through MetaTrader 5.
    Implements the same IBroker interface as VirtualBroker.
    
    Note: Requires MT5 terminal running and connected.
    
    Usage:
        broker = LiveBroker("instance_001")
        if broker.connect():
            result = broker.buy("XAUUSD", 0.1, sl=2840, tp=2870)
    """
    
    def __init__(self, instance_id: str):
        super().__init__(instance_id, BrokerMode.LIVE)
        
        self._connected = False
        self._lock = threading.Lock()
        self._prices: Dict[str, dict] = {}  # Price cache
        
        # Auto-connect on init if MT5 available
        if MT5_AVAILABLE:
            self._connected = self._init_mt5()
    
    def _init_mt5(self) -> bool:
        """Initialize MT5 connection"""
        if not MT5_AVAILABLE:
            return False
        
        if not mt5.initialize():
            print(f"[LiveBroker] MT5 initialize failed: {mt5.last_error()}")
            return False
        
        return True
    
    def connect(self) -> bool:
        """Ensure MT5 connection is active"""
        if not MT5_AVAILABLE:
            print("[LiveBroker] MT5 not installed")
            return False
        
        if not self._connected:
            self._connected = self._init_mt5()
        
        return self._connected
    
    def disconnect(self) -> None:
        """Shutdown MT5 connection"""
        if MT5_AVAILABLE and self._connected:
            mt5.shutdown()
            self._connected = False
    
    def on_tick(self, symbol: str, bid: float, ask: float) -> None:
        """Update price cache (for consistency with VirtualBroker)"""
        with self._lock:
            self._prices[symbol] = {'bid': bid, 'ask': ask}
    
    def buy(self, symbol: str, volume: float,
            sl: Optional[float] = None,
            tp: Optional[float] = None,
            comment: str = "") -> OrderResult:
        """Execute BUY order on MT5"""
        if not self._connected:
            return OrderResult(success=False, message="MT5 not connected")
        
        with self._lock:
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return OrderResult(success=False, message=f"Symbol {symbol} not found")
            
            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)
            
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return OrderResult(success=False, message=f"No tick data for {symbol}")
            
            price = tick.ask
            
            # Build order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": 20,
                "magic": hash(self.instance_id) % 1000000,
                "comment": comment or f"APEX_{self.instance_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            if sl:
                request["sl"] = sl
            if tp:
                request["tp"] = tp
            
            # Execute
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    message=f"Order failed: {result.retcode} - {result.comment}"
                )
            
            return OrderResult(
                success=True,
                ticket=result.order,
                price=result.price,
                message=f"BUY {volume} {symbol} @ {result.price}"
            )
    
    def sell(self, symbol: str, volume: float,
             sl: Optional[float] = None,
             tp: Optional[float] = None,
             comment: str = "") -> OrderResult:
        """Execute SELL order on MT5"""
        if not self._connected:
            return OrderResult(success=False, message="MT5 not connected")
        
        with self._lock:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return OrderResult(success=False, message=f"Symbol {symbol} not found")
            
            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return OrderResult(success=False, message=f"No tick data for {symbol}")
            
            price = tick.bid
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "deviation": 20,
                "magic": hash(self.instance_id) % 1000000,
                "comment": comment or f"APEX_{self.instance_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            if sl:
                request["sl"] = sl
            if tp:
                request["tp"] = tp
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    message=f"Order failed: {result.retcode} - {result.comment}"
                )
            
            return OrderResult(
                success=True,
                ticket=result.order,
                price=result.price,
                message=f"SELL {volume} {symbol} @ {result.price}"
            )
    
    def close(self, ticket: int) -> OrderResult:
        """Close position by ticket"""
        if not self._connected:
            return OrderResult(success=False, message="MT5 not connected")
        
        with self._lock:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return OrderResult(success=False, message=f"Position {ticket} not found")
            
            pos = position[0]
            symbol = pos.symbol
            volume = pos.volume
            pos_type = pos.type
            
            # Opposite order to close
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return OrderResult(success=False, message=f"No tick data for {symbol}")
            
            if pos_type == mt5.POSITION_TYPE_BUY:
                price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": hash(self.instance_id) % 1000000,
                "comment": f"CLOSE_{self.instance_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    message=f"Close failed: {result.retcode} - {result.comment}"
                )
            
            return OrderResult(
                success=True,
                ticket=ticket,
                price=result.price,
                message=f"Closed position {ticket} @ {result.price}"
            )
    
    def close_all(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """Close all positions"""
        if not self._connected:
            return [OrderResult(success=False, message="MT5 not connected")]
        
        with self._lock:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if not positions:
                return []
            
            results = []
            for pos in positions:
                # Release lock temporarily for each close
                self._lock.release()
                try:
                    result = self.close(pos.ticket)
                    results.append(result)
                finally:
                    self._lock.acquire()
            
            return results
    
    def modify(self, ticket: int,
               sl: Optional[float] = None,
               tp: Optional[float] = None) -> OrderResult:
        """Modify position SL/TP"""
        if not self._connected:
            return OrderResult(success=False, message="MT5 not connected")
        
        with self._lock:
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return OrderResult(success=False, message=f"Position {ticket} not found")
            
            pos = position[0]
            
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": pos.symbol,
                "position": ticket,
                "sl": sl if sl is not None else pos.sl,
                "tp": tp if tp is not None else pos.tp,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    message=f"Modify failed: {result.retcode} - {result.comment}"
                )
            
            return OrderResult(
                success=True,
                ticket=ticket,
                message=f"Modified {ticket}: SL={sl}, TP={tp}"
            )
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get all open positions from MT5"""
        if not self._connected:
            return []
        
        with self._lock:
            if symbol:
                mt5_positions = mt5.positions_get(symbol=symbol)
            else:
                mt5_positions = mt5.positions_get()
            
            if not mt5_positions:
                return []
            
            positions = []
            for p in mt5_positions:
                positions.append(Position(
                    ticket=p.ticket,
                    symbol=p.symbol,
                    direction="BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                    volume=p.volume,
                    open_price=p.price_open,
                    open_time=datetime.fromtimestamp(p.time),
                    sl=p.sl if p.sl > 0 else None,
                    tp=p.tp if p.tp > 0 else None,
                    current_price=p.price_current,
                    pnl=p.profit,
                    comment=p.comment
                ))
            
            return positions
    
    def get_position(self, ticket: int) -> Optional[Position]:
        """Get specific position"""
        if not self._connected:
            return None
        
        with self._lock:
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return None
            
            p = position[0]
            return Position(
                ticket=p.ticket,
                symbol=p.symbol,
                direction="BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                volume=p.volume,
                open_price=p.price_open,
                open_time=datetime.fromtimestamp(p.time),
                sl=p.sl if p.sl > 0 else None,
                tp=p.tp if p.tp > 0 else None,
                current_price=p.price_current,
                pnl=p.profit,
                comment=p.comment
            )
    
    def get_pnl(self) -> float:
        """Get total unrealized PnL"""
        positions = self.get_positions()
        return sum(p.pnl for p in positions)
    
    def get_state(self) -> dict:
        """Get broker state for API"""
        positions = self.get_positions()
        
        # Get account info
        account_info = {}
        if self._connected:
            info = mt5.account_info()
            if info:
                account_info = {
                    'balance': info.balance,
                    'equity': info.equity,
                    'margin': info.margin,
                    'free_margin': info.margin_free,
                }
        
        return {
            'instance_id': self.instance_id,
            'mode': self.mode.value,
            'connected': self._connected,
            'account': account_info,
            'unrealized_pnl': self.get_pnl(),
            'position_count': len(positions),
            'positions': [
                {
                    'ticket': p.ticket,
                    'symbol': p.symbol,
                    'direction': p.direction,
                    'volume': p.volume,
                    'open_price': p.open_price,
                    'current_price': p.current_price,
                    'pnl': p.pnl,
                    'sl': p.sl,
                    'tp': p.tp,
                    'comment': p.comment
                }
                for p in positions
            ],
            'prices': dict(self._prices)
        }
