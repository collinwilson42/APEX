"""
Seed 20B: Pre-Flight Fix — Force trading config into DB + diagnose ATH
Run this BEFORE starting the trader.
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apex_instances.db')
INTEL_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'XAUJ26_intelligence.db')

def fix_trading_config():
    """Force test-friendly thresholds directly into the profile."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get current profile for the trader instance
    cur.execute("""
        SELECT p.id, p.name, p.trading_config 
        FROM profiles p
        JOIN algorithm_instances ai ON ai.profile_id = p.id
        WHERE ai.id = 'tr_1770996647772'
    """)
    row = cur.fetchone()
    
    if not row:
        print("ERROR: No profile found for tr_1770996647772")
        return
    
    print(f"Profile: {row['name']} ({row['id']})")
    
    # Parse current config
    tc = json.loads(row['trading_config']) if row['trading_config'] else {}
    old_th = tc.get('thresholds', {})
    old_risk = tc.get('risk', {})
    print(f"  CURRENT thresholds: buy={old_th.get('buy')}, sell={old_th.get('sell')}")
    print(f"  CURRENT risk: lots={old_risk.get('base_lots')}, cooldown={old_risk.get('cooldown_seconds')}")
    
    # Force test-friendly values
    tc['thresholds'] = {
        'buy':       0.05,    # Anything >= +0.05 triggers BUY
        'sell':     -0.05,    # Anything <= -0.05 triggers SELL (your scores hit this)
        'dead_zone': 0.02,
        'gut_veto':  0.01
    }
    tc['risk'] = {
        'base_lots':             1.0,     # 1 lot minimum for this instrument
        'max_lots':              1.0,
        'stop_loss_points':      80,
        'take_profit_points':    200,
        'max_signals_per_hour':  10,      # Allow many signals for testing
        'cooldown_seconds':      30,      # Short cooldown for testing
        'consecutive_loss_halt': 5,
        'sentiment_exit':        True
    }
    
    # Write back
    tc_json = json.dumps(tc)
    cur.execute("UPDATE profiles SET trading_config = ? WHERE id = ?", (tc_json, row['id']))
    conn.commit()
    
    # Verify
    cur.execute("SELECT trading_config FROM profiles WHERE id = ?", (row['id'],))
    verify = json.loads(cur.fetchone()['trading_config'])
    new_th = verify['thresholds']
    new_risk = verify['risk']
    
    print(f"\n  NEW thresholds: buy={new_th['buy']}, sell={new_th['sell']}")
    print(f"  NEW risk: lots={new_risk['base_lots']}, cooldown={new_risk['cooldown_seconds']}s, max={new_risk['max_signals_per_hour']}/hr")
    print(f"\n  ✓ Profile updated in DB — trader will load these on next start")
    
    conn.close()


def diagnose_ath():
    """Check what's in the intelligence DB."""
    print(f"\n{'='*60}")
    print("ATH DIAGNOSIS")
    print(f"{'='*60}")
    
    if not os.path.exists(INTEL_DB):
        print(f"  ERROR: {INTEL_DB} not found!")
        return
    
    print(f"  DB: {INTEL_DB} ({os.path.getsize(INTEL_DB) / 1024 / 1024:.1f} MB)")
    
    conn = sqlite3.connect(INTEL_DB)
    cur = conn.cursor()
    
    # List all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  Tables: {tables}")
    
    # Check ath_tracking
    if 'ath_tracking' in tables:
        cur.execute("SELECT COUNT(*) FROM ath_tracking")
        count = cur.fetchone()[0]
        print(f"\n  ath_tracking: {count} rows")
        if count > 0:
            cur.execute("SELECT * FROM ath_tracking ORDER BY rowid DESC LIMIT 1")
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            print(f"    Latest row columns: {cols}")
            print(f"    Latest values: {list(row)}")
        else:
            print("    EMPTY — ATH will fallback to price_data_15m")
    else:
        print("\n  ath_tracking table: DOES NOT EXIST")
    
    # Check price_data_15m
    if 'price_data_15m' in tables:
        cur.execute("SELECT COUNT(*) FROM price_data_15m")
        count = cur.fetchone()[0]
        print(f"\n  price_data_15m: {count} rows")
        if count > 0:
            cur.execute("PRAGMA table_info(price_data_15m)")
            cols = [r[1] for r in cur.fetchall()]
            print(f"    Columns: {cols}")
            
            # Check if 'high' and 'close' columns exist
            has_high = 'high' in cols
            has_close = 'close' in cols
            print(f"    has 'high': {has_high}, has 'close': {has_close}")
            
            if has_high and has_close:
                cur.execute("SELECT high, close FROM price_data_15m ORDER BY rowid DESC LIMIT 1")
                r = cur.fetchone()
                print(f"    Latest: high={r[0]}, close={r[1]}")
                
                cur.execute("SELECT MAX(high), MIN(close) FROM price_data_15m")
                r = cur.fetchone()
                print(f"    ATH (max high): {r[0]}, Min close: {r[1]}")
            else:
                # Show what columns DO exist
                cur.execute(f"SELECT * FROM price_data_15m ORDER BY rowid DESC LIMIT 1")
                sample_cols = [d[0] for d in cur.description]
                sample_row = cur.fetchone()
                print(f"    Sample cols: {sample_cols}")
                print(f"    Sample row: {list(sample_row)[:10]}...")
        else:
            print("    EMPTY — ATH cannot calculate")
    else:
        print("\n  price_data_15m table: DOES NOT EXIST")
        # Show what tables exist that might have price data
        price_tables = [t for t in tables if 'price' in t.lower() or 'candle' in t.lower() or 'bar' in t.lower() or 'ohlc' in t.lower()]
        print(f"    Price-like tables: {price_tables}")
        if price_tables:
            for t in price_tables[:3]:
                cur.execute(f"PRAGMA table_info({t})")
                cols = [r[1] for r in cur.fetchall()]
                cur.execute(f"SELECT COUNT(*) FROM [{t}]")
                count = cur.fetchone()[0]
                print(f"      {t}: {count} rows, cols={cols[:8]}")
    
    conn.close()


if __name__ == '__main__':
    fix_trading_config()
    diagnose_ath()
    print(f"\n{'='*60}")
    print("NEXT STEPS:")
    print("  1. Restart init2.py")
    print("  2. Start trader — banner should show BUY≥+0.050 SELL≤-0.050")
    print("  3. With scores around -0.116, SELL should trigger")
    print(f"{'='*60}")
