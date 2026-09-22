.PHONY: install generate run report all test

install:
	pip install -r requirements.txt

generate:
	python generator/generate_deliveries.py --days 45 --seed 42

run:
	python -m pipeline.run --raw-dir data/raw --db-path warehouse.duckdb

report:
	python -m reports.print_summary --db-path warehouse.duckdb

all: generate run report

test:
	python -m pytest -q
