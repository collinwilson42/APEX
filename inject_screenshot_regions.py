"""
Seed 24: Inject screenshot_regions into existing profile trading_config.
Run once to update the DB profile with per-timeframe mss capture regions.

Usage: python inject_screenshot_regions.py
"""

import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "apex_instances.db")

# Seed 24: Default regions for 3840x2140 native resolution
SCREENSHOT_REGIONS = {
    "_note": "mss capture regions in NATIVE screen pixels (3840x2140)",
    "15m": {
        "_description": "TACTICAL panel — top chart + transition matrix",
        "left": 1040,
        "top": 200,
        "width": 1840,
        "height": 520
    },
    "1h": {
        "_description": "TREND panel — middle chart + transition matrix",
        "left": 1040,
        "top": 710,
        "width": 1840,
        "height": 500
    }
}


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all profiles
    cursor.execute("SELECT id, name, trading_config FROM profiles")
    profiles = cursor.fetchall()

    if not profiles:
        print("[WARN] No profiles found in database")
        conn.close()
        return

    updated = 0
    for p in profiles:
        pid = p['id']
        name = p['name']
        tc_raw = p['trading_config']

        if not tc_raw:
            print(f"  [{pid}] {name} — no trading_config, skipping")
            continue

        try:
            tc = json.loads(tc_raw) if isinstance(tc_raw, str) else tc_raw
        except (json.JSONDecodeError, TypeError):
            print(f"  [{pid}] {name} — invalid trading_config JSON, skipping")
            continue

        if 'screenshot_regions' in tc:
            print(f"  [{pid}] {name} — already has screenshot_regions, skipping")
            continue

        # Inject screenshot_regions
        tc['screenshot_regions'] = SCREENSHOT_REGIONS
        new_tc_json = json.dumps(tc)

        cursor.execute("UPDATE profiles SET trading_config = ? WHERE id = ?",
                       (new_tc_json, pid))
        print(f"  [{pid}] {name} — INJECTED screenshot_regions")
        updated += 1

    conn.commit()
    conn.close()

    print(f"\nDone. Updated {updated} profile(s).")
    print(f"  15m region: left=1040, top=200, 1840x520")
    print(f"  1h  region: left=1040, top=710, 1840x500")
    print(f"\nThese coordinates are estimates for 3840x2140 native resolution.")
    print(f"Fine-tune in Profile Manager if charts aren't captured correctly.")


if __name__ == "__main__":
    main()
