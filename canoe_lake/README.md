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

## Transportation sector sources (bronze)
These ingestors download the raw files that canoe-transportation uses (see its `config/sources.yaml`). There are no silver transforms for them yet. URLs and pinned checksums live in `config.yaml`. If a download does not match its pinned sha256, md5 or byte count, the ingest fails and nothing is catalogued.

| Code | Publisher and dataset |
|---|---|
| `nrcan_ceud_transport` | NRCan CEUD Transportation tables, each province separately (AB, BCT, MB, NB, NL, NS, ON, PE, QC, SK), NRCan's combined Atlantic region (ATL) and Canada |
| `nrcan_fcr` | NRCan Fuel Consumption Ratings |
| `dunsky` | Dunsky EV Charging Infrastructure for Canada (NRCan report page); disabled |
| `statcan_transport` | StatCan 20-10-0021, 20-10-0025, 23-10-0308, 34-10-0254, 23-10-0142 (WDS ZIP and metadata) |
| `ontario_mto` | Ontario MTO vehicle population ZIPs |
| `izev` | Transport Canada iZEV incentive records |
| `atb_transport` | NLR Transportation ATB |
| `afdc` | AFDC Canadian electric charging stations (`NLR_API_KEY`, default `DEMO_KEY`); disabled |
| `nhtsa_cafe` | NHTSA CAFE 2024 Central Analysis inputs |
| `nhts` | FHWA NHTS 2022 public-use data |
| `faa` | FAA Economic Values, sections 3 and 4 |
| `fueleconomy` | FuelEconomy.gov vehicles.csv.zip |
| `eia_nems` | EIA NEMS trnhdvx.xlsx (pinned commit) |
| `epa_moves` | EPA MOVES6 population and activity report |
| `gcam` | JGCRI GCAM UCD_trn_data_CORE.csv (pinned commit) |
| `epri_regen` | EPRI US-REGEN v2025 transportation page and data module |
| `hatch` | HATCH technology growth evidence (Zenodo) |
| `eafo` | EAFO Norway fleet and registrations; disabled |

Sources whose transport pins went stale (checked 2026-11-23):
- `statcan_transport`: each table ZIP includes its `_MetaData.csv`, so the ZIP pin covers the metadata. The WDS metadata JSON is downloaded but not pinned.
- `epri_regen`: EPRI republished the page and removed the pinned data module, so it is downloaded from its Wayback Machine capture, which matches the pin.
- `afdc`: disabled like `dunsky` and `eafo`. AFDC has added a field (`ev_power_sharing`) to every station record, so none of the pinned snapshots reproduce, including the historical-date ones. The live 2026-11-14 snapshot is also commented out in `config.yaml`.
- `dunsky` and `eafo`: the ingestors are kept, but their `@register_ingestor` decorators are commented out, because no copy matching transport's pins exists. Uncomment them if one turns up. The Dunsky page differs only in cache tokens. EAFO's data has been replaced upstream; Statistics Norway is a possible replacement.

CER Canada's Energy Future is covered by the `cer` ingestor. Sources that cannot be downloaded (GREET, Autonomie/BEAN, RAMP charging profiles, EPA OMEGA extract and reviewed manual values) go through `bronze register-manual`.
