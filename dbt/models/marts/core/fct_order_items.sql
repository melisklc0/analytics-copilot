{{
    config(tags=['core', 'fct'])
}}

/*
PURPOSE:
Item-level fact table for category and seller revenue analysis. One row per
(order_id, order_item_id). A single order can contain items from multiple
categories and sellers — this grain makes that split possible.
Join to dim_products for category breakdown, dim_sellers for seller geography.

GRAIN: one row per (order_id, order_item_id)

SOURCES:
- int__order_items_enriched: item-level data with product, seller, and order context

USAGE:
Dashboard canonical layer. Referenced by marts/dashboard presentation models.
*/

with order_items as (
    select * from {{ ref('int__order_items_enriched') }}
)

select
    -- Composite PK
    order_id,
    order_item_id,

    -- Foreign keys
    product_id,
    seller_id,
    order_date,

    -- Financials
    price,
    freight_value,
    item_revenue

from order_items
