"""Load: full-refresh the DuckDB warehouse from the star-schema DataFrames."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
STAR_TABLES = [
    "fact_order_items",
    "fact_orders",
    "dim_date",
    "dim_seller",
    "dim_product",
    "dim_customer",
]


def load_warehouse(star: dict[str, pd.DataFrame], warehouse_path: Path) -> None:
    warehouse_path = Path(warehouse_path)
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse_path))
    try:
        for table in STAR_TABLES:
            con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(SCHEMA_PATH.read_text())

        # dims first, then facts
        for table in reversed(STAR_TABLES):
            df = star[table]
            con.register("_stage", df)
            con.execute(f"INSERT INTO {table} BY NAME SELECT * FROM _stage")
            con.unregister("_stage")
            log.info("loaded %-18s rows=%d", table, len(df))

        run_id = con.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM etl_runs").fetchone()[0]
        now = datetime.now()
        for table in reversed(STAR_TABLES):
            con.execute("INSERT INTO etl_runs VALUES (?, ?, ?, ?)", [run_id, now, table, len(star[table])])
    finally:
        con.close()
