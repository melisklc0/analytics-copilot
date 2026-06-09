{{
    config(
        materialized='view',
        tags=['staging', 'atomic']
    )
}}

/*
Source: raw.orders
Entity: Order
Grain: one row per order_id

Purpose:
- Rename customer_id to customer_order_key (order-scoped surrogate)
- Cast estimated_delivery_date to DATE
- Add is_delivered flag (readable alias for order_status check)
*/

with source as (
    select * from {{ source('raw', 'orders') }}
)

select
    -- Primary key
    order_id,

    -- Foreign keys
    customer_id as customer_order_key,

    -- Status
    order_status,

    case
        when order_status = 'delivered' then true
        else false
    end as is_delivered,

    -- Timestamps (time component is meaningful)
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,

    -- Date (always midnight in source — time component carries no information)
    order_estimated_delivery_date::date as order_estimated_delivery_date

from source
