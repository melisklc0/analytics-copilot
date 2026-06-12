{{
    config(
        materialized='table',
        tags=['ai', 'mart']
    )
}}

/*
AI MART — mart_product_categories
GRAIN: one row per product_category_name_english
SOURCE: int__order_items_enriched

Category-level comparative analysis across all time. For time-series or geography-sliced
category analysis use mart_monthly_revenue_by_category instead.

EXAMPLE QUESTIONS:
- "Which category has the lowest average review score?"
- "What is the total revenue for the health_beauty category?"
- "Which 5 categories have the highest on-time delivery rate?"
- "What is the average price per item in the computers_accessories category?"
- "Which category has sold the most distinct products?"
- "Which categories have both high revenue and low review scores?"
*/

with items as (
    select * from {{ ref('int__order_items_enriched') }}
)

select
    product_category_name_english,

    -- Volume
    count(distinct product_id) as total_products,
    count(distinct order_id) as total_orders,
    count(*) as total_items_sold,

    -- Financial
    round(sum(price)::numeric, 2) as gross_revenue,
    round(avg(price)::numeric, 2) as avg_price,
    round(avg(freight_value)::numeric, 2) as avg_freight_value,

    -- Satisfaction
    round(avg(review_score)::numeric, 2) as avg_review_score,

    -- Delivery reliability
    round(
        count(case when is_on_time then 1 end)::numeric
        / nullif(count(case when is_delivered then 1 end), 0),
        4
    ) as on_time_delivery_rate

from items
where product_category_name_english is not null
group by product_category_name_english
