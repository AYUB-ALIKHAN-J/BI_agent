"""Validate: data-quality checks run against the *loaded* warehouse.

Every check returns (name, passed, detail). The pipeline fails loudly if any check fails,
because a silently wrong revenue number is the worst possible failure for a BI system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

log = logging.getLogger(__name__)


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _scalar(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).fetchone()[0]


def run_checks(warehouse_path: Path, tables: dict[str, pd.DataFrame]) -> list[Check]:
    con = duckdb.connect(str(warehouse_path), read_only=True)
    checks: list[Check] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append(Check(name, bool(passed), detail))

    try:
        # 1. Reconciliation against the raw source (the check that catches join fan-out)
        raw_orders = tables["orders"]["order_id"].nunique()
        wh_orders = _scalar(con, "SELECT COUNT(*) FROM fact_orders")
        add(
            "order_count_reconciles",
            wh_orders <= raw_orders and wh_orders > 0,
            f"warehouse={wh_orders} raw={raw_orders}",
        )

        wh_item_rev = _scalar(con, "SELECT ROUND(SUM(price), 2) FROM fact_order_items")
        wh_order_rev = _scalar(con, "SELECT ROUND(SUM(items_revenue), 2) FROM fact_orders")
        add(
            "item_vs_order_revenue_match",
            abs(wh_item_rev - wh_order_rev) < 0.5,
            f"items={wh_item_rev} orders={wh_order_rev}",
        )

        raw_rev = round(float(tables["order_items"]["price"].sum()), 2)
        add(
            "revenue_matches_raw_source",
            abs(wh_item_rev - raw_rev) / max(raw_rev, 1) < 0.001,
            f"warehouse={wh_item_rev} raw={raw_rev}",
        )

        # 2. Key integrity
        add(
            "fact_orders_pk_unique",
            _scalar(con, "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM fact_orders") == 0,
            "order_id unique",
        )
        for fk, dim in (("customer_key", "dim_customer"),):
            bad = _scalar(
                con, f"SELECT COUNT(*) FROM fact_orders f LEFT JOIN {dim} d USING ({fk}) WHERE d.{fk} IS NULL"
            )
            add(f"fk_fact_orders_{fk}", bad == 0, f"orphans={bad}")
        for fk, dim in (
            ("product_key", "dim_product"),
            ("seller_key", "dim_seller"),
            ("date_key", "dim_date"),
        ):
            bad = _scalar(
                con,
                f"SELECT COUNT(*) FROM fact_order_items f LEFT JOIN {dim} d "
                f"USING ({fk}) WHERE d.{fk} IS NULL",
            )
            add(f"fk_fact_order_items_{fk}", bad == 0, f"orphans={bad}")
        bad = _scalar(
            con,
            "SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_date d "
            "USING (date_key) WHERE d.date_key IS NULL",
        )
        add("fk_fact_orders_date_key", bad == 0, f"orphans={bad}")

        # 3. Domain rules
        bad = _scalar(
            con,
            "SELECT COUNT(*) FROM fact_orders "
            "WHERE review_score IS NOT NULL AND review_score NOT BETWEEN 1 AND 5",
        )
        add("review_score_in_range", bad == 0, f"violations={bad}")
        bad = _scalar(con, "SELECT COUNT(*) FROM fact_order_items WHERE price < 0 OR freight_value < 0")
        add("no_negative_money", bad == 0, f"violations={bad}")
        bad = _scalar(
            con,
            "SELECT COUNT(*) FROM fact_orders WHERE delivered_ts IS NOT NULL AND delivered_ts < purchase_ts",
        )
        add("delivered_after_purchase", bad == 0, f"violations={bad}")
        bad = _scalar(
            con,
            "SELECT COUNT(*) FROM fact_orders WHERE items_count = 0 "
            "AND order_status NOT IN ('canceled','unavailable','created','approved','shipped','invoiced')",
        )
        add("fulfilled_orders_have_items", bad == 0, f"violations={bad}")
    finally:
        con.close()

    for c in checks:
        (log.info if c.passed else log.error)(
            "check %-32s %s  (%s)", c.name, "PASS" if c.passed else "FAIL", c.detail
        )
    return checks
