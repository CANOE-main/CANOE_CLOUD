import os
import uuid
import logging
from datetime import date
from pathlib import Path
from typing import Callable, Dict, Any
import pandas as pd
from canoe_lake.catalog import get_connection, PROJECT_ROOT

logger = logging.getLogger(__name__)

# Registry for silver transformations
SILVER_TRANSFORMERS: Dict[str, Dict[str, Any]] = {}

def register_silver(dataset_name: str, bronze_source: str):
    """Decorator to register a Silver transformation function."""
    def decorator(func: Callable[[Path], pd.DataFrame]):
        SILVER_TRANSFORMERS[dataset_name] = {
            "func": func,
            "bronze_source": bronze_source
        }
        return func
    return decorator

def get_git_hash() -> str:
    """Returns the current git short hash, or a fallback if not in a git repo."""
    try:
        import subprocess
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=PROJECT_ROOT).decode('utf-8').strip()
    except Exception:
        return "unknown"

def build_silver(dataset_name: str):
    """Executes a silver transformation and registers it in the catalog."""
    if dataset_name not in SILVER_TRANSFORMERS:
        raise ValueError(f"No Silver transformer registered for dataset: {dataset_name}")
        
    transformer_info = SILVER_TRANSFORMERS[dataset_name]
    transformer_func = transformer_info["func"]
    bronze_source = transformer_info["bronze_source"]
    
    logger.info(f"Starting Silver build for dataset: {dataset_name} (using bronze source: {bronze_source})")
    
    conn = get_connection()
    
    # 1. Locate the most recent matching Bronze file in the DuckDB catalog
    row = conn.execute(
        "SELECT id, file_path FROM bronze_sources WHERE source_name = ? ORDER BY collection_date DESC LIMIT 1",
        [bronze_source]
    ).fetchone()
    
    if not row:
        raise ValueError(f"No Bronze data found for source '{bronze_source}'. Please run 'canoe-lake bronze ingest {bronze_source}' first.")
        
    bronze_id, rel_bronze_path = row
    bronze_path = PROJECT_ROOT / rel_bronze_path
    
    # 2. Run the transformation function
    logger.info(f"Applying transformation using Bronze data: {bronze_path}")
    try:
        df = transformer_func(bronze_path)
    except Exception as e:
        logger.error(f"Silver transformation failed: {e}")
        raise
        
    import numpy as np
    
    if isinstance(df, (pd.DataFrame, np.ndarray)):
        datasets_to_save = {dataset_name: df}
    elif isinstance(df, dict):
        datasets_to_save = df
    else:
        raise TypeError(f"Transformer for {dataset_name} must return a Pandas DataFrame, NumPy array, or a dict of them.")
        
    git_hash = get_git_hash()
    processed_date = date.today().isoformat()
    canoe_user = os.environ.get("CANOE_USER", "unknown_user")
    
    for ds_key, ds_df in datasets_to_save.items():
        if not isinstance(ds_df, (pd.DataFrame, np.ndarray)):
            logger.warning(f"Skipping key {ds_key} as it is not a DataFrame or NumPy array.")
            continue
            
        # The true name we register in DuckDB: if returning a single DataFrame, it's just `dataset_name`
        # if returning a dict and the key doesn't start with `dataset_name`, we prefix it.
        # e.g., dataset="coders", key="generators" -> "coders_generators"
        if ds_key == dataset_name:
            final_ds_name = dataset_name
        else:
            final_ds_name = f"{dataset_name}_{ds_key}"
            
        # Path: data-lake/silver/{date}/{data}/
        date_dir = PROJECT_ROOT / "data-lake" / "silver" / processed_date
        output_dir = date_dir / final_ds_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Automatically generate the report.json from config.yaml if it doesn't exist for today
        report_path = date_dir / "report.json"
        if not report_path.exists():
            import yaml
            import json
            config_path = PROJECT_ROOT / "canoe_lake" / "config.yaml"
            if config_path.exists():
                try:
                    with open(config_path, 'r') as cf:
                        config_data = yaml.safe_load(cf)
                    with open(report_path, 'w') as rf:
                        json.dump(config_data, rf, indent=4)
                    logger.info(f"Generated {report_path} from config.yaml")
                except Exception as e:
                    logger.error(f"Failed to generate report.json: {e}")
        
        is_numpy = isinstance(ds_df, np.ndarray)
        ext = "npz" if is_numpy else "parquet"
        
        filename = f"{final_ds_name}_{processed_date}.{ext}"
        out_path = output_dir / filename
        
        logger.info(f"Saving Silver dataset to: {out_path}")
        if is_numpy:
            with open(out_path, 'wb') as file:
                np.savez_compressed(file, ds_df)
        else:
            ds_df.to_parquet(out_path, engine='pyarrow', compression='snappy')
        
        # 4. Register the metadata in the `silver_datasets` catalog table
        silver_id = str(uuid.uuid4())
        rel_out_path = out_path.relative_to(PROJECT_ROOT).as_posix()
        
        conn.execute("""
            INSERT INTO silver_datasets (
                id, bronze_id, source_name, processing_script_path, git_hash, 
                processed_date, processed_by, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            silver_id,
            bronze_id,
            final_ds_name,
            "canoe_lake.transformers",
            git_hash,
            processed_date,
            canoe_user,
            rel_out_path
        ])
        
        logger.info(f"Successfully registered Silver catalog record for {final_ds_name} (ID: {silver_id})")
