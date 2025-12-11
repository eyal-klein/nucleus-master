#!/usr/bin/env python3
"""
NUCLEUS Migration Runner Job
One-time job to run database migrations
"""

import os
import sys
import logging

# Add backend to path
sys.path.append("/app/backend")

from sqlalchemy import text
from shared.models import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migration_file(filepath: str):
    """Run a SQL migration file"""
    logger.info(f"Running migration: {filepath}")
    
    # Read migration file
    with open(filepath, 'r') as f:
        migration_sql = f.read()
    
    # Execute migration
    try:
        with engine.begin() as conn:
            # Execute entire migration as single transaction
            logger.info("Executing migration SQL...")
            conn.execute(text(migration_sql))
            logger.info(f"✅ Migration completed: {filepath}")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("NUCLEUS Migration Runner - Starting")
    logger.info("=" * 80)
    
    # Get migration file from environment or default to 005
    migration_name = os.getenv("MIGRATION_NAME", "005_add_extended_dna_tables")
    migration_path = f"/app/backend/shared/migrations/{migration_name}.sql"
    
    if not os.path.exists(migration_path):
        logger.error(f"Migration file not found: {migration_path}")
        sys.exit(1)
    
    try:
        run_migration_file(migration_path)
        logger.info("=" * 80)
        logger.info("Migration completed successfully!")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
