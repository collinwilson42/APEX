"""
COMPLETE WEBHOOK WRITER - TP/SL + EXECUTION_GATE SUPPORT
Sends full trading signals with 5 TP levels, 5 SL levels, and gate info
"""

import json
from datetime import datetime
from typing import List, Optional
import logging

class WebhookWriter:
    """
    Complete webhook writer with TP/SL arrays and execution_gate
    """
    
    def __init__(self, filepath: str = "webhook_signals.txt"):
        self.filepath = filepath
        self.logger = self._setup_logger()
        self.logger.info(f"✓ WebhookWriter initialized")
        self.logger.info(f"  Webhook file: {self.filepath}")
        self.logger.info(f"  Format: Complete (action, symbol, qty, tp1-5, sl1-5, gate)")
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('WebhookWriter')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def send_signal(
        self,
        action: str,
        symbol: str,
        qty: float,
        tp_levels: Optional[List[float]] = None,
        sl_level: Optional[float] = None,
        comment: str = "",
        gate_zone: Optional[int] = None
    ) -> bool:
        """
        Write complete webhook signal with TP/SL and execution_gate
        
        Args:
            action: BUY, SELL, CLOSE, or SCALE_PARTIAL
            symbol: Trading symbol (e.g., XAUG26.sim)
            qty: Lot size (1.0+ for futures)
            tp_levels: List of 5 take profit levels
            sl_level: Stop loss (will be replicated to sl1-sl5)
            comment: Trade comment
            gate_zone: Execution gate (1-10)
        
        Returns:
            bool: True if signal written successfully
        """
        try:
            # Build complete signal
            signal = {
                "action": action,
                "symbol": symbol,
                "qty": qty,
                "comment": comment
            }
            
            # Add execution_gate
            if gate_zone is not None:
                signal["execution_gate"] = gate_zone
            
            # Add TP levels as individual fields (tp1-tp5)
            if tp_levels and len(tp_levels) >= 5:
                signal["tp1"] = round(tp_levels[0], 2)
                signal["tp2"] = round(tp_levels[1], 2)
                signal["tp3"] = round(tp_levels[2], 2)
                signal["tp4"] = round(tp_levels[3], 2)
                signal["tp5"] = round(tp_levels[4], 2)
            elif tp_levels and len(tp_levels) > 0:
                # If less than 5 TPs, fill remaining with last value
                for i in range(5):
                    tp_val = tp_levels[i] if i < len(tp_levels) else tp_levels[-1]
                    signal[f"tp{i+1}"] = round(tp_val, 2)
            
            # Add SL as individual fields (sl1-sl5)
            if sl_level is not None:
                sl_rounded = round(sl_level, 2)
                signal["sl1"] = sl_rounded
                signal["sl2"] = sl_rounded
                signal["sl3"] = sl_rounded
                signal["sl4"] = sl_rounded
                signal["sl5"] = sl_rounded
            
            # Write as pure ASCII JSON (no encoding issues)
            with open(self.filepath, 'w', encoding='ascii') as f:
                f.write(json.dumps(signal))
            
            # Comprehensive logging
            self.logger.info(f"[SIGNAL SENT] {action} {qty} {symbol} | {comment}")
            
            if gate_zone:
                self.logger.info(f"  Execution Gate: {gate_zone}")
            
            if tp_levels:
                self.logger.info(f"  TPs: {[round(tp, 2) for tp in tp_levels[:5]]}")
            
            if sl_level:
                self.logger.info(f"  SL: {round(sl_level, 2)} (replicated to sl1-sl5)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to write webhook: {e}")
            return False
    
    def send_scale_partial(
        self,
        symbol: str,
        percent: float,
        comment: str = "Adaptive_Scale"
    ) -> bool:
        """
        Send SCALE_PARTIAL signal for position reduction
        
        Args:
            symbol: Trading symbol
            percent: Percentage to close (e.g., 20.0 for 20%)
            comment: Trade comment
        
        Returns:
            bool: True if signal written successfully
        """
        try:
            signal = {
                "action": "SCALE_PARTIAL",
                "symbol": symbol,
                "percent": percent,
                "comment": comment
            }
            
            with open(self.filepath, 'w', encoding='ascii') as f:
                f.write(json.dumps(signal))
            
            self.logger.info(f"[SCALE PARTIAL] {percent}% of {symbol} | {comment}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to write scale partial: {e}")
            return False
    
    def send_close(
        self,
        symbol: str,
        comment: str = "Close_All"
    ) -> bool:
        """
        Send CLOSE signal to close all positions for symbol
        
        Args:
            symbol: Trading symbol
            comment: Trade comment
        
        Returns:
            bool: True if signal written successfully
        """
        try:
            signal = {
                "action": "CLOSE",
                "symbol": symbol,
                "comment": comment
            }
            
            with open(self.filepath, 'w', encoding='ascii') as f:
                f.write(json.dumps(signal))
            
            self.logger.info(f"[CLOSE ALL] {symbol} | {comment}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to write close signal: {e}")
            return False


