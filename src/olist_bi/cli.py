"""Command line entry point:  olist-bi <command>"""

from __future__ import annotations

import argparse
import sys

from .config import get_settings
from .logging_setup import setup_logging


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(prog="olist-bi", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_synth = sub.add_parser("synth", help="generate a synthetic Olist-shaped dev dataset")
    p_synth.add_argument("--orders", type=int, default=6000)
    p_synth.add_argument("--seed", type=int, default=42)
    p_synth.add_argument("--out", default=str(settings.data_dir))

    p_etl = sub.add_parser("etl", help="build the star-schema warehouse from data/raw")
    p_etl.add_argument("--data-dir", default=str(settings.data_dir))
    p_etl.add_argument("--warehouse", default=str(settings.warehouse_path))
    p_etl.add_argument("--no-strict", action="store_true", help="don't fail on check errors")

    p_kpi = sub.add_parser("kpis", help="print headline KPIs from the warehouse")
    p_kpi.add_argument("--warehouse", default=str(settings.warehouse_path))

    args = parser.parse_args(argv)
    setup_logging(settings.log_level)

    if args.cmd == "synth":
        from .synthetic import generate

        generate(args.out, n_orders=args.orders, seed=args.seed)
        print(f"Synthetic dataset written to {args.out}")
        return 0

    if args.cmd == "etl":
        from .etl.pipeline import run_pipeline

        result = run_pipeline(args.data_dir, args.warehouse, strict=not args.no_strict)
        for c in result.checks:
            print(f"[{'PASS' if c.passed else 'FAIL'}] {c.name:<34} {c.detail}")
        print(f"\nRows: {result.row_counts}\nDone in {result.seconds:.1f}s")
        return 0 if result.ok else 1

    if args.cmd == "kpis":
        from .warehouse import kpis

        for k, v in kpis.headline_kpis(args.warehouse).items():
            print(f"{k:<22} {v}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
