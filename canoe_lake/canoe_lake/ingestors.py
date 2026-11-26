import os
import json
import logging
import requests
from pathlib import Path
from canoe_lake.bronze import register_ingestor
from canoe_lake.rninja_ingestor import ingest_renewables_ninja

import yaml

logger = logging.getLogger(__name__)

def get_config():
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}
@register_ingestor("eia")
def ingest_eia(output_dir: Path) -> dict:
    """Ingests EIA AEO table 3."""
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        raise ValueError("EIA_API_KEY not found in environment.")

    cfg = get_config().get("eia", {})
    year = cfg.get("year", 2025)
    scenario = cfg.get("scenario", "ref2025")
    base_url = (
        f"https://api.eia.gov/v2/aeo/{year}/data/?frequency=annual&data[0]=value"
        f"&facets[regionId][]=1-0&facets[scenario][]={scenario}&facets[tableId][]=3"
        "&start=2023&end=2050&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000"
    )
    
    logger.info(f"Requesting EIA data from: {base_url}")
    resp = requests.get(base_url, params={'api_key': api_key}, timeout=60)
    resp.raise_for_status()
    
    data = resp.json()
    file_path = output_dir / "eia_aeo_table3.json"
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    return {
        "file_path": str(file_path),
        "source_type": "api",
        "source_url_or_doc_id": base_url,
        "file_format": "json",
        "notes": f"EIA AEO {year} Table 3"
    }

@register_ingestor("coders")
def ingest_coders(output_dir: Path) -> dict:
    """Ingests CODERS reference data.
    
    For a full data lake snapshot, we download several key endpoints.
    """
    api_key = os.environ.get("CODERS_API_KEY")
    if not api_key:
        raise ValueError("CODERS_API_KEY not found in environment.")

    coders_root = "https://api.sesit.ca/"
    endpoints = [
        "generators",
        "storage",
        "transmission_losses",
        "reserve_requirements",
        "interface_capacities",
        "generation_generic",
        "interprovincial_transfers",
        "international_transfers",
        "historic_and_forecasted_annual_energy_demand",
        "provincial_demand"
    ]
    
    snapshot = {}
    for ep in endpoints:
        logger.info(f"Fetching CODERS endpoint: {ep}")
        try:
            # Add parameters like year=2025 if needed, but we pull base for now
            url = f"{coders_root}{ep}?key={api_key}"
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                snapshot[ep] = resp.json()
            else:
                logger.warning(f"Failed to fetch {ep}: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Exception fetching {ep}: {e}")

    file_path = output_dir / "coders_snapshot.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f)

    return {
        "file_path": str(file_path),
        "source_type": "api",
        "source_url_or_doc_id": coders_root,
        "file_format": "json",
        "notes": "Full CODERS database snapshot"
    }

@register_ingestor("statcan")
def ingest_statcan(output_dir: Path) -> dict:
    """Ingests StatCan Tables: 25-10-0029, 17-10-0009, 17-10-0057, 38-10-0048."""
    tables = ["25100029", "17100009", "17100057", "38100048"]
    
    # StatCan blocks default python-requests user agents.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for tbl in tables:
        url = f"https://www150.statcan.gc.ca/n1/tbl/csv/{tbl}-eng.zip"
        logger.info(f"Downloading StatCan data from {url}")
        
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        
        file_path = output_dir / f"{tbl}-eng.zip"
        with open(file_path, "wb") as f:
            f.write(resp.content)
            
    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "multiple_statcan_tables",
        "file_format": "dir",
        "notes": "StatCan Tables 25-10-0029, 17-10-0009, 17-10-0057, 38-10-0048"
    }

@register_ingestor("cer")
def ingest_cer(output_dir: Path) -> dict:
    """Ingests CER Macro-Indicators CSV."""
    year = get_config().get("cer", {}).get("year", 2023)
    url = f"https://www.cer-rec.gc.ca/open/energy/energyfutures{year}/macro-indicators-{year}.csv"
    logger.info(f"Downloading CER data from {url}")
    
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    
    file_path = output_dir / "macro-indicators-2023.csv"
    with open(file_path, "wb") as f:
        f.write(resp.content)
        
    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "csv",
        "notes": "CER Macro-Indicators 2023"
    }

