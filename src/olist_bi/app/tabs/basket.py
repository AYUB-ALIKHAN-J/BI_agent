"""Market Basket Analysis tab."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from olist_bi.analytics import basket as basket_module
from olist_bi.app.common import cached_query

popular_q = cached_query(basket_module.popular_products)

_CHART = dict(
    paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
    font=dict(color="#c9d1d9", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
    yaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
)


def render(wh, start: str, end: str) -> None:
    st.markdown("<div class='section-header'>Market Basket Analysis</div>", unsafe_allow_html=True)
    st.caption("Association rules showing which product categories are frequently purchased together (Apriori).")

    col1, col2 = st.columns(2)
    min_support = col1.slider("Min support", 0.001, 0.05, 0.01, 0.001, key="basket_support",
                               help="Fraction of orders containing the itemset")
    min_lift    = col2.slider("Min lift",    1.0,   5.0,  1.5,  0.1,   key="basket_lift",
                               help="How much more likely items are bought together vs independently")

    try:
        rules = basket_module.basket_analysis(str(wh), start, end, min_support=min_support, min_threshold=min_lift)
    except Exception as exc:
        st.warning(f"Error analyzing baskets: {exc}")
        return

    if rules.empty:
        # ── No rules: show popular products instead ───────────────────────
        st.markdown(
            """
            <div style='background:#1e2130; border:1px solid #f0883e; border-radius:10px; padding:16px; margin:10px 0;'>
                <span style='color:#f0883e; font-weight:700;'>ℹ️ No association rules found</span><br>
                <span style='color:#8b949e; font-size:0.88rem;'>
                The Olist dataset averages 1.14 items per order — most orders contain a single item,
                so cross-category rules are rare. Showing popular categories instead.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        popular = popular_q(str(wh), start, end, 15)
        left, right = st.columns(2)

        fig = px.bar(
            popular, x="orders", y="category", orientation="h",
            title="Most Popular Categories by Orders",
            color="orders", color_continuous_scale="Blues",
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(**_CHART, coloraxis_showscale=False)
        left.plotly_chart(fig, width="stretch")

        fig2 = px.bar(
            popular, x="revenue", y="category", orientation="h",
            title="Most Popular Categories by Revenue",
            color="revenue", color_continuous_scale="Purples",
        )
        fig2.update_yaxes(autorange="reversed")
        fig2.update_layout(**_CHART, coloraxis_showscale=False)
        right.plotly_chart(fig2, width="stretch")
        return

    # ── Rules found ───────────────────────────────────────────────────────
    st.markdown(
        f"<div class='badge badge-green'>✅ {len(rules)} rules found</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>Top Association Rules</div>", unsafe_allow_html=True)
    st.dataframe(
        rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(20),
        width="stretch", hide_index=True,
        column_config={
            "support":    st.column_config.NumberColumn("Support",    format="%.4f"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.4f"),
            "lift":       st.column_config.NumberColumn("Lift",       format="%.4f"),
        },
    )

    left, right = st.columns(2)
    fig_lift = px.scatter(
        rules, x="support", y="confidence", size="lift", color="lift",
        hover_data=["antecedents", "consequents"],
        title="Support vs Confidence (size = lift)",
        color_continuous_scale="Viridis",
    )
    fig_lift.update_layout(**_CHART)
    left.plotly_chart(fig_lift, width="stretch")

    with right.expander("ℹ️ How to interpret"):
        st.markdown("""
        - **Support**: Fraction of orders containing both items
        - **Confidence**: P(consequent | antecedent)
        - **Lift**: How much more likely vs random — lift > 1 means positive association
        """)
