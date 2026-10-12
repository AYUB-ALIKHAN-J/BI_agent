"""RFM analysis: Recency, Frequency, Monetary value segmentation.

Uses K-Means clustering to segment customers into groups based on:
- R (Recency): Days since last purchase
- F (Frequency): Number of orders
- M (Monetary): Total spend
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from olist_bi.warehouse.connection import query_df


def rfm_summary(warehouse: str | Path, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Calculate RFM metrics for all customers."""
    # Get reference date (last order date in the period)
    ref_date = query_df(
        warehouse,
        f"""
        SELECT MAX(o.purchase_ts) as ref_date
        FROM fact_orders o
        JOIN dim_date d USING (date_key)
        WHERE d.year_month BETWEEN ? AND ?
        """,
        [start or "0000-00", end or "9999-99"],
    ).iloc[0, 0]

    df = query_df(
        warehouse,
        f"""
        SELECT
            c.customer_unique_id,
            c.customer_city,
            c.customer_state,
            COUNT(DISTINCT o.order_id) as frequency,
            SUM(CASE WHEN o.order_status NOT IN ('canceled', 'unavailable') THEN o.items_revenue ELSE 0 END) as monetary,
            MAX(o.purchase_ts) as last_purchase
        FROM fact_orders o
        JOIN dim_customer c USING (customer_key)
        JOIN dim_date d USING (date_key)
        WHERE d.year_month BETWEEN ? AND ?
        GROUP BY c.customer_unique_id, c.customer_city, c.customer_state
        """,
        [start or "0000-00", end or "9999-99"],
    )

    df["recency"] = (ref_date - df["last_purchase"]).dt.days
    df = df.drop(columns=["last_purchase"])

    return df


def rfm_segment(
    warehouse: str | Path,
    start: str | None = None,
    end: str | None = None,
    n_clusters: int = 5,
) -> pd.DataFrame:
    """Perform K-Means clustering on RFM metrics."""
    df = rfm_summary(warehouse, start, end)

    if len(df) < n_clusters:
        raise ValueError(f"Not enough customers ({len(df)}) for {n_clusters} clusters")

    # Scale features for K-Means
    scaler = StandardScaler()
    features = ["recency", "frequency", "monetary"]
    X = scaler.fit_transform(df[features])

    # K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X)

    # Cluster profiles
    cluster_profiles = df.groupby("cluster")[features].mean().sort_values("recency")

    # Assign cluster names based on profile
    cluster_names = {}
    for i, (cluster, row) in enumerate(cluster_profiles.iterrows()):
        if row["recency"] < df["recency"].median() and row["frequency"] > df["frequency"].median():
            name = "Champions"
        elif row["recency"] < df["recency"].median():
            name = "Recent Customers"
        elif row["frequency"] > df["frequency"].median():
            name = "Loyal Customers"
        elif row["monetary"] > df["monetary"].median():
            name = "Big Spenders"
        else:
            name = "At Risk"
        cluster_names[cluster] = name

    df["cluster_name"] = df["cluster"].map(cluster_names)

    return df


def top_segments(
    warehouse: str | Path,
    start: str | None = None,
    end: str | None = None,
    n_clusters: int = 5,
) -> pd.DataFrame:
    """Get summary statistics for each segment."""
    df = rfm_segment(warehouse, start, end, n_clusters)

    summary = df.groupby("cluster_name").agg(
        customers=("customer_unique_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum"),
    ).sort_values("total_revenue", ascending=False)

    summary["pct_customers"] = summary["customers"] / summary["customers"].sum() * 100
    summary["pct_revenue"] = summary["total_revenue"] / summary["total_revenue"].sum() * 100

    return summary.round(2)
