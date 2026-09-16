"""Generate synthetic chemical delivery and usage records for the pipeline.

Writes reference (master) data once, then a pair of daily transaction CSVs
per day in the requested date range, mimicking the batch files a QC lab
would actually export. A small fraction of rows are deliberately corrupted
so the validation stage has real dirty data to work against.
"""
import argparse
import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

CHEMICALS = [
    {"name": "Sulfuric Acid", "cas_number": "7664-93-9", "hazard_class": "Corrosive", "unit_of_measure": "L"},
    {"name": "Hydrochloric Acid", "cas_number": "7647-01-0", "hazard_class": "Corrosive", "unit_of_measure": "L"},
    {"name": "Nitric Acid", "cas_number": "7697-37-2", "hazard_class": "Oxidizer", "unit_of_measure": "L"},
    {"name": "Sodium Hydroxide", "cas_number": "1310-73-2", "hazard_class": "Corrosive", "unit_of_measure": "kg"},
    {"name": "Potassium Dichromate", "cas_number": "7778-50-9", "hazard_class": "Toxic", "unit_of_measure": "kg"},
    {"name": "Benzoic Acid", "cas_number": "65-85-0", "hazard_class": "Non-hazardous", "unit_of_measure": "kg"},
    {"name": "Calcium Carbonate", "cas_number": "471-34-1", "hazard_class": "Non-hazardous", "unit_of_measure": "kg"},
    {"name": "Toluene", "cas_number": "108-88-3", "hazard_class": "Flammable", "unit_of_measure": "L"},
    {"name": "Acetone", "cas_number": "67-64-1", "hazard_class": "Flammable", "unit_of_measure": "L"},
    {"name": "Magnesium Oxide", "cas_number": "1309-48-4", "hazard_class": "Non-hazardous", "unit_of_measure": "kg"},
    {"name": "Ammonium Molybdate", "cas_number": "12054-85-2", "hazard_class": "Irritant", "unit_of_measure": "kg"},
    {"name": "Barium Chloride", "cas_number": "10361-37-2", "hazard_class": "Toxic", "unit_of_measure": "kg"},
    {"name": "Silver Nitrate", "cas_number": "7761-88-8", "hazard_class": "Oxidizer", "unit_of_measure": "kg"},
    {"name": "Potassium Iodide", "cas_number": "7681-11-0", "hazard_class": "Non-hazardous", "unit_of_measure": "kg"},
    {"name": "Sodium Thiosulfate", "cas_number": "7772-98-7", "hazard_class": "Non-hazardous", "unit_of_measure": "kg"},
    {"name": "Iron(III) Chloride", "cas_number": "7705-08-0", "hazard_class": "Corrosive", "unit_of_measure": "kg"},
    {"name": "Ethanol", "cas_number": "64-17-5", "hazard_class": "Flammable", "unit_of_measure": "L"},
    {"name": "Certified Coal Ash Reference Material", "cas_number": "CRM-ASH-01", "hazard_class": "Non-hazardous", "unit_of_measure": "kg"},
    {"name": "Certified Moisture Reference Standard", "cas_number": "CRM-MOIST-01", "hazard_class": "Non-hazardous", "unit_of_measure": "L"},
    {"name": "Certified Sulphur Reference Standard", "cas_number": "CRM-SULPH-01", "hazard_class": "Non-hazardous", "unit_of_measure": "kg"},
]

LAB_LOCATIONS = [
    {"name": "Main QC Lab", "site": "Coal Mine Site A"},
    {"name": "Sample Prep Lab", "site": "Coal Mine Site A"},
    {"name": "Central Reagent Store", "site": "Regional Depot"},
]

REFERENCE_FIELDS = {
    "chemicals": ["name", "cas_number", "hazard_class", "unit_of_measure"],
    "suppliers": ["name", "contact_email"],
    "lab_locations": ["name", "site"],
}

DELIVERY_FIELDS = [
    "date", "chemical_name", "cas_number", "supplier_name", "location_name",
    "quantity", "unit_of_measure", "batch_number", "expiry_date",
]
USAGE_FIELDS = [
    "date", "chemical_name", "cas_number", "location_name", "movement_type",
    "quantity", "unit_of_measure", "batch_number", "notes",
]


@dataclass
class GeneratorConfig:
    start_date: date
    days: int
    out_dir: Path
    dirty_rate: float
    seed: int


def build_suppliers(fake: Faker, count: int = 6) -> list[dict]:
    return [
        {"name": fake.company(), "contact_email": fake.company_email()}
        for _ in range(count)
    ]


def write_reference_data(cfg: GeneratorConfig, suppliers: list[dict]) -> None:
    ref_dir = cfg.out_dir / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(ref_dir / "chemicals.csv", CHEMICALS, REFERENCE_FIELDS["chemicals"])
    _write_csv(ref_dir / "suppliers.csv", suppliers, REFERENCE_FIELDS["suppliers"])
    _write_csv(ref_dir / "lab_locations.csv", LAB_LOCATIONS, REFERENCE_FIELDS["lab_locations"])


