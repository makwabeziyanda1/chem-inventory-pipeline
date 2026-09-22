from datetime import date

import duckdb
import pytest

from pipeline.ingest import ReferenceData
from pipeline.load import init_schema, load_reference_data, load_transactions
from reports.print_summary import format_summary

REFERENCE = ReferenceData(
    chemicals=[{"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"}],
    suppliers=[{"name": "Acme Labs", "contact_email": "orders@acmelabs.test"}],
    lab_locations=[{"name": "Main QC Lab", "site": "Coal Mine Site A"}],
)

RECEIPT_ROW = {
    "source_file": "deliveries_2026-01-01.csv", "date": "2026-01-01",
    "chemical_name": "Toluene", "cas_number": "108-88-3", "supplier_name": "Acme Labs",
    "location_name": "Main QC Lab", "movement_type": "RECEIPT", "quantity": 10.0,
    "unit_of_measure": "L", "batch_number": "BN1", "expiry_date": "2026-02-01", "notes": "",
}


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")
    init_schema(connection)
    load_reference_data(connection, REFERENCE)
    load_transactions(connection, [RECEIPT_ROW])
    yield connection
    connection.close()


def test_format_summary_includes_all_three_sections(con):
    summary = format_summary(con, as_of=date(2026, 1, 1))
    assert "Consumption trends" in summary
    assert "Expiry risk" in summary
    assert "Reorder points" in summary


def test_format_summary_lists_upcoming_expiry(con):
    summary = format_summary(con, as_of=date(2026, 1, 1))
    assert "Toluene" in summary
    assert "BN1" in summary
