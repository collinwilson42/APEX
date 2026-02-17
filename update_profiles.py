"""
Update all profiles — target ~$200 reward per trade with 1:2.5 R:R
Lot sizes calibrated per symbol based on broker tick_value and point size.
"""
import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "apex_instances.db")

# Target: ~$200 TP reward, ~$80 SL risk (1:2.5 R:R)
# Formula: lots = target_reward / (tp_points * dollar_per_point)
SYMBOL_CONFIG = {
    # Gold: point=0.001, tick_val=$0.10/lot, contract=100
    # 20000pts * $0.001 = $20 move, $20 * 1.0 lot * (0.10/0.001) = $200
    "XAUJ26":     {"sl": 8000,  "tp": 20000,  "lots": 1.0},
    "XAUJ26.SIM": {"sl": 8000,  "tp": 20000,  "lots": 1.0},
    
    # Oil: point=0.001, tick_val=$0.10/lot
    # 12500pts = $12.50 move, need 1.6 lots for $200
    "USOIL":      {"sl": 5000,  "tp": 12500,  "lots": 1.6},
    "USOILH26":   {"sl": 5000,  "tp": 12500,  "lots": 1.6},
    
    # US500: point=0.1, tick_val=$0.10/lot
    # 1250pts = 125 index pts, need 1.6 lots for $200
    "US500":      {"sl": 500,   "tp": 1250,   "lots": 1.6},
    "US500H26":   {"sl": 500,   "tp": 1250,   "lots": 1.6},
    
    # US100: point=0.1, tick_val=$0.10/lot
    # 3750pts = 375 index pts, need 0.53 lots for ~$199
    "US100":      {"sl": 1500,  "tp": 3750,   "lots": 0.53},
    "US100H26":   {"sl": 1500,  "tp": 3750,   "lots": 0.53},
    
    # US30: point=0.1, tick_val=$0.10/lot
    # 5000pts = 500 index pts, need 1.0 lots for $200 -- wait that's wrong
    # 5000pts * $0.10/tick/lot * (0.1 point/tick) ... let me recalc
    # dollar_per_point = tick_value / tick_size * point = 0.10/0.1*0.1 = $0.10/pt/lot
    # 5000 pts * $0.10 = $500/lot, need 0.4 lots for $200
    "US30":       {"sl": 2000,  "tp": 5000,   "lots": 0.4},
    "US30H26":    {"sl": 2000,  "tp": 5000,   "lots": 0.4},
    
    # BTC: point=0.01, tick_val=$0.01/lot, contract=1
    # 125000pts = $1250 move, $0.01/tick means $0.01 per 0.01 point per lot
    # dollar_per_point = 0.01/0.01*0.01 = $0.01/pt/lot
    # 125000 * $0.01 = $1250/lot ... need 0.16 lots for $200
    "BTCUSD":     {"sl": 50000, "tp": 125000, "lots": 0.16},
    "BTCF26":     {"sl": 50000, "tp": 125000, "lots": 0.16},
}

def main():
    conn = sqlite3.connect(DB_PATH)
    
    print("=" * 70)
    print("UPDATING ALL PROFILES — Target $200 TP / $80 SL")
    print("=" * 70)
    
    profiles = conn.execute("SELECT id, name, symbol, trading_config, risk_config FROM profiles").fetchall()
    
    updated = 0
    for pid, name, symbol, tc_raw, rc_raw in profiles:
        sym_upper = symbol.upper().replace('.SIM', '')
        
        cfg = None
        for key, val in SYMBOL_CONFIG.items():
            if key.upper().replace('.SIM', '') == sym_upper or sym_upper in key.upper():
                cfg = val
                break
        
        if not cfg:
            print(f"  ⚠ No config for '{symbol}' — skipping {name}")
            continue
        
        sl = cfg["sl"]
        tp = cfg["tp"]
        lots = cfg["lots"]
        
        # Update trading_config
        tc = json.loads(tc_raw) if tc_raw else {}
        if "risk" not in tc:
            tc["risk"] = {}
        
        old_sl = tc["risk"].get("stop_loss_points", "?")
        old_tp = tc["risk"].get("take_profit_points", "?")
        old_lots = tc["risk"].get("base_lots", "?")
        
        tc["risk"]["stop_loss_points"] = sl
        tc["risk"]["take_profit_points"] = tp
        tc["risk"]["base_lots"] = lots
        tc["risk"]["max_lots"] = round(lots * 5, 2)
        
        # Update legacy risk_config
        rc = json.loads(rc_raw) if rc_raw else {}
        rc["stop_loss_points"] = sl
        rc["take_profit_points"] = tp
        rc["base_lots"] = lots
        rc["max_lots"] = round(lots * 5, 2)
        
        conn.execute(
            "UPDATE profiles SET trading_config=?, risk_config=?, position_sizing=? WHERE id=?",
            (json.dumps(tc), json.dumps(rc), json.dumps({"base_lots": lots, "max_lots": round(lots * 5, 2)}), pid)
        )
        
        print(f"  ✓ {name} ({symbol})")
        print(f"    SL: {old_sl} → {sl} pts | TP: {old_tp} → {tp} pts | Lots: {old_lots} → {lots}")
        updated += 1
    
    # Also link unlinked instances
    print(f"\n{'=' * 70}")
    print("LINKING UNLINKED INSTANCES")
    print("=" * 70)
    
    instances = conn.execute(
        "SELECT id, display_name, symbol, profile_id FROM algorithm_instances WHERE status='ACTIVE'"
    ).fetchall()
    
    all_profiles = conn.execute("SELECT id, name, symbol FROM profiles WHERE status='ACTIVE'").fetchall()
    
    linked = 0
    for inst_id, inst_name, inst_sym, inst_profile in instances:
        if inst_profile:
            continue
        
        inst_clean = inst_sym.upper().replace('.SIM', '')
        for p_id, p_name, p_sym in all_profiles:
            p_clean = p_sym.upper().replace('.SIM', '')
            if p_clean == inst_clean:
                conn.execute("UPDATE algorithm_instances SET profile_id=? WHERE id=?", (p_id, inst_id))
                print(f"  ✓ {inst_name} → {p_name}")
                linked += 1
                break
    
    if linked == 0:
        print("  All instances already linked")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 70}")
    print(f"DONE — Updated {updated} profiles, linked {linked} instances")
    print(f"Target per trade: ~$80 risk / ~$200 reward (1:2.5 R:R)")
    print("=" * 70)

if __name__ == "__main__":
    main()