@register_ingestor("nrcan")
def ingest_nrcan(output_dir: Path) -> dict:
    """Ingests NRCan Comprehensive Energy Use Database HTML tables and Handbook Excel files."""
    import time
    
    url = "https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/showTable.cfm"
    PROV_CODES = ['on', 'ab', 'qc', 'bct', 'mb', 'sk', 'atl']
    cfg = get_config().get("nrcan", {})
    YEAR = cfg.get("year", 2022)
    HANDBOOK_YEAR = cfg.get("handbook_year", 2021)
    
    # We need agr (1), agg (2..12), com (1, 24, 32), res (3, 4, 8, 10, 13, 14, 21, 26, 27, 28, 31)
    requests_to_make = [
        ("agr", 1),
        *[( "agg", rn ) for rn in range(2, 13)],
        *[( "com", rn ) for rn in [1, 24, 32]],
        *[( "res", rn ) for rn in [3, 4, 8, 10, 13, 14, 21, 26, 27, 28, 31]]
    ]
    
    results = {}
    
    sess = requests.Session()
    sess.headers.update({"User-Agent": "canoe-etl/1.0"})
    
    for sector, rn in requests_to_make:
        if sector not in results:
            results[sector] = {}
        results[sector][str(rn)] = {}
        
        for code in PROV_CODES:
            params = {
                "type": "CP",
                "sector": sector,
                "juris": code,
                "year": YEAR,
                "rn": rn,
                "page": "0",
            }
            logger.info(f"Downloading NRCan HTML for sector={sector}, rn={rn}, juris={code}, year={YEAR}")
            r = sess.get(url, params=params, timeout=45)
            r.raise_for_status()
            results[sector][str(rn)][code] = r.text
            time.sleep(0.5) # Be polite
            
    file_path_json = output_dir / "nrcan_html.json"
    with open(file_path_json, "w", encoding="utf-8") as f:
        json.dump(results, f)
        
    # Download res_00_16_e.xls handbook file
    # Note: If a link is broken, the user can configure a different year for the handbook in config.yaml
    handbook_url = f"https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/data_e/downloads/handbook/Excel/{HANDBOOK_YEAR}/res_00_16_e.xls"
    logger.info(f"Downloading NRCan Handbook {handbook_url}")
    r_hb = sess.get(handbook_url, timeout=45)
    r_hb.raise_for_status()
    file_path_xls = output_dir / "res_00_16_e.xls"
    with open(file_path_xls, "wb") as f:
        f.write(r_hb.content)
        
    return {
        "file_path": str(output_dir), # return the dir because we have multiple files
        "source_type": "url",
        "source_url_or_doc_id": "multiple_nrcan_urls",
        "file_format": "dir",
        "notes": f"NRCan HTML tables for year {YEAR} and handbook"
    }

# Register the imported rninja ingestor
register_ingestor("renewables_ninja")(ingest_renewables_ninja)

