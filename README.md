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

Day 1: repo scaffolding + warehouse schema (`schema/schema.sql`) committed.
Pipeline scripts land over the following days — see commit history for
progress.

## Running it

Not runnable yet — `pipeline/` and `generator/` are still empty. This
section will be filled in once `make all` actually works end to end.

## Demo video

Coming soon — will be linked here once the pipeline is complete.
