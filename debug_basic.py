# debug_basic.py - Check basic_15m table specifically
import sqlite3
import os

db_path = r"C:\Users\colli\Downloads\#CodeBase\XAUJ26_intelligence.db"

print(f"Database: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nTables in DB: {tables}")
    
    # Check basic_15m schema
    print("\n--- basic_15m Schema ---")
    cursor.execute("PRAGMA table_info(basic_15m)")
    for col in cursor.fetchall():
        print(f"  {col}")
    
    # Count by timeframe
    print("\n--- basic_15m Counts ---")
    cursor.execute("SELECT timeframe, COUNT(*) FROM basic_15m GROUP BY timeframe")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} rows")
    
    # Sample data
    print("\n--- basic_15m Sample (first 3 rows) ---")
    cursor.execute("SELECT * FROM basic_15m LIMIT 3")
    cols = [desc[0] for desc in cursor.description]
    print(f"  Columns: {cols}")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    # Check what symbol values exist
    print("\n--- Symbols in basic_15m ---")
    cursor.execute("SELECT DISTINCT symbol FROM basic_15m")
    symbols = [row[0] for row in cursor.fetchall()]
    print(f"  Symbols: {symbols}")
    
    # Compare to core_15m
    print("\n--- core_15m Counts ---")
    cursor.execute("SELECT timeframe, COUNT(*) FROM core_15m GROUP BY timeframe")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} rows")
    
    print("\n--- Symbols in core_15m ---")
    cursor.execute("SELECT DISTINCT symbol FROM core_15m")
    symbols = [row[0] for row in cursor.fetchall()]
    print(f"  Symbols: {symbols}")
    
    conn.close()