@register_ingestor("oedi_stock")
def ingest_oedi_stock(output_dir: Path) -> dict:
    import requests
    states = ['MI', 'MT', 'WA', 'ME', 'ND']
    
    cfg = get_config().get("oedi", {})
    year = cfg.get("year", 2024)
    c_release = cfg.get("comstock_release", "comstock_amy2018_release_2")
    c_up = cfg.get("comstock_upgrade", 39)
    
    # ComStock (up39)
    buildings = [
        'fullservicerestaurant', 'hospital', 'largehotel', 'largeoffice', 'mediumoffice', 
        'outpatient', 'primaryschool', 'quickservicerestaurant', 'retailstandalone', 
        'retailstripmall', 'secondaryschool', 'smallhotel', 'smalloffice', 'warehouse'
    ]
    for st in states:
        for bldg in buildings:
            file_path = output_dir / f"up{c_up}-{st.lower()}-{bldg}.csv"
            # Resume capability: skip if already downloaded (files are typically >1MB)
            if file_path.exists() and file_path.stat().st_size > 100000:
                continue
                
            url = f"https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/{year}/{c_release}/timeseries_aggregates/by_state/upgrade={c_up}/state={st}/up{c_up}-{st.lower()}-{bldg}.csv"
            logger.info(f"Downloading {url}")
            try:
                r = requests.get(url, timeout=(15, 120))
                if r.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(r.content)
                else:
                    logger.warning(f"Failed to fetch {url}: {r.status_code}")
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                
    r_release = cfg.get("resstock_release", "resstock_amy2018_release_2")
    r_up = cfg.get("resstock_upgrade", 16)
    
    # ResStock (up16)
    housing_files = [
        'mobile_home', 'multi-family_with_5plus_units', 
        'single-family_attached', 'single-family_detached'
    ]
    for st in states:
        for h in housing_files:
            file_path = output_dir / f"up{r_up}-{st.lower()}-{h}.csv"
            if file_path.exists() and file_path.stat().st_size > 100000:
                continue
                
            url = f"https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/{year}/{r_release}/timeseries_aggregates/by_state/upgrade={r_up}/state={st}/up{r_up}-{st.lower()}-{h}.csv"
            logger.info(f"Downloading {url}")
            try:
                r = requests.get(url, timeout=(15, 120))
                if r.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(r.content)
                else:
                    logger.warning(f"Failed to fetch {url}: {r.status_code}")
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "oedi_data_lake_s3",
        "file_format": "dir",
        "notes": "OEDI ComStock up39 and ResStock up16"
    }

@register_ingestor("ieso")
def ingest_ieso(output_dir: Path) -> dict:
    import requests
    from datetime import date
    weather_year = get_config().get("ieso", {}).get("weather_year", 2023)
    
    # PUB_GenOutputbyFuelHourly
    url_hourly = f"http://reports.ieso.ca/public/GenOutputbyFuelHourly/PUB_GenOutputbyFuelHourly_{weather_year}.xml"
    r = requests.get(url_hourly, timeout=45)
    if r.status_code == 200:
        with open(output_dir / f"PUB_GenOutputbyFuelHourly_{weather_year}.xml", "wb") as f:
            f.write(r.content)

    # PUB_GenOutputCapabilityMonth
    for m in range(1, 13):
        mm = f"{m:02d}"
        url_mon = f"http://reports.ieso.ca/public/GenOutputCapabilityMonth/PUB_GenOutputCapabilityMonth_{weather_year}{mm}.csv"
        r = requests.get(url_mon, timeout=45)
        if r.status_code == 200:
            with open(output_dir / f"PUB_GenOutputCapabilityMonth_{weather_year}{mm}.csv", "wb") as f:
                f.write(r.content)

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "ieso_reports",
        "file_format": "dir",
        "notes": "IESO Hourly and Monthly Reports"
    }

@register_ingestor("atb")
def ingest_atb(output_dir: Path) -> dict:
    import requests
    cfg = get_config().get("atb", {})
    year = cfg.get("year", 2024)
    version = cfg.get("version", "v3.0.0")
    url = f"https://oedi-data-lake.s3.amazonaws.com/ATB/electricity/csv/{year}/{version}/ATBe.csv"
    r = requests.get(url, timeout=45)
    if r.status_code == 200:
        with open(output_dir / "ATBe.csv", "wb") as f:
            f.write(r.content)
            
    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "dir",
        "notes": "NREL ATB 2024"
    }

@register_ingestor("epa")
def ingest_epa(output_dir: Path) -> dict:
    import requests
    url = get_config().get("epa", {}).get("url", "https://www.epa.gov/system/files/other-files/2025-01/ghg-emission-factors-hub-2025.xlsx")
    r = requests.get(url, timeout=45)
    if r.status_code == 200:
        with open(output_dir / "ghg-emission-factors-hub-2025.xlsx", "wb") as f:
            f.write(r.content)
            
    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "dir",
        "notes": "EPA GHG Emission Factors 2025"
    }

# ---------------------------------------------------------------------------
# Transportation sector sources (bronze only). URLs, editions and pinned
# checksums follow canoe-transportation's config/sources.yaml.
# ---------------------------------------------------------------------------

