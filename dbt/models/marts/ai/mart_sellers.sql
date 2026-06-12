{{
    config(
        materialized='table',
        tags=['ai', 'mart']
    )
}}

/*
AI MART — mart_sellers
GRAIN: one row per seller_id
SOURCE: int__order_items_enriched + int__orders_enriched (for delivery_days, customer_id)

Seller performance scorecard. Delivery reliability, satisfaction, and revenue
all in one table. AI filters by seller_state or thresholds on any metric.
distinct_customers requires the order-grain join to access customer_id.

EXAMPLE QUESTIONS:
- "Which sellers have an on-time delivery rate below 70%?"
- "What is the average review score for sellers in SP?"
- "Who are the top 10 sellers by total revenue?"
- "How many sellers have served more than 100 distinct customers?"
- "What is the average delivery time for sellers in the Northeast?"
- "Which seller state has the best on-time delivery rate?"
*/

with items as (
    select * from {{ ref('int__order_items_enriched') }}
),

orders as (
    select
        order_id,
        customer_id,
        delivery_days
    from {{ ref('int__orders_enriched') }}
)

select
    i.seller_id,
    i.seller_city,
    i.seller_state,

    -- Volume
    count(distinct i.order_id) as total_orders,
    count(distinct o.customer_id) as distinct_customers,

    -- Financial
    round(sum(i.price)::numeric, 2) as gross_revenue,
    round(sum(i.item_revenue)::numeric, 2) as total_revenue,

    -- Satisfaction
    round(avg(i.review_score)::numeric, 2) as avg_review_score,

    -- Delivery reliability
    round(
        count(case when i.is_on_time then 1 end)::numeric
        / nullif(count(case when i.is_delivered then 1 end), 0),
        4
    ) as on_time_delivery_rate,
    round(
        avg(case when i.is_delivered then o.delivery_days end)::numeric,
        1
    ) as avg_delivery_days,

    -- Tenure
    min(i.order_date) as first_sale_date

from items i
left join orders o on i.order_id = o.order_id
group by i.seller_id, i.seller_city, i.seller_state
