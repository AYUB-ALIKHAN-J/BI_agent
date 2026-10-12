# Iteration roadmap

| # | Deliverable | Visible result | Status |
|---|---|---|---|
| 0 | Scaffold: packaging, Docker, CI, Makefile, lint, tests | `make test` green, `docker compose build` | ✅ done |
| 1 | ETL + star schema + validation + KPI dashboard | 13/13 checks pass, dashboard with 6 KPIs and 4 charts | ✅ done |
| 2 | Delivery/CX view, drill-downs (category/state/seller), demand forecast | 4 dashboard tabs; forecast with backtest MAPE vs naive per category | ✅ done |
| 3 | RFM + K-Means segments, market-basket rules | 6 dashboard tabs; customer segments, association rules | ✅ done |
| 4 | Agent: 8 tools, LangGraph ReAct loop, Ollama llama3.1, Docker Ollama backup | Chat answers "why did health_beauty drop in Q2 2018?" with evidence | ✅ done |
| 5 | Agent evaluation set, report + demo | Accuracy table over 10 test questions | |