def download_file(url: str, file_path: Path, sha256: str = None, md5: str = None, size: int = None,
                  session=None, params: dict = None, retries: int = 3) -> Path:
    """Downloads url to file_path and checks any pinned sha256, md5 or byte count.

    Raises ValueError when the download does not match a pin, so the ingest fails
    instead of registering a file that differs from the one transport validated.
    """
    import time
    import hashlib

    getter = session or requests
    for attempt in range(1, retries + 1):
        try:
            with getter.get(url, params=params, timeout=(15, 300), stream=True) as r:
                r.raise_for_status()
                h_sha256, h_md5 = hashlib.sha256(), hashlib.md5()
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                        h_sha256.update(chunk)
                        h_md5.update(chunk)
            break
        except requests.RequestException as e:
            if attempt == retries:
                raise
            logger.warning(f"Retrying {url} after error: {e}")
            time.sleep(attempt)

    actual_size = file_path.stat().st_size
    if size is not None and actual_size != size:
        raise ValueError(f"{file_path.name}: expected {size} bytes, got {actual_size} ({url})")
    if sha256 and h_sha256.hexdigest() != sha256:
        raise ValueError(f"{file_path.name}: sha256 {h_sha256.hexdigest()} does not match pinned {sha256} ({url})")
    if md5 and h_md5.hexdigest() != md5:
        raise ValueError(f"{file_path.name}: md5 {h_md5.hexdigest()} does not match pinned {md5} ({url})")
    return file_path

@register_ingestor("nrcan_ceud_transport")
def ingest_nrcan_ceud_transport(output_dir: Path) -> dict:
    """Ingests NRCan CEUD Transportation Sector Excel tables, every province separately plus Canada."""
    import time

    year = get_config().get("nrcan_ceud_transport", {}).get("year", 2023)
    base_url = f"https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/data_e/downloads/comprehensive/Excel/{year}"
    # Provinces are not merged here: NB, NS, PE and NL are each downloaded on their own.
    regions = ["ab", "bct", "mb", "nb", "nl", "ns", "on", "pe", "qc", "sk"]
    provincial_tables = [7, 14, 15, 17, 18, 19, 20, 21, 28, 29, 30, 31, 32, 34, 35, 36, 37]
    national_tables = [20, 21, 26, 27, 28]

    sess = requests.Session()
    sess.headers.update({"User-Agent": "canoe-etl/1.0"})

    files = [(region, tbl) for region in regions for tbl in provincial_tables]
    files += [("ca", tbl) for tbl in national_tables]
    for region, tbl in files:
        name = f"tran_{region}_e_{tbl}.xls"
        logger.info(f"Downloading NRCan CEUD {year} {name}")
        download_file(f"{base_url}/{name}", output_dir / name, session=sess)
        time.sleep(0.5)  # Be polite

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": base_url,
        "file_format": "dir",
        "notes": f"NRCan CEUD Transportation {year}: {len(provincial_tables)} tables for each of {', '.join(regions)}; national tables {', '.join(map(str, national_tables))}"
    }

@register_ingestor("nrcan_fcr")
def ingest_nrcan_fcr(output_dir: Path) -> dict:
    """Ingests NRCan Fuel Consumption Ratings CSVs (pinned English resources)."""
    files = get_config().get("nrcan_fcr", {}).get("files", [])
    for item in files:
        logger.info(f"Downloading NRCan Fuel Consumption Ratings from {item['url']}")
        download_file(item["url"], output_dir / item["name"], md5=item.get("md5"), size=item.get("bytes"))

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "multiple_nrcan_fcr_csvs",
        "file_format": "dir",
        "notes": f"NRCan Fuel Consumption Ratings: {', '.join(item['name'] for item in files)}"
    }

# Disabled: the page no longer matches transport's pin (only Drupal cache tokens differ) and no
# pinned copy exists elsewhere. Uncomment the decorator to ingest again once a matching copy is found.
# @register_ingestor("dunsky")
def ingest_dunsky(output_dir: Path) -> dict:
    """Ingests the Dunsky EV Charging Infrastructure for Canada report page (NRCan, Feb 2024)."""
    cfg = get_config().get("dunsky", {})
    url = cfg["url"]
    logger.info(f"Downloading Dunsky report page from {url}")
    file_path = download_file(url, output_dir / "electric-vehicle-charging-infrastructure-canada.html",
                              sha256=cfg.get("sha256"), size=cfg.get("bytes"))

    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "html",
        "notes": "Dunsky Electric Vehicle Charging Infrastructure for Canada, 2024 update"
    }

