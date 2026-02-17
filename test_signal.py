"""
Direct signal write test — no prompts, just writes and verifies.
"""
import os, json, time

SIGNAL_PATH = os.path.join(
    os.path.expanduser("~"),
    "AppData", "Roaming", "MetaQuotes", "Terminal", "Common", "Files",
    "webhook_signals.txt"
)

# Ensure directory exists
sig_dir = os.path.dirname(SIGNAL_PATH)
os.makedirs(sig_dir, exist_ok=True)

# The JSON the EA expects
signal = {
    "action": "BUY",
    "symbol": "XAUJ26.sim",
    "qty": 1.0,
    "comment": "TORRA_TEST_DIRECT"
}

print(f"Path: {SIGNAL_PATH}")
print(f"Dir exists: {os.path.isdir(sig_dir)}")
print(f"JSON: {json.dumps(signal)}")

# Write it
with open(SIGNAL_PATH, 'w', encoding='ascii', errors='replace', newline='\n') as f:
    f.write(json.dumps(signal))

# Verify
with open(SIGNAL_PATH, 'r') as f:
    written = f.read()
print(f"Written: {written}")
print(f"File size: {os.path.getsize(SIGNAL_PATH)} bytes")

# Wait for EA
print("Waiting 5 seconds for EA to process...")
time.sleep(5)

with open(SIGNAL_PATH, 'r') as f:
    after = f.read().strip()

if after == "PROCESSED":
    print("EA PROCESSED IT - check MT5 for the trade")
elif after == written.strip():
    print("FILE UNCHANGED - EA did not read it")
    print("Check: is EA attached? Is EnableWebhook=true?")
else:
    print(f"File now contains: [{after}]")
