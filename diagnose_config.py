"""Quick diagnostic: check profiles, instances, and point sizes"""
import sqlite3
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "apex_instances.db")

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except:
    HAS_MT5 = False

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # ── Profiles ──
    print("=" * 70)
    print("PROFILES IN DATABASE")
    print("=" * 70)
    
    profiles = conn.execute("SELECT * FROM profiles").fetchall()
    if not profiles:
        print("  NO PROFILES FOUND — using dataclass defaults!")
    
    for p in profiles:
        print(f"\n  Profile: {p['name']} ({p['id'][:16]}...)")
        print(f"  Symbol:  {p['symbol']}")
        print(f"  Status:  {p['status']}")
        print(f"  Model:   {p['sentiment_model']}")
        
        # Check trading_config (source of truth for torra_trader)
        tc = p['trading_config']
        if tc:
            try:
                tc_parsed = json.loads(tc)
                risk = tc_parsed.get('risk', {})
                thresholds = tc_parsed.get('thresholds', {})
                sw = tc_parsed.get('sentiment_weights', {})
                tw = tc_parsed.get('timeframe_weights', {})
                
                print(f"  trading_config: YES")
                print(f"    risk.stop_loss_points:   {risk.get('stop_loss_points', 'NOT SET')}")
                print(f"    risk.take_profit_points: {risk.get('take_profit_points', 'NOT SET')}")
                print(f"    risk.base_lots:          {risk.get('base_lots', 'NOT SET')}")
                print(f"    risk.cooldown_seconds:   {risk.get('cooldown_seconds', 'NOT SET')}")
                print(f"    risk.max_signals_per_hr: {risk.get('max_signals_per_hour', 'NOT SET')}")
                print(f"    thresholds.buy:          {thresholds.get('buy', 'NOT SET')}")
                print(f"    thresholds.sell:         {thresholds.get('sell', 'NOT SET')}")
                print(f"    sentiment_weights:       {json.dumps(sw)}")
                print(f"    timeframe_weights:       {json.dumps(tw)}")
            except:
                print(f"  trading_config: INVALID JSON")
        else:
            print(f"  trading_config: NULL — torra_trader will fail validate_config()")
        
        # Legacy fields
        rc = p['risk_config']
        if rc:
            try:
                rc_parsed = json.loads(rc)
                print(f"  legacy risk_config:        {json.dumps(rc_parsed)}")
            except:
                pass
    
    # ── Instances ──
    print(f"\n{'=' * 70}")
    print("INSTANCES IN DATABASE")
    print("=" * 70)
    
    instances = conn.execute("SELECT * FROM instances WHERE status='ACTIVE'").fetchall()
    if not instances:
        print("  NO ACTIVE INSTANCES")
    
    for inst in instances:
        print(f"\n  Instance: {inst['display_name']}")
        print(f"  ID:       {inst['id'][:24]}...")
        print(f"  Symbol:   {inst['symbol']}")
        print(f"  Type:     {inst['account_type']}")
        print(f"  Profile:  {inst['profile_id'][:16] + '...' if inst['profile_id'] else 'NONE ← NOT LINKED!'}")
    
    conn.close()
    
    # ── MT5 Point Sizes ──
    if HAS_MT5:
        print(f"\n{'=' * 70}")
        print("MT5 SYMBOL POINT SIZES")
        print("=" * 70)
        
        if not mt5.initialize():
            print(f"  MT5 init failed: {mt5.last_error()}")
            return
        
        symbols_to_check = [
            "XAUUSD", "XAUUSD.sim", "XAUJ26", "XAUJ26.sim",
            "USOIL", "USOIL.sim",
            "US500", "US500.sim", 
            "US100", "US100.sim",
            "US30", "US30.sim",
            "BTCUSD", "BTCUSD.sim"
        ]
        
        for sym in symbols_to_check:
            info = mt5.symbol_info(sym)
            if info:
                tick = mt5.symbol_info_tick(sym)
                bid = tick.bid if tick else 0
                print(f"\n  {sym}:")
                print(f"    point:       {info.point}")
                print(f"    digits:      {info.digits}")
                print(f"    bid:         {bid}")
                print(f"    trade_tick:  {info.trade_tick_size}")
                print(f"    contract:    {info.trade_contract_size}")
                print(f"    1 point ($): ~${info.trade_tick_value:.4f} per lot per tick")
                if bid > 0 and info.point > 0:
                    print(f"    80 points =  ${bid} → ${bid - 80*info.point:.5f} (SL example for BUY)")
                    print(f"    200 points = ${bid} → ${bid + 200*info.point:.5f} (TP example for BUY)")
        
        mt5.shutdown()

if __name__ == "__main__":
    main()