@register_ingestor("statcan_transport")
def ingest_statcan_transport(output_dir: Path) -> dict:
    """Ingests StatCan transport tables 20-10-0021, 20-10-0025, 23-10-0308, 34-10-0254, 23-10-0142 via WDS.

    Each full-table ZIP includes its own {pid}_MetaData.csv, so pinning the ZIP pins the metadata.
    The WDS cube metadata JSON is kept as an unpinned extra: it changes even when the data does not.
    """
    tables = ["20100021", "20100025", "23100308", "34100254", "23100142"]
    pins = get_config().get("statcan_transport", {}).get("pins", {})

    # StatCan blocks default python-requests user agents.
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })

    for tbl in tables:
        pin = pins.get(int(tbl), {})
        resp = sess.get(f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{tbl}/en", timeout=60)
        resp.raise_for_status()
        zip_url = resp.json()["object"]
        logger.info(f"Downloading StatCan table {tbl} from {zip_url}")
        download_file(zip_url, output_dir / f"{tbl}-eng.zip", sha256=pin.get("zip_sha256"), session=sess)

        resp = sess.post("https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata",
                         json=[{"productId": int(tbl)}], timeout=60)
        resp.raise_for_status()
        with open(output_dir / f"{tbl}-metadata.json", "wb") as f:
            f.write(resp.content)

    return {
        "file_path": str(output_dir),
        "source_type": "api",
        "source_url_or_doc_id": "multiple_statcan_tables",
        "file_format": "dir",
        "notes": "StatCan Tables 20-10-0021, 20-10-0025, 23-10-0308, 34-10-0254, 23-10-0142 with WDS cube metadata"
    }

@register_ingestor("ontario_mto")
def ingest_ontario_mto(output_dir: Path) -> dict:
    """Ingests Ontario Ministry of Transportation annual vehicle population ZIPs."""
    files = get_config().get("ontario_mto", {}).get("files", [])
    for item in files:
        logger.info(f"Downloading Ontario vehicle population {item['year']} from {item['url']}")
        download_file(item["url"], output_dir / f"{item['year']}_vehicle_population_data.zip", sha256=item.get("sha256"))

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "https://data.ontario.ca/dataset/vehicle-population-data",
        "file_format": "dir",
        "notes": f"Ontario MTO vehicle population data {', '.join(str(item['year']) for item in files)}"
    }

@register_ingestor("izev")
def ingest_izev(output_dir: Path) -> dict:
    """Ingests Transport Canada iZEV incentive CSVs and the data dictionary."""
    cfg = get_config().get("izev", {})
    files = cfg.get("files", [])
    for item in files:
        logger.info(f"Downloading iZEV data from {item['url']}")
        download_file(item["url"], output_dir / item["name"], md5=item.get("md5"), size=item.get("bytes"))
    download_file(cfg["dictionary_url"], output_dir / "izev-data-dictionary.pdf")

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "https://open.canada.ca/data/dataset/42986a95-be23-436e-af15-7c6bf292a2e1",
        "file_format": "dir",
        "notes": "Transport Canada iZEV November 2025 English snapshots and data dictionary"
    }

@register_ingestor("atb_transport")
def ingest_atb_transport(output_dir: Path) -> dict:
    """Ingests the NLR (NREL) Transportation ATB data ZIP."""
    url = get_config().get("atb_transport", {}).get("url", "https://atb.nlr.gov/img/other/2024_atb_transportation_data_v1.zip")
    logger.info(f"Downloading Transportation ATB from {url}")
    file_path = download_file(url, output_dir / url.rsplit("/", 1)[-1])

    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "zip",
        "notes": "NLR 2024 Transportation ATB v1"
    }

