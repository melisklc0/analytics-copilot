{{
    config(
        materialized='view',
        tags=['intermediate']
    )
}}

/*
PURPOSE:
Central order hub. Joins order, customer, item aggregates, payment, and review data
into a single row per order. All downstream mart models are fed from this model
or int__order_items_enriched — never directly from staging.

GRAIN: order_id (one row per order)

SOURCES:
- stg__orders: Order lifecycle and timestamps
- stg__customers: Customer identity and location
- stg__order_items: Item-level financials (aggregated to order grain here)
- stg__payments: Payment method and installments (aggregated to order grain here)
- stg__reviews: Customer satisfaction score (deduplicated to order grain here)

USAGE:
Referenced by mart_orders, mart_customers, mart_payment_behavior (marts/ai)
and fct_orders, dim_customers (marts/core).
*/

with orders as (
    select * from {{ ref('stg__orders') }}
),

customers as (
    select * from {{ ref('stg__customers') }}
),

items_agg as (
    select
        order_id,
        count(*) as total_items,
        sum(price) as gross_revenue,
        sum(freight_value) as total_freight
    from {{ ref('stg__order_items') }}
    group by order_id
),

payments_by_type as (
    select
        order_id,
        payment_type,
        sum(payment_value) as payment_value_by_type,
        max(payment_installments) as installments_by_type
    from {{ ref('stg__payments') }}
    group by order_id, payment_type
),

payments_agg as (
    -- dominant payment type: highest total payment_value wins (DISTINCT ON + ORDER BY)
    select distinct on (order_id)
        order_id,
        payment_type as payment_type,
        installments_by_type as payment_installments,
        sum(payment_value_by_type) over (partition by order_id) as total_payment_value
    from payments_by_type
    order by order_id, payment_value_by_type desc
),

reviews_agg as (
    -- one review per order; latest answer wins; review_id breaks ties deterministically
    select distinct on (order_id)
        order_id,
        review_score
    from {{ ref('stg__reviews') }}
    order by
        order_id,
        review_answer_timestamp desc nulls last,
        review_creation_date desc nulls last,
        review_id
)

select
    -- Keys
    o.order_id,
    c.customer_id,
    o.customer_order_key,

    -- Customer location
    c.customer_city,
    c.customer_state,

    -- Order status
    o.order_status,
    o.is_delivered,

    -- Time
    o.order_purchase_timestamp::date as order_date,
    extract(year  from o.order_purchase_timestamp)::int as order_year,
    extract(month from o.order_purchase_timestamp)::int as order_month,

    -- Delivery metrics (only meaningful for delivered orders)
    case
        when o.is_delivered
        then o.order_delivered_customer_date::date - o.order_purchase_timestamp::date
    end as delivery_days,

    (o.order_estimated_delivery_date - o.order_purchase_timestamp::date) as estimated_delivery_days,

    case
        when o.is_delivered
        then o.order_delivered_customer_date::date - o.order_estimated_delivery_date
    end as days_late,

    case
        when o.is_delivered
        then o.order_delivered_customer_date::date <= o.order_estimated_delivery_date
    end as is_on_time,

    -- Item aggregates
    coalesce(i.total_items,    0) as total_items,
    coalesce(i.gross_revenue,  0) as gross_revenue,
    coalesce(i.total_freight,  0) as total_freight,
    coalesce(i.gross_revenue,  0)
        + coalesce(i.total_freight, 0) as total_revenue,

    -- Payment
    p.payment_type,
    coalesce(p.payment_installments, 0) as payment_installments,
    coalesce(p.total_payment_value,  0.0) as total_payment_value,

    -- Review
    r.review_score,
    r.review_score is not null as has_review

from orders o
left join customers c on o.customer_order_key = c.customer_order_key
left join items_agg i on o.order_id = i.order_id
left join payments_agg p on o.order_id = p.order_id
left join reviews_agg  r on o.order_id = r.order_id
