"""Transform: clean the 9 raw tables and build the star schema.

Star schema (constellation of two facts sharing conformed dimensions):

    fact_orders        grain = one row per order       (delivery, review, payment, totals)
    fact_order_items   grain = one row per order item  (price, freight, product, seller)
    dim_customer / dim_product / dim_seller / dim_date

Payments and reviews are aggregated to ORDER grain *before* joining. Joining them straight
onto items would duplicate rows (multi-payment / multi-review orders) and inflate revenue.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

UNKNOWN_CATEGORY = "unknown"


def _surrogate(df: pd.DataFrame, natural: str, key: str) -> pd.DataFrame:
    df = df.drop_duplicates(subset=natural).sort_values(natural).reset_index(drop=True)
    df.insert(0, key, np.arange(1, len(df) + 1, dtype="int64"))
    return df


def build_dim_product(products: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    cat_map = dict(
        zip(
            translation["product_category_name"],
            translation["product_category_name_english"],
            strict=False,
        )
    )
    df = products.copy()
    df["category"] = df["product_category_name"].map(cat_map)
    # fall back to the raw (Portuguese) name, then to 'unknown'
    df["category"] = df["category"].fillna(df["product_category_name"]).fillna(UNKNOWN_CATEGORY)
    df = _surrogate(df, "product_id", "product_key")
    for col in ("product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"):
        if col not in df.columns:
            df[col] = np.nan
    return df[
        [
            "product_key",
            "product_id",
            "category",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ]
    ]


def build_dim_seller(sellers: pd.DataFrame) -> pd.DataFrame:
    df = _surrogate(sellers, "seller_id", "seller_key")
    return df[["seller_key", "seller_id", "seller_city", "seller_state"]]


def build_dim_customer(customers: pd.DataFrame) -> pd.DataFrame:
    """One row per *real* customer (customer_unique_id), not per order-scoped customer_id."""
    df = _surrogate(customers, "customer_unique_id", "customer_key")
    return df[["customer_key", "customer_unique_id", "customer_city", "customer_state"]]


def build_dim_date(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    days = pd.date_range(start.normalize(), end.normalize(), freq="D")
    return pd.DataFrame(
        {
            "date_key": days.strftime("%Y%m%d").astype("int64"),
            "date": days,
            "year": days.year.astype("int64"),
            "quarter": days.quarter.astype("int64"),
            "month": days.month.astype("int64"),
            "year_month": days.strftime("%Y-%m"),
            "day": days.day.astype("int64"),
            "day_of_week": days.dayofweek.astype("int64"),
            "is_weekend": days.dayofweek >= 5,
        }
    )


def _payments_per_order(payments: pd.DataFrame) -> pd.DataFrame:
    ordered = payments.sort_values(["order_id", "payment_value"], ascending=[True, False])
    primary = ordered.drop_duplicates("order_id")[["order_id", "payment_type"]]
    totals = payments.groupby("order_id", as_index=False).agg(
        payment_value=("payment_value", "sum"), payment_count=("payment_sequential", "count")
    )
    return totals.merge(primary, on="order_id", how="left")


def _reviews_per_order(reviews: pd.DataFrame) -> pd.DataFrame:
    valid = reviews[reviews["review_score"].between(1, 5)]
    return valid.groupby("order_id", as_index=False).agg(review_score=("review_score", "mean"))


def _items_per_order(items: pd.DataFrame) -> pd.DataFrame:
    return items.groupby("order_id", as_index=False).agg(
        items_count=("order_item_id", "count"),
        items_revenue=("price", "sum"),
        freight_total=("freight_value", "sum"),
    )


def build_star(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    orders = tables["orders"].dropna(subset=["order_purchase_timestamp"]).copy()
    orders = orders.drop_duplicates("order_id")

    dim_product = build_dim_product(tables["products"], tables["category_translation"])
    dim_seller = build_dim_seller(tables["sellers"])
    dim_customer = build_dim_customer(tables["customers"])

    # order-scoped customer_id -> real customer -> surrogate key
    cust_map = (
        tables["customers"][["customer_id", "customer_unique_id"]]
        .drop_duplicates("customer_id")
        .merge(dim_customer[["customer_key", "customer_unique_id"]], on="customer_unique_id")[
            ["customer_id", "customer_key"]
        ]
    )

    # ---- fact_orders (order grain) --------------------------------------------------
    fo = orders.merge(cust_map, on="customer_id", how="inner")
    fo = fo.merge(_items_per_order(tables["order_items"]), on="order_id", how="left")
    fo = fo.merge(_payments_per_order(tables["payments"]), on="order_id", how="left")
    fo = fo.merge(_reviews_per_order(tables["reviews"]), on="order_id", how="left")

    fo["date_key"] = fo["order_purchase_timestamp"].dt.strftime("%Y%m%d").astype("int64")
    delivered = fo["order_delivered_customer_date"].notna()
    fo["delivery_days"] = (
        fo["order_delivered_customer_date"] - fo["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    fo["delay_days"] = (
        fo["order_delivered_customer_date"] - fo["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    fo["is_late"] = pd.array(
        np.where(delivered, (fo["delay_days"] > 0).astype("int64"), pd.NA), dtype="Int64"
    )
    for col, default in (("items_count", 0), ("items_revenue", 0.0), ("freight_total", 0.0)):
        fo[col] = fo[col].fillna(default)

    fact_orders = fo[
        [
            "order_id",
            "customer_key",
            "date_key",
            "order_status",
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
            "delivery_days",
            "delay_days",
            "is_late",
            "review_score",
            "payment_type",
            "payment_value",
            "items_count",
            "items_revenue",
            "freight_total",
        ]
    ].rename(
        columns={
            "order_purchase_timestamp": "purchase_ts",
            "order_delivered_customer_date": "delivered_ts",
            "order_estimated_delivery_date": "estimated_ts",
        }
    )

    # ---- fact_order_items (item grain) ----------------------------------------------
    items = tables["order_items"].merge(
        fact_orders[["order_id", "date_key", "order_status"]], on="order_id", how="inner"
    )
    items = items.merge(dim_product[["product_key", "product_id"]], on="product_id", how="inner")
    items = items.merge(dim_seller[["seller_key", "seller_id"]], on="seller_id", how="inner")
    dropped = len(tables["order_items"]) - len(items)
    if dropped:
        log.warning("dropped %d order_items rows with orphan order/product/seller", dropped)
    fact_items = items[
        [
            "order_id",
            "order_item_id",
            "product_key",
            "seller_key",
            "date_key",
            "order_status",
            "price",
            "freight_value",
        ]
    ]

    dim_date = build_dim_date(fact_orders["purchase_ts"].min(), fact_orders["purchase_ts"].max())

    star = {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_seller": dim_seller,
        "dim_date": dim_date,
        "fact_orders": fact_orders.reset_index(drop=True),
        "fact_order_items": fact_items.reset_index(drop=True),
    }
    for name, df in star.items():
        log.info("built %-18s rows=%d", name, len(df))
    return star
