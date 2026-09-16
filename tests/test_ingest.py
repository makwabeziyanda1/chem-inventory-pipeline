import csv
from pathlib import Path

from pipeline.ingest import ingest_reference_data, ingest_transactions


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_ingest_reference_data_reads_all_three_files(tmp_path: Path):
    ref_dir = tmp_path / "reference"
    _write_csv(ref_dir / "chemicals.csv", ["name", "cas_number", "hazard_class", "unit_of_measure"],
               [{"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"}])
    _write_csv(ref_dir / "suppliers.csv", ["name", "contact_email"],
               [{"name": "Acme Labs", "contact_email": "orders@acmelabs.test"}])
    _write_csv(ref_dir / "lab_locations.csv", ["name", "site"],
               [{"name": "Main QC Lab", "site": "Coal Mine Site A"}])

    reference = ingest_reference_data(tmp_path)

    assert reference.chemicals == [{"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"}]
    assert reference.suppliers[0]["name"] == "Acme Labs"
    assert reference.lab_locations[0]["site"] == "Coal Mine Site A"


def test_ingest_transactions_tags_source_file_and_normalizes_shape(tmp_path: Path):
    delivery_fields = ["date", "chemical_name", "cas_number", "supplier_name", "location_name",
                        "quantity", "unit_of_measure", "batch_number", "expiry_date"]
    _write_csv(tmp_path / "deliveries_2026-01-01.csv", delivery_fields, [{
        "date": "2026-01-01", "chemical_name": "Toluene", "cas_number": "108-88-3",
        "supplier_name": "Acme Labs", "location_name": "Main QC Lab", "quantity": "10",
        "unit_of_measure": "L", "batch_number": "BN260101001", "expiry_date": "2027-01-01",
    }])

    usage_fields = ["date", "chemical_name", "cas_number", "location_name", "movement_type",
                     "quantity", "unit_of_measure", "batch_number", "notes"]
    _write_csv(tmp_path / "usage_2026-01-01.csv", usage_fields, [{
        "date": "2026-01-01", "chemical_name": "Toluene", "cas_number": "108-88-3",
        "location_name": "Main QC Lab", "movement_type": "USAGE", "quantity": "1.5",
        "unit_of_measure": "L", "batch_number": "BN251201007", "notes": "",
    }])

    rows = ingest_transactions(tmp_path)

    assert len(rows) == 2
    delivery_row = next(r for r in rows if r["movement_type"] == "RECEIPT")
    assert delivery_row["source_file"] == "deliveries_2026-01-01.csv"
    assert delivery_row["supplier_name"] == "Acme Labs"
    assert delivery_row["expiry_date"] == "2027-01-01"

    usage_row = next(r for r in rows if r["movement_type"] == "USAGE")
    assert usage_row["source_file"] == "usage_2026-01-01.csv"
    assert usage_row["supplier_name"] == ""
    assert usage_row["expiry_date"] == ""


def test_ingest_transactions_ignores_reference_directory(tmp_path: Path):
    _write_csv(tmp_path / "reference" / "chemicals.csv", ["name", "cas_number", "hazard_class", "unit_of_measure"],
               [{"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"}])

    rows = ingest_transactions(tmp_path)

    assert rows == []
