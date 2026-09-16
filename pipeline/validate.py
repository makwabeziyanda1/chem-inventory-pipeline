"""Data quality rules for ingested transaction rows.

Each rule returns a rejection reason or None. Rules run in a fixed order
and a row is rejected on the first rule it fails, so exactly one reason is
recorded per rejected row rather than piling up every problem with it.
"""
import re
from dataclasses import dataclass, field

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
REFERENCE_MATERIAL_RE = re.compile(r"^CRM-[A-Z]+-\d{2}$")


@dataclass
class ValidationResult:
    valid: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)


def _check_chemical_name(row: dict) -> str | None:
    if not row["chemical_name"].strip():
        return "missing chemical_name"
    return None


def _check_cas_number(row: dict) -> str | None:
    cas = row["cas_number"].strip()
    if not cas:
        return "missing cas_number"
    if not (CAS_RE.match(cas) or REFERENCE_MATERIAL_RE.match(cas)):
        return "malformed cas_number"
    return None


def _check_quantity(row: dict) -> str | None:
    try:
        quantity = float(row["quantity"])
    except (TypeError, ValueError):
        return "non-numeric quantity"
    if quantity <= 0:
        return "non-positive quantity"
    return None


def _check_expiry_date(row: dict) -> str | None:
    if row["movement_type"] != "RECEIPT":
        return None
    if row["expiry_date"] and row["expiry_date"] <= row["date"]:
        return "expiry_date before delivery date"
    return None


def _check_supplier(row: dict) -> str | None:
    if row["movement_type"] == "RECEIPT" and not row["supplier_name"].strip():
        return "missing supplier_name on RECEIPT"
    return None


RULES = [
    _check_chemical_name,
    _check_cas_number,
    _check_quantity,
    _check_expiry_date,
    _check_supplier,
]


def validate_transactions(rows: list[dict]) -> ValidationResult:
    result = ValidationResult()
    for row in rows:
        reason = next((r for r in (rule(row) for rule in RULES) if r), None)
        if reason:
            result.rejected.append({
                "source_file": row["source_file"],
                "raw_row": str(row),
                "reason": reason,
            })
        else:
            result.valid.append(row)
    return result
