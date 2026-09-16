"""Load transformed records into the DuckDB warehouse (schema/schema.sql).

Dimension rows are resolved get-or-create style against their natural
business key (CAS number, supplier name, location name), so reloading the
same reference data twice is a no-op. Fact rows (stock_movements,
rejected_records) are made idempotent per source file: before inserting a
file's rows, any existing rows already loaded from that file are deleted
first, so re-running the pipeline on the same raw CSVs doesn't duplicate
data.
"""
from datetime import date
from pathlib import Path

from pipeline.ingest import ReferenceData

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "schema.sql"


def init_schema(con, schema_path: Path = SCHEMA_PATH) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            con.execute(statement)


def _get_or_create(con, table: str, id_col: str, key_col: str, key_value: str, row: dict) -> int:
    existing = con.execute(f"SELECT {id_col} FROM {table} WHERE {key_col} = ?", [key_value]).fetchone()
    if existing:
        return existing[0]
    next_id = con.execute(f"SELECT COALESCE(MAX({id_col}), 0) + 1 FROM {table}").fetchone()[0]
    columns = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    con.execute(
        f"INSERT INTO {table} ({id_col}, {columns}) VALUES (?, {placeholders})",
        [next_id, *row.values()],
    )
    return next_id


def load_reference_data(con, reference: ReferenceData) -> None:
    for chemical in reference.chemicals:
        _get_or_create(con, "dim_chemical", "chemical_id", "cas_number", chemical["cas_number"], chemical)
    for supplier in reference.suppliers:
        _get_or_create(con, "dim_supplier", "supplier_id", "name", supplier["name"], supplier)
    for location in reference.lab_locations:
        _get_or_create(con, "dim_lab_location", "location_id", "name", location["name"], location)


def _ensure_dim_date(con, date_str: str) -> int:
    d = date.fromisoformat(date_str)
    date_id = int(d.strftime("%Y%m%d"))
    if not con.execute("SELECT 1 FROM dim_date WHERE date_id = ?", [date_id]).fetchone():
        con.execute(
            "INSERT INTO dim_date (date_id, full_date, year, quarter, month, day) VALUES (?, ?, ?, ?, ?, ?)",
            [date_id, d, d.year, (d.month - 1) // 3 + 1, d.month, d.day],
        )
    return date_id


def _lookup_id(con, table: str, id_col: str, key_col: str, key_value: str) -> int | None:
    result = con.execute(f"SELECT {id_col} FROM {table} WHERE {key_col} = ?", [key_value]).fetchone()
    return result[0] if result else None


def load_transactions(con, rows: list[dict]) -> None:
    for source_file in {row["source_file"] for row in rows}:
        con.execute("DELETE FROM stock_movements WHERE source_file = ?", [source_file])

    next_id = con.execute("SELECT COALESCE(MAX(movement_id), 0) FROM stock_movements").fetchone()[0]
    for row in rows:
        chemical_id = _lookup_id(con, "dim_chemical", "chemical_id", "cas_number", row["cas_number"])
        if chemical_id is None:
            raise ValueError(f"unknown chemical CAS number {row['cas_number']!r}; load reference data first")

        location_id = _lookup_id(con, "dim_lab_location", "location_id", "name", row["location_name"])
        if location_id is None:
            raise ValueError(f"unknown lab location {row['location_name']!r}; load reference data first")

        supplier_id = (
            _lookup_id(con, "dim_supplier", "supplier_id", "name", row["supplier_name"])
            if row["supplier_name"] else None
        )
        date_id = _ensure_dim_date(con, row["date"])
        expiry_date = date.fromisoformat(row["expiry_date"]) if row["expiry_date"] else None

        next_id += 1
        con.execute(
            """INSERT INTO stock_movements
               (movement_id, chemical_id, supplier_id, location_id, date_id, movement_type,
                quantity, batch_number, expiry_date, source_file)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [next_id, chemical_id, supplier_id, location_id, date_id, row["movement_type"],
             row["quantity"], row["batch_number"], expiry_date, row["source_file"]],
        )


def load_rejected_records(con, rejected: list[dict]) -> None:
    for source_file in {r["source_file"] for r in rejected}:
        con.execute("DELETE FROM rejected_records WHERE source_file = ?", [source_file])

    next_id = con.execute("SELECT COALESCE(MAX(rejected_id), 0) FROM rejected_records").fetchone()[0]
    for r in rejected:
        next_id += 1
        con.execute(
            "INSERT INTO rejected_records (rejected_id, source_file, raw_row, reason) VALUES (?, ?, ?, ?)",
            [next_id, r["source_file"], r["raw_row"], r["reason"]],
        )
