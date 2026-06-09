{{
    config(
        materialized='view',
        tags=['staging', 'atomic']
    )
}}

/*
Source: raw.customers
Entity: Customer
Grain: one row per customer_order_key

Naming note: the source table uses customer_id as an order-scoped surrogate
and customer_unique_id as the true person identifier. We flip the names here
so that customer_id means "the person" throughout the project.
  customer_order_key  — joins to stg__orders.customer_order_key
  customer_id         — stable person identifier, use for repeat-buyer analysis
*/

with source as (
    select * from {{ source('raw', 'customers') }}
)

select

    -- Person identifier (renamed from source customer_unique_id)
    customer_unique_id  as customer_id,

    -- Order-scoped join key (renamed from source customer_id)
    customer_id         as customer_order_key,

    -- Location
    customer_zip_code_prefix,
    customer_city,
    customer_state

from source
