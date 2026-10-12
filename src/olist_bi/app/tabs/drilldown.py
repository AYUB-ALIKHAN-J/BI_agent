from __future__ import annotations

import plotly.express as px
import streamlit as st

from olist_bi.app.common import cached_query
from olist_bi.warehouse import drilldown as dd

cats_q = cached_query(dd.categories_by_revenue)
cat_monthly_q = cached_query(dd.category_monthly)
seller_q = cached_query(dd.seller_scorecard)


def render(wh, start: str, end: str) -> None:
    st.subheader("Category and seller drill-down")
    cats = cats_q(wh)
    category = st.selectbox("Category", ["All categories"] + cats, key="dd_cat")
    cat = None if category == "All categories" else category

    if cat:
        m = cat_monthly_q(wh, cat, start, end)
        st.plotly_chart(
            px.bar(m, x="year_month", y="revenue", hover_data=["orders"], title=f"Monthly revenue: {cat}"),
            use_container_width=True,
        )

    min_orders = st.slider("Minimum orders per seller", 5, 100, 30, step=5, key="dd_min")
    sc = seller_q(wh, start, end, cat, min_orders, 15)
    st.markdown("**Seller scorecard** (worst late-delivery rate first)")
    if sc.empty:
        st.info("No sellers meet the minimum-orders threshold for this selection.")
    else:
        st.dataframe(
            sc,
            use_container_width=True,
            hide_index=True,
            column_config={
                "late_rate": st.column_config.ProgressColumn(
                    "late_rate", min_value=0, max_value=1, format="%.0f%%"
                ),
            },
        )
