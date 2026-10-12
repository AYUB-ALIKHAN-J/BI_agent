"""Customer-experience queries: how delivery performance drives reviews."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .connection import query_df
from .kpis import OPEN_END, OPEN_START, VALID

BUCKET_CASE = """
    CASE WHEN o.delay_days <= -3 THEN '1. Early (3+ days)'
         WHEN o.delay_days <= 0  THEN '2. On time'
         WHEN o.delay_days <= 3  THEN '3. Late 1-3 days'
         WHEN o.delay_days <= 7  THEN '4. Late 4-7 days'
         WHEN o.delay_days <= 14 THEN '5. Late 8-14 days'
         ELSE '6. Late 15+ days' END
"""


def review_by_delay_bucket(
    warehouse: str | Path, start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    return query_df(
        warehouse,
        f"""
        SELECT {BUCKET_CASE} AS bucket,
               COUNT(*)                                              AS orders,
               ROUND(AVG(o.review_score), 3)                         AS avg_review,
               ROUND(AVG(CASE WHEN o.review_score <= 2 THEN 1.0 ELSE 0.0 END), 3) AS pct_low_review
        FROM fact_orders o JOIN dim_date d USING (date_key)
        WHERE o.delay_days IS NOT NULL AND o.review_score IS NOT NULL
          AND d.year_month BETWEEN ? AND ?
        GROUP BY 1 ORDER BY 1
        """,
        [start or OPEN_START, end or OPEN_END],
    )


def delivery_by_state(
    warehouse: str | Path, start: str | None = None, end: str | None = None, min_orders: int = 50
) -> pd.DataFrame:
    return query_df(
        warehouse,
        """
        SELECT c.customer_state AS state,
               COUNT(*)                                       AS orders,
               ROUND(AVG(1 - o.is_late), 3)                   AS on_time_rate,
               ROUND(AVG(o.delivery_days), 1)                 AS avg_delivery_days,
               ROUND(AVG(o.review_score), 2)                  AS avg_review
        FROM fact_orders o
        JOIN dim_customer c USING (customer_key)
        JOIN dim_date d USING (date_key)
        WHERE o.is_late IS NOT NULL AND d.year_month BETWEEN ? AND ?
        GROUP BY 1 HAVING COUNT(*) >= ? ORDER BY on_time_rate
        """,
        [start or OPEN_START, end or OPEN_END, int(min_orders)],
    )


def delivery_days_distribution(
    warehouse: str | Path, start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    return query_df(
        warehouse,
        f"""
        SELECT LEAST(CAST(FLOOR(o.delivery_days) AS INTEGER), 40) AS days, COUNT(*) AS orders
        FROM fact_orders o JOIN dim_date d USING (date_key)
        WHERE o.delivery_days IS NOT NULL AND {VALID} AND d.year_month BETWEEN ? AND ?
        GROUP BY 1 ORDER BY 1
        """,
        [start or OPEN_START, end or OPEN_END],
    )
