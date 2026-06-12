{{
    config(
        materialized='table',
        tags=['ai', 'mart']
    )
}}

/*
AI MART — mart_payment_behavior
GRAIN: one row per (payment_type, order_year, order_month, customer_state)
SOURCE: int__orders_enriched

Payment method behavior analysis pre-aggregated across time and geography.
mart_orders can answer the same questions with GROUP BY but this table is faster
and more explicit for payment-focused queries.

EXAMPLE QUESTIONS:
- "Is average order value higher for credit card vs boleto users?"
- "What is the most popular payment method in SP?"
- "How has credit card usage changed over 2017?"
- "Which states use the most installments on average?"
- "Do boleto users leave lower review scores than credit card users?"
- "How many orders used debit card in Q1 2018?"
*/

with orders as (
    select * from {{ ref('int__orders_enriched') }}
)

select
    -- Composite PK / filter dimensions
    payment_type,
    order_year,
    order_month,
    customer_state,

    -- Volume
    count(distinct order_id) as orders,

    -- Financial
    round(sum(total_revenue)::numeric, 2) as total_revenue,
    round(avg(total_revenue)::numeric, 2) as avg_order_value,

    -- Installment behavior
    round(avg(payment_installments)::numeric, 2) as avg_installments,

    -- Satisfaction
    round(avg(review_score)::numeric, 2) as avg_review_score

from orders
where payment_type is not null
group by payment_type, order_year, order_month, customer_state
