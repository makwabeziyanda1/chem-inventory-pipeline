"""Read raw delivery/usage/reference CSVs into a normalized in-memory shape.

No validation or business logic here — just parsing raw files into records
that validate.py can then check, each transaction row tagged with the
source file it came from for lineage.
"""
import csv
from dataclasses import dataclass
from pathlib import Path

TRANSACTION_FIELDS = [
    "source_file", "date", "chemical_name", "cas_number", "supplier_name",
    "location_name", "movement_type", "quantity", "unit_of_measure",
    "batch_number", "expiry_date", "notes",
]


@dataclass
class ReferenceData:
    chemicals: list[dict]
    suppliers: list[dict]
    lab_locations: list[dict]


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ingest_reference_data(raw_dir: Path) -> ReferenceData:
    ref_dir = Path(raw_dir) / "reference"
    return ReferenceData(
        chemicals=_read_csv(ref_dir / "chemicals.csv"),
        suppliers=_read_csv(ref_dir / "suppliers.csv"),
        lab_locations=_read_csv(ref_dir / "lab_locations.csv"),
    )


def _normalize_delivery_row(row: dict, source_file: str) -> dict:
    return {
        "source_file": source_file,
        "date": row["date"],
        "chemical_name": row["chemical_name"],
        "cas_number": row["cas_number"],
        "supplier_name": row["supplier_name"],
        "location_name": row["location_name"],
        "movement_type": "RECEIPT",
        "quantity": row["quantity"],
        "unit_of_measure": row["unit_of_measure"],
        "batch_number": row["batch_number"],
        "expiry_date": row["expiry_date"],
        "notes": "",
    }


def _normalize_usage_row(row: dict, source_file: str) -> dict:
    return {
        "source_file": source_file,
        "date": row["date"],
        "chemical_name": row["chemical_name"],
        "cas_number": row["cas_number"],
        "supplier_name": "",
        "location_name": row["location_name"],
        "movement_type": row["movement_type"],
        "quantity": row["quantity"],
        "unit_of_measure": row["unit_of_measure"],
        "batch_number": row["batch_number"],
        "expiry_date": "",
        "notes": row["notes"],
    }


def ingest_transactions(raw_dir: Path) -> list[dict]:
    raw_dir = Path(raw_dir)
    rows = []
    for path in sorted(raw_dir.glob("deliveries_*.csv")):
        rows.extend(_normalize_delivery_row(r, path.name) for r in _read_csv(path))
    for path in sorted(raw_dir.glob("usage_*.csv")):
        rows.extend(_normalize_usage_row(r, path.name) for r in _read_csv(path))
    return rows
