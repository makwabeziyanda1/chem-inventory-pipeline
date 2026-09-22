import csv
from pathlib import Path

import duckdb
import pytest

from pipeline.run import run

CHEMICAL_FIELDS = ["name", "cas_number", "hazard_class", "unit_of_measure"]
SUPPLIER_FIELDS = ["name", "contact_email"]
LOCATION_FIELDS = ["name", "site"]
DELIVERY_FIELDS = ["date", "chemical_name", "cas_number", "supplier_name", "location_name",
                    "quantity", "unit_of_measure", "batch_number", "expiry_date"]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _seed_reference(raw_dir: Path) -> None:
    _write_csv(raw_dir / "reference" / "chemicals.csv", CHEMICAL_FIELDS, [
        {"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"},
    ])
    _write_csv(raw_dir / "reference" / "suppliers.csv", SUPPLIER_FIELDS, [
        {"name": "Acme Labs", "contact_email": "orders@acmelabs.test"},
    ])
    _write_csv(raw_dir / "reference" / "lab_locations.csv", LOCATION_FIELDS, [
        {"name": "Main QC Lab", "site": "Coal Mine Site A"},
    ])


def test_run_loads_valid_rows_and_rejects_invalid_ones(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    _seed_reference(raw_dir)
    _write_csv(raw_dir / "deliveries_2026-01-01.csv", DELIVERY_FIELDS, [
        {"date": "2026-01-01", "chemical_name": "Toluene", "cas_number": "108-88-3",
         "supplier_name": "Acme Labs", "location_name": "Main QC Lab", "quantity": "10",
         "unit_of_measure": "L", "batch_number": "BN1", "expiry_date": "2027-01-01"},
        {"date": "2026-01-01", "chemical_name": "", "cas_number": "108-88-3",
         "supplier_name": "Acme Labs", "location_name": "Main QC Lab", "quantity": "5",
         "unit_of_measure": "L", "batch_number": "BN2", "expiry_date": "2027-01-01"},
    ])

    db_path = str(tmp_path / "warehouse.duckdb")
    summary = run(raw_dir, db_path)

    assert summary == {"loaded": 1, "rejected": 1}
    con = duckdb.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM rejected_records").fetchone()[0] == 1
    con.close()


def test_run_with_only_corrupted_rows_loads_nothing(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    _seed_reference(raw_dir)
    _write_csv(raw_dir / "deliveries_2026-01-01.csv", DELIVERY_FIELDS, [
        {"date": "2026-01-01", "chemical_name": "", "cas_number": "108-88-3",
         "supplier_name": "Acme Labs", "location_name": "Main QC Lab", "quantity": "-1",
         "unit_of_measure": "L", "batch_number": "BN1", "expiry_date": "2027-01-01"},
    ])

    db_path = str(tmp_path / "warehouse.duckdb")
    summary = run(raw_dir, db_path)

    assert summary == {"loaded": 0, "rejected": 1}


def test_run_is_idempotent_when_rerun_on_same_raw_dir(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    _seed_reference(raw_dir)
    _write_csv(raw_dir / "deliveries_2026-01-01.csv", DELIVERY_FIELDS, [
        {"date": "2026-01-01", "chemical_name": "Toluene", "cas_number": "108-88-3",
         "supplier_name": "Acme Labs", "location_name": "Main QC Lab", "quantity": "10",
         "unit_of_measure": "L", "batch_number": "BN1", "expiry_date": "2027-01-01"},
    ])

    db_path = str(tmp_path / "warehouse.duckdb")
    run(raw_dir, db_path)
    run(raw_dir, db_path)

    con = duckdb.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 1
    con.close()


def test_run_with_missing_reference_data_raises_clear_error(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        run(raw_dir, str(tmp_path / "warehouse.duckdb"))
