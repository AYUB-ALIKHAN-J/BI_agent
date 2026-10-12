import pandas as pd
import pytest

from olist_bi.etl.extract import ExtractError, extract_all
from olist_bi.etl.transform import build_star
from olist_bi.warehouse.connection import query_df


def test_extract_fails_clearly_when_files_missing(tmp_path):
    with pytest.raises(ExtractError, match="Missing Olist files"):
        extract_all(tmp_path)


def test_all_quality_checks_pass(raw_dir, tmp_path):
    from olist_bi.etl.pipeline import run_pipeline

    result = run_pipeline(raw_dir, tmp_path / "w.duckdb")
    assert result.ok and len(result.checks) >= 10


def test_no_revenue_fanout_from_multi_payment_orders(raw_dir, warehouse):
    raw = extract_all(raw_dir)
    assert (raw["payments"].groupby("order_id").size() > 1).any(), "fixture must have splits"
    wh = query_df(warehouse, "SELECT SUM(price) s FROM fact_order_items").iloc[0, 0]
    assert wh == pytest.approx(raw["order_items"]["price"].sum(), rel=1e-6)


def test_one_review_row_per_order(raw_dir, warehouse):
    raw = extract_all(raw_dir)
    assert raw["reviews"]["order_id"].duplicated().any(), "fixture must have double reviews"
    dup = query_df(warehouse, "SELECT COUNT(*)-COUNT(DISTINCT order_id) d FROM fact_orders")
    assert dup.iloc[0, 0] == 0


def test_missing_category_translation_falls_back(raw_dir):
    star = build_star(extract_all(raw_dir))
    cats = set(star["dim_product"]["category"])
    assert "unknown" in cats and "pc_gamer" in cats and "health_beauty" in cats


def test_is_late_is_null_for_undelivered(warehouse):
    df = query_df(warehouse, "SELECT is_late, delivered_ts FROM fact_orders")
    assert df.loc[df["delivered_ts"].isna(), "is_late"].isna().all()
    assert df.loc[df["delivered_ts"].notna(), "is_late"].notna().all()


def test_dim_date_is_continuous(warehouse):
    d = query_df(warehouse, "SELECT date FROM dim_date ORDER BY date")["date"]
    assert (pd.to_datetime(d).diff().dropna() == pd.Timedelta(days=1)).all()
