# Olist Decision Intelligence — Agentic BI Platform

End-to-end BI system on the Olist Brazilian e-commerce dataset: ETL to a star-schema warehouse,
KPI dashboard, forecasting and segmentation, and an LLM analyst agent that diagnoses sales
changes and recommends actions. Course project for Business Intelligence Lab.

**Stack:** Python 3.11 · pandas · DuckDB · Streamlit/Plotly · scikit-learn · mlxtend · LangGraph + Ollama · Docker

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
make install

# Option A: real data. Download from Kaggle (olistbr/brazilian-ecommerce) into data/raw/
# Option B: synthetic dev data (planted scenario for agent testing)
make synth

make etl        # build warehouse, runs 13 data-quality checks
make kpis       # headline KPIs in the terminal
make app        # dashboard on http://localhost:8501
make test       # pytest (14 tests passing)
```

## Quick start (Docker)

```bash
make docker-build
make docker-synth     # or put real CSVs in data/raw
make docker-etl
make docker-up        # http://localhost:8501
```

## Project layout

```
src/olist_bi/
  etl/         extract.py transform.py load.py validate.py pipeline.py schema.sql
  warehouse/   connection.py (read-only) kpis.py (shared KPI definitions)
  analytics/   forecast / rfm / basket        (Iterations 2-3)
  agent/       tools + LangGraph agent        (Iteration 4)
  app/         streamlit_app.py
  synthetic.py dev dataset generator with a planted ground-truth scenario
tests/  docs/  Dockerfile  docker-compose.yml  Makefile  .github/workflows/ci.yml
```

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.

> The synthetic generator is for development and CI only. Report results must come from the real Olist data.

## Current status

✅ **Iteration 1, 2 & 3 complete:**
- ETL pipeline with 13 data quality checks
- Star schema warehouse (6 tables, ~100K orders)
- 7 dashboard tabs: Overview, Delivery & CX, Drill-down, Forecast, Segments, Basket, Chat
- Demand forecasting with backtest MAPE per category
- RFM customer segmentation with K-Means clustering
- Market basket analysis with association rules
- All 14 tests passing
