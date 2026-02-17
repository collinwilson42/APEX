"""
Quick threshold updater — sets buy/sell thresholds for a profile.
Also prints current state so you can verify.

Usage:
  python update_threshold.py                      # Show all profiles
  python update_threshold.py 0.30                  # Set active XAUJ26 profile to ±0.30
  python update_threshold.py 0.30 6bd1dfe7-824     # Set specific profile
"""

import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "apex_instances.db")


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Show current state
    print("\n" + "=" * 70)
    print("  PROFILE THRESHOLDS")
    print("=" * 70)

    cur = conn.execute("SELECT id, name, symbol, trading_config FROM profiles WHERE status != 'ARCHIVED'")
    profiles = cur.fetchall()

    for p in profiles:
        tc = json.loads(p['trading_config']) if p['trading_config'] else {}
        th = tc.get('thresholds', {})
        print(f"  [{p['id'][:16]}] {p['name']:<30} {p['symbol']:<15} buy={th.get('buy', '?'):>6}  sell={th.get('sell', '?'):>7}")

    # If no args, just show
    if len(sys.argv) < 2:
        print("\nUsage: python update_threshold.py <threshold> [profile_id_prefix]")
        print("Example: python update_threshold.py 0.30")
        conn.close()
        return

    # Parse threshold
    new_threshold = float(sys.argv[1])
    profile_prefix = sys.argv[2] if len(sys.argv) > 2 else None

    # Find target profile
    if profile_prefix:
        targets = [p for p in profiles if p['id'].startswith(profile_prefix)]
    else:
        # Default: find XAUJ26 profiles
        targets = [p for p in profiles if 'XAUJ26' in (p['symbol'] or '').upper()]

    if not targets:
        print(f"\n[ERROR] No matching profile found")
        conn.close()
        return

    # Update each target
    print(f"\n--- UPDATING ---")
    for p in targets:
        tc = json.loads(p['trading_config']) if p['trading_config'] else {}

        if 'thresholds' not in tc:
            tc['thresholds'] = {}

        old_buy = tc['thresholds'].get('buy', '?')
        old_sell = tc['thresholds'].get('sell', '?')

        tc['thresholds']['buy'] = new_threshold
        tc['thresholds']['sell'] = -new_threshold

        new_json = json.dumps(tc)
        conn.execute("UPDATE profiles SET trading_config = ?, sentiment_threshold = ? WHERE id = ?",
                      (new_json, new_threshold, p['id']))

        print(f"  [{p['id'][:16]}] {p['name']}")
        print(f"    buy:  {old_buy} -> {new_threshold}")
        print(f"    sell: {old_sell} -> {-new_threshold}")

    conn.commit()
    conn.close()

    print(f"\nDone. {len(targets)} profile(s) updated.")
    print(f"Restart the trader for the change to take effect.")
    print(f"(Hot-reload should also pick it up on next tick)")


if __name__ == "__main__":
    main()
