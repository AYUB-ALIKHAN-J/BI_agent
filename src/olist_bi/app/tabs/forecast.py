from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from olist_bi.analytics import forecast as fc
from olist_bi.app.common import cached_query
from olist_bi.warehouse import drilldown as dd

cats_q = cached_query(dd.categories_by_revenue)
summary_q = cached_query(fc.forecast_categories)


@st.cache_data(show_spinner=False)
def _run(wh: str, mtime: float, category: str | None, metric: str):
    series = fc.monthly_series(wh, category, metric)
    return fc.forecast_series(series, horizon=3, holdout=3)


def render(wh, start: str, end: str) -> None:  # noqa: ARG001 - forecast uses the full reliable window
    st.subheader("Monthly demand forecast (next 3 months)")
    st.caption(
        "Trained on the reliable window only (sparse launch/cut-off months excluded). Three models are "
        "backtested on the last 3 months; the best by MAPE is refit and used. Naive = last month."
    )
    left, right = st.columns(2)
    category = left.selectbox("Category", ["All categories"] + cats_q(wh)[:20], key="fc_cat")
    metric = right.radio("Metric", ["revenue", "orders"], horizontal=True, key="fc_metric")
    cat = None if category == "All categories" else category

    try:
        r = _run(str(wh), wh.stat().st_mtime, cat, metric)
    except ValueError as exc:
        st.warning(f"Not enough history to forecast: {exc}")
        return

    c = st.columns(3)
    c[0].metric("Best model", r.best_model)
    c[1].metric(
        "Backtest MAPE",
        f"{r.mape:.1%}",
        delta=f"{r.mape - r.naive_mape:+.1%} vs naive",
        delta_color="inverse",
    )
    c[2].metric("Next 3 months", f"{r.forecast.sum():,.0f}")

    fig = go.Figure()
    fig.add_scatter(x=r.history.index, y=r.history.values, name="Actual", mode="lines+markers")
    fig.add_scatter(
        x=r.backtest.index,
        y=r.backtest[r.best_model],
        name="Backtest (holdout)",
        mode="lines+markers",
        line={"dash": "dot"},
    )
    fig.add_scatter(
        x=r.forecast.index, y=r.forecast.values, name="Forecast", mode="lines+markers", line={"dash": "dash"}
    )
    fig.update_layout(title=f"{metric.title()} - {category}", legend={"orientation": "h", "y": -0.2})
    st.plotly_chart(fig, width="stretch")

    m = pd.DataFrame(r.metrics).T.rename_axis("model").reset_index()
    st.markdown("**Backtest accuracy by model** (last 3 months held out)")
    st.dataframe(m.style.format({"mape": "{:.1%}", "wape": "{:.1%}"}), hide_index=True)

    with st.expander("Top-10 categories: forecast summary"):
        st.dataframe(summary_q(wh, 10, metric, 3), hide_index=True, width="stretch")
