"""
TRADE.PY - WEBHOOK WRITER
Reads from bridge.txt and writes to webhook_signals.txt
Listens for signals from enginev5.py
"""

import json
import time
import os
from datetime import datetime

BRIDGE_FILE = "bridge.txt"
WEBHOOK_FILE = "webhook_signals.txt"

print("="*70)
print("TRADE.PY - WEBHOOK WRITER ACTIVE")
print("="*70)
print(f"Bridge file: {BRIDGE_FILE}")
print(f"Webhook file: {WEBHOOK_FILE}")
print(f"Waiting for enginev5 signals...")
print("="*70)

last_signal = None
signals_written = 0

while True:
    try:
        # Check if bridge file exists and has content
        if not os.path.exists(BRIDGE_FILE):
            time.sleep(0.1)
            continue
        
        with open(BRIDGE_FILE, "r") as f:
            content = f.read().strip()
        
        # Skip if empty or same as last
        if not content or content == last_signal:
            time.sleep(0.1)
            continue
        
        # New signal received!
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📨 New signal from enginev5")
        
        try:
            signal = json.loads(content)
            
            # Write to webhook
            with open(WEBHOOK_FILE, "w") as f:
                f.write(json.dumps(signal))
            
            signals_written += 1
            
            print(f"✓ Signal #{signals_written} written to {WEBHOOK_FILE}")
            print(f"  Action: {signal.get('action')}")
            print(f"  Symbol: {signal.get('symbol')}")
            print(f"  Qty: {signal.get('qty', 'N/A')}")
            print(f"  Comment: {signal.get('comment', '')}")
            
            # Clear bridge file
            with open(BRIDGE_FILE, "w") as f:
                f.write("")
            
            last_signal = content
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid JSON in bridge file: {e}")
            # Clear it anyway
            with open(BRIDGE_FILE, "w") as f:
                f.write("")
        
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"TRADE.PY STOPPED")
        print(f"{'='*70}")
        print(f"Total signals written: {signals_written}")
        print(f"{'='*70}")
        break
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(1)
