# check_db_counts.py - Quick script to check record counts in all databases
import sqlite3
import os

CODEBASE_DIR = r'C:\Users\colli\Downloads\#CodeBase'

databases = [
    'XAUJ26_intelligence.db',
    'USOILH26_intelligence.db', 
    'US500H26_intelligence.db',
    'US100H26_intelligence.db',
    'US30H26_intelligence.db',
    'BTCF26_intelligence.db'
]

print("="*70)
print("DATABASE RECORD COUNTS")
print("="*70)

for db_name in databases:
    db_path = os.path.join(CODEBASE_DIR, db_name)
    
    if not os.path.exists(db_path):
        print(f"\n{db_name}: NOT FOUND")
        continue
    
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"\n{db_name} ({size_mb:.1f} MB)")
    print("-" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check each table
        tables = ['core_15m', 'basic_15m', 'advanced_indicators', 'fibonacci_data', 'ath_tracking']
        
        for table in tables:
            try:
                # Total count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total = cursor.fetchone()[0]
                
                # Count by timeframe
                cursor.execute(f"SELECT timeframe, COUNT(*) FROM {table} GROUP BY timeframe")
                by_tf = cursor.fetchall()
                
                tf_str = ", ".join([f"{tf}: {cnt:,}" for tf, cnt in by_tf])
                print(f"  {table}: {total:,} total | {tf_str}")
            except Exception as e:
                print(f"  {table}: ERROR - {e}")
        
        conn.close()
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "="*70)
