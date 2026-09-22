"""Wire ingest -> validate -> transform -> load into one end-to-end run."""
import argparse
from pathlib import Path

import duckdb

from pipeline.ingest import ingest_reference_data, ingest_transactions
from pipeline.load import init_schema, load_reference_data, load_rejected_records, load_transactions
from pipeline.transform import transform_transactions
from pipeline.validate import validate_transactions


def run(raw_dir: Path, db_path: str) -> dict:
    raw_dir = Path(raw_dir)
    reference = ingest_reference_data(raw_dir)
    rows = ingest_transactions(raw_dir)

    validation = validate_transactions(rows)
    transformed = transform_transactions(validation.valid, reference)

    con = duckdb.connect(db_path)
    try:
        init_schema(con)
        load_reference_data(con, reference)
        load_transactions(con, transformed)
        load_rejected_records(con, validation.rejected)
    finally:
        con.close()

    return {"loaded": len(transformed), "rejected": len(validation.rejected)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw", help="directory of raw CSVs to ingest")
    parser.add_argument("--db-path", default="warehouse.duckdb", help="DuckDB file to load into")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary = run(Path(args.raw_dir), args.db_path)
    print(f"Loaded {summary['loaded']} movements, rejected {summary['rejected']} rows.")
