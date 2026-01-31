"""
SIGNAL BRIDGE - V4 ENGINE TO WEBHOOK WRITER
v4_engine writes to bridge.txt → webhook_writer reads bridge.txt → writes to webhook_signals.txt
"""

import json
import time
import os
from datetime import datetime

BRIDGE_FILE = "bridge.txt"
WEBHOOK_FILE = "webhook_signals.txt"
CHECK_INTERVAL = 0.1  # Check every 100ms

print("="*70)
print("SIGNAL BRIDGE - LISTENING FOR COMMANDS")
print("="*70)
print(f"Bridge file: {BRIDGE_FILE}")
print(f"Webhook file: {WEBHOOK_FILE}")
print(f"Waiting for v4_engine to write commands...")
print("="*70)

last_content = None
signals_written = 0

while True:
    try:
        # Check if bridge file exists
        if not os.path.exists(BRIDGE_FILE):
            time.sleep(CHECK_INTERVAL)
            continue
        
        # Read bridge file
        with open(BRIDGE_FILE, 'r') as f:
            content = f.read().strip()
        
        # Skip if empty or already processed
        if not content or content == last_content:
            time.sleep(CHECK_INTERVAL)
            continue
        
        # New command received!
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Bridge command received: {content[:100]}")
        
        # Parse and write to webhook
        try:
            signal = json.loads(content)
            
            # Write to webhook file
            with open(WEBHOOK_FILE, 'w') as f:
                f.write(json.dumps(signal))
            
            signals_written += 1
            print(f"✓ Signal #{signals_written} written to webhook")
            print(f"  Action: {signal.get('action')}")
            print(f"  Symbol: {signal.get('symbol')}")
            print(f"  Qty: {signal.get('qty', 'N/A')}")
            print(f"  Comment: {signal.get('comment', '')}")
            
            # Clear bridge file
            with open(BRIDGE_FILE, 'w') as f:
                f.write("")
            
            last_content = content
            
        except json.JSONDecodeError:
            print(f"⚠️  Invalid JSON in bridge file, skipping")
            with open(BRIDGE_FILE, 'w') as f:
                f.write("")
        
        time.sleep(CHECK_INTERVAL)
        
    except KeyboardInterrupt:
        print(f"\n\n✓ Bridge stopped. Total signals written: {signals_written}")
        break
    except Exception as e:
        print(f"✗ Error: {e}")
        time.sleep(1)
