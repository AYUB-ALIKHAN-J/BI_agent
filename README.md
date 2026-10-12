# Olist Decision Intelligence — Agentic BI Platform

End-to-end BI system on the Olist Brazilian e-commerce dataset: ETL to a star-schema warehouse,
KPI dashboard, forecasting and segmentation, and an LLM analyst agent that diagnoses sales
changes and recommends actions. Course project for Business Intelligence Lab.

**Stack:** Python 3.11 · pandas · DuckDB · Streamlit/Plotly · scikit-learn · mlxtend · LangGraph + Ollama · Docker

## Quick start (local)

### Automated Setup (Recommended)

We provide cross-platform setup scripts for easy installation:

**Windows:**
```cmd
setup.bat
```

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

The script will:
- Create a virtual environment
- Install all dependencies
- Generate synthetic test data
- Build the data warehouse
- Run tests

### Manual Setup

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

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Starting the Dashboard

After setup is complete, start the dashboard with:

```bash
make app
# or
./start.sh    # macOS/Linux
start.bat     # Windows
```

The dashboard will be available at: http://localhost:8501

## Data Information

- **Synthetic Data**: Generated automatically by the setup script for testing
- **Real Olist Data**: Available at [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- **CSV Files**: Included in the repository under `data/raw/` for immediate use
- **Warehouse**: Built automatically in `warehouse/olist.duckdb`

> The synthetic generator is for development and CI only. Report results must come from the real Olist data.

## Quick start (Docker)

```bash
make docker-build
make docker-synth     # or put real CSVs in data/raw
make docker-etl
make docker-ollama    # start Ollama container (backup if no local Ollama)
make docker-up        # http://localhost:8501
```

## Project layout

```
src/olist_bi/
  etl/         extract.py transform.py load.py validate.py pipeline.py schema.sql
  warehouse/   connection.py (read-only) kpis.py (shared KPI definitions)
  analytics/   forecast / rfm / basket        (Iterations 2-3)
  agent/       tools.py langgraph_agent.py   (Iteration 4)
  app/         streamlit_app.py tabs/chat.py
  synthetic.py dev dataset generator with a planted ground-truth scenario
tests/  docs/  Dockerfile  docker-compose.yml  Makefile  .github/workflows/ci.yml
```

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.

> The synthetic generator is for development and CI only. Report results must come from the real Olist data.

## Current status

✅ **Iteration 1, 2, 3 & 4 complete:**
- ETL pipeline with 13 data quality checks
- Star schema warehouse (6 tables, ~100K orders)
- 7 dashboard tabs: Overview, Delivery & CX, Drill-down, Forecast, Segments, Basket, Chat
- Demand forecasting with backtest MAPE per category
- RFM customer segmentation with K-Means clustering
- Market basket analysis with association rules
- LLM analyst agent with 8 tools (KPIs, trends, forecasts, segments, basket rules)
- All 14 tests passing
- Local Ollama support + Docker Ollama backup

## Agent tools

The LLM agent can answer questions using these tools:
- `get_headline_kpis` - Revenue, orders, AOV, cancellation rate, on-time rate, avg review
- `get_monthly_trend` - Monthly revenue and order trends
- `get_revenue_by_category` - Revenue breakdown by product category
- `get_revenue_by_state` - Revenue breakdown by customer state
- `get_available_months` - List of available months in the warehouse
- `get_forecast` - Demand forecast for a category and metric
- `get_rfm_segments` - RFM customer segmentation results
- `get_basket_rules` - Market basket association rules
