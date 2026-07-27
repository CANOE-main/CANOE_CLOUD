import pytest
import pandas as pd
from pathlib import Path
import json

from canoe_lake.bronze import register_ingestor, INGESTORS
from canoe_lake.silver import register_silver, SILVER_TRANSFORMERS

@pytest.fixture
def mock_bronze_source(tmp_path):
    # Register a dummy ingestor
    @register_ingestor("test_dummy")
    def ingest_dummy(output_dir: Path) -> dict:
        data = {"hello": "world"}
        file_path = output_dir / "dummy.json"
        with open(file_path, "w") as f:
            json.dump(data, f)
            
        return {
            "file_path": str(file_path),
            "source_type": "dummy",
            "file_format": "json"
        }
        
    yield "test_dummy"
    
    # Clean up
    if "test_dummy" in INGESTORS:
        del INGESTORS["test_dummy"]

@pytest.fixture
def mock_silver_transformer(tmp_path):
    # Register a dummy transformer
    @register_silver("test_silver_dummy", bronze_source="test_dummy")
    def transform_dummy(bronze_path: Path) -> pd.DataFrame:
        with open(bronze_path / "dummy.json", "r") as f:
            data = json.load(f)
        return pd.DataFrame([data])
        
    yield "test_silver_dummy"
    
    # Clean up
    if "test_silver_dummy" in SILVER_TRANSFORMERS:
        del SILVER_TRANSFORMERS["test_silver_dummy"]

def test_dummy_ingestor(mock_bronze_source, tmp_path):
    ingestor = INGESTORS[mock_bronze_source]
    res = ingestor(tmp_path)
    
    assert res["source_type"] == "dummy"
    assert Path(res["file_path"]).exists()
    
def test_dummy_transformer(mock_silver_transformer, tmp_path):
    # We create the mock file first
    with open(tmp_path / "dummy.json", "w") as f:
        json.dump({"test": "data"}, f)
        
    transformer_func = SILVER_TRANSFORMERS[mock_silver_transformer]["func"]
    df = transformer_func(tmp_path)
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert df.iloc[0]["test"] == "data"
