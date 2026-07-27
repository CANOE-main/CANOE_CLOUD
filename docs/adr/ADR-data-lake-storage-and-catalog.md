# ADR: Data Lake Storage and Catalog Design

## Status
Accepted

## Context
The CANOE sector-building workflow currently fetches upstream data (such as StatCan, NRCan, EIA, CODERS, AEO, Renewables Ninja) dynamically or relies on manually placed CSV files in `input_files/` folders across various subdirectories (`canoe-electricity`, `canoe-commercial`, etc.). This causes several issues:
- Repeated, time-consuming downloads during normal sector builds.
- Redundant and heavy preprocessing of raw inputs across different scripts.
- Lack of clear provenance tracking (where a dataset came from and what version of processing was used).

To address these issues, we need to implement a Data Lake architecture caching prerequisite source data and reusable intermediate datasets.

## Decision

We will use a Bronze/Silver Data Lake architecture with the following choices:

1. **Bronze Format**: Raw files stored locally by source and collection date.
2. **Silver Format**: Processed Parquet files stored locally by source and processing version (identified by the git short hash).
3. **Catalog Technology**: A lightweight DuckDB metadata database (`catalog.duckdb`).
4. **CLI Framework**: Python CLI using `argparse`, conforming to existing project conventions (as seen in `canoe-agriculture/canoe_agriculture/main.py`).
5. **Credentials/User Identity**: `.env` loaded via `python-dotenv`.

## Justification

- **Local workstation usage**: The CANOE model is primarily run by researchers on local workstations rather than a distributed cloud cluster. A local file system approach combined with DuckDB is extremely fast, easy to set up, and requires no external database servers.
- **Small-to-medium data size**: The raw data for CANOE sectors, while sometimes complex (like the AEO spreadsheets), fits comfortably on a standard workstation's hard drive. Parquet provides excellent compression for intermediate tabular data, and DuckDB is highly optimized for analyzing these files locally.
- **Schema volatility of upstream data**: External sources (like StatCan APIs or Renewables Ninja) often change or have complex JSON/CSV structures. Keeping the raw files intact in the Bronze layer allows us to re-parse them later without redownloading if the upstream source changes its schema unexpectedly or if our parsing logic improves.
- **Need for reproducibility**: By tagging Bronze data by collection date and Silver data by processing script git hash, we can exactly trace the lineage of a model build.
- **Avoid repeated preprocessing**: Storing the results of heavy parsing steps (such as extracting the AEO `rsmess.xlsx` equipment sheets) into Silver Parquet files guarantees that sector builders (the model) just read a clean DataFrame, shaving significant time off every model run.

## Alternatives Considered

- **Bronze Format Alternative**: Storing raw data in an SQL database like SQLite. *Rejected* because upstream data comes in various unstructured or semi-structured formats (ZIP, Excel, HTML, JSON) that don't map cleanly to relational tables without loss of fidelity.
- **Silver Format Alternative**: Storing intermediate datasets as CSVs or inside SQLite. *Rejected* because Parquet natively preserves data types (reducing parsing errors), compresses well, and reads orders of magnitude faster into Pandas.
- **Catalog Technology Alternative**: JSON files or SQLite. *Rejected* JSON because concurrent writes or complex metadata queries become cumbersome. SQLite is a valid choice, but DuckDB can natively query our Silver Parquet files directly if needed, offering a more unified analytical engine footprint for future expansions.
- **CLI Framework Alternative**: `Typer` or `Click`. *Rejected* (for now) because `argparse` is built-in and already used in `canoe-agriculture/canoe_agriculture/main.py`, reducing the need for new third-party dependencies unless the CLI becomes overly complex.
- **Credentials Alternative**: Hardcoding keys or requiring system-wide environment variables. *Rejected* because a `.env` file via `python-dotenv` is the industry standard for portable, developer-friendly local secrets management that cleanly prevents accidental commits.