def generate_delivery_rows(day: date, suppliers: list[dict], rng: random.Random) -> list[dict]:
    rows = []
    for _ in range(rng.randint(0, 4)):
        chemical = rng.choice(CHEMICALS)
        supplier = rng.choice(suppliers)
        location = rng.choice(LAB_LOCATIONS)
        shelf_life_days = rng.randint(365, 1095)
        rows.append({
            "date": day.isoformat(),
            "chemical_name": chemical["name"],
            "cas_number": chemical["cas_number"],
            "supplier_name": supplier["name"],
            "location_name": location["name"],
            "quantity": round(rng.uniform(1, 50), 2),
            "unit_of_measure": chemical["unit_of_measure"],
            "batch_number": f"BN{day.strftime('%y%m%d')}{rng.randint(100, 999)}",
            "expiry_date": (day + timedelta(days=shelf_life_days)).isoformat(),
        })
    return rows


def generate_usage_rows(day: date, rng: random.Random) -> list[dict]:
    rows = []
    for _ in range(rng.randint(3, 10)):
        chemical = rng.choice(CHEMICALS)
        location = rng.choice(LAB_LOCATIONS)
        movement_type = rng.choices(
            ["USAGE", "DISPOSAL", "ADJUSTMENT"], weights=[85, 10, 5], k=1
        )[0]
        rows.append({
            "date": day.isoformat(),
            "chemical_name": chemical["name"],
            "cas_number": chemical["cas_number"],
            "location_name": location["name"],
            "movement_type": movement_type,
            "quantity": round(rng.uniform(0.1, 5), 2),
            "unit_of_measure": chemical["unit_of_measure"],
            "batch_number": f"BN{(day - timedelta(days=rng.randint(1, 60))).strftime('%y%m%d')}{rng.randint(100, 999)}",
            "notes": "" if movement_type == "USAGE" else rng.choice(
                ["expired stock", "damaged container", "stock count correction"]
            ),
        })
    return rows


def maybe_corrupt(row: dict, rng: random.Random, dirty_rate: float) -> dict:
    if rng.random() >= dirty_rate:
        return row
    row = dict(row)
    fault = rng.choice([
        "blank_chemical_name", "blank_cas", "malformed_cas", "negative_quantity",
        "non_numeric_quantity", "expiry_before_date", "blank_supplier",
    ])
    if fault == "blank_chemical_name":
        row["chemical_name"] = ""
    elif fault == "blank_cas" and "cas_number" in row:
        row["cas_number"] = ""
    elif fault == "malformed_cas" and "cas_number" in row:
        row["cas_number"] = row["cas_number"].replace("-", " ")
    elif fault == "negative_quantity":
        row["quantity"] = -abs(float(row["quantity"]))
    elif fault == "non_numeric_quantity":
        row["quantity"] = "N/A"
    elif fault == "expiry_before_date" and "expiry_date" in row:
        row["expiry_date"] = row["date"]
    elif fault == "blank_supplier" and "supplier_name" in row:
        row["supplier_name"] = ""
    return row


def generate_transactions(cfg: GeneratorConfig, suppliers: list[dict]) -> None:
    rng = random.Random(cfg.seed)
    for offset in range(cfg.days):
        day = cfg.start_date + timedelta(days=offset)
        deliveries = [
            maybe_corrupt(row, rng, cfg.dirty_rate)
            for row in generate_delivery_rows(day, suppliers, rng)
        ]
        usage = [
            maybe_corrupt(row, rng, cfg.dirty_rate)
            for row in generate_usage_rows(day, rng)
        ]
        if deliveries:
            _write_csv(cfg.out_dir / f"deliveries_{day.isoformat()}.csv", deliveries, DELIVERY_FIELDS)
        if usage:
            _write_csv(cfg.out_dir / f"usage_{day.isoformat()}.csv", usage, USAGE_FIELDS)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(cfg: GeneratorConfig) -> None:
    fake = Faker()
    fake.seed_instance(cfg.seed)
    suppliers = build_suppliers(fake)
    write_reference_data(cfg, suppliers)
    generate_transactions(cfg, suppliers)


def parse_args() -> GeneratorConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=45, help="how many days of transaction history to generate")
    parser.add_argument("--start-date", type=str, default=None, help="ISO date to start from (default: today minus --days)")
    parser.add_argument("--out-dir", type=str, default="data/raw", help="directory to write generated CSVs into")
    parser.add_argument("--dirty-rate", type=float, default=0.08, help="fraction of rows to deliberately corrupt")
    parser.add_argument("--seed", type=int, default=42, help="random seed, for reproducible runs")
    args = parser.parse_args()

    if args.start_date:
        start = date.fromisoformat(args.start_date)
    else:
        start = date.today() - timedelta(days=args.days)

    return GeneratorConfig(
        start_date=start,
        days=args.days,
        out_dir=Path(args.out_dir),
        dirty_rate=args.dirty_rate,
        seed=args.seed,
    )


if __name__ == "__main__":
    run(parse_args())
