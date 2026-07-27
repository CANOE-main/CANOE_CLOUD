import pytest
import tempfile
import duckdb
from pathlib import Path
from unittest.mock import patch

from canoe_lake.catalog import init_catalog, get_connection
import canoe_lake.catalog

@pytest.fixture
def mock_catalog_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Mock CATALOG_DIR and CATALOG_DB_PATH
        with patch.object(canoe_lake.catalog, "CATALOG_DIR", temp_path):
            with patch.object(canoe_lake.catalog, "CATALOG_DB_PATH", temp_path / "catalog.duckdb"):
                yield temp_path

def test_init_catalog(mock_catalog_dir):
    # This shouldn't raise any errors
    init_catalog()
    
    # Check that duckdb can connect and the tables exist
    db_path = mock_catalog_dir / "catalog.duckdb"
    assert db_path.exists()
    
    with duckdb.connect(str(db_path)) as conn:
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert "bronze_sources" in table_names
        assert "silver_datasets" in table_names
