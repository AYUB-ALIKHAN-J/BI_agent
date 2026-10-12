from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import duckdb
import pandas as pd


class WarehouseNotFound(FileNotFoundError):
    pass


@contextmanager
def connect(warehouse_path: str | Path):
    """Read-only connection. The app and the agent must never be able to modify the warehouse."""
    path = Path(warehouse_path)
    if not path.exists():
        raise WarehouseNotFound(f"Warehouse not found at {path}. Run `olist-bi etl` (or `make etl`) first.")
    con = duckdb.connect(str(path), read_only=True)
    try:
        yield con
    finally:
        con.close()


def query_df(warehouse_path: str | Path, sql: str, params: list | None = None) -> pd.DataFrame:
    with connect(warehouse_path) as con:
        return con.execute(sql, params or []).df()