# Disabled: AFDC has added a field (ev_power_sharing) to every station record, so none of the pinned
# snapshots reproduce, including the historical-date ones. The lake keeps the copies registered on
# 2026-11-22. Uncomment the decorator to ingest again once matching copies (or new pins) are available.
# @register_ingestor("afdc")
def ingest_afdc(output_dir: Path) -> dict:
    """Ingests AFDC Canadian electric charging station snapshots from the NLR API."""
    api_key = os.environ.get("NLR_API_KEY", "DEMO_KEY")
    snapshots = get_config().get("afdc", {}).get("snapshots", [])
    for item in snapshots:
        logger.info(f"Requesting AFDC stations from {item['url']} with {item['query']}")
        download_file(item["url"], output_dir / item["name"], params={**item["query"], "api_key": api_key},
                      sha256=item.get("sha256"), size=item.get("bytes"))

    return {
        "file_path": str(output_dir),
        "source_type": "api",
        "source_url_or_doc_id": "https://developer.nlr.gov/api/alt-fuel-stations/",
        "file_format": "dir",
        "notes": f"AFDC Canadian electric stations: {', '.join(item['name'] for item in snapshots)}"
    }

@register_ingestor("nhtsa_cafe")
def ingest_nhtsa_cafe(output_dir: Path) -> dict:
    """Ingests NHTSA CAFE 2024 Final Rule Central Analysis inputs ZIP."""
    cfg = get_config().get("nhtsa_cafe", {})
    url = cfg["url"]
    logger.info(f"Downloading NHTSA CAFE inputs from {url}")
    file_path = download_file(url, output_dir / "Central_Analysis_Inputs.zip", sha256=cfg.get("sha256"), size=cfg.get("bytes"))

    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "zip",
        "notes": "NHTSA CAFE 2024-FRM-LD-2b3-2027-2035 Central Analysis inputs"
    }

@register_ingestor("nhts")
def ingest_nhts(output_dir: Path) -> dict:
    """Ingests FHWA NHTS 2022 V2.1 public-use CSVs, codebook, user guide and release notes."""
    files = get_config().get("nhts", {}).get("files", [])
    for item in files:
        logger.info(f"Downloading NHTS from {item['url']}")
        download_file(item["url"], output_dir / item["name"], sha256=item.get("sha256"), size=item.get("bytes"))

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "https://nhts.ornl.gov/",
        "file_format": "dir",
        "notes": "FHWA NHTS 2022 V2.1 public-use data and documentation"
    }

@register_ingestor("faa")
def ingest_faa(output_dir: Path) -> dict:
    """Ingests FAA Economic Values report sections 3 (capacity) and 4 (operating costs)."""
    files = get_config().get("faa", {}).get("files", [])
    for item in files:
        logger.info(f"Downloading FAA Economic Values from {item['url']}")
        download_file(item["url"], output_dir / item["name"], sha256=item.get("sha256"), size=item.get("bytes"))

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "https://www.faa.gov/regulations_policies/policy_guidance/benefit_cost",
        "file_format": "dir",
        "notes": "FAA Economic Values for Investment and Regulatory Decisions 2024, sections 3 and 4"
    }

@register_ingestor("fueleconomy")
def ingest_fueleconomy(output_dir: Path) -> dict:
    """Ingests the FuelEconomy.gov vehicles.csv.zip."""
    cfg = get_config().get("fueleconomy", {})
    url = cfg.get("url", "https://www.fueleconomy.gov/feg/epadata/vehicles.csv.zip")
    logger.info(f"Downloading FuelEconomy.gov vehicles from {url}")
    file_path = download_file(url, output_dir / "vehicles.csv.zip", sha256=cfg.get("sha256"), size=cfg.get("bytes"))

    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "zip",
        "notes": "FuelEconomy.gov Find a Car vehicle data"
    }

@register_ingestor("eia_nems")
def ingest_eia_nems(output_dir: Path) -> dict:
    """Ingests the EIA NEMS trnhdvx.xlsx transportation input workbook at a pinned commit."""
    cfg = get_config().get("eia_nems", {})
    url = cfg["url"]
    logger.info(f"Downloading EIA NEMS workbook from {url}")
    file_path = download_file(url, output_dir / "trnhdvx.xlsx", sha256=cfg.get("sha256"), size=cfg.get("bytes"))

    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "xlsx",
        "notes": "EIA NEMS input/tdm/trnhdvx.xlsx"
    }

