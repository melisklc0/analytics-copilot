{{
    config(
        materialized='view',
        tags=['staging', 'atomic']
    )
}}

/*
Source: raw.order_items
Entity: Order Item
Grain: one row per (order_id, order_item_id)

Purpose:
- Expose item-level revenue (price + freight) as a single column
- No aggregation — totals per order are computed in intermediate/mart layers
*/

with source as (
    select * from {{ source('raw', 'order_items') }}
)

select
    -- Composite primary key
    order_id,
    order_item_id,

    -- Foreign keys
    product_id,
    seller_id,

    -- Dates
    shipping_limit_date,

    -- Financials
    price,
    freight_value,
    price + freight_value   as item_revenue

from source
