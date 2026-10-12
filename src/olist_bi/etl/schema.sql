-- Star schema DDL (DuckDB). Applied by etl/load.py on every full refresh.

CREATE TABLE dim_customer (
    customer_key        BIGINT PRIMARY KEY,
    customer_unique_id  VARCHAR NOT NULL,
    customer_city       VARCHAR,
    customer_state      VARCHAR
);

CREATE TABLE dim_product (
    product_key         BIGINT PRIMARY KEY,
    product_id          VARCHAR NOT NULL,
    category            VARCHAR NOT NULL,
    product_weight_g    DOUBLE,
    product_length_cm   DOUBLE,
    product_height_cm   DOUBLE,
    product_width_cm    DOUBLE
);

CREATE TABLE dim_seller (
    seller_key          BIGINT PRIMARY KEY,
    seller_id           VARCHAR NOT NULL,
    seller_city         VARCHAR,
    seller_state        VARCHAR
);

CREATE TABLE dim_date (
    date_key            BIGINT PRIMARY KEY,
    date                DATE NOT NULL,
    year                BIGINT,
    quarter             BIGINT,
    month               BIGINT,
    year_month          VARCHAR,
    day                 BIGINT,
    day_of_week         BIGINT,
    is_weekend          BOOLEAN
);

CREATE TABLE fact_orders (
    order_id            VARCHAR PRIMARY KEY,
    customer_key        BIGINT NOT NULL,
    date_key            BIGINT NOT NULL,
    order_status        VARCHAR NOT NULL,
    purchase_ts         TIMESTAMP NOT NULL,
    delivered_ts        TIMESTAMP,
    estimated_ts        TIMESTAMP,
    delivery_days       DOUBLE,
    delay_days          DOUBLE,
    is_late             TINYINT,
    review_score        DOUBLE,
    payment_type        VARCHAR,
    payment_value       DOUBLE,
    items_count         BIGINT,
    items_revenue       DOUBLE,
    freight_total       DOUBLE
);

CREATE TABLE fact_order_items (
    order_id            VARCHAR NOT NULL,
    order_item_id       BIGINT NOT NULL,
    product_key         BIGINT NOT NULL,
    seller_key          BIGINT NOT NULL,
    date_key            BIGINT NOT NULL,
    order_status        VARCHAR NOT NULL,
    price               DOUBLE NOT NULL,
    freight_value       DOUBLE NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS etl_runs (
    run_id              BIGINT,
    run_ts              TIMESTAMP,
    table_name          VARCHAR,
    row_count           BIGINT
);
