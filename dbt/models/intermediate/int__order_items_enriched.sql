{{
    config(
        materialized='view',
        tags=['intermediate']
    )
}}

/*
PURPOSE:
Item-level hub. Enriches each order item with product category, seller location,
and order-grain context (time, customer geography, delivery status, review score)
pulled from int__orders_enriched. Avoids repeating the order JOIN chain in every
category and seller mart.

GRAIN: order_id × order_item_id (one row per item per order)

SOURCES:
- stg__order_items: Base item table (price, freight, product, seller)
- stg__products: Product category and physical attributes
- stg__sellers: Seller location
- int__orders_enriched: Order-level context (time, customer_state, delivery, review)

USAGE:
Referenced by mart_sellers, mart_product_categories,
mart_monthly_revenue_by_category (marts/ai) and fct_order_items (marts/core).
*/

with order_items as (
    select * from {{ ref('stg__order_items') }}
),

products as (
    select * from {{ ref('stg__products') }}
),

sellers as (
    select * from {{ ref('stg__sellers') }}
),

orders as (
    select
        order_id,
        order_date,
        order_year,
        order_month,
        order_quarter,
        customer_state,
        is_delivered,
        is_on_time,
        review_score
    from {{ ref('int__orders_enriched') }}
)

select
    -- Composite PK
    oi.order_id,
    oi.order_item_id,

    -- Time (from order grain)
    o.order_date,
    o.order_year,
    o.order_month,
    o.order_quarter,

    -- Customer geography (denormalized for mart filtering)
    o.customer_state,

    -- Delivery status (denormalized for category-level delivery analysis)
    o.is_delivered,
    o.is_on_time,

    -- Product
    oi.product_id,
    p.product_category_name,
    p.product_category_name_english,

    -- Seller
    oi.seller_id,
    s.seller_city,
    s.seller_state,

    -- Financials
    oi.price,
    oi.freight_value,
    oi.item_revenue,

    -- Dates
    oi.shipping_limit_date,

    -- Review (order-level score repeated at item grain)
    o.review_score

from order_items oi
left join products p on oi.product_id = p.product_id
left join sellers  s on oi.seller_id  = s.seller_id
left join orders   o on oi.order_id   = o.order_id
