# migrate_ath_columns.py
"""
Migration script to add missing columns to ath_tracking table.
Adds: ath_distance_points, distance_from_ath_percentile

Run this once to update all symbol databases.
"""

import sqlite3
import os
from config import SYMBOL_DATABASES

def migrate_database(db_path):
    """Add missing columns to ath_tracking table."""
    if not os.path.exists(db_path):
        print(f"  ✗ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(ath_tracking)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    columns_to_add = {
        'ath_distance_points': 'REAL',
        'distance_from_ath_percentile': 'REAL'
    }
    
    added = []
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE ath_tracking ADD COLUMN {col_name} {col_type}")
                added.append(col_name)
            except sqlite3.OperationalError as e:
                print(f"  ⚠️  Could not add {col_name}: {e}")
    
    conn.commit()
    conn.close()
    
    if added:
        print(f"  ✓ Added columns: {', '.join(added)}")
    else:
        print(f"  ✓ All columns already exist")
    
    return True

def main():
    print("\n" + "="*70)
    print("ATH_TRACKING TABLE MIGRATION")
    print("Adding: ath_distance_points, distance_from_ath_percentile")
    print("="*70 + "\n")
    
    for symbol_id, config in SYMBOL_DATABASES.items():
        db_path = config['db_path']
        print(f"[{symbol_id}] {db_path}")
        migrate_database(db_path)
    
    print("\n" + "="*70)
    print("✓ Migration complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
