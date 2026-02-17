"""
ONE-TIME FIX: Update all profile thresholds and timeframe weights.
Fixes the "always HOLD" bug where thresholds (0.55) were unreachable
given the system's actual composite score range (~0.30-0.47).

Run once: python fix_thresholds.py
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apex_instances.db")

CORRECT_THRESHOLDS = {"buy": 0.30, "sell": -0.30, "dead_zone": 0.10, "gut_veto": 0.20}
CORRECT_TF_WEIGHTS = {"15m": 0.60, "1h": 0.40}

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, symbol, trading_config FROM profiles")
    rows = cursor.fetchall()
    
    fixed = 0
    for row in rows:
        tc_raw = row["trading_config"]
        if not tc_raw:
            continue
        
        try:
            tc = json.loads(tc_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        
        # Always update thresholds and TF weights to calibrated values
        tc["thresholds"] = CORRECT_THRESHOLDS
        tc["timeframe_weights"] = CORRECT_TF_WEIGHTS
        
        cursor.execute(
            "UPDATE profiles SET trading_config = ?, sentiment_threshold = 0.30 WHERE id = ?",
            (json.dumps(tc), row["id"])
        )
        fixed += 1
        print(f"  ✓ {row['name']} ({row['symbol']}) -> buy=0.30 sell=-0.30 15m=0.60 1h=0.40")
    
    conn.commit()
    
    # Verify
    print(f"\n{'='*60}")
    print(f"Fixed {fixed} profiles. Verification:")
    print(f"{'='*60}")
    
    cursor.execute("SELECT name, symbol, trading_config FROM profiles")
    for row in cursor.fetchall():
        parsed = json.loads(row["trading_config"])
        th = parsed.get("thresholds", {})
        tw = parsed.get("timeframe_weights", {})
        print(f"  {row['name']:35s} buy={th.get('buy'):+.2f} sell={th.get('sell'):+.2f} | 15m={tw.get('15m')} 1h={tw.get('1h')}")
    
    conn.close()
    print(f"\nDone. Restart init2.py to pick up the changes.")

if __name__ == "__main__":
    main()
