"""Run the .sql reports in this directory and return rows as dicts."""
from datetime import date, timedelta
from pathlib import Path

QUERIES_DIR = Path(__file__).resolve().parent


def _load_sql(name: str) -> str:
    return (QUERIES_DIR / name).read_text(encoding="utf-8")


def _as_dicts(con, sql: str, columns: list[str], params: list | None = None) -> list[dict]:
    rows = con.execute(sql, params or []).fetchall()
    return [dict(zip(columns, row)) for row in rows]


def consumption_trends(con) -> list[dict]:
    return _as_dicts(
        con, _load_sql("consumption_trends.sql"),
        ["chemical_name", "year", "month", "total_used"],
    )


def expiry_risk(con, as_of: date, horizon_days: int = 90) -> list[dict]:
    horizon_end = as_of + timedelta(days=horizon_days)
    return _as_dicts(
        con, _load_sql("expiry_risk.sql"),
        ["chemical_name", "location_name", "batch_number", "expiry_date"],
        [as_of, horizon_end],
    )
