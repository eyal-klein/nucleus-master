#!/usr/bin/env python3
"""
NUCLEUS Migration Runner
Runs a specific migration file against the database
"""

import os
import sys
import psycopg2
from psycopg2 import sql

def run_migration(migration_file: str):
    """Run a migration file"""
    
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Read migration file
    if not os.path.exists(migration_file):
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print(f"Running migration: {migration_file}")
    print("="*60)
    
    # Connect to database
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cur = conn.cursor()
        
        # Execute migration
        print("Executing SQL...")
        cur.execute(migration_sql)
        
        # Commit transaction
        conn.commit()
        print("✅ Migration completed successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_migration.py <migration_file>")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    run_migration(migration_file)
