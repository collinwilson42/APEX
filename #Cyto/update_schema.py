"""
Update CYTO schema to support wisdom framework
Adds section column if it doesn't exist
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "cyto.db"

def update_schema():
    """Add section column to nodes table if it doesn't exist."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check if section column exists
    cursor.execute("PRAGMA table_info(nodes)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'section' not in columns:
        print("Adding 'section' column to nodes table...")
        cursor.execute("ALTER TABLE nodes ADD COLUMN section INTEGER DEFAULT 9")
        conn.commit()
        print("✓ Section column added")
    else:
        print("✓ Section column already exists")
    
    conn.close()

if __name__ == '__main__':
    print("Updating CYTO database schema for wisdom framework...")
    update_schema()
    print("✓ Schema update complete")
