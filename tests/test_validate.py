from pipeline.validate import validate_transactions

GOOD_RECEIPT = {
    "source_file": "deliveries_2026-01-01.csv", "date": "2026-01-01",
    "chemical_name": "Toluene", "cas_number": "108-88-3", "supplier_name": "Acme Labs",
    "location_name": "Main QC Lab", "movement_type": "RECEIPT", "quantity": "10",
    "unit_of_measure": "L", "batch_number": "BN260101001", "expiry_date": "2027-01-01",
    "notes": "",
}

GOOD_USAGE = {
    "source_file": "usage_2026-01-01.csv", "date": "2026-01-01",
    "chemical_name": "Toluene", "cas_number": "108-88-3", "supplier_name": "",
    "location_name": "Main QC Lab", "movement_type": "USAGE", "quantity": "1.5",
    "unit_of_measure": "L", "batch_number": "BN251201007", "expiry_date": "", "notes": "",
}


def test_valid_rows_pass_through_untouched():
    result = validate_transactions([GOOD_RECEIPT, GOOD_USAGE])
    assert result.valid == [GOOD_RECEIPT, GOOD_USAGE]
    assert result.rejected == []


def test_blank_chemical_name_is_rejected():
    row = {**GOOD_RECEIPT, "chemical_name": ""}
    result = validate_transactions([row])
    assert result.valid == []
    assert result.rejected[0]["reason"] == "missing chemical_name"
    assert result.rejected[0]["source_file"] == row["source_file"]


def test_blank_cas_number_is_rejected():
    row = {**GOOD_RECEIPT, "cas_number": ""}
    result = validate_transactions([row])
    assert result.rejected[0]["reason"] == "missing cas_number"


def test_malformed_cas_number_is_rejected():
    row = {**GOOD_RECEIPT, "cas_number": "108 88 3"}
    result = validate_transactions([row])
    assert result.rejected[0]["reason"] == "malformed cas_number"


def test_reference_material_cas_format_is_accepted():
    row = {**GOOD_RECEIPT, "cas_number": "CRM-ASH-01"}
    result = validate_transactions([row])
    assert result.valid == [row]


def test_non_numeric_quantity_is_rejected():
    row = {**GOOD_RECEIPT, "quantity": "N/A"}
    result = validate_transactions([row])
    assert result.rejected[0]["reason"] == "non-numeric quantity"


def test_negative_quantity_is_rejected():
    row = {**GOOD_RECEIPT, "quantity": "-5"}
    result = validate_transactions([row])
    assert result.rejected[0]["reason"] == "non-positive quantity"


def test_zero_quantity_is_rejected():
    row = {**GOOD_USAGE, "quantity": "0"}
    result = validate_transactions([row])
    assert result.rejected[0]["reason"] == "non-positive quantity"


def test_expiry_before_delivery_date_is_rejected_for_receipts():
    row = {**GOOD_RECEIPT, "expiry_date": "2026-01-01"}
    result = validate_transactions([row])
    assert result.rejected[0]["reason"] == "expiry_date before delivery date"


def test_missing_supplier_on_receipt_is_rejected():
    row = {**GOOD_RECEIPT, "supplier_name": ""}
    result = validate_transactions([row])
    assert result.rejected[0]["reason"] == "missing supplier_name on RECEIPT"


def test_missing_supplier_on_usage_is_not_an_error():
    result = validate_transactions([GOOD_USAGE])
    assert result.valid == [GOOD_USAGE]


def test_first_failing_rule_wins_when_multiple_fields_are_bad():
    row = {**GOOD_RECEIPT, "chemical_name": "", "quantity": "-5"}
    result = validate_transactions([row])
    assert len(result.rejected) == 1
    assert result.rejected[0]["reason"] == "missing chemical_name"
