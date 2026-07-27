import argparse
import sys
import logging
import os
import getpass
from dotenv import load_dotenv
from canoe_lake.catalog import init_catalog
from canoe_lake.bronze import ingest_bronze, register_manual_bronze
from canoe_lake.silver import build_silver
import canoe_lake.ingestors  # Loads the ingestor registry
import canoe_lake.transformers # Loads the silver transformers

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def main():
    # Load environment variables from .env
    load_dotenv()
    
    # Check User Identity
    canoe_user = os.environ.get("CANOE_USER")
    if not canoe_user:
        try:
            canoe_user = getpass.getuser()
            os.environ["CANOE_USER"] = canoe_user
            logger.info(f"CANOE_USER not set in .env. Falling back to system user: {canoe_user}")
        except Exception:
            logger.error("CANOE_USER must be set in .env file (and could not be inferred from system).")
            sys.exit(1)
            
    parser = argparse.ArgumentParser(description="CANOE Data Lake Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # catalog command
    catalog_parser = subparsers.add_parser("catalog", help="Manage the DuckDB catalog")
    catalog_subparsers = catalog_parser.add_subparsers(dest="catalog_command", help="Catalog commands")
    init_parser = catalog_subparsers.add_parser("init", help="Initialize the catalog and apply migrations")

    # bronze command
    bronze_parser = subparsers.add_parser("bronze", help="Manage Bronze layer")
    bronze_subparsers = bronze_parser.add_subparsers(dest="bronze_command", help="Bronze commands")
    
    ingest_parser = bronze_subparsers.add_parser("ingest", help="Ingest a raw data source")
    ingest_parser.add_argument("source", help="The name of the source to ingest")

    manual_parser = bronze_subparsers.add_parser("register-manual", help="Register a manually downloaded file")
    manual_parser.add_argument("--source", required=True, help="The name of the source")
    manual_parser.add_argument("--file", required=True, help="Path to the manually gathered file")
    manual_parser.add_argument("--collection-date", required=True, help="Collection date (YYYY-MM-DD)")
    manual_parser.add_argument("--doc-id", help="Document title or ID")
    manual_parser.add_argument("--pub-date", help="Publication date (YYYY-MM-DD)")
    manual_parser.add_argument("--notes", help="Description/notes")

    # silver command
    silver_parser = subparsers.add_parser("silver", help="Manage Silver layer")
    silver_subparsers = silver_parser.add_subparsers(dest="silver_command", help="Silver commands")
    
    build_parser = silver_subparsers.add_parser("build", help="Build a silver dataset from bronze")
    build_parser.add_argument("dataset", help="The name of the dataset to build (e.g., eia_table3)")

    args = parser.parse_args()

    if args.command == "catalog":
        if args.catalog_command == "init":
            try:
                init_catalog()
                logger.info("Catalog initialization complete.")
            except Exception as e:
                logger.error(f"Failed to initialize catalog: {e}")
                sys.exit(1)
        else:
            catalog_parser.print_help()
    elif args.command == "bronze":
        if args.bronze_command == "ingest":
            ingest_bronze(args.source)
        elif args.bronze_command == "register-manual":
            register_manual_bronze(
                source_name=args.source,
                file_path=args.file,
                collection_date=args.collection_date,
                doc_id=args.doc_id,
                pub_date=args.pub_date,
                notes=args.notes
            )
        else:
            bronze_parser.print_help()
    elif args.command == "silver":
        if args.silver_command == "build":
            build_silver(args.dataset)
        else:
            silver_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

