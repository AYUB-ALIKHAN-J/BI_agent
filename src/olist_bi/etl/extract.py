"""Extract: read the 9 raw CSVs and fail fast if anything is missing or malformed."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .files import DATE_COLUMNS, REQUIRED_COLUMNS, TABLE_FILES

log = logging.getLogger(__name__)


class ExtractError(RuntimeError):
    pass


def extract_all(data_dir: Path) -> dict[str, pd.DataFrame]:
    data_dir = Path(data_dir)
    missing = [f for f in TABLE_FILES.values() if not (data_dir / f).exists()]
    if missing:
        raise ExtractError(
            f"Missing Olist files in {data_dir}: {missing}. "
            "Download the dataset from Kaggle (olistbr/brazilian-ecommerce) into this folder, "
            "or run `olist-bi synth` to generate a development dataset."
        )

    tables: dict[str, pd.DataFrame] = {}
    for name, filename in TABLE_FILES.items():
        df = pd.read_csv(data_dir / filename)
        absent = REQUIRED_COLUMNS[name] - set(df.columns)
        if absent:
            raise ExtractError(f"{filename}: missing required columns {sorted(absent)}")
        for col in DATE_COLUMNS.get(name, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        tables[name] = df
        log.info("extracted %-22s rows=%d", name, len(df))
    return tables
