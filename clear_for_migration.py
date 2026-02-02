"""
═══════════════════════════════════════════════════════════════════════════
SEED 13 - DATABASE MIGRATION PREP
Clears old 1m data and prepares for 15m/1h backfill
Run this BEFORE init2.py to force full 50,000 bar backfill
═══════════════════════════════════════════════════════════════════════════
"""

import sqlite3
import os
from pathlib import Path

# All intelligence databases
DB_FILES = [
    "XAUJ26_intelligence.db",
    "BTCF26_intelligence.db",
    "US100H26_intelligence.db",
    "US30H26_intelligence.db",
    "US500H26_intelligence.db",
    "USOILH26_intelligence.db",
]

# Tables that contain timeframe-specific data
TABLES_TO_CLEAR = [
    "core_15m",
    "basic_15m",
    "advanced_indicators",
    "fibonacci_data",
    "ath_tracking",
]

def clear_database(db_path: str):
    """Clear all timeframe data from a database to force full backfill."""
    if not os.path.exists(db_path):
        print(f"  ⚠ {db_path} not found, skipping")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    db_name = Path(db_path).stem
    print(f"\n[{db_name}]")
    
    for table in TABLES_TO_CLEAR:
        try:
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                # Get row count before
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]
                
                # Delete ALL rows (we want fresh 1h data)
                cursor.execute(f"DELETE FROM {table}")
                
                print(f"  ✓ {table}: cleared {count_before:,} rows")
            else:
                print(f"  - {table}: table doesn't exist (will be created)")
        except Exception as e:
            print(f"  ✗ {table}: {e}")
    
    # Vacuum to reclaim space
    conn.commit()
    cursor.execute("VACUUM")
    conn.commit()
    conn.close()
    
    print(f"  ✓ Database vacuumed")

def main():
    print("=" * 70)
    print("  SEED 13 - DATABASE MIGRATION: 1m/15m → 15m/1h")
    print("  Clearing all data for fresh 50,000 bar backfill")
    print("=" * 70)
    
    base_path = Path(__file__).parent
    
    cleared_count = 0
    for db_file in DB_FILES:
        db_path = base_path / db_file
        if db_path.exists():
            clear_database(str(db_path))
            cleared_count += 1
    
    print("\n" + "=" * 70)
    print(f"  ✓ Cleared {cleared_count} databases")
    print("  → Run 'python init2.py' to start fresh 15m/1h backfill")
    print("=" * 70)

if __name__ == "__main__":
    main()
