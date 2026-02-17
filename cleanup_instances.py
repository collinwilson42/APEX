"""
Seed 20: Symbol Alignment — One-time DB cleanup
Normalizes .SIM suffixes and archives empty duplicate instances.
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apex_instances.db')

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("=" * 60)
    print("SEED 20: INSTANCE CLEANUP")
    print("=" * 60)
    
    # 1. Show current state
    cur.execute("SELECT id, display_name, symbol, status, profile_id FROM algorithm_instances ORDER BY created_at")
    rows = cur.fetchall()
    print(f"\nFound {len(rows)} instances:\n")
    for r in rows:
        profile_tag = f" [profile={r['profile_id']}]" if r['profile_id'] and r['profile_id'].strip() else ""
        print(f"  {r['status']:8s} | {r['symbol']:15s} | {r['display_name']:30s} | {r['id']}{profile_tag}")
    
    # 2. Check which instances have sentiment data
    print("\nSentiment data check:")
    instances_with_data = set()
    for r in rows:
        safe_id = r['id'].replace("-", "_").replace(".", "_").lower()
        table_name = f"sentiment_{safe_id}"
        try:
            cur.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cur.fetchone()[0]
            if count > 0:
                instances_with_data.add(r['id'])
                print(f"  {r['id']:40s} -> {count} rows OK")
            else:
                print(f"  {r['id']:40s} -> empty")
        except:
            print(f"  {r['id']:40s} -> no table")
    
    # 3. Normalize symbols (strip .SIM)
    print("\nNormalizing symbols...")
    cur.execute("SELECT id, symbol FROM algorithm_instances WHERE symbol LIKE '%.SIM'")
    to_fix = cur.fetchall()
    for r in to_fix:
        new_symbol = r['symbol'].replace('.SIM', '').replace('.sim', '')
        cur.execute("UPDATE algorithm_instances SET symbol = ? WHERE id = ?", (new_symbol, r['id']))
        print(f"  {r['id']}: {r['symbol']} -> {new_symbol}")
    
    if not to_fix:
        print("  (no .SIM symbols found)")
    
    # 4. Archive empty duplicates
    # Group by normalized symbol, keep the best (has data or profile), archive rest
    print("\nArchiving empty duplicates...")
    cur.execute("SELECT id, symbol, profile_id, status FROM algorithm_instances WHERE status = 'ACTIVE' ORDER BY created_at")
    active = cur.fetchall()
    
    by_symbol = {}
    for r in active:
        sym = r['symbol'].upper().replace('.SIM', '')
        by_symbol.setdefault(sym, []).append(r)
    
    archived_count = 0
    for sym, instances in by_symbol.items():
        if len(instances) <= 1:
            continue
        
        # Pick the best: has data > has profile > newest
        def score(inst):
            s = 0
            if inst['id'] in instances_with_data:
                s += 100
            if inst['profile_id'] and inst['profile_id'].strip():
                s += 10
            return s
        
        ranked = sorted(instances, key=score, reverse=True)
        keeper = ranked[0]
        print(f"\n  {sym}: keeping {keeper['id']}")
        
        for inst in ranked[1:]:
            if inst['id'] in instances_with_data:
                print(f"    SKIP archiving {inst['id']} (has data)")
                continue
            cur.execute("UPDATE algorithm_instances SET status = 'ARCHIVED' WHERE id = ?", (inst['id'],))
            print(f"    archived {inst['id']}")
            archived_count += 1
    
    if archived_count == 0:
        print("  (no duplicates to archive)")
    
    conn.commit()
    
    # 5. Final state
    print("\n" + "=" * 60)
    print("FINAL STATE:")
    print("=" * 60)
    cur.execute("SELECT id, display_name, symbol, status, profile_id FROM algorithm_instances ORDER BY status, symbol, created_at")
    for r in cur.fetchall():
        profile_tag = f" [profile]" if r['profile_id'] and r['profile_id'].strip() else ""
        data_tag = " [HAS DATA]" if r['id'] in instances_with_data else ""
        print(f"  {r['status']:8s} | {r['symbol']:15s} | {r['display_name']:30s} | {r['id']}{profile_tag}{data_tag}")
    
    conn.close()
    print(f"\nDone. Archived {archived_count} empty duplicates.")

if __name__ == '__main__':
    main()
