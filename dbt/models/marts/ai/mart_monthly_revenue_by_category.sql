{{
    config(
        materialized='table',
        tags=['ai', 'mart']
    )
}}

/*
AI MART — mart_monthly_revenue_by_category
GRAIN: one row per (order_year, order_month, customer_state, product_category_name_english)
SOURCE: int__order_items_enriched

Time + geography + category triple breakdown for trend analysis. Use this instead of
mart_orders when a question involves both a time dimension and category simultaneously —
mart_orders has no category column because a single order can span multiple categories.

EXAMPLE QUESTIONS:
- "Which category had the highest revenue in SP in 2017?"
- "Is health_beauty revenue growing month over month?"
- "What is the monthly revenue trend for electronics in RJ?"
- "Which category had the most orders in Q4 2017?"
- "How did on-time delivery rates change for furniture across 2017?"
- "Which state drove the most growth in sports_leisure in 2017?"
*/

with items as (
    select * from {{ ref('int__order_items_enriched') }}
)

select
    -- Composite PK / filter dimensions
    order_year,
    order_month,
    customer_state,
    product_category_name_english,

    -- Volume
    count(distinct order_id) as orders,
    count(*) as items_sold,

    -- Financial
    round(sum(price)::numeric, 2) as gross_revenue,
    round(sum(item_revenue)::numeric, 2) as total_revenue,
    round(avg(price)::numeric, 2) as avg_price,

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
group by order_year, order_month, customer_state, product_category_name_english
