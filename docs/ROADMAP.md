# Iteration roadmap

| # | Deliverable | Visible result | Status |
|---|---|---|---|
| 0 | Scaffold: packaging, Docker, CI, Makefile, lint, tests | `make test` green, `docker compose build` | ✅ done |
| 1 | ETL + star schema + validation + KPI dashboard | 13/13 checks pass, dashboard with 6 KPIs and 4 charts | ✅ done |
| 2 | Delivery/CX view, drill-downs (category/state/seller), demand forecast | 4 dashboard tabs; forecast with backtest MAPE vs naive per category | ✅ done |
| 3 | RFM + K-Means segments, market-basket rules | Segment profiles page, top association rules | 🔄 next |
| 4 | Agent: 6 tools, LangGraph ReAct loop, Ollama llama3.1 | Chat answers "why did health_beauty drop in Q2 2018?" with evidence | |
| 5 | Chat tab in Streamlit, agent evaluation set, report + demo | Accuracy table over 10 test questions | |
