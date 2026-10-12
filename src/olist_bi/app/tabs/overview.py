from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from olist_bi.app.common import cached_query
from olist_bi.warehouse import kpis

headline = cached_query(kpis.headline_kpis)
trend_q = cached_query(kpis.monthly_trend)
cat_q = cached_query(kpis.revenue_by_category)
state_q = cached_query(kpis.revenue_by_state)


def render(wh, start: str, end: str) -> None:
    k = headline(wh, start, end)
    c = st.columns(6)
    c[0].metric("Revenue", f"R$ {k['revenue']:,.0f}")
    c[1].metric("Orders", f"{k['valid_orders']:,}")
    c[2].metric("Avg order value", f"R$ {k['avg_order_value']:,.2f}")
    c[3].metric("Cancellation rate", f"{k['cancellation_rate']:.1%}")
    c[4].metric("On-time delivery", f"{k['on_time_rate']:.1%}")
    c[5].metric("Avg review", f"{k['avg_review']:.2f} / 5")

    trend = trend_q(wh, start, end)
    left, right = st.columns(2)
    left.plotly_chart(
        px.line(trend, x="year_month", y="revenue", markers=True, title="Monthly revenue"),
        use_container_width=True,
    )
    dual = go.Figure()
    dual.add_scatter(
        x=trend["year_month"], y=trend["on_time_rate"], name="On-time rate", mode="lines+markers", yaxis="y"
    )
    dual.add_scatter(
        x=trend["year_month"],
        y=trend["avg_review"],
        name="Avg review (1-5)",
        mode="lines+markers",
        yaxis="y2",
    )
    dual.update_layout(
        title="Delivery & satisfaction",
        yaxis={"title": "On-time rate", "tickformat": ".0%", "range": [0, 1.02]},
        yaxis2={"title": "Avg review", "overlaying": "y", "side": "right", "range": [1, 5]},
        legend={"orientation": "h", "y": -0.2},
    )
    right.plotly_chart(dual, use_container_width=True)

    left, right = st.columns(2)
    cat = cat_q(wh, start, end)
    left.plotly_chart(
        px.bar(cat, x="revenue", y="category", orientation="h", title="Top categories").update_yaxes(
            autorange="reversed"
        ),
        use_container_width=True,
    )
    right.plotly_chart(
        px.bar(state_q(wh, start, end), x="state", y="revenue", title="Revenue by customer state"),
        use_container_width=True,
    )
