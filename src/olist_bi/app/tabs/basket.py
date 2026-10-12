"""Market Basket Analysis tab for Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

from olist_bi.analytics import basket as basket_module
from olist_bi.app.common import cached_query

rules_q = cached_query(basket_module.top_rules_by_category)


def render(wh, start: str, end: str) -> None:
    st.subheader("Market Basket Analysis")
    st.caption(
        "Association rules showing which products are frequently purchased together (Apriori algorithm)."
    )

    left, right = st.columns(2)
    min_support = left.slider("Min support", 0.001, 0.05, 0.01, 0.001, key="basket_support")
    min_lift = right.slider("Min lift", 1.0, 5.0, 1.5, 0.1, key="basket_lift")

    try:
        rules = basket_module.basket_analysis(
            str(wh), start, end, min_support=min_support, min_threshold=min_lift
        )
    except Exception as exc:
        st.warning(f"Error analyzing baskets: {exc}")
        return

    if rules.empty:
        st.info("No association rules found for the selected parameters")
        return

    st.caption(f"Found {len(rules)} association rules")

    # Display top rules
    st.subheader("Top Association Rules")
    st.dataframe(
        rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(20),
        use_container_width=True,
        hide_index=True,
    )

    # Rule interpretation
    with st.expander("How to interpret"):
        st.markdown(
            """
            - **Antecedents**: Products in the first part of the rule (if)
            - **Consequents**: Products in the second part (then)
            - **Support**: Fraction of orders containing both antecedents and consequents
            - **Confidence**: Probability of consequent given antecedent
            - **Lift**: How much more likely consequent is when antecedent is present
            """
        )

    # Category breakdown
    with st.expander("Top rules by category"):
        top_rules = rules_q(str(wh), start, end, 10)
        if not top_rules.empty:
            st.dataframe(top_rules, use_container_width=True, hide_index=True)
