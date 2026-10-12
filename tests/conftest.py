import pytest

from olist_bi.etl.pipeline import run_pipeline
from olist_bi.synthetic import generate


@pytest.fixture(scope="session")
def raw_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("raw")
    generate(d, n_orders=1500, seed=7)
    return d


@pytest.fixture(scope="session")
def warehouse(raw_dir, tmp_path_factory):
    path = tmp_path_factory.mktemp("wh") / "test.duckdb"
    run_pipeline(raw_dir, path, strict=True)
    return path
