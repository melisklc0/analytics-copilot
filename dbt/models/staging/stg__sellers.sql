{{
    config(
        materialized='view',
        tags=['staging', 'atomic']
    )
}}

/*
Source: raw.sellers
Entity: Seller
Grain: one row per seller_id
*/

with source as (
    select * from {{ source('raw', 'sellers') }}
)

select
    -- Primary key
    seller_id,

    -- Location
    seller_zip_code_prefix,
    seller_city,
    seller_state

from source
