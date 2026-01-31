"""
SIMPLE WEBHOOK SIGNAL WRITER - NO BULLSHIT
Just writes the damn signal to the file
"""

import json
import os
import glob
from datetime import datetime
import time
import anthropic

# ============================================================================
# SIMPLE CONFIG
# ============================================================================

API_KEY = "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"
SYMBOL = "XAUG26.sim"
SCREENSHOT_FOLDER = r"C:\Users\cwils\OneDrive\Desktop\Adaptive MT5 Meta Agent\V11\screenshots"
WEBHOOK_FILE = "webhook_signals.txt"
CHECK_INTERVAL_SEC = 60  # How often to check for new signals

# ============================================================================
# SIMPLE FUNCTIONS
# ============================================================================

def get_newest_screenshot():
    """Get the newest screenshot file"""
    screenshots = glob.glob(os.path.join(SCREENSHOT_FOLDER, "*.png"))
    if not screenshots:
        return None
    return max(screenshots, key=os.path.getmtime)

def write_signal(action, symbol, qty=1.0, comment=""):
    """Write signal to webhook file"""
    signal = {
        "action": action,
        "symbol": symbol,
        "qty": qty,
        "comment": comment
    }
    
    with open(WEBHOOK_FILE, 'w') as f:
        f.write(json.dumps(signal))
    
    print(f"✓ SIGNAL WRITTEN: {action} {qty} {symbol}")
    return True

def ask_claude_for_decision(screenshot_path):
    """Ask Claude what to do"""
    try:
        client = anthropic.Anthropic(api_key=API_KEY)
        
        # Read screenshot
        with open(screenshot_path, 'rb') as f:
            import base64
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Simple prompt
        prompt = """Look at this gold futures chart.

Should I:
- BUY (go long)
- SELL (go short)  
- CLOSE (close all positions)
- HOLD (do nothing)

Respond with ONLY ONE WORD: BUY, SELL, CLOSE, or HOLD"""

        # Call API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_data
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        
        # Parse response
        response = message.content[0].text.strip().upper()
        
        print(f"Claude says: {response}")
        return response
        
    except Exception as e:
        print(f"API error: {e}")
        return "HOLD"

# ============================================================================
# MAIN LOOP
# ============================================================================

def main():
    print("="*70)
    print("SIMPLE SIGNAL WRITER - RUNNING")
    print("="*70)
    print(f"Symbol: {SYMBOL}")
    print(f"Screenshot folder: {SCREENSHOT_FOLDER}")
    print(f"Webhook file: {WEBHOOK_FILE}")
    print(f"Check interval: {CHECK_INTERVAL_SEC}s")
    print("="*70)
    
    iteration = 0
    
    while True:
        iteration += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Check #{iteration}")
        
        # Get newest screenshot
        screenshot = get_newest_screenshot()
        
        if not screenshot:
            print("⚠️  No screenshots found")
            time.sleep(CHECK_INTERVAL_SEC)
            continue
        
        age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(screenshot))).total_seconds()
        print(f"📸 Screenshot: {os.path.basename(screenshot)} ({age:.0f}s old)")
        
        # Ask Claude
        decision = ask_claude_for_decision(screenshot)
        
        # Write signal
        if decision == "BUY":
            write_signal("BUY", SYMBOL, 1.0, f"Simple_BUY_{iteration}")
        elif decision == "SELL":
            write_signal("SELL", SYMBOL, 1.0, f"Simple_SELL_{iteration}")
        elif decision == "CLOSE":
            write_signal("CLOSE", SYMBOL, 0.0, f"Simple_CLOSE_{iteration}")
        else:
            print("✓ HOLD - No signal written")
        
        # Wait
        print(f"Waiting {CHECK_INTERVAL_SEC}s...")
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped.")