@register_ingestor("epa_moves")
def ingest_epa_moves(output_dir: Path) -> dict:
    """Ingests EPA Population and Activity of Onroad Vehicles in MOVES6 (EPA-420-R-26-010)."""
    cfg = get_config().get("epa_moves", {})
    url = cfg["url"]
    logger.info(f"Downloading EPA MOVES6 report from {url}")
    file_path = download_file(url, output_dir / "420r26010.pdf", sha256=cfg.get("sha256"), size=cfg.get("bytes"))

    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "pdf",
        "notes": "EPA-420-R-26-010, August 2026"
    }

@register_ingestor("gcam")
def ingest_gcam(output_dir: Path) -> dict:
    """Ingests the JGCRI GCAM core UCD_trn_data_CORE.csv at a pinned commit."""
    cfg = get_config().get("gcam", {})
    url = cfg["url"]
    logger.info(f"Downloading GCAM UCD transportation data from {url}")
    file_path = download_file(url, output_dir / "UCD_trn_data_CORE.csv", sha256=cfg.get("sha256"), size=cfg.get("bytes"))

    return {
        "file_path": str(file_path),
        "source_type": "url",
        "source_url_or_doc_id": url,
        "file_format": "csv",
        "notes": "JGCRI GCAM core UCD transportation data"
    }

@register_ingestor("epri_regen")
def ingest_epri_regen(output_dir: Path) -> dict:
    """Ingests the EPRI US-REGEN v2025 transportation data module (the file transport parses).

    EPRI has republished the page and removed the pinned module, so it comes from its Wayback Machine
    capture, which matches transport's pin. The live page URL is recorded as the source.
    """
    cfg = get_config().get("epri_regen", {})
    logger.info(f"Downloading EPRI US-REGEN data module from {cfg['payload_url']}")
    download_file(cfg["payload_url"], output_dir / cfg["payload_url"].rsplit("/", 1)[-1],
                  sha256=cfg.get("payload_sha256"), size=cfg.get("payload_bytes"))

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": cfg["url"],
        "file_format": "dir",
        "notes": f"EPRI US-REGEN v2025 transportation JavaScript data module, from {cfg['payload_url']}"
    }

@register_ingestor("hatch")
def ingest_hatch(output_dir: Path) -> dict:
    """Ingests HATCH technology growth evidence from Zenodo records 10231865, 10056128 and 19579793."""
    files = get_config().get("hatch", {}).get("files", [])
    for item in files:
        logger.info(f"Downloading HATCH file from {item['url']}")
        download_file(item["url"], output_dir / item["name"], sha256=item.get("sha256"), size=item.get("bytes"))

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "multiple_zenodo_records",
        "file_format": "dir",
        "notes": "HATCH original (Zenodo 10231865, 10056128) and extended (Zenodo 19579793) files"
    }

# Disabled: EAFO has replaced the pinned page and CSVs with newer data and keeps no old versions.
# Uncomment the decorator to ingest again once a matching copy (or a replacement source) is found.
# @register_ingestor("eafo")
def ingest_eafo(output_dir: Path) -> dict:
    """Ingests EAFO Norway fleet, registrations and shares CSVs and their page."""
    import time

    files = get_config().get("eafo", {}).get("files", [])
    for item in files:
        logger.info(f"Downloading EAFO file from {item['url']}")
        download_file(item["url"], output_dir / item["name"], sha256=item.get("sha256"), size=item.get("bytes"))
        time.sleep(2)  # EAFO rate-limits rapid requests (HTTP 429)

    return {
        "file_path": str(output_dir),
        "source_type": "url",
        "source_url_or_doc_id": "https://alternative-fuels-observatory.ec.europa.eu/transport-mode/road/norway/vehicles-and-fleet",
        "file_format": "dir",
        "notes": "EAFO Norway M1/N1/N2-N3 fleet, new registrations and shares"
    }
