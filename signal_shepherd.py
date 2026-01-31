"""
TUNITY SIGNAL SHEPHERD v1.0
Bulletproof background service for MT5 webhook signal delivery

TUNITY: T(1.0) × O(1.0) × C(1.0) × Cr(0.8) = 0.80
"""

import json
import time
import os
from datetime import datetime
from pathlib import Path
import hashlib
import logging
from typing import Dict, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
BRIDGE_FILE = "bridge.txt"
WEBHOOK_FILE = "webhook_signals.txt"
LOG_FILE = "shepherd.log"
HEALTH_FILE = "shepherd_health.txt"

# Settings
CHECK_INTERVAL_MS = 100  # Check every 100ms
HEALTH_UPDATE_SEC = 5    # Update health every 5s
MAX_SIGNAL_AGE_SEC = 30  # Reject signals older than 30s

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('SignalShepherd')

# ============================================================================
# SIGNAL SHEPHERD CLASS
# ============================================================================

class SignalShepherd:
    """
    Bulletproof signal delivery service
    
    Responsibilities:
    - Monitor bridge.txt for incoming signals
    - Validate signal format and timestamp
    - Write to webhook_signals.txt in ASCII (for EA)
    - Track health and statistics
    - Auto-recover from errors
    """
    
    def __init__(self):
        self.signals_processed = 0
        self.signals_failed = 0
        self.last_signal_id = None
        self.last_signal_time = None
        self.start_time = datetime.now()
        self.last_health_update = datetime.now()
        
        logger.info("="*70)
        logger.info("TUNITY SIGNAL SHEPHERD v1.0 - STARTING")
        logger.info("="*70)
        logger.info(f"Bridge file: {BRIDGE_FILE}")
        logger.info(f"Webhook file: {WEBHOOK_FILE}")
        logger.info(f"Check interval: {CHECK_INTERVAL_MS}ms")
        logger.info("="*70)
        
        self.update_health()
    
    def generate_signal_id(self, signal: Dict) -> str:
        """Generate unique ID for signal deduplication"""
        content = f"{signal.get('action')}_{signal.get('symbol')}_{signal.get('qty')}_{signal.get('timestamp')}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def validate_signal(self, signal: Dict) -> tuple[bool, str]:
        """
        Validate signal structure and content
        
        Returns: (is_valid, error_message)
        """
        # Check required fields
        required = ['timestamp', 'action', 'symbol', 'qty']
        for field in required:
            if field not in signal:
                return False, f"Missing required field: {field}"
        
        # Validate action
        valid_actions = ['BUY', 'SELL', 'CLOSE']
        if signal['action'] not in valid_actions:
            return False, f"Invalid action: {signal['action']}"
        
        # Validate qty
        try:
            qty = float(signal['qty'])
            if qty <= 0:
                return False, f"Invalid qty: {qty}"
        except:
            return False, f"Qty is not a number: {signal['qty']}"
        
        # Validate timestamp age
        try:
            # Parse timestamp (ISO format)
            if isinstance(signal['timestamp'], str):
                signal_time = datetime.fromisoformat(signal['timestamp'].replace('T', ' '))
            else:
                # Unix timestamp
                signal_time = datetime.fromtimestamp(signal['timestamp'])
            
            age_sec = (datetime.now() - signal_time).total_seconds()
            
            if age_sec > MAX_SIGNAL_AGE_SEC:
                return False, f"Signal too old: {age_sec:.1f}s"
            
            if age_sec < -5:  # Signal from future (clock skew)
                return False, f"Signal from future: {age_sec:.1f}s"
                
        except Exception as e:
            return False, f"Invalid timestamp: {e}"
        
        return True, ""
    
    def write_to_webhook(self, signal: Dict) -> bool:
        """
        Write signal to webhook file in pure ASCII
        
        This is what the EA reads
        """
        try:
            # Convert to JSON string
            json_str = json.dumps(signal, separators=(',', ':'))
            
            # Write in pure ASCII (no UTF-16, no BOM)
            with open(WEBHOOK_FILE, 'w', encoding='ascii') as f:
                f.write(json_str)
            
            logger.info(f"[OK] Webhook written: {json_str}")
            return True
            
        except Exception as e:
            logger.error(f"[FAIL] Webhook write failed: {e}")
            return False
    
    def process_signal(self, json_content: str) -> bool:
        """
        Process incoming signal from bridge
        
        Returns: True if processed successfully
        """
        try:
            # Parse JSON
            signal = json.loads(json_content)
            
            logger.info(f"\n{'='*70}")
            logger.info(f"NEW SIGNAL RECEIVED")
            logger.info(f"{'='*70}")
            logger.info(f"Raw: {json_content}")
            
            # Generate ID for deduplication
            signal_id = self.generate_signal_id(signal)
            
            # Check for duplicate
            if signal_id == self.last_signal_id:
                logger.warning(f"[WARN]  DUPLICATE signal (ID: {signal_id}), skipping")
                return False
            
            # Validate signal
            is_valid, error_msg = self.validate_signal(signal)
            
            if not is_valid:
                logger.error(f"[FAIL] VALIDATION FAILED: {error_msg}")
                self.signals_failed += 1
                return False
            
            logger.info(f"[OK] Validation passed")
            logger.info(f"  Action: {signal['action']}")
            logger.info(f"  Symbol: {signal['symbol']}")
            logger.info(f"  Qty: {signal['qty']}")
            logger.info(f"  Timestamp: {signal['timestamp']}")
            logger.info(f"  Signal ID: {signal_id}")
            
            # Write to webhook
            if self.write_to_webhook(signal):
                self.signals_processed += 1
                self.last_signal_id = signal_id
                self.last_signal_time = datetime.now()
                
                logger.info(f"[OK] SIGNAL #{self.signals_processed} DELIVERED TO MT5")
                logger.info(f"{'='*70}\n")
                return True
            else:
                self.signals_failed += 1
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"[FAIL] JSON parse error: {e}")
            self.signals_failed += 1
            return False
            
        except Exception as e:
            logger.error(f"[FAIL] Process error: {e}")
            import traceback
            traceback.print_exc()
            self.signals_failed += 1
            return False
    
    def update_health(self):
        """Write health status to file"""
        try:
            uptime_sec = (datetime.now() - self.start_time).total_seconds()
            
            health = {
                "status": "RUNNING",
                "uptime_seconds": int(uptime_sec),
                "signals_processed": self.signals_processed,
                "signals_failed": self.signals_failed,
                "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time else None,
                "last_update": datetime.now().isoformat()
            }
            
            with open(HEALTH_FILE, 'w') as f:
                f.write(json.dumps(health, indent=2))
                
        except Exception as e:
            logger.error(f"Health update failed: {e}")
    
    def run(self):
        """Main run loop"""
        last_content = None
        
        logger.info("[OK] Shepherd is now listening for signals...\n")
        
        try:
            while True:
                # Health check
                if (datetime.now() - self.last_health_update).total_seconds() >= HEALTH_UPDATE_SEC:
                    self.update_health()
                    self.last_health_update = datetime.now()
                
                # Check for bridge file
                if not os.path.exists(BRIDGE_FILE):
                    time.sleep(CHECK_INTERVAL_MS / 1000.0)
                    continue
                
                # Read bridge file
                try:
                    with open(BRIDGE_FILE, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                except Exception as e:
                    logger.error(f"Error reading bridge: {e}")
                    time.sleep(CHECK_INTERVAL_MS / 1000.0)
                    continue
                
                # Skip if empty or same as last
                if not content or content == last_content:
                    time.sleep(CHECK_INTERVAL_MS / 1000.0)
                    continue
                
                # New signal detected!
                if self.process_signal(content):
                    # Clear bridge file after successful processing
                    try:
                        with open(BRIDGE_FILE, 'w') as f:
                            f.write("")
                    except:
                        pass
                
                last_content = content
                time.sleep(CHECK_INTERVAL_MS / 1000.0)
                
        except KeyboardInterrupt:
            logger.info("\n" + "="*70)
            logger.info("SHEPHERD STOPPED BY USER")
            logger.info("="*70)
            logger.info(f"Total signals processed: {self.signals_processed}")
            logger.info(f"Total signals failed: {self.signals_failed}")
            logger.info(f"Uptime: {(datetime.now() - self.start_time).total_seconds():.0f}s")
            logger.info("="*70)
            
        except Exception as e:
            logger.error(f"FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    shepherd = SignalShepherd()
    shepherd.run()
