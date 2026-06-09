{{
    config(tags=['core', 'dim'])
}}

/*
PURPOSE:
One row per seller. Holds static location attributes.
Performance metrics (on-time rate, avg review) live in mart_sellers.

GRAIN: one row per seller_id

SOURCES:
- stg__sellers: seller identity and location

USAGE:
Referenced by fct_order_items (marts/core) via seller_id FK.
*/

with sellers as (
    select * from {{ ref('stg__sellers') }}
)

select
    seller_id,
    seller_city,
    seller_state
from sellers
