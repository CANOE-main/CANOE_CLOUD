import duckdb
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Assume we run from CANOE_CLOUD_2 root, or use relative paths carefully
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_DIR = PROJECT_ROOT / "data-lake" / "catalog"
CATALOG_DB_PATH = CATALOG_DIR / "catalog.duckdb"
MIGRATIONS_DIR = PROJECT_ROOT / "canoe_lake" / "migrations"

def get_connection():
    # Create the catalog directory if it doesn't exist
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    # Return DuckDB connection
    return duckdb.connect(str(CATALOG_DB_PATH))

def init_catalog():
    """Initializes the catalog database and applies migrations."""
    logger.info(f"Initializing catalog at {CATALOG_DB_PATH}")
    
    # Ensure directory exists before connecting
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    
    with duckdb.connect(str(CATALOG_DB_PATH)) as conn:
        logger.info("Connected to DuckDB successfully.")
        
        # Look for migration scripts
        if not MIGRATIONS_DIR.exists():
            logger.warning(f"Migrations directory not found at {MIGRATIONS_DIR}")
            return
            
        migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not migrations:
            logger.info("No SQL migrations found.")
            return
            
        for migration_file in migrations:
            logger.info(f"Applying migration: {migration_file.name}")
            sql_script = migration_file.read_text()
            try:
                # DuckDB execute can run multiple statements separated by semicolons
                conn.execute(sql_script)
                logger.info(f"Successfully applied {migration_file.name}")
            except Exception as e:
                logger.error(f"Error applying migration {migration_file.name}: {e}")
                raise
