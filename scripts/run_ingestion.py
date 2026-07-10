import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion import db_loader, parser, qc_filter


def main(max_floats: int = 0) -> None:
    """
    Runs the full local-file ingestion pipeline for `.nc` files in `data/raw/`.

    Args:
        max_floats: Maximum number of floats to ingest. 0 means all.

    Side effects:
        Reads NetCDF files, writes validated rows to PostgreSQL and Parquet, and prints progress.
    """
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        raise SystemExit("data/raw/ directory does not exist.")

    nc_files = sorted(raw_dir.glob("*.nc"))
    if not nc_files:
        print("No .nc files found in data/raw/. Nothing to ingest.")
        return

    # Check already loaded float IDs to make ingestion resumeable and idempotent
    from db.connection import get_engine
    from sqlalchemy import text
    engine = get_engine()
    existing_floats = set()
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT DISTINCT float_id FROM argo_profiles"))
            existing_floats = {row[0] for row in res.fetchall()}
            print(f"Found {len(existing_floats)} existing floats already in database.")
    except Exception as e:
        print(f"Could not check existing floats: {e}. Proceeding.")

    total_rows = 0
    floats_ingested = 0

    for filepath in nc_files:
        if max_floats > 0 and floats_ingested >= max_floats:
            print(f"Reached max_floats limit ({max_floats}). Stopping.")
            break

        float_id = filepath.name.split("_")[0]
        if float_id in existing_floats:
            print(f"{filepath.name}: Float {float_id} already loaded. Skipping.")
            continue

        try:
            df, dataset = parser.parse_netcdf(str(filepath))
            clean_df = qc_filter.apply_qc(df, dataset)
            dataset.close()

            db_loader.save_to_postgres(clean_df)
            db_loader.save_to_parquet(clean_df)

            print(f"{filepath.name}: {len(df)} raw -> {len(clean_df)} after QC")
            total_rows += len(clean_df)
            floats_ingested += 1
        except Exception as e:
            print(f"ERROR processing {filepath.name}: {e}. Skipping.")
            continue

    print(f"Total new rows ingested: {total_rows} ({floats_ingested} floats)")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(max_floats=limit)
