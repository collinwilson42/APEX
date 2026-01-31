"""
MT5 POSITION TRACKER
Gets live position data including current lots, P&L, SL, and TP from MT5
"""

import MetaTrader5 as mt5
from typing import Dict, List, Optional, Any
from datetime import datetime


class MT5PositionTracker:
    """Tracks live MT5 positions"""
    
    def __init__(self, symbol: str = "XAUG26.sim"):
        self.symbol = symbol
        self.connected = False
        
    def connect(self) -> bool:
        """Initialize MT5 connection"""
        if self.connected:
            return True
            
        if not mt5.initialize():
            print(f"✗ MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Verify symbol
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"✗ Symbol {self.symbol} not found")
            mt5.shutdown()
            return False
        
        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                print(f"✗ Failed to select {self.symbol}")
                mt5.shutdown()
                return False
        
        self.connected = True
        return True
    
    def disconnect(self):
        """Shutdown MT5 connection"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all positions for the symbol
        
        Returns:
            List of position dictionaries with:
            - ticket: Position ticket number
            - type: "BUY" or "SELL"
            - volume: Current lot size
            - price_open: Entry price
            - price_current: Current price
            - sl: Stop loss price (0 if not set)
            - tp: Take profit price (0 if not set)
            - profit: Current profit/loss in account currency
            - swap: Swap/rollover charges
            - comment: Position comment
        """
        if not self.connected:
            if not self.connect():
                return []
        
        positions = mt5.positions_get(symbol=self.symbol)
        
        if positions is None or len(positions) == 0:
            return []
        
        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'swap': pos.swap,
                'comment': pos.comment,
                'time': datetime.fromtimestamp(pos.time)
            })
        
        return result
    
    def get_total_position(self) -> Dict[str, Any]:
        """
        Get aggregated position data
        
        Returns:
            Dictionary with:
            - total_volume: Total lots (positive for net long, negative for net short)
            - total_profit: Total P&L including swap
            - num_positions: Number of open positions
            - avg_entry: Volume-weighted average entry price
            - has_sl: True if any position has SL set
            - has_tp: True if any position has TP set
            - sl_prices: List of all SL prices
            - tp_prices: List of all TP prices
        """
        positions = self.get_positions()
        
        if not positions:
            return {
                'total_volume': 0.0,
                'total_profit': 0.0,
                'num_positions': 0,
                'avg_entry': 0.0,
                'has_sl': False,
                'has_tp': False,
                'sl_prices': [],
                'tp_prices': [],
                'net_direction': 'FLAT'
            }
        
        total_long = 0.0
        total_short = 0.0
        total_profit = 0.0
        weighted_entry_sum = 0.0
        total_volume = 0.0
        sl_prices = []
        tp_prices = []
        
        for pos in positions:
            volume = pos['volume']
            
            if pos['type'] == 'BUY':
                total_long += volume
            else:
                total_short += volume
            
            total_profit += (pos['profit'] + pos['swap'])
            weighted_entry_sum += pos['price_open'] * volume
            total_volume += volume
            
            if pos['sl'] > 0:
                sl_prices.append(pos['sl'])
            if pos['tp'] > 0:
                tp_prices.append(pos['tp'])
        
        net_volume = total_long - total_short
        avg_entry = weighted_entry_sum / total_volume if total_volume > 0 else 0.0
        
        # Determine net direction
        if net_volume > 0.1:
            net_direction = 'LONG'
        elif net_volume < -0.1:
            net_direction = 'SHORT'
        else:
            net_direction = 'FLAT'
        
        return {
            'total_volume': round(net_volume, 2),
            'total_profit': round(total_profit, 2),
            'num_positions': len(positions),
            'avg_entry': round(avg_entry, 5),
            'has_sl': len(sl_prices) > 0,
            'has_tp': len(tp_prices) > 0,
            'sl_prices': sl_prices,
            'tp_prices': tp_prices,
            'net_direction': net_direction
        }
    
    def get_current_price(self) -> Optional[float]:
        """Get current market price for symbol"""
        if not self.connected:
            if not self.connect():
                return None
        
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return None
        
        # Return mid price
        return round((tick.bid + tick.ask) / 2, 5)
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account balance and equity"""
        if not self.connected:
            if not self.connect():
                return {}
        
        account = mt5.account_info()
        if account is None:
            return {}
        
        return {
            'balance': account.balance,
            'equity': account.equity,
            'profit': account.profit,
            'margin': account.margin,
            'margin_free': account.margin_free,
            'margin_level': account.margin_level if account.margin > 0 else 0
        }


# Global singleton
_position_tracker = None

def get_position_tracker(symbol: str = "XAUG26.sim") -> MT5PositionTracker:
    """Get or create global position tracker"""
    global _position_tracker
    if _position_tracker is None:
        _position_tracker = MT5PositionTracker(symbol)
    return _position_tracker


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("MT5 POSITION TRACKER TEST")
    print("="*70)
    
    tracker = get_position_tracker()
    
    print("\nConnecting to MT5...")
    if not tracker.connect():
        print("✗ Connection failed")
        exit(1)
    
    print("✓ Connected to MT5")
    
    # Get current price
    print("\n" + "="*70)
    print("CURRENT MARKET DATA")
    print("="*70)
    price = tracker.get_current_price()
    print(f"Current Price: ${price:.2f}")
    
    # Get account info
    print("\n" + "="*70)
    print("ACCOUNT INFO")
    print("="*70)
    account = tracker.get_account_info()
    for key, value in account.items():
        if 'margin' in key.lower() or key in ['balance', 'equity', 'profit']:
            print(f"{key}: ${value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # Get positions
    print("\n" + "="*70)
    print("OPEN POSITIONS")
    print("="*70)
    positions = tracker.get_positions()
    
    if not positions:
        print("No open positions")
    else:
        for i, pos in enumerate(positions, 1):
            print(f"\nPosition #{i}:")
            print(f"  Ticket: {pos['ticket']}")
            print(f"  Type: {pos['type']}")
            print(f"  Volume: {pos['volume']} lots")
            print(f"  Entry: ${pos['price_open']:.2f}")
            print(f"  Current: ${pos['price_current']:.2f}")
            print(f"  SL: ${pos['sl']:.2f}" if pos['sl'] > 0 else "  SL: Not set")
            print(f"  TP: ${pos['tp']:.2f}" if pos['tp'] > 0 else "  TP: Not set")
            print(f"  P&L: ${pos['profit']:.2f}")
            print(f"  Time: {pos['time']}")
    
    # Get total position
    print("\n" + "="*70)
    print("AGGREGATED POSITION")
    print("="*70)
    total = tracker.get_total_position()
    print(f"Net Direction: {total['net_direction']}")
    print(f"Net Volume: {total['total_volume']:+.2f} lots")
    print(f"Number of Positions: {total['num_positions']}")
    print(f"Avg Entry: ${total['avg_entry']:.2f}")
    print(f"Total P&L: ${total['total_profit']:+.2f}")
    print(f"Has SL: {'Yes' if total['has_sl'] else 'No'}")
    print(f"Has TP: {'Yes' if total['has_tp'] else 'No'}")
    if total['sl_prices']:
        print(f"SL Prices: {[f'${x:.2f}' for x in total['sl_prices']]}")
    if total['tp_prices']:
        print(f"TP Prices: {[f'${x:.2f}' for x in total['tp_prices']]}")
    
    print("\n" + "="*70)
    
    tracker.disconnect()
