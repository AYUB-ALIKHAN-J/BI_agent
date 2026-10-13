from __future__ import annotations

import plotly.express as px
import streamlit as st

from olist_bi.app.common import cached_query
from olist_bi.warehouse import cx

bucket_q = cached_query(cx.review_by_delay_bucket)
state_q  = cached_query(cx.delivery_by_state)
dist_q   = cached_query(cx.delivery_days_distribution)

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
    st.markdown(
        "<div class='section-header'>Does late delivery hurt customer satisfaction?</div>",
        unsafe_allow_html=True,
    )

    b = bucket_q(wh, start, end)
    if b.empty:
        st.info("No delivered orders with reviews in this period.")
        return

    on_time = b[b["bucket"].str[0].isin(["1", "2"])]
    late    = b[~b["bucket"].str[0].isin(["1", "2"])]

    if not late.empty and not on_time.empty:
        a  = (on_time["avg_review"] * on_time["orders"]).sum() / on_time["orders"].sum()
        l_ = (late["avg_review"]    * late["orders"]).sum()    / late["orders"].sum()
        c  = st.columns(4)
        c[0].metric("⭐ On-time review",  f"{a:.2f}")
        c[1].metric("⭐ Late review",     f"{l_:.2f}", delta=f"{l_ - a:.2f}", delta_color="inverse")
        c[2].metric("⏰ Late order share", f"{late['orders'].sum() / b['orders'].sum():.1%}")
        c[3].metric("📦 Total orders",    f"{b['orders'].sum():,}")

    st.markdown("<div class='section-header'>Review Score by Delivery Delay</div>", unsafe_allow_html=True)

    left, right = st.columns(2)

    fig_review = px.bar(
        b, x="bucket", y="avg_review", text="avg_review",
        title="Avg Review by Delivery Delay",
        range_y=[0, 5],
        color="avg_review",
        color_continuous_scale=["#f85149", "#f0883e", "#3fb950"],
    )
    fig_review.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig_review.update_layout(**_CHART, **_AXES, coloraxis_showscale=False)
    left.plotly_chart(fig_review, width="stretch")

    fig_low = px.bar(
        b, x="bucket", y="pct_low_review",
        title="Share of 1-2 Star Reviews",
        color="pct_low_review",
        color_continuous_scale=["#3fb950", "#f0883e", "#f85149"],
    )
    fig_low.update_yaxes(tickformat=".0%")
    fig_low.update_layout(**_CHART, **_AXES, coloraxis_showscale=False)
    right.plotly_chart(fig_low, width="stretch")

    st.markdown("<div class='section-header'>Delivery Performance by State</div>", unsafe_allow_html=True)

    left, right = st.columns(2)
    s = state_q(wh, start, end)

    s_ranked = s.sort_values("on_time_rate", ascending=True).reset_index(drop=True)
    fig_state = px.bar(
        s_ranked,
        x="on_time_rate",
        y="state",
        orientation="h",
        title="On-time Rate by State",
        color="on_time_rate",
        color_continuous_scale=["#f85149", "#f0883e", "#3fb950"],
        text=s_ranked["on_time_rate"].map(lambda v: f"{v:.0%}"),
    )
    fig_state.add_vline(x=0.9, line_dash="dash", line_color="#8b949e", annotation_text="90% target")
    fig_state.update_traces(textposition="outside", cliponaxis=False)
    fig_state.update_xaxes(tickformat=".0%", range=[0, 1.05])
    fig_state.update_yaxes(categoryorder="total ascending")
    fig_state.update_layout(**_CHART, showlegend=False, xaxis_title="On-time rate", yaxis_title="State")
    left.plotly_chart(fig_state, width="stretch")

    fig_dist = px.bar(
        dist_q(wh, start, end), x="days", y="orders",
        title="Delivery Time Distribution (days)",
        color_discrete_sequence=["#4f8ef7"],
    )
    fig_dist.update_layout(**_CHART, **_AXES)
    right.plotly_chart(fig_dist, width="stretch")