# Global instance
_webhook_writer = None

def get_webhook_writer() -> WebhookWriter:
    """Get or create webhook writer instance"""
    global _webhook_writer
    if _webhook_writer is None:
        _webhook_writer = WebhookWriter()
    return _webhook_writer


if __name__ == "__main__":
    # Comprehensive test
    print("="*70)
    print("TESTING COMPLETE WEBHOOK WRITER")
    print("="*70)
    
    writer = get_webhook_writer()
    
    # Test 1: BUY with full TP/SL and gate
    print("\n[TEST 1] BUY Signal with TP/SL and Execution Gate")
    print("-"*70)
    success = writer.send_signal(
        action="BUY",
        symbol="XAUG26.sim",
        qty=3.8,
        tp_levels=[4273.4, 4276.25, 4279.09, 4281.93, 4284.77],
        sl_level=4264.88,
        comment="Gate7_Score65",
        gate_zone=7
    )
    
    if success:
        with open(writer.filepath, 'r') as f:
            content = f.read()
        
        print("\nGenerated JSON:")
        signal = json.loads(content)
        print(json.dumps(signal, indent=2))
        
        print("\nField Count:", len(signal))
        print("Has execution_gate:", "execution_gate" in signal)
        print("Has all TPs (1-5):", all(f"tp{i}" in signal for i in range(1, 6)))
        print("Has all SLs (1-5):", all(f"sl{i}" in signal for i in range(1, 6)))
    
    # Test 2: SELL signal
    print("\n[TEST 2] SELL Signal")
    print("-"*70)
    writer.send_signal(
        action="SELL",
        symbol="XAUG26.sim",
        qty=2.5,
        tp_levels=[4260.0, 4257.0, 4254.0, 4251.0, 4248.0],
        sl_level=4270.0,
        comment="Gate5_Score55",
        gate_zone=5
    )
    
    # Test 3: SCALE_PARTIAL
    print("\n[TEST 3] SCALE_PARTIAL Signal")
    print("-"*70)
    writer.send_scale_partial(
        symbol="XAUG26.sim",
        percent=20.0,
        comment="Reduce_Risk"
    )
    
    # Test 4: CLOSE
    print("\n[TEST 4] CLOSE Signal")
    print("-"*70)
    writer.send_close(
        symbol="XAUG26.sim",
        comment="Take_Profit"
    )
    
    print("\n" + "="*70)
    print("✓ ALL TESTS COMPLETE")
    print("="*70)
    print("\nCheck webhook_signals.txt for final output")
    print("This format includes:")
    print("  ✓ action, symbol, qty, comment")
    print("  ✓ execution_gate (gate zone 1-10)")
    print("  ✓ tp1, tp2, tp3, tp4, tp5 (5 take profit levels)")
    print("  ✓ sl1, sl2, sl3, sl4, sl5 (5 stop loss levels)")
    print("\nYour EA can now read ALL of this data!")
    print("="*70)
