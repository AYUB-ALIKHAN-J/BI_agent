"""Market basket analysis using association rules (Apriori algorithm)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

from olist_bi.warehouse.connection import query_df


def basket_analysis(
    warehouse: str | Path,
    start: str | None = None,
    end: str | None = None,
    min_support: float = 0.01,
    min_threshold: float = 1.0,
) -> pd.DataFrame:
    """Find association rules between products using Apriori algorithm."""
    # Get orders with products
    df = query_df(
        warehouse,
        f"""
        SELECT
            o.order_id,
            p.category as product
        FROM fact_order_items i
        JOIN fact_orders o USING (order_id)
        JOIN dim_product p USING (product_key)
        JOIN dim_date d ON d.date_key = i.date_key
        WHERE o.order_status NOT IN ('canceled', 'unavailable')
          AND d.year_month BETWEEN ? AND ?
        """,
        [start or "0000-00", end or "9999-99"],
    )

    if len(df) == 0:
        return pd.DataFrame()

    # Create basket matrix (one row per order, one column per product)
    basket = df.groupby(["order_id", "product"]).size().unstack(fill_value=0)
    basket = basket > 0  # Convert to boolean

    if len(basket) == 0:
        return pd.DataFrame()

    # Find frequent itemsets
    frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)

    if len(frequent_itemsets) == 0:
        return pd.DataFrame()

    # Generate association rules
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_threshold)

    if len(rules) == 0:
        # No rules found - this is common when items are purchased individually
        # Return a message DataFrame
        return pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift", "conviction"])

    # Sort by lift and confidence
    rules = rules.sort_values(["lift", "confidence"], ascending=False)

    # Format output
    rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(x)))
    rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(sorted(x)))

    return rules[
        ["antecedents", "consequents", "support", "confidence", "lift", "conviction"]
    ].round(4)


def top_rules_by_category(
    warehouse: str | Path,
    start: str | None = None,
    end: str | None = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """Get top association rules grouped by antecedent category."""
    rules = basket_analysis(warehouse, start, end)

    if len(rules) == 0:
        return pd.DataFrame()

    # Group by antecedent and get best rule for each
    rules["antecedent_count"] = rules.groupby("antecedents")["support"].transform("count")
    rules = rules.sort_values(["antecedent_count", "lift"], ascending=False)

    return rules.drop_duplicates(subset=["antecedents"]).head(top_n)
