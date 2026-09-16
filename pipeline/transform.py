"""Normalize validated rows against the reference catalog before loading.

Raw quantities are always positive magnitudes (see generator/validate); the
sign convention that stock_movements needs is applied here, based on
movement_type. RECEIPT increases stock; USAGE, DISPOSAL, and ADJUSTMENT all
decrease it — the raw schema has no direction field for adjustments, so an
ADJUSTMENT is currently modeled as a downward correction (the more common
real-world case: a recount finding less than expected).
"""
from pipeline.ingest import ReferenceData

UNIT_CONVERSIONS = {
    ("mL", "L"): 0.001,
    ("L", "mL"): 1000,
    ("g", "kg"): 0.001,
    ("kg", "g"): 1000,
}


def _normalize_unit(quantity: float, unit: str, canonical_unit: str) -> float:
    if unit == canonical_unit:
        return quantity
    factor = UNIT_CONVERSIONS.get((unit, canonical_unit))
    if factor is None:
        raise ValueError(f"no known conversion from {unit!r} to {canonical_unit!r}")
    return quantity * factor


def _signed_quantity(quantity: float, movement_type: str) -> float:
    return quantity if movement_type == "RECEIPT" else -quantity


def transform_transactions(rows: list[dict], reference: ReferenceData) -> list[dict]:
    by_cas = {c["cas_number"]: c for c in reference.chemicals}
    transformed = []
    for row in rows:
        chemical = by_cas.get(row["cas_number"])
        canonical_name = chemical["name"] if chemical else row["chemical_name"].strip()
        canonical_unit = chemical["unit_of_measure"] if chemical else row["unit_of_measure"]

        quantity = _normalize_unit(float(row["quantity"]), row["unit_of_measure"], canonical_unit)
        quantity = _signed_quantity(quantity, row["movement_type"])

        transformed.append({
            **row,
            "chemical_name": canonical_name,
            "unit_of_measure": canonical_unit,
            "quantity": quantity,
        })
    return transformed
