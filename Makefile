.PHONY: help install synth etl kpis app test lint fmt docker-build docker-synth docker-etl docker-up docker-ollama clean

PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)
STREAMLIT ?= $(if $(wildcard .venv/bin/streamlit),.venv/bin/streamlit,streamlit)
help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ -/'

install:         ## editable install with all extras
	$(PY) -m pip install -e ".[app,analytics,agent,dev]"

synth:           ## generate a synthetic dev dataset into data/raw (skip if you have real Olist)
	$(PY) -m olist_bi.cli synth

etl:             ## build the star-schema warehouse
	$(PY) -m olist_bi.cli etl

kpis:            ## print headline KPIs
	$(PY) -m olist_bi.cli kpis

app:             ## run the dashboard locally
	$(STREAMLIT) run src/olist_bi/app/streamlit_app.py

start:           ## alias for 'app'
	$(STREAMLIT) run src/olist_bi/app/streamlit_app.py

test:            ## run the test-suite
	$(PY) -m pytest

lint:            ## lint + format check
	ruff check . && ruff format --check .

fmt:
	ruff check . --fix && ruff format .

docker-build:
	docker compose build

docker-synth:
	docker compose --profile dev run --rm synth

docker-etl:
	docker compose --profile etl run --rm etl

docker-up:
	docker compose up app

docker-ollama:
	docker compose --profile ollama up -d ollama

clean:
	rm -rf warehouse/*.duckdb .pytest_cache .ruff_cache
