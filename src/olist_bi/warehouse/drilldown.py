"""Drill-down helpers: reliable-month detection, category series, seller scorecard.

Shared by the dashboard, the forecasting module and (Iteration 4) the agent tools.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .connection import query_df
from .kpis import OPEN_END, OPEN_START, VALID


def select_reliable(orders_per_month: pd.Series, min_share: float = 0.10) -> list[str]:
    """Months whose order count is at least `min_share` of the median month.

    Olist has near-empty tails (2016 launch months, Sep/Oct 2018 cut-off). Plotting or
    forecasting them produces fake collapses, so analyses default to the reliable window.
    """
    if orders_per_month.empty:
        return []
    threshold = float(orders_per_month.median()) * min_share
    return sorted(orders_per_month[orders_per_month >= threshold].index.tolist())


def reliable_months(warehouse: str | Path, min_share: float = 0.10) -> list[str]:
    df = query_df(
        warehouse,
        "SELECT d.year_month, COUNT(*) AS orders FROM fact_orders o "
        "JOIN dim_date d USING (date_key) GROUP BY 1 ORDER BY 1",
    )
    return select_reliable(df.set_index("year_month")["orders"], min_share)


def categories_by_revenue(warehouse: str | Path, top: int = 100) -> list[str]:
    df = query_df(
        warehouse,
        f"""SELECT p.category, SUM(i.price) AS revenue
            FROM fact_order_items i JOIN fact_orders o USING (order_id)
            JOIN dim_product p USING (product_key)
            WHERE {VALID} GROUP BY 1 ORDER BY 2 DESC LIMIT {int(top)}""",
    )
    return df["category"].tolist()


def category_monthly(
    warehouse: str | Path, category: str, start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    """Monthly revenue and order count for one category (valid orders only)."""
    return query_df(
        warehouse,
        f"""
        SELECT d.year_month,
               SUM(i.price)               AS revenue,
               COUNT(DISTINCT i.order_id) AS orders
        FROM fact_order_items i
        JOIN fact_orders o USING (order_id)
        JOIN dim_product p USING (product_key)
        JOIN dim_date d ON d.date_key = i.date_key
        WHERE {VALID} AND p.category = ? AND d.year_month BETWEEN ? AND ?
        GROUP BY d.year_month ORDER BY d.year_month
        """,
        [category, start or OPEN_START, end or OPEN_END],
    )


def seller_scorecard(
    warehouse: str | Path,
    start: str | None = None,
    end: str | None = None,
    category: str | None = None,
    min_orders: int = 30,
    top: int = 15,
) -> pd.DataFrame:
    """Sellers ranked by late-delivery rate (worst first), with revenue and review score."""
    cat_clause = "AND p.category = ?" if category else ""
    params: list = [start or OPEN_START, end or OPEN_END]
    if category:
        params.append(category)
    params += [int(min_orders)]
    return query_df(
        warehouse,
        f"""
        WITH s AS (
            SELECT i.seller_key, i.order_id, SUM(i.price) AS revenue
            FROM fact_order_items i
            JOIN dim_product p USING (product_key)
            JOIN dim_date d ON d.date_key = i.date_key
            WHERE d.year_month BETWEEN ? AND ? {cat_clause}
            GROUP BY 1, 2
        )
        SELECT sel.seller_id, sel.seller_state,
               COUNT(*)                                                       AS orders,
               ROUND(SUM(s.revenue), 2)                                       AS revenue,
               ROUND(AVG(o.is_late) FILTER (WHERE o.is_late IS NOT NULL) * 100, 1) AS late_rate,
               ROUND(AVG(o.review_score), 2)                                  AS avg_review
        FROM s
        JOIN fact_orders o USING (order_id)
        JOIN dim_seller sel USING (seller_key)
        WHERE {VALID}
        GROUP BY 1, 2
        HAVING COUNT(*) >= ?
        ORDER BY late_rate DESC NULLS LAST, orders DESC
        LIMIT {int(top)}
        """,
        params,
    )
