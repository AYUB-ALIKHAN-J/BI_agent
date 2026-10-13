"""RFM Segmentation tab for Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

from olist_bi.analytics import rfm as rfm_module
from olist_bi.app.common import cached_query

summary_q = cached_query(rfm_module.top_segments)


def render(wh, start: str, end: str) -> None:
    st.subheader("Customer Segmentation (RFM + K-Means)")
    st.caption(
        "Customers grouped by Recency, Frequency, and Monetary value using K-Means clustering."
    )

    left, right = st.columns(2)
    n_clusters = left.selectbox("Number of clusters", [3, 4, 5, 6, 7], index=2, key="rfm_clusters")
    period_label = f"{start} to {end}"

    try:
        summary = summary_q(str(wh), start, end, n_clusters)
    except ValueError as exc:
        st.warning(f"Not enough data: {exc}")
        return

    if summary.empty:
        st.info("No data for the selected period")
        return

    # Display segment metrics
    st.dataframe(
        summary[
            [
                "customers",
                "pct_customers",
                "pct_revenue",
                "avg_recency",
                "avg_frequency",
                "avg_monetary",
            ]
        ],
        width="stretch",
    )

    # Visualize revenue share
    st.subheader("Revenue by Segment")
    st.bar_chart(summary["pct_revenue"].sort_index())

    # Show top customers in each segment
    with st.expander("Top customers by revenue"):
        df = rfm_module.rfm_segment(str(wh), start, end, n_clusters)
        for segment in summary.index:
            seg_df = df[df["cluster_name"] == segment].nlargest(5, "monetary")
            if not seg_df.empty:
                st.markdown(f"**{segment}**")
                st.dataframe(
                    seg_df[["customer_unique_id", "customer_state", "monetary", "frequency"]],
                    width="stretch",
                    hide_index=True,
                )
