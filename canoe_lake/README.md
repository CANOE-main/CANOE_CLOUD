# CANOE Data Lake (`canoe_lake`)

This package is a standalone Data Lake ingestion and transformation framework for the CANOE project. It acts as a decoupled pipeline that pulls data from external APIs and HTML endpoints into a local **Bronze** folder, processes that data into a clean **Silver** Parquet layer, and registers the datasets in a DuckDB catalog.

The broader CANOE ecosystem models consume this processed Parquet data at runtime.

## Installation

Ensure you have your environment set up with `requirements.txt` from the parent repository:
```bash
pip install -r ../requirements.txt
```

## Configuration & Setup

1. Copy `.env.example` to `.env` in the root repository.
2. Provide your API keys inside `.env` (`EIA_API_KEY`, `CODERS_API_KEY`, `RNINJA_API_KEY`).
3. You can configure target extraction years and release versions in `config.yaml` located in this directory. If missing or incomplete, the ingestors will fallback to defaults.

## Usage

### The Master Script
To execute the entire pipeline end-to-end (initializing the catalog, ingesting Bronze data, and building Silver data):
```bash
python run_all.py
```

### The CLI
You can also run specific pieces of the architecture individually via the `canoe-lake` CLI:

```bash
# 1. Initialize the catalog (applies SQL migrations)
canoe-lake catalog init

# 2. Ingest a specific Bronze source (e.g., eia, statcan, oedi_stock)
canoe-lake bronze ingest eia

# 3. Build a specific Silver dataset (e.g., statcan_17100009, atb)
canoe-lake silver build atb
```

## Structure
- `canoe_lake/bronze.py`: Core logic for fetching API payloads.
- `canoe_lake/silver.py`: Core logic for saving Parquet and registering schemas.
- `canoe_lake/catalog.py`: DuckDB connection state and migrations.
- `canoe_lake/ingestors.py`: All `@register_ingestor` definitions for data sources.
- `canoe_lake/transformers.py`: All `@register_silver` transformations mapping Bronze to Silver.
- `migrations/01_initial.sql`: The primary schema definition for the Data Lake DuckDB Catalog.
