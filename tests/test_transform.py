from pipeline.ingest import ReferenceData
from pipeline.transform import transform_transactions

REFERENCE = ReferenceData(
    chemicals=[
        {"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"},
        {"name": "Sodium Hydroxide", "cas_number": "1310-73-2", "hazard_class": "Corrosive", "unit_of_measure": "kg"},
    ],
    suppliers=[], lab_locations=[],
)

BASE_ROW = {
    "source_file": "deliveries_2026-01-01.csv", "date": "2026-01-01",
    "chemical_name": "Toluene", "cas_number": "108-88-3", "supplier_name": "Acme Labs",
    "location_name": "Main QC Lab", "movement_type": "RECEIPT", "quantity": "10",
    "unit_of_measure": "L", "batch_number": "BN260101001", "expiry_date": "2027-01-01",
    "notes": "",
}


def test_receipt_quantity_becomes_positive_float():
    result = transform_transactions([BASE_ROW], REFERENCE)
    assert result[0]["quantity"] == 10.0


def test_usage_quantity_becomes_negative():
    row = {**BASE_ROW, "movement_type": "USAGE", "quantity": "1.5"}
    result = transform_transactions([row], REFERENCE)
    assert result[0]["quantity"] == -1.5


def test_disposal_quantity_becomes_negative():
    row = {**BASE_ROW, "movement_type": "DISPOSAL", "quantity": "2"}
    result = transform_transactions([row], REFERENCE)
    assert result[0]["quantity"] == -2.0


def test_adjustment_quantity_becomes_negative():
    row = {**BASE_ROW, "movement_type": "ADJUSTMENT", "quantity": "3"}
    result = transform_transactions([row], REFERENCE)
    assert result[0]["quantity"] == -3.0


def test_millilitres_are_normalized_to_litres():
    row = {**BASE_ROW, "quantity": "500", "unit_of_measure": "mL"}
    result = transform_transactions([row], REFERENCE)
    assert result[0]["quantity"] == 0.5
    assert result[0]["unit_of_measure"] == "L"


def test_grams_are_normalized_to_kilograms():
    row = {**BASE_ROW, "chemical_name": "Sodium Hydroxide", "cas_number": "1310-73-2",
           "quantity": "250", "unit_of_measure": "g"}
    result = transform_transactions([row], REFERENCE)
    assert result[0]["quantity"] == 0.25
    assert result[0]["unit_of_measure"] == "kg"


def test_chemical_name_variant_is_resolved_to_canonical_via_cas():
    row = {**BASE_ROW, "chemical_name": "toluene "}
    result = transform_transactions([row], REFERENCE)
    assert result[0]["chemical_name"] == "Toluene"


def test_unknown_cas_number_falls_back_to_original_name_and_unit():
    row = {**BASE_ROW, "chemical_name": "Mystery Chemical", "cas_number": "0000-00-0", "unit_of_measure": "L"}
    result = transform_transactions([row], REFERENCE)
    assert result[0]["chemical_name"] == "Mystery Chemical"
    assert result[0]["unit_of_measure"] == "L"


def test_non_transformed_fields_pass_through_unchanged():
    result = transform_transactions([BASE_ROW], REFERENCE)
    assert result[0]["source_file"] == BASE_ROW["source_file"]
    assert result[0]["batch_number"] == BASE_ROW["batch_number"]
    assert result[0]["supplier_name"] == BASE_ROW["supplier_name"]
