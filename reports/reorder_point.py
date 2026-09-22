"""Simple moving-average reorder point: avg daily usage x supplier lead time."""
from datetime import date, timedelta


def compute_reorder_points(
    con, as_of: date, lookback_days: int = 30, lead_time_days: int = 14
) -> list[dict]:
    window_start = as_of - timedelta(days=lookback_days)
    rows = con.execute(
        """
        SELECT c.name, SUM(-m.quantity) AS total_used
        FROM stock_movements m
        JOIN dim_chemical c ON c.chemical_id = m.chemical_id
        JOIN dim_date d ON d.date_id = m.date_id
        WHERE m.movement_type = 'USAGE' AND d.full_date BETWEEN ? AND ?
        GROUP BY c.name
        """,
        [window_start, as_of],
    ).fetchall()

    results = []
    for name, total_used in rows:
        avg_daily_usage = total_used / lookback_days
        results.append({
            "chemical_name": name,
            "avg_daily_usage": round(avg_daily_usage, 3),
            "reorder_point": round(avg_daily_usage * lead_time_days, 3),
        })
    return sorted(results, key=lambda r: r["chemical_name"])
