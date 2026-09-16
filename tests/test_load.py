import duckdb
import pytest

from pipeline.ingest import ReferenceData
from pipeline.load import init_schema, load_reference_data, load_rejected_records, load_transactions

REFERENCE = ReferenceData(
    chemicals=[
        {"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"},
    ],
    suppliers=[
        {"name": "Acme Labs", "contact_email": "orders@acmelabs.test"},
    ],
    lab_locations=[
        {"name": "Main QC Lab", "site": "Coal Mine Site A"},
    ],
)

RECEIPT_ROW = {
    "source_file": "deliveries_2026-01-01.csv", "date": "2026-01-01",
    "chemical_name": "Toluene", "cas_number": "108-88-3", "supplier_name": "Acme Labs",
    "location_name": "Main QC Lab", "movement_type": "RECEIPT", "quantity": 10.0,
    "unit_of_measure": "L", "batch_number": "BN260101001", "expiry_date": "2027-01-01",
    "notes": "",
}

USAGE_ROW = {
    "source_file": "usage_2026-01-01.csv", "date": "2026-01-01",
    "chemical_name": "Toluene", "cas_number": "108-88-3", "supplier_name": "",
    "location_name": "Main QC Lab", "movement_type": "USAGE", "quantity": -1.5,
    "unit_of_measure": "L", "batch_number": "BN251201007", "expiry_date": "", "notes": "",
}


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")
    init_schema(connection)
    yield connection
    connection.close()


def test_init_schema_creates_all_tables(con):
    tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    assert tables == {
        "dim_chemical", "dim_supplier", "dim_lab_location", "dim_date",
        "stock_movements", "rejected_records",
    }


def test_load_reference_data_inserts_rows(con):
    load_reference_data(con, REFERENCE)
    assert con.execute("SELECT name FROM dim_chemical").fetchone()[0] == "Toluene"
    assert con.execute("SELECT name FROM dim_supplier").fetchone()[0] == "Acme Labs"
    assert con.execute("SELECT site FROM dim_lab_location").fetchone()[0] == "Coal Mine Site A"


def test_load_reference_data_is_idempotent(con):
    load_reference_data(con, REFERENCE)
    load_reference_data(con, REFERENCE)
    assert con.execute("SELECT COUNT(*) FROM dim_chemical").fetchone()[0] == 1


def test_load_transactions_resolves_dimension_ids(con):
    load_reference_data(con, REFERENCE)
    load_transactions(con, [RECEIPT_ROW])

    row = con.execute("""
        SELECT c.name, s.name, l.name, d.full_date, m.quantity, m.movement_type
        FROM stock_movements m
        JOIN dim_chemical c ON c.chemical_id = m.chemical_id
        JOIN dim_supplier s ON s.supplier_id = m.supplier_id
        JOIN dim_lab_location l ON l.location_id = m.location_id
        JOIN dim_date d ON d.date_id = m.date_id
    """).fetchone()

    assert row[0] == "Toluene"
    assert row[1] == "Acme Labs"
    assert row[2] == "Main QC Lab"
    assert str(row[3]) == "2026-01-01"
    assert row[4] == 10.0
    assert row[5] == "RECEIPT"


def test_load_transactions_usage_row_has_no_supplier(con):
    load_reference_data(con, REFERENCE)
    load_transactions(con, [USAGE_ROW])
    supplier_id = con.execute("SELECT supplier_id FROM stock_movements").fetchone()[0]
    assert supplier_id is None


def test_load_transactions_is_idempotent_per_source_file(con):
    load_reference_data(con, REFERENCE)
    load_transactions(con, [RECEIPT_ROW])
    load_transactions(con, [RECEIPT_ROW])
    count = con.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE source_file = ?", [RECEIPT_ROW["source_file"]]
    ).fetchone()[0]
    assert count == 1


def test_load_transactions_unknown_chemical_raises(con):
    load_reference_data(con, REFERENCE)
    bad_row = {**RECEIPT_ROW, "cas_number": "0000-00-0"}
    with pytest.raises(ValueError):
        load_transactions(con, [bad_row])


def test_load_rejected_records_is_idempotent_per_source_file(con):
    rejected = [{"source_file": "deliveries_2026-01-01.csv", "raw_row": "{...}", "reason": "missing chemical_name"}]
    load_rejected_records(con, rejected)
    load_rejected_records(con, rejected)
    count = con.execute("SELECT COUNT(*) FROM rejected_records").fetchone()[0]
    assert count == 1
