"""RFM Segmentation tab."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from olist_bi.analytics import rfm as rfm_module
from olist_bi.app.common import cached_query

summary_q = cached_query(rfm_module.top_segments)

_CHART = dict(
    paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
    font=dict(color="#c9d1d9", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
    yaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
)

_SEGMENT_COLORS = {
    "Champions":        "#3fb950",
    "Loyal Customers":  "#4f8ef7",
    "Recent Customers": "#f0883e",
    "Big Spenders":     "#bc8cff",
    "At Risk":          "#f85149",
}


def render(wh, start: str, end: str) -> None:
    st.markdown("<div class='section-header'>Customer Segmentation — RFM + K-Means</div>", unsafe_allow_html=True)
    st.caption("Customers grouped by Recency, Frequency, and Monetary value using K-Means clustering.")

    col1, col2 = st.columns([2, 4])
    n_clusters = col1.selectbox("Number of segments", [3, 4, 5, 6, 7], index=2, key="rfm_clusters")

    try:
        summary = summary_q(str(wh), start, end, n_clusters)
    except ValueError as exc:
        st.warning(f"Not enough data: {exc}")
        return

    if summary.empty:
        st.info("No data for the selected period.")
        return

    # ── Segment KPI cards ────────────────────────────────────────────────────
    cols = st.columns(len(summary))
    for i, (seg, row) in enumerate(summary.iterrows()):
        color = _SEGMENT_COLORS.get(seg, "#8b949e")
        cols[i].markdown(
            f"""
            <div style='background:#1e2130; border:1px solid {color}; border-radius:12px;
                        padding:14px; text-align:center;'>
                <div style='color:{color}; font-weight:700; font-size:0.85rem;'>{seg}</div>
                <div style='color:#e6edf3; font-size:1.4rem; font-weight:700;'>{int(row["customers"]):,}</div>
                <div style='color:#8b949e; font-size:0.75rem;'>customers</div>
                <div style='color:{color}; font-size:0.9rem; margin-top:6px;'>{row["pct_revenue"]:.1f}% revenue</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ───────────────────────────────────────────────────────────────
    left, right = st.columns(2)

    fig_rev = px.pie(
        summary.reset_index(), values="pct_revenue", names="cluster_name",
        title="Revenue Share by Segment",
        color="cluster_name",
        color_discrete_map=_SEGMENT_COLORS,
        hole=0.45,
    )
    fig_rev.update_layout(**_CHART)
    left.plotly_chart(fig_rev, width="stretch")

    fig_cust = px.bar(
        summary.reset_index(), x="cluster_name", y="customers",
        title="Customers per Segment",
        color="cluster_name",
        color_discrete_map=_SEGMENT_COLORS,
    )
    fig_cust.update_layout(**_CHART, showlegend=False)
    right.plotly_chart(fig_cust, width="stretch")

    # ── Summary table ────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Segment Profiles</div>", unsafe_allow_html=True)
    st.dataframe(
        summary[["customers", "pct_customers", "pct_revenue", "avg_recency", "avg_frequency", "avg_monetary"]],
        width="stretch",
        column_config={
            "pct_customers": st.column_config.NumberColumn("% Customers", format="%.1f%%"),
            "pct_revenue":   st.column_config.NumberColumn("% Revenue",   format="%.1f%%"),
            "avg_recency":   st.column_config.NumberColumn("Avg Recency (days)", format="%.0f"),
            "avg_frequency": st.column_config.NumberColumn("Avg Orders",  format="%.1f"),
            "avg_monetary":  st.column_config.NumberColumn("Avg Spend (R$)", format="R$ %.0f"),
        },
    )

    with st.expander("🔍 Top customers by segment"):
        df = rfm_module.rfm_segment(str(wh), start, end, n_clusters)
        for seg in summary.index:
            seg_df = df[df["cluster_name"] == seg].nlargest(5, "monetary")
            if not seg_df.empty:
                color = _SEGMENT_COLORS.get(seg, "#8b949e")
                st.markdown(f"<span style='color:{color}; font-weight:700;'>● {seg}</span>", unsafe_allow_html=True)
                st.dataframe(
                    seg_df[["customer_unique_id", "customer_state", "monetary", "frequency", "recency"]],
                    width="stretch", hide_index=True,
                    column_config={
                        "monetary":  st.column_config.NumberColumn("Spend (R$)", format="R$ %.0f"),
                        "recency":   st.column_config.NumberColumn("Recency (days)", format="%.0f"),
                    },
                )
