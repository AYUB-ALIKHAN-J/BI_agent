# Architecture

```
 9 Olist CSVs ──► ETL (pandas) ──► DuckDB star schema ──► KPI layer (SQL) ──► Streamlit dashboard
   (data/raw)    extract/transform/    warehouse/olist.duckdb     │
                 load/validate                                     ├──► Analytics: forecast, RFM, basket   (Iter 2-3)
                                                                   └──► Agent tools ──► LangGraph + Ollama (Iter 4)
```

## Layers and responsibilities

| Layer | Package | Responsibility |
|---|---|---|
| Extract | `olist_bi.etl.extract` | Read 9 CSVs, check required columns, parse dates. Fails fast with a clear message. |
| Transform | `olist_bi.etl.transform` | Clean, aggregate payments/reviews to order grain, build dims + 2 facts. |
| Load | `olist_bi.etl.load` | Full refresh into DuckDB from `schema.sql`; logs row counts to `etl_runs`. |
| Validate | `olist_bi.etl.validate` | 13 checks on the loaded warehouse (reconciliation, keys, domain rules). Pipeline fails if any fail. |
| KPI layer | `olist_bi.warehouse.kpis` | Single source of truth for KPI definitions. Dashboard **and** agent tools call the same functions. |
| App | `olist_bi.app` | Streamlit GUI. Read-only warehouse access. |
| Analytics | `olist_bi.analytics` | Forecast / RFM / basket (Iterations 2-3). |
| Agent | `olist_bi.agent` | LangGraph ReAct agent + 6 tools (Iteration 4). |

## Star schema

* `fact_orders` (grain: order): status, timestamps, delivery_days, delay_days, is_late, review_score,
  payment_type, payment_value, items_count, items_revenue, freight_total
* `fact_order_items` (grain: order item): product_key, seller_key, date_key, price, freight_value
* `dim_customer` (per real customer = `customer_unique_id`), `dim_product`, `dim_seller`, `dim_date`

Two fact tables because payments/reviews live at order grain and price at item grain; putting
both in one table fans out joins and inflates revenue.

## Design decisions

1. **DuckDB**: single-file columnar warehouse, no server, fast analytics SQL, trivial in Docker.
2. **Surrogate keys** on all dimensions; natural ids kept for traceability.
3. **Validation is part of the pipeline**, not an afterthought; the revenue reconciliation
   check exists specifically to catch join fan-out.
4. **Read-only connections** for the app and agent: they can never modify the warehouse.
5. **Shared KPI definitions** so the dashboard and the agent can never disagree.
6. **Agent tools are plain Python functions over SQL**; the LLM never calculates and never writes SQL.
7. **Synthetic dataset with a planted scenario** gives the agent a known ground truth for evaluation.

## KPI definitions
See `src/olist_bi/warehouse/kpis.py` docstring (revenue excludes canceled/unavailable orders, etc.).

## Current status (as of Iteration 4)

✅ **ETL Pipeline**: 13/13 data quality checks passing
✅ **Star Schema**: 6 tables (~100K orders, ~113K items)
✅ **Dashboard**: 7 tabs (Overview, Delivery & CX, Drill-down, Forecast, Segments, Basket, Chat)
✅ **Forecasting**: Backtest MAPE per category with naive/MA3/Holt-damped models
✅ **RFM Segmentation**: K-Means clustering on Recency, Frequency, Monetary
✅ **Basket Analysis**: Association rules (Apriori algorithm)
✅ **LLM Agent**: 8 tools, LangGraph ReAct loop, Ollama llama3.1
✅ **Tests**: 14/14 passing
✅ **Docker**: Ollama container as backup, host.docker.internal for local Ollama

## Recent changes (Iteration 4)

* Added agent tools module with 8 functions for KPIs, trends, forecasts, segments, basket rules
* Implemented LangGraph ReAct agent with tool calling
* Added Chat tab to Streamlit dashboard with agent integration
* Added Ollama service to docker-compose.yml as backup
* Updated Dockerfile to include agent dependencies
* Added docker-ollama Makefile target
* Updated README with agent tools documentation
