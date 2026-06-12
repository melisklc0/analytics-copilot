{{
    config(
        materialized='table',
        tags=['ai', 'mart']
    )
}}

/*
AI MART — mart_orders
GRAIN: one row per order_id
SOURCE: int__orders_enriched

AI layer queries this table for any order-level question. All filter dimensions are
denormalized — AI writes only SELECT / WHERE / GROUP BY / ORDER BY / LIMIT, no JOINs.

EXAMPLE QUESTIONS:
- "How many orders were placed in November 2017?"
- "What is the average order value for credit card payments?"
- "What percentage of orders in SP were delivered on time?"
- "Do late deliveries correlate with lower review scores?"
- "What is the average delivery time for orders from RJ customers?"
- "How many orders had a review score below 3?"
- "Which state placed the most orders in 2017?"
*/

with source as (
    select * from {{ ref('int__orders_enriched') }}
)

select
    -- Keys
    order_id,
    customer_id,
    customer_city,
    customer_state,

    -- Order status
    order_status,
    is_delivered,
    is_on_time,

    -- Time filter dimensions
    order_date,
    order_year,
    order_month,

    -- Item count
    total_items,

    -- Financial metrics
    gross_revenue,
    total_freight,
    total_revenue,

    -- Delivery metrics (NULL for non-delivered orders)
    delivery_days,
    estimated_delivery_days,
    days_from_estimate,

    -- Payment
    payment_type,
    payment_installments,

    -- Satisfaction
    review_score,
    has_review

from source
