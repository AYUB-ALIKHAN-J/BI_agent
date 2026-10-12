"""Orchestrates extract -> transform -> load -> validate."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .extract import extract_all
from .load import load_warehouse
from .transform import build_star
from .validate import Check, run_checks

log = logging.getLogger(__name__)


class DataQualityError(RuntimeError):
    pass


@dataclass
class PipelineResult:
    checks: list[Check]
    row_counts: dict[str, int]
    seconds: float

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)


def run_pipeline(data_dir: Path, warehouse_path: Path, strict: bool = True) -> PipelineResult:
    t0 = time.perf_counter()
    tables = extract_all(data_dir)
    star = build_star(tables)
    load_warehouse(star, warehouse_path)
    checks = run_checks(warehouse_path, tables)
    result = PipelineResult(checks, {k: len(v) for k, v in star.items()}, time.perf_counter() - t0)
    failed = [c for c in checks if not c.passed]
    if failed and strict:
        raise DataQualityError("Data quality checks failed: " + ", ".join(c.name for c in failed))
    log.info(
        "pipeline finished in %.1fs, %d/%d checks passed",
        result.seconds,
        len(checks) - len(failed),
        len(checks),
    )
    return result
