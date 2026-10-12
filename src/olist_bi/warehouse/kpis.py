"""KPI definitions: the single source of truth shared by the dashboard AND the agent tools.

Definitions (documented so the report and the agent agree):
  revenue            sum of item price on orders that are not canceled/unavailable
  valid orders       orders that are not canceled/unavailable
  AOV                revenue / valid orders
  cancellation rate  canceled orders / all orders
  on-time rate       delivered orders with delivered_ts <= estimated_ts / delivered orders
  avg review         mean of per-order mean review score
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .connection import query_df

VALID = "o.order_status NOT IN ('canceled', 'unavailable')"
OPEN_START, OPEN_END = "0000-00", "9999-99"


def _range(start: str | None, end: str | None) -> list[str]:
    return [start or OPEN_START, end or OPEN_END]


def headline_kpis(
    warehouse: str | Path, start: str | None = None, end: str | None = None
) -> dict[str, float]:
    df = query_df(
        warehouse,
        f"""
        SELECT
            COALESCE(SUM(CASE WHEN {VALID} THEN o.items_revenue END), 0)        AS revenue,
            COUNT(*)                                                             AS total_orders,
            COUNT(*) FILTER (WHERE {VALID})                                      AS valid_orders,
            AVG(CASE WHEN o.order_status = 'canceled' THEN 1.0 ELSE 0.0 END)     AS cancellation_rate,
            AVG(1 - o.is_late) FILTER (WHERE o.is_late IS NOT NULL)              AS on_time_rate,
            AVG(o.review_score)                                                  AS avg_review
        FROM fact_orders o JOIN dim_date d USING (date_key)
        WHERE d.year_month BETWEEN ? AND ?
        """,
        _range(start, end),
    )
    r = df.iloc[0]
    valid = float(r["valid_orders"])
    return {
        "revenue": round(float(r["revenue"]), 2),
        "total_orders": int(r["total_orders"]),
        "valid_orders": int(valid),
        "avg_order_value": round(float(r["revenue"]) / valid, 2) if valid else 0.0,
        "cancellation_rate": round(float(r["cancellation_rate"] or 0), 4),
        "on_time_rate": round(float(r["on_time_rate"] or 0), 4),
        "avg_review": round(float(r["avg_review"] or 0), 3),
    }


def monthly_trend(warehouse: str | Path, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    return query_df(
        warehouse,
        f"""
        SELECT d.year_month,
               COALESCE(SUM(CASE WHEN {VALID} THEN o.items_revenue END), 0)    AS revenue,
               COUNT(*) FILTER (WHERE {VALID})                                  AS orders,
               AVG(CASE WHEN o.order_status = 'canceled' THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
               AVG(1 - o.is_late) FILTER (WHERE o.is_late IS NOT NULL)          AS on_time_rate,
               AVG(o.review_score)                                              AS avg_review
        FROM fact_orders o JOIN dim_date d USING (date_key)
        WHERE d.year_month BETWEEN ? AND ?
        GROUP BY d.year_month ORDER BY d.year_month
        """,
        _range(start, end),
    )


def revenue_by_category(
    warehouse: str | Path, start: str | None = None, end: str | None = None, top: int = 15
) -> pd.DataFrame:
    return query_df(
        warehouse,
        f"""
        SELECT p.category,
               SUM(i.price)                 AS revenue,
               COUNT(DISTINCT i.order_id)   AS orders
        FROM fact_order_items i
        JOIN fact_orders o USING (order_id)
        JOIN dim_product p USING (product_key)
        JOIN dim_date d ON d.date_key = i.date_key
        WHERE {VALID} AND d.year_month BETWEEN ? AND ?
        GROUP BY p.category ORDER BY revenue DESC LIMIT {int(top)}
        """,
        _range(start, end),
    )


def revenue_by_state(warehouse: str | Path, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    return query_df(
        warehouse,
        f"""
        SELECT c.customer_state AS state,
               SUM(o.items_revenue) AS revenue,
               COUNT(*)             AS orders
        FROM fact_orders o
        JOIN dim_customer c USING (customer_key)
        JOIN dim_date d USING (date_key)
        WHERE {VALID} AND d.year_month BETWEEN ? AND ?
        GROUP BY c.customer_state ORDER BY revenue DESC
        """,
        _range(start, end),
    )


def available_months(warehouse: str | Path) -> list[str]:
    df = query_df(
        warehouse,
        "SELECT DISTINCT d.year_month FROM fact_orders o JOIN dim_date d USING (date_key) ORDER BY 1",
    )
    return df["year_month"].tolist()
