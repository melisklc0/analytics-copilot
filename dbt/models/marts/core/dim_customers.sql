{{
    config(tags=['core', 'dim'])
}}

/*
PURPOSE:
One row per unique customer (person). Olist's source customer_id is order-scoped;
staging renames customer_unique_id → customer_id so this dim uses the stable person key.
Holds static location only — behavioral metrics (LTV, segment) live in mart_customers.

GRAIN: one row per customer_id (person identifier)

SOURCES:
- stg__customers: provides customer_id (renamed from customer_unique_id) and location

USAGE:
Referenced by fct_orders (marts/core) via customer_id FK.
*/

with customers as (
    select * from {{ ref('stg__customers') }}
)

select distinct on (customer_id)
    customer_id,
    customer_city,
    customer_state
from customers
order by customer_id
