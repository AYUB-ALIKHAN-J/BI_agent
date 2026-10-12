from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src/olist_bi/app/streamlit_app.py")


def test_dashboard_renders_without_exceptions(warehouse, monkeypatch):
    monkeypatch.setenv("OLIST_WAREHOUSE_PATH", str(warehouse))
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    # Overview tab has 6 metrics; Forecast tab adds more
    assert len(at.metric) >= 6


def test_app_shows_helpful_error_without_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("OLIST_WAREHOUSE_PATH", str(tmp_path / "missing.duckdb"))
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert any("Warehouse not found" in e.value for e in at.error)
