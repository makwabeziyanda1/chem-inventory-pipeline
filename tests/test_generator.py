import random
from pathlib import Path

from generator.generate_deliveries import (
    CHEMICALS,
    GeneratorConfig,
    build_suppliers,
    generate_delivery_rows,
    generate_transactions,
    generate_usage_rows,
    maybe_corrupt,
)
from faker import Faker
from datetime import date


def test_chemical_catalog_has_unique_cas_numbers():
    cas_numbers = [c["cas_number"] for c in CHEMICALS]
    assert len(cas_numbers) == len(set(cas_numbers))
    assert len(CHEMICALS) >= 15


def test_generate_delivery_rows_have_required_fields():
    suppliers = build_suppliers(Faker(), count=3)
    rng = random.Random(1)
    rows = generate_delivery_rows(date(2026, 1, 1), suppliers, rng)
    for row in rows:
        assert row["chemical_name"]
        assert row["quantity"] > 0
        assert row["expiry_date"] > row["date"]


def test_generate_usage_rows_have_required_fields():
    rng = random.Random(2)
    rows = generate_usage_rows(date(2026, 1, 1), rng)
    for row in rows:
        assert row["movement_type"] in {"USAGE", "DISPOSAL", "ADJUSTMENT"}
        assert row["quantity"] > 0


def test_maybe_corrupt_never_mutates_at_zero_dirty_rate():
    rng = random.Random(3)
    row = {"chemical_name": "Toluene", "cas_number": "108-88-3", "date": "2026-01-01",
           "quantity": 5, "expiry_date": "2027-01-01", "supplier_name": "Acme"}
    assert maybe_corrupt(row, rng, dirty_rate=0.0) == row


def test_maybe_corrupt_always_mutates_at_full_dirty_rate():
    rng = random.Random(4)
    row = {"chemical_name": "Toluene", "cas_number": "108-88-3", "date": "2026-01-01",
           "quantity": 5, "expiry_date": "2027-01-01", "supplier_name": "Acme"}
    corrupted = [maybe_corrupt(row, rng, dirty_rate=1.0) for _ in range(20)]
    assert any(c != row for c in corrupted)


def test_generate_transactions_writes_expected_files(tmp_path: Path):
    cfg = GeneratorConfig(
        start_date=date(2026, 1, 1), days=3, out_dir=tmp_path,
        dirty_rate=0.0, seed=7,
    )
    suppliers = build_suppliers(Faker(), count=2)
    generate_transactions(cfg, suppliers)
    written = {p.name for p in tmp_path.glob("*.csv")}
    assert any(name.startswith("usage_2026-01-01") for name in written)
