{{
    config(
        materialized='table',
        tags=['ai', 'mart']
    )
}}

/*
AI MART — mart_customers
GRAIN: one row per customer_id (person)
SOURCE: int__orders_enriched

Customer lifecycle and LTV questions. Segment label is pre-computed so AI can filter
directly with WHERE customer_segment = 'loyal'. Location columns are denormalized
from the customer's most recent order — AI writes no JOINs.

EXAMPLE QUESTIONS:
- "How many customers are in the loyal segment?"
- "What is the average lifetime revenue for customers in RJ?"
- "How many customers have made only one purchase?"
- "Which state has the highest average order value per customer?"
- "What is the average review score for returning customers?"
- "Which segment contributes the most total revenue?"
*/

with orders as (
    select * from {{ ref('int__orders_enriched') }}
),

customer_metrics as (
    select
        customer_id,
        -- Location: most recent order's city/state as canonical
        (array_agg(customer_state order by order_date desc))[1] as customer_state,
        (array_agg(customer_city order by order_date desc))[1] as customer_city,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        count(distinct order_id) as total_orders,
        sum(total_revenue) as total_revenue,
        avg(total_revenue) as avg_order_value,
        avg(review_score) as avg_review_score
    from orders
    where customer_id is not null
    group by customer_id
)

select
    customer_id,
    customer_city,
    customer_state,
    first_order_date,
    last_order_date,
    total_orders,
    round(total_revenue::numeric, 2) as total_revenue,
    round(avg_order_value::numeric, 2) as avg_order_value,
    round(avg_review_score::numeric, 2) as avg_review_score,

    -- Segment: new (1 order), returning (2–3 orders), loyal (4+ orders)
    case
        when total_orders = 1 then 'new'
        when total_orders between 2 and 3 then 'returning'
        else 'loyal'
    end as customer_segment

from customer_metrics
