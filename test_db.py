# test_db.py - Quick test to verify database writes
import sqlite3
import os

db_path = r"C:\Users\colli\Downloads\#CodeBase\XAUJ26_intelligence.db"

print(f"Database: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = ['core_15m', 'basic_15m', 'advanced_indicators', 'fibonacci_data', 'ath_tracking']
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")
    
    # Show sample data from core_15m
    print("\nSample from core_15m:")
    cursor.execute("SELECT * FROM core_15m LIMIT 3")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    conn.close()
else:
    print("Database doesn't exist!")
