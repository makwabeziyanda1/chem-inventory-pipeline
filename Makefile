.PHONY: install generate test

install:
	pip install -r requirements.txt

generate:
	python generator/generate_deliveries.py --days 45 --seed 42

test:
	python -m pytest -q
