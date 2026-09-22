# chem-inventory-pipeline

A data pipeline for tracking chemical/reagent stock in a QC lab: supplier
deliveries and usage arrive as batch files, get validated and loaded into a
warehouse, and come out the other side as reports a lab can act on
(consumption trends, expiry risk, reorder points).

## Why this problem

QC labs (e.g. coal analysis, running ash/moisture/sulphur tests) depend on a
steady supply of reagents and calibration standards. Running out mid-batch,
or using an expired reagent, breaks test validity. This project treats
inventory tracking as a data engineering problem rather than a CRUD app:
the interesting part is getting messy delivery/usage records into a
trustworthy warehouse, not the forms around it.

## Architecture

```
generator/  -->  data/raw/  -->  pipeline/ingest.py   -->  pipeline/validate.py
(synthetic       (delivery/         |                          |
 delivery &       usage CSVs)       v                          v
 usage data)                  parsed records            rejected_records
                                     |                    (kept, not dropped)
                                     v
                              pipeline/transform.py
                              (unit normalization,
                               CAS/name dedup)
                                     |
                                     v
                              pipeline/load.py
                              (DuckDB star schema,
                               schema/schema.sql)
                                     |
                                     v
                                reports/
                         (consumption trends, expiry
                          risk, reorder point calc)
```

## Status

The pipeline is complete: generator, ingest, validate, transform, load,
and reports all have test coverage (`pytest`), and `make all` runs the
whole thing end to end. See the commit history and closed issues for how
it was built, day by day.

## Running it

```
python -m venv .venv
source .venv/Scripts/activate   # or .venv\Scripts\activate on Windows cmd
make install
make all       # generate synthetic data, run the pipeline, print the reports
make test      # run the test suite
```

`make all` chains three steps you can also run separately:

- `make generate` — writes synthetic reference + daily delivery/usage CSVs into `data/raw/`
- `make run` — ingests, validates, transforms, and loads `data/raw/` into `warehouse.duckdb`
- `make report` — prints consumption trends, expiry risk, and reorder points from the warehouse

Rows that fail validation aren't dropped — they land in the `rejected_records`
table with a reason, queryable straight from `warehouse.duckdb`.

## Demo video

[Link to be added once recorded]

## Design decisions

- **DuckDB, not Postgres** — a single-file warehouse is enough at this
  scale and needs no infrastructure to run or grade.
- **Plain scripts + Makefile, not Airflow** — the pipeline is small enough
  that an orchestrator would add setup risk without adding clarity.
- **Synthetic data, not real records** — avoids needing proprietary mine
  data, and the generator deliberately corrupts ~8% of rows so validation
  has real problems to catch instead of clean data it can never fail on.
- **ADJUSTMENT movements are modeled as downward-only** — the raw schema
  has no direction field for stock corrections; documented as a known
  simplification in `pipeline/transform.py` rather than silently assumed.
