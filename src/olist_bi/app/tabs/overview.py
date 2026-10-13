from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from olist_bi.app.common import cached_query
from olist_bi.warehouse import kpis

headline = cached_query(kpis.headline_kpis)
trend_q  = cached_query(kpis.monthly_trend)
cat_q    = cached_query(kpis.revenue_by_category)
state_q  = cached_query(kpis.revenue_by_state)

_CHART = dict(
    paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
    font=dict(color="#c9d1d9", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
)
_AXES = dict(
    xaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
    yaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
)


def render(wh, start: str, end: str) -> None:
    k = headline(wh, start, end)

    # ── KPI cards ────────────────────────────────────────────────────────────
    c = st.columns(6)
    c[0].metric("💰 Revenue",        f"R$ {k['revenue']:,.0f}")
    c[1].metric("📦 Orders",         f"{k['valid_orders']:,}")
    c[2].metric("🛍️ Avg Order Value", f"R$ {k['avg_order_value']:,.2f}")
    c[3].metric("❌ Cancellation",   f"{k['cancellation_rate']:.1%}")
    c[4].metric("🚚 On-time",        f"{k['on_time_rate']:.1%}")
    c[5].metric("⭐ Avg Review",     f"{k['avg_review']:.2f} / 5")

    st.markdown("<div class='section-header'>Revenue & Satisfaction Trends</div>", unsafe_allow_html=True)

    trend = trend_q(wh, start, end)
    left, right = st.columns(2)

    # Revenue line
    fig_rev = px.area(
        trend, x="year_month", y="revenue",
        title="Monthly Revenue",
        color_discrete_sequence=["#4f8ef7"],
    )
    fig_rev.update_traces(fill="tozeroy", fillcolor="rgba(79,142,247,0.15)")
    fig_rev.update_layout(**_CHART, **_AXES)
    left.plotly_chart(fig_rev, width="stretch")

    # Dual axis: on-time + review
    dual = go.Figure()
    dual.add_scatter(x=trend["year_month"], y=trend["on_time_rate"],
                     name="On-time rate", mode="lines+markers",
                     line=dict(color="#3fb950", width=2), yaxis="y")
    dual.add_scatter(x=trend["year_month"], y=trend["avg_review"],
                     name="Avg review", mode="lines+markers",
                     line=dict(color="#f0883e", width=2, dash="dot"), yaxis="y2")
    dual_layout = {
        **_CHART,
        "title": "Delivery & Satisfaction",
        "xaxis": dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
        "yaxis": dict(title="On-time rate", tickformat=".0%", range=[0, 1.05], gridcolor="#2a2d3e"),
        "yaxis2": dict(title="Avg review", overlaying="y", side="right", range=[1, 5], gridcolor="#2a2d3e"),
        "legend": dict(orientation="h", y=-0.25),
    }
    dual.update_layout(**dual_layout)
    right.plotly_chart(dual, width="stretch")

    st.markdown("<div class='section-header'>Revenue Breakdown</div>", unsafe_allow_html=True)

    left, right = st.columns(2)
    cat = cat_q(wh, start, end)
    fig_cat = px.bar(
        cat, x="revenue", y="category", orientation="h",
        title="Top Categories by Revenue",
        color="revenue", color_continuous_scale="Blues",
    )
    fig_cat.update_yaxes(autorange="reversed")
    fig_cat.update_layout(**_CHART, **_AXES, coloraxis_showscale=False)
    left.plotly_chart(fig_cat, width="stretch")

    fig_state = px.bar(
        state_q(wh, start, end).head(15), x="state", y="revenue",
        title="Revenue by Customer State",
        color="revenue", color_continuous_scale="Purples",
    )
    fig_state.update_layout(**_CHART, **_AXES, coloraxis_showscale=False)
    right.plotly_chart(fig_state, width="stretch")
