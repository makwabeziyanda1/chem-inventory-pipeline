-- Star schema for the chemical inventory warehouse (DuckDB).
-- Fact: stock_movements records every receipt, usage, disposal, and manual
-- adjustment of a chemical, each traceable back to the source file it was
-- loaded from.

CREATE TABLE IF NOT EXISTS dim_chemical (
    chemical_id     INTEGER PRIMARY KEY,
    cas_number      VARCHAR NOT NULL UNIQUE,
    name            VARCHAR NOT NULL,
    hazard_class    VARCHAR,
    unit_of_measure VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_supplier (
    supplier_id     INTEGER PRIMARY KEY,
    name            VARCHAR NOT NULL,
    contact_email   VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_lab_location (
    location_id     INTEGER PRIMARY KEY,
    name            VARCHAR NOT NULL,
    site            VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id         INTEGER PRIMARY KEY,   -- YYYYMMDD
    full_date       DATE NOT NULL UNIQUE,
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    day             INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_movements (
    movement_id     INTEGER PRIMARY KEY,
    chemical_id     INTEGER NOT NULL REFERENCES dim_chemical(chemical_id),
    supplier_id     INTEGER REFERENCES dim_supplier(supplier_id),      -- NULL for usage/disposal
    location_id     INTEGER NOT NULL REFERENCES dim_lab_location(location_id),
    date_id         INTEGER NOT NULL REFERENCES dim_date(date_id),
    movement_type   VARCHAR NOT NULL,      -- RECEIPT | USAGE | DISPOSAL | ADJUSTMENT
    quantity        DOUBLE NOT NULL,       -- positive for RECEIPT, negative for USAGE/DISPOSAL
    batch_number    VARCHAR,
    expiry_date     DATE,
    source_file     VARCHAR NOT NULL       -- lineage: which raw delivery/usage file this came from
);

-- Records that failed validation during ingest, kept for review rather than
-- silently dropped.
CREATE TABLE IF NOT EXISTS rejected_records (
    rejected_id     INTEGER PRIMARY KEY,
    source_file     VARCHAR NOT NULL,
    raw_row         VARCHAR NOT NULL,      -- original row, as text, for inspection
    reason          VARCHAR NOT NULL,
    rejected_at     TIMESTAMP NOT NULL DEFAULT current_timestamp
);
