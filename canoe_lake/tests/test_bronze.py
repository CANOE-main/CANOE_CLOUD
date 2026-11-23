import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from canoe_lake.catalog import init_catalog, get_connection
from canoe_lake.bronze import register_manual_bronze
import canoe_lake.catalog
import canoe_lake.bronze

@pytest.fixture
def mock_lake_root():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        catalog_dir = temp_path / "data-lake" / "catalog"
        # Mock the catalog location and the lake root used for bronze files
        with patch.object(canoe_lake.catalog, "CATALOG_DIR", catalog_dir), \
             patch.object(canoe_lake.catalog, "CATALOG_DB_PATH", catalog_dir / "catalog.duckdb"), \
             patch.object(canoe_lake.bronze, "PROJECT_ROOT", temp_path), \
             patch.object(canoe_lake.catalog, "PROJECT_ROOT", temp_path):
            init_catalog()
            yield temp_path

def test_register_manual_bronze(mock_lake_root):
    src_file = mock_lake_root / "manual_table.csv"
    src_file.write_text("a,b\n1,2\n")

    registered = register_manual_bronze(
        source_name="test_manual",
        file_path=str(src_file),
        collection_date="2026-11-22",
        doc_id="Test document",
        pub_date="2024-02-01",
        notes="test"
    )
    assert registered

    row = get_connection().execute(
        "SELECT file_path, file_format, publication_date FROM bronze_sources WHERE source_name = 'test_manual'"
    ).fetchone()
    assert row is not None
    assert row[0] == "data-lake/bronze/test_manual/2026-11-22/manual_table.csv"
    assert row[1] == "csv"
    assert str(row[2]) == "2024-02-01"

def test_register_manual_bronze_missing_file(mock_lake_root):
    assert not register_manual_bronze(
        source_name="test_manual",
        file_path=str(mock_lake_root / "missing.csv"),
        collection_date="2026-11-22"
    )
