# CANOE Project

The CANOE Project is an integrated framework for energy sector modeling. These sector-specific components fetch data, execute complex business logic, and generate outputs for end-use modeling.

Recently, the data fetching logic for these models was completely refactored into a centralized **Data Lake Architecture**. The Data Lake decouple ingestion and transformation from the models, ensuring that data is securely versioned, reproducible, and easily accessible via a unified Parquet format.

## Repository Structure

- `canoe_lake/`: The source code for the standalone Data Lake framework. Contains the ingestors, transformers, and catalog management CLI.
- `data-lake/`: The generated data outputs. Consists of a `bronze` folder (raw data), a `silver` folder (processed Parquet), and a DuckDB `catalog`.
- `canoe-schema/`: The database schemas and migration scripts for the CANOE ecosystem.

## Quick Start

1. Install global requirements:
```bash
pip install -r requirements.txt
```

2. Copy the example environment variables and add your API keys:
```bash
cp .env.example .env
```

3. Navigate to the data lake orchestrator and run the pipeline:
```bash
cd canoe_lake
python run_all.py
```

This will automatically pull all data from external APIs (EIA, StatCan, NREL OEDI, IESO) into the `data-lake/bronze` layer and transform it into the `data-lake/silver` layer. The downstream CANOE models are configured to read directly from this Silver layer.
