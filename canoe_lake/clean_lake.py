import shutil
import sys
from pathlib import Path

def clean_lake():
    print("=====================================================")
    print("WARNING: You are about to wipe the CANOE Data Lake!")
    print("=====================================================")
    print("This will delete:")
    print("  - ALL downloaded raw data (Bronze layer)")
    print("  - ALL transformed Parquet datasets (Silver layer)")
    print("  - The DuckDB Database Catalog")
    print("\nIf you do this, running run_all.py will take 6+ hours to re-download everything from scratch.")
    print("NOTE: You do NOT need to run this if you just want to resume a crashed run.")
    
    confirm = input("\nAre you absolutely sure you want to delete everything? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted. Nothing was deleted.")
        sys.exit(0)

    lake_dir = Path(__file__).resolve().parent.parent / "data-lake"
    if not lake_dir.exists():
        print(f"Data Lake directory not found at {lake_dir}")
        sys.exit(0)

    for sub in ["bronze", "silver", "catalog"]:
        target = lake_dir / sub
        if target.exists():
            print(f"Deleting {target}...")
            shutil.rmtree(target)
            
    print("Data Lake cache cleared successfully! You are now starting from a blank slate.")

if __name__ == "__main__":
    clean_lake()
