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

import os
import shutil
import subprocess
from canoe_lake.bronze import compute_file_hash, rehash_bronze

def _make_tree(root: Path):
    (root / "sub" / "deeper").mkdir(parents=True)
    (root / "a.csv").write_text("x,y\n1,2\n")
    (root / "b.txt").write_text("hello")
    (root / "sub" / "c.csv").write_text("nested")
    (root / "sub" / "deeper" / "d.bin").write_bytes(b"\x00\x01\x02")

def test_folder_hash_ignores_mtime_and_location(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    _make_tree(one)
    _make_tree(two)
    for f in two.rglob("*"):
        os.utime(f, (1, 1))
    assert compute_file_hash(one) == compute_file_hash(two)

def test_folder_hash_detects_content_change_with_same_mtime(tmp_path):
    _make_tree(tmp_path)
    before = compute_file_hash(tmp_path)
    target = tmp_path / "a.csv"
    st = target.stat()
    target.write_text("x,y\n1,3\n")
    os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert compute_file_hash(tmp_path) != before

def test_folder_hash_covers_subfolders_and_names(tmp_path):
    _make_tree(tmp_path)
    before = compute_file_hash(tmp_path)
    (tmp_path / "sub" / "deeper" / "d.bin").write_bytes(b"\x00\x01\x03")
    changed = compute_file_hash(tmp_path)
    assert changed != before
    (tmp_path / "sub" / "deeper" / "d.bin").rename(tmp_path / "sub" / "deeper" / "e.bin")
    assert compute_file_hash(tmp_path) != changed

def test_folder_hash_matches_sha256sum_manifest(tmp_path):
    if not (shutil.which("sha256sum") and shutil.which("find")):
        pytest.skip("GNU coreutils not available")
    _make_tree(tmp_path)
    out = subprocess.run(
        "find . -type f -printf '%P\\n' | LC_ALL=C sort | xargs -d '\\n' sha256sum | sha256sum",
        shell=True, cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.split()[0]
    assert compute_file_hash(tmp_path) == out

def test_single_file_hash_is_plain_sha256(tmp_path):
    import hashlib
    f = tmp_path / "f.csv"
    f.write_bytes(b"abc" * 100000)
    assert compute_file_hash(f) == hashlib.sha256(b"abc" * 100000).hexdigest()

def test_rehash_bronze(mock_lake_root):
    folder = mock_lake_root / "data-lake" / "bronze" / "2026-11-22" / "src"
    _make_tree(folder)
    conn = get_connection()
    conn.execute(
        "INSERT INTO bronze_sources (id, source_name, source_type, collection_date, collected_by, file_path, file_hash, file_format) "
        "VALUES ('00000000-0000-0000-0000-000000000001', 'src', 'api', DATE '2026-11-22', 'me', 'data-lake/bronze/2026-11-22/src', 'oldhash', 'dir')"
    )
    conn.execute(
        "INSERT INTO bronze_sources (id, source_name, source_type, collection_date, collected_by, file_path, file_hash, file_format) "
        "VALUES ('00000000-0000-0000-0000-000000000002', 'gone', 'api', DATE '2026-11-22', 'me', 'data-lake/bronze/2026-11-22/gone', 'keep', 'dir')"
    )
    changes = rehash_bronze(apply=False)
    assert [c[0] for c in changes] == ["src"]
    assert get_connection().execute("SELECT file_hash FROM bronze_sources WHERE id = '00000000-0000-0000-0000-000000000001'").fetchone()[0] == "oldhash"

    rehash_bronze(apply=True)
    assert get_connection().execute("SELECT file_hash FROM bronze_sources WHERE id = '00000000-0000-0000-0000-000000000001'").fetchone()[0] == compute_file_hash(folder)
    assert get_connection().execute("SELECT file_hash FROM bronze_sources WHERE id = '00000000-0000-0000-0000-000000000002'").fetchone()[0] == "keep"
    assert rehash_bronze(apply=False) == []
