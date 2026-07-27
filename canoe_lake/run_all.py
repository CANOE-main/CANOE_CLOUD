import logging
import sys
import traceback
from dotenv import load_dotenv
load_dotenv('../.env')

from canoe_lake.catalog import init_catalog
from canoe_lake.bronze import ingest_bronze, INGESTORS
from canoe_lake.silver import build_silver, SILVER_TRANSFORMERS

import canoe_lake.ingestors
import canoe_lake.transformers

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def run_all():
    logger.info("Starting master orchestration script for CANOE Data Lake...")
    
    logger.info("--- Step 1: Initializing Catalog ---")
    try:
        init_catalog()
    except Exception as e:
        logger.error(f"Catalog initialization failed: {e}")
        sys.exit(1)
        
    logger.info("--- Step 2: Running Bronze Ingestion ---")
    bronze_sources = list(INGESTORS.keys())
    for source in bronze_sources:
        logger.info(f"Ingesting Bronze source: {source}")
        try:
            ingest_bronze(source)
        except Exception as e:
            logger.error(f"Failed to ingest {source}: {e}")
            traceback.print_exc()
            
    logger.info("--- Step 3: Running Silver Transformations ---")
    silver_datasets = list(SILVER_TRANSFORMERS.keys())
    for dataset in silver_datasets:
        logger.info(f"Building Silver dataset: {dataset}")
        try:
            build_silver(dataset)
        except Exception as e:
            logger.error(f"Failed to build {dataset}: {e}")
            traceback.print_exc()
            
    logger.info("Master orchestration script completed.")

if __name__ == "__main__":
    run_all()
