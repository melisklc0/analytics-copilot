{{
    config(tags=['core', 'dim'])
}}

/*
PURPOSE:
Standard calendar dimension for BI tool time intelligence.
fct_orders and fct_order_items join here via order_date_key (order_date).

GRAIN: one row per calendar date — range derived from min/max order_purchase_timestamp
in the source orders table, so no hardcoded dates.

SOURCES:
- stg__orders: provides the actual date range of the dataset
- generate_series: PostgreSQL native, produces one row per day

USAGE:
Referenced by fct_orders, fct_order_items (marts/core).
Not used by AI mart layer — AI uses pre-computed order_year/order_month columns instead.
*/

with date_range as (
    select
        min(order_purchase_timestamp)::date as start_date,
        max(order_purchase_timestamp)::date as end_date
    from {{ ref('stg__orders') }}
)

select
    date_day::date as date_day,
    extract(year from date_day)::int as year,
    extract(quarter from date_day)::int as quarter,
    extract(month from date_day)::int as month,
    trim(to_char(date_day, 'Month')) as month_name,
    extract(week from date_day)::int as week_of_year,
    extract(isodow from date_day)::int as day_of_week,
    trim(to_char(date_day, 'Day')) as day_name,
    extract(isodow  from date_day) in (6, 7) as is_weekend

from date_range,
    generate_series(start_date, end_date, '1 day'::interval) as t(date_day)
