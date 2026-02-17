"""Quick fix: find instance table name and get MT5 point sizes"""
import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "apex_instances.db")

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except:
    HAS_MT5 = False

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Find the right table name
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("ALL TABLES:")
for t in tables:
    print(f"  {t['name']}")

# Try common names
for tbl in ['instances', 'algorithm_instances', 'algo_instances']:
    try:
        rows = conn.execute(f"SELECT * FROM {tbl} WHERE status='ACTIVE'").fetchall()
        print(f"\nACTIVE INSTANCES (from {tbl}):")
        for r in rows:
            cols = r.keys()
            print(f"\n  {r['display_name'] if 'display_name' in cols else 'unknown'}")
            print(f"  ID:      {r['id'][:24]}...")
            if 'symbol' in cols: print(f"  Symbol:  {r['symbol']}")
            if 'account_type' in cols: print(f"  Type:    {r['account_type']}")
            if 'profile_id' in cols: 
                pid = r['profile_id']
                print(f"  Profile: {pid[:16] + '...' if pid else 'NONE ← NOT LINKED!'}")
        break
    except:
        continue

conn.close()

# MT5 Point Sizes
if HAS_MT5:
    print(f"\n{'='*70}")
    print("MT5 SYMBOL POINT SIZES (LIVE ACCOUNT)")
    print("="*70)
    
    if not mt5.initialize():
        print(f"  MT5 init failed: {mt5.last_error()}")
    else:
        # Get all visible symbols that match our targets
        for sym in ["XAUUSD", "XAUUSD.sim", "USOIL", "USOIL.sim", "US500", "US500.sim", 
                     "US100", "US100.sim", "US30", "US30.sim", "BTCUSD", "BTCUSD.sim"]:
            info = mt5.symbol_info(sym)
            if info:
                tick = mt5.symbol_info_tick(sym)
                bid = tick.bid if tick else 0
                print(f"\n  {sym}:")
                print(f"    point={info.point}  digits={info.digits}  bid={bid}")
                print(f"    tick_value=${info.trade_tick_value:.4f}/lot/tick  contract={info.trade_contract_size}")
                if bid > 0:
                    # Show what 80pts and 200pts means in $ movement
                    sl_dist = 80 * info.point
                    tp_dist = 200 * info.point
                    print(f"    80 pts  = ${sl_dist:.5f} price move  (SL at {bid - sl_dist:.5f})")
                    print(f"    200 pts = ${tp_dist:.5f} price move  (TP at {bid + tp_dist:.5f})")
                    # Dollar risk per lot
                    dollar_per_point = info.trade_tick_value / info.trade_tick_size * info.point if info.trade_tick_size > 0 else 0
                    print(f"    $ risk per lot: SL(80pts)=${80 * dollar_per_point:.2f}  TP(200pts)=${200 * dollar_per_point:.2f}")
                    print(f"    $ risk 0.10 lots: SL=${80 * dollar_per_point * 0.10:.2f}  TP=${200 * dollar_per_point * 0.10:.2f}")
        
        mt5.shutdown()
