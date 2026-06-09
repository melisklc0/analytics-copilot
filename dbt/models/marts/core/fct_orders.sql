{{
    config(tags=['core', 'fct'])
}}

/*
PURPOSE:
Primary fact table for dashboard order analysis. One row per order with delivery
performance, revenue, satisfaction, and payment metrics. Join to dim_customers,
dim_dates, dim_sellers in BI tool for segmented analysis.
For category-level analysis use fct_order_items — a single order can span
multiple categories so category is intentionally absent here.

GRAIN: one row per order_id

SOURCES:
- int__orders_enriched: all order-level metrics pre-joined and aggregated

USAGE:
Dashboard canonical layer. Referenced by marts/dashboard presentation models.
*/

with orders as (
    select * from {{ ref('int__orders_enriched') }}
)

select
    -- Keys
    order_id,
    customer_id,
    order_date,

    -- Status
    order_status,
    is_delivered,
    is_on_time,

    -- Items
    total_items,

    -- Financials
    gross_revenue,
    total_freight,
    total_revenue,

    -- Delivery
    delivery_days,
    days_from_estimate,

    -- Payment
    payment_type,
    payment_installments,

    -- Satisfaction
    review_score

from orders
