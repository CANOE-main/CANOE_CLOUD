# CANOE Data Lake Output Directory

This `data-lake` directory is entirely **generated** by the `canoe_lake` ingestion pipeline. It acts as the centralized file storage for all CANOE external data.

Do not commit this folder's contents directly to source control (the `.gitignore` is configured to exclude large data files but retain these READMEs).

## Subdirectories

- **`catalog/`**: Contains `catalog.duckdb`, a SQLite-like database that tracks the provenance (source URLs, versions, timestamps) of all files in the lake.
- **`bronze/`**: The landing zone for all raw data fetched from external APIs.
- **`silver/`**: The curated zone containing clean, standardized `.parquet` files that are ingested by the CANOE sector models.

To populate this directory, navigate to `../canoe_lake` and run:
```bash
python run_all.py
```
