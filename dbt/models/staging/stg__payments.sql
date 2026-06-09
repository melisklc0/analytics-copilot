{{
    config(
        materialized='view',
        tags=['staging', 'atomic']
    )
}}

with source as (
    select * from {{ source('raw', 'payments') }}
)

select
    -- Keys
    order_id,
    payment_sequential,

    -- Payment details
    payment_type,
    payment_installments,
    payment_value

from source
