# Sector Preprocessing Audit

This document identifies the preprocessing responsibilities and data dependencies of each sector build in the CANOE model. It serves as the foundation for migrating the system to a Bronze/Silver Data Lake architecture.

## 1. Agriculture (`canoe-agriculture`)

- **Input Sources**: 
  - NRCan datasets (fetched via `data_scraper.py`).
  - StatCan zip file `25100029-eng.zip` (fetched via `statcan.py`).
  - Local inputs (`input/config.toml`).
- **Current Preprocessing Steps**: 
  - Downloading and extracting StatCan CSVs, filtering by agriculture sectors and fuels.
  - Scraping NRCan HTML tables to build initial demand and population data frames.
- **Intermediate Datasets Created**: 
  - Pickled cache files (`statcan_agri.pkl`, NRCan cache).
- **Final Outputs**: 
  - SQLite database containing agriculture-specific demands, capacities, and costs.
- **Candidate Bronze Sources**: 
  - StatCan Table 25-10-0029 (Energy supply and demand).
  - NRCan Agriculture data.
- **Candidate Silver Datasets**: 
  - Cleaned StatCan ATL shares for agriculture.
  - Cleaned NRCan agriculture energy usage.
- **Migration Risk Level**: Low
- **Shared Sources**: StatCan, NRCan.

## 2. Commercial (`canoe-commercial`)

- **Input Sources**: 
  - StatCan API (various tables, including population and GDP).
  - AEO excel workbook (`ktekx.xlsx`).
  - GDP projections (`gdp_projections.csv` from URL).
  - Renewables Ninja API (via `rninja_api_token.txt`).
  - Local inputs (`regions.csv`, `time.csv`, `end_use_demands.csv`, etc.).
- **Current Preprocessing Steps**: 
  - Fetching from StatCan API, unzipping and filtering.
  - Parsing AEO excel workbook, mapping indices.
  - Fetching GDP projections and normalizing to base year.
  - Querying Renewables Ninja for weather and capacity factors.
- **Intermediate Datasets Created**: 
  - Local cache directory (`data_cache/` containing `.csv` files).
- **Final Outputs**: 
  - SQLite database for the commercial sector.
- **Candidate Bronze Sources**: 
  - StatCan tables.
  - AEO Commercial datasets.
  - Renewables Ninja data.
  - GDP Projections.
- **Candidate Silver Datasets**: 
  - Cleaned AEO commercial equipment data.
  - Normalized GDP projections.
  - Cleaned Renewables Ninja commercial capacity factors.
- **Migration Risk Level**: High
- **Shared Sources**: StatCan, Renewables Ninja, AEO.

## 3. Electricity (`canoe-electricity`)

- **Input Sources**: 
  - ATB master workbook (downloaded via `urllib.request`).
  - CODERS API (for generator data, using API key).
  - Local inputs (`commodities.csv`, `regions.csv`, etc.).
- **Current Preprocessing Steps**: 
  - Downloading ATB.
  - Querying CODERS API and extracting generator technical and cost parameters.
  - Currency conversion and inflation adjustments.
- **Intermediate Datasets Created**: 
  - Cached CSV files for CODERS data and the ATB master workbook in `data_cache/`.
- **Final Outputs**: 
  - SQLite database for the electricity sector.
- **Candidate Bronze Sources**: 
  - ATB master tables.
  - CODERS API database.
- **Candidate Silver Datasets**: 
  - Cleaned CODERS generator data.
  - Extracted ATB technical and economic parameters.
- **Migration Risk Level**: High
- **Shared Sources**: CODERS, ATB.

## 4. Residential (`canoe-residential`)

- **Input Sources**: 
  - StatCan API (Population tables: 17100009, 17100057).
  - AEO excel workbook (`rsmess.xlsx`).
  - Renewables Ninja API.
  - Local inputs.
- **Current Preprocessing Steps**: 
  - Fetching population projections from StatCan and interpolating for missing regions.
  - Parsing AEO residential equipment workbook (`RSCLASS`, `RSMEQP` sheets).
  - Querying Renewables Ninja for capacity factors.
- **Intermediate Datasets Created**: 
  - Local cache directory (`data_cache/` containing `.csv` files).
- **Final Outputs**: 
  - SQLite database for the residential sector.
- **Candidate Bronze Sources**: 
  - StatCan population tables.
  - AEO Residential datasets.
  - Renewables Ninja data.
- **Candidate Silver Datasets**: 
  - Processed residential population projections.
  - Cleaned AEO residential equipment lists.
  - Cleaned Renewables Ninja capacity factors.
- **Migration Risk Level**: High
- **Shared Sources**: StatCan, Renewables Ninja, AEO.

## 5. Industry (`canoe-industry`)

- **Input Sources**: 
  - NRCan datasets (fetched via `data_scraper.py`).
  - StatCan zip file `25100029-eng.zip` (fetched via `statcan.py`).
  - Local inputs.
- **Current Preprocessing Steps**: 
  - Downloading and extracting StatCan CSVs, filtering by industrial subsectors.
  - Scraping NRCan HTML tables to build initial industrial demand data frames.
- **Intermediate Datasets Created**: 
  - Pickled cache files (`statcan_atl.pkl`, NRCan cache).
- **Final Outputs**: 
  - SQLite database containing industry-specific demands and parameters.
- **Candidate Bronze Sources**: 
  - StatCan Table 25-10-0029.
  - NRCan Industry data.
- **Candidate Silver Datasets**: 
  - Cleaned StatCan ATL shares for industry.
  - Cleaned NRCan industrial energy usage.
- **Migration Risk Level**: Medium
- **Shared Sources**: StatCan, NRCan.

## 6. Fuel (`canoe-fuel`)

- **Input Sources**: 
  - EIA API for AEO table 3.
  - Local inputs (`input/fuel_list.csv`).
- **Current Preprocessing Steps**: 
  - Fetching data from the EIA API via `requests.get`.
- **Intermediate Datasets Created**: 
  - Pickled dataframes in `cache/dataframes.pkl`.
- **Final Outputs**: 
  - SQLite database.
- **Candidate Bronze Sources**: 
  - EIA AEO tables.
- **Candidate Silver Datasets**: 
  - Processed EIA AEO fuel tables.
- **Migration Risk Level**: Low
- **Shared Sources**: EIA.

## 7. Canada's Energy Future (CEF) (`canoe-cef`)

- **Input Sources**: 
  - Local static CSV files (`end-use-demand-2023.csv`, `dsd_electricity.csv`).
- **Current Preprocessing Steps**: 
  - Parsing the CEF dataset.
  - Filtering by scenario, sector, region, and commodity.
  - Mapping CEF indices to CANOE indices.
  - Creating time segment fractions (DSD).
- **Intermediate Datasets Created**: 
  - Handled in memory.
- **Final Outputs**: 
  - SQLite database representing the CEF sector parameters.
- **Candidate Bronze Sources**: 
  - CEF `end-use-demand-2023.csv`.
- **Candidate Silver Datasets**: 
  - Cleaned CEF end-use demands.
  - Processed DSD tables.
- **Migration Risk Level**: Low
- **Shared Sources**: None (Though some mapping files are shared).
