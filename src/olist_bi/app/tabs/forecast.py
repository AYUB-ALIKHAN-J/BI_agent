from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from olist_bi.analytics import forecast as fc
from olist_bi.app.common import cached_query
from olist_bi.warehouse import drilldown as dd

cats_q    = cached_query(dd.categories_by_revenue)
summary_q = cached_query(fc.forecast_categories)

_CHART = dict(
    paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
    font=dict(color="#c9d1d9", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
)
_AXES = dict(
    xaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
    yaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
)


@st.cache_data(show_spinner=False)
def _run(wh: str, mtime: float, category: str | None, metric: str):
    series = fc.monthly_series(wh, category, metric)
    return fc.forecast_series(series, horizon=3, holdout=3)


def render(wh, start: str, end: str) -> None:
    st.markdown("<div class='section-header'>Monthly Demand Forecast (Next 3 Months)</div>", unsafe_allow_html=True)
    st.caption(
        "Three models backtested on the last 3 months; best by MAPE is refit on all history. "
        "Sparse launch/cut-off months excluded."
    )

    left, right = st.columns([3, 1])
    category = left.selectbox("📂 Category", ["All categories"] + cats_q(wh)[:20], key="fc_cat")
    metric   = right.radio("Metric", ["revenue", "orders"], horizontal=True, key="fc_metric")
    cat = None if category == "All categories" else category

    try:
        r = _run(str(wh), wh.stat().st_mtime, cat, metric)
    except ValueError as exc:
        st.warning(f"Not enough history to forecast: {exc}")
        return

    # ── KPI cards ────────────────────────────────────────────────────────────
    c = st.columns(3)
    c[0].metric("🏆 Best Model",    r.best_model)
    c[1].metric("📉 Backtest MAPE", f"{r.mape:.1%}",
                delta=f"{r.mape - r.naive_mape:+.1%} vs naive", delta_color="inverse")
    c[2].metric("🔮 Next 3 Months", f"{r.forecast.sum():,.0f}")

    # ── Forecast chart ───────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_scatter(
        x=r.history.index, y=r.history.values,
        name="Actual", mode="lines+markers",
        line=dict(color="#4f8ef7", width=2),
        marker=dict(size=5),
    )
    fig.add_scatter(
        x=r.backtest.index, y=r.backtest[r.best_model],
        name="Backtest (holdout)", mode="lines+markers",
        line=dict(color="#f0883e", width=2, dash="dot"),
        marker=dict(size=6, symbol="diamond"),
    )
    fig.add_scatter(
        x=r.forecast.index, y=r.forecast.values,
        name="Forecast", mode="lines+markers",
        line=dict(color="#3fb950", width=2, dash="dash"),
        marker=dict(size=8, symbol="star"),
    )
    fig.update_layout(
        title=f"{metric.title()} Forecast — {category}",
        legend=dict(orientation="h", y=-0.25),
        **_CHART,
    )
    st.plotly_chart(fig, width="stretch")

    # ── Model accuracy table ─────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Backtest Accuracy by Model</div>", unsafe_allow_html=True)
    m = pd.DataFrame(r.metrics).T.rename_axis("model").reset_index()
    st.dataframe(
        m.style.format({"mape": "{:.1%}", "wape": "{:.1%}"}),
        hide_index=True,
        width="stretch",
    )

    with st.expander("📊 Top-10 Categories Forecast Summary"):
        st.dataframe(summary_q(wh, 10, metric, 3), hide_index=True, width="stretch")
