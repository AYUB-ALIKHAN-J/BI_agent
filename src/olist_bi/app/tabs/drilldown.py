from __future__ import annotations

import plotly.express as px
import streamlit as st

from olist_bi.app.common import cached_query
from olist_bi.warehouse import drilldown as dd

cats_q       = cached_query(dd.categories_by_revenue)
cat_monthly_q = cached_query(dd.category_monthly)
seller_q     = cached_query(dd.seller_scorecard)

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
    st.markdown("<div class='section-header'>Category & Seller Drill-down</div>", unsafe_allow_html=True)

    cats = cats_q(wh)
    col1, col2 = st.columns([3, 1])
    category = col1.selectbox("📂 Category", ["All categories"] + cats, key="dd_cat")
    cat = None if category == "All categories" else category

    if cat:
        m = cat_monthly_q(wh, cat, start, end)
        fig = px.bar(
            m, x="year_month", y="revenue",
            hover_data=["orders"],
            title=f"Monthly Revenue — {cat}",
            color_discrete_sequence=["#4f8ef7"],
        )
        fig.update_layout(**_CHART, **_AXES)
        st.plotly_chart(fig, width="stretch")

    st.markdown("<div class='section-header'>Seller Scorecard</div>", unsafe_allow_html=True)

    min_orders = st.slider("Minimum orders per seller", 5, 100, 30, step=5, key="dd_min")
    sc = seller_q(wh, start, end, cat, min_orders, 15)

    if sc.empty:
        st.info("No sellers meet the minimum-orders threshold for this selection.")
    else:
        # Color late_rate column
        st.dataframe(
            sc,
            width="stretch",
            hide_index=True,
            column_config={
                "late_rate": st.column_config.ProgressColumn(
                    "Late Rate", min_value=0, max_value=1, format="%.0f%%"
                ),
                "avg_review": st.column_config.NumberColumn("Avg Review", format="%.2f ⭐"),
                "revenue": st.column_config.NumberColumn("Revenue (R$)", format="R$ %.0f"),
            },
        )
