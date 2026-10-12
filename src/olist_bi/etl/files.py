"""Names of the 9 Olist source files and the columns we depend on."""

from __future__ import annotations

TABLE_FILES: dict[str, str] = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "customers": {"customer_id", "customer_unique_id", "customer_city", "customer_state"},
    "orders": {
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    },
    "order_items": {"order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"},
    "payments": {"order_id", "payment_sequential", "payment_type", "payment_value"},
    "reviews": {"review_id", "order_id", "review_score"},
    "products": {"product_id", "product_category_name"},
    "sellers": {"seller_id", "seller_city", "seller_state"},
    "geolocation": {"geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"},
    "category_translation": {"product_category_name", "product_category_name_english"},
}

DATE_COLUMNS: dict[str, list[str]] = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}
