"""Print a human-readable summary of the three reports, for the CLI/demo."""
import argparse
from datetime import date

import duckdb

from reports.queries import consumption_trends, expiry_risk
from reports.reorder_point import compute_reorder_points


def format_summary(con, as_of: date) -> str:
    lines = ["=== Consumption trends (by month) ==="]
    for row in consumption_trends(con):
        lines.append(f"{row['chemical_name']:<35} {row['year']}-{row['month']:02d}  used {row['total_used']}")

    lines.append("")
    lines.append(f"=== Expiry risk (batches expiring within 90 days of {as_of}) ===")
    for row in expiry_risk(con, as_of):
        lines.append(
            f"{row['chemical_name']:<35} {row['location_name']:<20} "
            f"batch {row['batch_number']:<12} expires {row['expiry_date']}"
        )

    lines.append("")
    lines.append(f"=== Reorder points (30d lookback, 14d lead time, as of {as_of}) ===")
    for row in compute_reorder_points(con, as_of):
        lines.append(
            f"{row['chemical_name']:<35} avg/day {row['avg_daily_usage']:<10} "
            f"reorder_point {row['reorder_point']}"
        )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="warehouse.duckdb")
    parser.add_argument("--as-of", default=None, help="ISO date to report as of (default: today)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    con = duckdb.connect(args.db_path)
    try:
        print(format_summary(con, as_of))
    finally:
        con.close()
