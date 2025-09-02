#!/usr/bin/env python3
"""Initialize or update the knowledge.db SQLite database."""

import sqlite3
import pathlib
import sys

def create_database():
    """Create or update the knowledge database with proper schema."""
    base = pathlib.Path(__file__).resolve().parent
    db_path = base / "knowledge.db"
    schema_path = base / "schema.sql"
    
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}")
        sys.exit(1)
    
    # Read schema
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    
    # Create/update database
    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.executescript(schema)
        con.commit()
        
        # Verify tables were created
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        
        print(f"✓ Database created/updated at {db_path}")
        print(f"  Tables: {', '.join([t[0] for t in tables])}")
        
        con.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)
