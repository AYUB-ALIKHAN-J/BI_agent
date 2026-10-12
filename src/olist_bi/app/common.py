"""Shared Streamlit helpers."""

from __future__ import annotations

import functools
from pathlib import Path

import streamlit as st


def cached_query(fn):
    """Cache a warehouse query. The warehouse file's mtime is part of the key, so a fresh ETL
    run invalidates the cache automatically."""

    key = f"{fn.__module__}.{fn.__qualname__}"

    # `key` is part of the cache key. Without it every query shares one inner function and
    # streamlit would return one query's result for another when the arguments match.
    @st.cache_data(show_spinner=False)
    def _cached(key: str, wh: str, mtime: float, *args, **kwargs):  # noqa: ARG001
        return fn(wh, *args, **kwargs)

    @functools.wraps(fn)
    def wrapper(wh: str | Path, *args, **kwargs):
        wh = Path(wh)
        return _cached(key, str(wh), wh.stat().st_mtime, *args, **kwargs)

    return wrapper
