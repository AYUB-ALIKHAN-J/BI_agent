from __future__ import annotations

import plotly.express as px
import streamlit as st

from olist_bi.app.common import cached_query
from olist_bi.warehouse import cx

bucket_q = cached_query(cx.review_by_delay_bucket)
state_q = cached_query(cx.delivery_by_state)
dist_q = cached_query(cx.delivery_days_distribution)


def render(wh, start: str, end: str) -> None:
    st.subheader("Does late delivery hurt customer satisfaction?")
    b = bucket_q(wh, start, end)
    if b.empty:
        st.info("No delivered orders with reviews in this period.")
        return

    on_time = b[b["bucket"].str[0].isin(["1", "2"])]
    late = b[~b["bucket"].str[0].isin(["1", "2"])]
    if not late.empty and not on_time.empty:
        a = (on_time["avg_review"] * on_time["orders"]).sum() / on_time["orders"].sum()
        l_ = (late["avg_review"] * late["orders"]).sum() / late["orders"].sum()
        c = st.columns(3)
        c[0].metric("Avg review - on time", f"{a:.2f}")
        c[1].metric("Avg review - late", f"{l_:.2f}", delta=f"{l_ - a:.2f}", delta_color="inverse")
        c[2].metric("Late orders", f"{late['orders'].sum() / b['orders'].sum():.1%}")

    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            b,
            x="bucket",
            y="avg_review",
            text="avg_review",
            title="Avg review by delivery delay",
            range_y=[0, 5],
        ),
        width="stretch",
    )
    right.plotly_chart(
        px.bar(
            b,
            x="bucket",
            y="pct_low_review",
            title="Share of 1-2 star reviews",
        ).update_yaxes(tickformat=".0%"),
        width="stretch",
    )

    left, right = st.columns(2)
    s = state_q(wh, start, end)
    left.plotly_chart(
        px.bar(
            s,
            x="state",
            y="on_time_rate",
            title="On-time rate by customer state (worst first)",
        ).update_yaxes(tickformat=".0%", range=[0, 1]),
        width="stretch",
    )
    right.plotly_chart(
        px.bar(
            dist_q(wh, start, end), x="days", y="orders", title="Delivery time distribution (days, 40 = 40+)"
        ),
        width="stretch",
    )
