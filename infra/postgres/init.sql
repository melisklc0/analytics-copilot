-- Analytics Copilot — PostgreSQL initialization
-- Creates raw schema, Olist tables, and analyst_ro read-only role.

CREATE SCHEMA IF NOT EXISTS raw;

-- ── Customers ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id              VARCHAR(50) PRIMARY KEY,
    customer_unique_id       VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city            VARCHAR(100),
    customer_state           CHAR(2)
);

-- ── Orders ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.orders (
    order_id                        VARCHAR(50) PRIMARY KEY,
    customer_id                     VARCHAR(50) NOT NULL,
    order_status                    VARCHAR(30),
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP
);

-- ── Order Items ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id            VARCHAR(50)    NOT NULL,
    order_item_id       INTEGER        NOT NULL,
    product_id          VARCHAR(50)    NOT NULL,
    seller_id           VARCHAR(50)    NOT NULL,
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10, 2),
    freight_value       NUMERIC(10, 2),
    PRIMARY KEY (order_id, order_item_id)
);

-- ── Products ───────────────────────────────────────────────────────────────
-- Column names match the Olist CSV exactly (upstream has "lenght" typos).
-- Staging model will rename them to correct spellings.
CREATE TABLE IF NOT EXISTS raw.products (
    product_id                  VARCHAR(50) PRIMARY KEY,
    product_category_name       VARCHAR(100),
    product_name_lenght         INTEGER,
    product_description_lenght  INTEGER,
    product_photos_qty          INTEGER,
    product_weight_g            NUMERIC(10, 2),
    product_length_cm           NUMERIC(10, 2),
    product_height_cm           NUMERIC(10, 2),
    product_width_cm            NUMERIC(10, 2)
);

-- ── Sellers ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.sellers (
    seller_id              VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10),
    seller_city            VARCHAR(100),
    seller_state           CHAR(2)
);

-- ── Order Reviews ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.reviews (
    review_id               VARCHAR(50) NOT NULL,
    order_id                VARCHAR(50) NOT NULL,
    review_score            INTEGER,
    review_comment_title    VARCHAR(200),
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

-- ── Order Payments ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.payments (
    order_id             VARCHAR(50) NOT NULL,
    payment_sequential   INTEGER     NOT NULL,
    payment_type         VARCHAR(30),
    payment_installments INTEGER,
    payment_value        NUMERIC(10, 2),
    PRIMARY KEY (order_id, payment_sequential)
);

-- ── Geolocation ────────────────────────────────────────────────────────────
-- No PK — zip prefixes repeat with different lat/lng entries.
CREATE TABLE IF NOT EXISTS raw.geolocation (
    geolocation_zip_code_prefix VARCHAR(10),
    geolocation_lat             NUMERIC(12, 8),
    geolocation_lng             NUMERIC(12, 8),
    geolocation_city            VARCHAR(100),
    geolocation_state           CHAR(2)
);

-- ── Category Translation ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.category_translation (
    product_category_name         VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);

-- ── Read-only role (AI executor) ───────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analyst_ro') THEN
        CREATE ROLE analyst_ro WITH LOGIN PASSWORD 'analyst_ro' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE analytics_copilot TO analyst_ro;
GRANT USAGE ON SCHEMA raw TO analyst_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO analyst_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO analyst_ro;

-- ── Superset read-only role ────────────────────────────────────────────────
-- Used by Superset's data source connection to read dbt mart tables.
-- dbt creates the mart schemas at runtime; ALTER DEFAULT PRIVILEGES ensures
-- tables created later are automatically accessible.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'superset_ro') THEN
        CREATE ROLE superset_ro WITH LOGIN PASSWORD 'superset_ro' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE analytics_copilot TO superset_ro;

-- Pre-create schemas so default privileges take effect before dbt runs.
CREATE SCHEMA IF NOT EXISTS main_marts;
CREATE SCHEMA IF NOT EXISTS main_staging;
CREATE SCHEMA IF NOT EXISTS main_intermediate;

GRANT USAGE ON SCHEMA main_marts TO superset_ro;
GRANT USAGE ON SCHEMA main_staging TO superset_ro;
GRANT USAGE ON SCHEMA main_intermediate TO superset_ro;

-- Grant analyst_ro the same schema access (used by AI executor).
GRANT USAGE ON SCHEMA main_marts TO analyst_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA main_marts GRANT SELECT ON TABLES TO analyst_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA main_marts GRANT SELECT ON TABLES TO superset_ro;

ALTER DEFAULT PRIVILEGES IN SCHEMA main_staging GRANT SELECT ON TABLES TO analyst_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA main_intermediate GRANT SELECT ON TABLES TO analyst_ro;
