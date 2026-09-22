from datetime import date

import duckdb
import pytest

from pipeline.ingest import ReferenceData
from pipeline.load import init_schema, load_reference_data, load_transactions
from reports.queries import consumption_trends, expiry_risk
from reports.reorder_point import compute_reorder_points

REFERENCE = ReferenceData(
    chemicals=[
        {"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"},
    ],
    suppliers=[{"name": "Acme Labs", "contact_email": "orders@acmelabs.test"}],
    lab_locations=[{"name": "Main QC Lab", "site": "Coal Mine Site A"}],
)


def _receipt(day: str, expiry: str, batch: str, quantity: float = 10.0) -> dict:
    return {
        "source_file": f"deliveries_{day}.csv", "date": day, "chemical_name": "Toluene",
        "cas_number": "108-88-3", "supplier_name": "Acme Labs", "location_name": "Main QC Lab",
        "movement_type": "RECEIPT", "quantity": quantity, "unit_of_measure": "L",
        "batch_number": batch, "expiry_date": expiry, "notes": "",
    }


def _usage(day: str, quantity: float) -> dict:
    return {
        "source_file": f"usage_{day}.csv", "date": day, "chemical_name": "Toluene",
        "cas_number": "108-88-3", "supplier_name": "", "location_name": "Main QC Lab",
        "movement_type": "USAGE", "quantity": -quantity, "unit_of_measure": "L",
        "batch_number": "BN000", "expiry_date": "", "notes": "",
    }


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")
    init_schema(connection)
    load_reference_data(connection, REFERENCE)
    yield connection
    connection.close()


def test_consumption_trends_sums_usage_by_month(con):
    load_transactions(con, [_usage("2026-01-05", 2.0), _usage("2026-01-20", 1.0), _usage("2026-02-01", 3.0)])
    trends = consumption_trends(con)
    assert {"chemical_name": "Toluene", "year": 2026, "month": 1, "total_used": 3.0} in trends
    assert {"chemical_name": "Toluene", "year": 2026, "month": 2, "total_used": 3.0} in trends


def test_consumption_trends_ignores_receipts(con):
    load_transactions(con, [_receipt("2026-01-05", "2027-01-01", "BN1")])
    assert consumption_trends(con) == []


def test_expiry_risk_returns_batches_within_horizon(con):
    load_transactions(con, [
        _receipt("2026-01-01", "2026-04-01", "BN-SOON"),
        _receipt("2026-01-01", "2028-01-01", "BN-FAR"),
    ])
    risk = expiry_risk(con, as_of=date(2026, 1, 1), horizon_days=90)
    batches = {r["batch_number"] for r in risk}
    assert "BN-SOON" in batches
    assert "BN-FAR" not in batches


def test_expiry_risk_excludes_already_expired_batches(con):
    load_transactions(con, [_receipt("2026-01-01", "2025-12-01", "BN-EXPIRED")])
    risk = expiry_risk(con, as_of=date(2026, 1, 1), horizon_days=90)
    assert risk == []


def test_reorder_point_scales_with_average_daily_usage(con):
    load_transactions(con, [_usage(f"2026-01-{d:02d}", 3.0) for d in range(1, 11)])
    points = compute_reorder_points(con, as_of=date(2026, 1, 10), lookback_days=10, lead_time_days=5)
    toluene = next(p for p in points if p["chemical_name"] == "Toluene")
    assert toluene["avg_daily_usage"] == pytest.approx(3.0)
    assert toluene["reorder_point"] == pytest.approx(15.0)
