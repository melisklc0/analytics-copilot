{{
    config(tags=['dashboard'])
}}

/*
PURPOSE:
Dashboard: Payment Method Mix — long-format payment breakdown.
Grain: one row per (payment_type, order_year, order_month, customer_state).

CHART TYPE (1): Pie Chart  — DIMENSION: payment_type, METRIC: SUM(orders)
CHART TYPE (2): Bar Chart  — X: payment_type, Y: AVG(avg_order_value)
                              (shows which payment method drives higher order value)
CHART TYPE (3): Line Chart — X: order_month_start (TEMPORAL), Y: SUM(orders), GROUPBY: payment_type
                              (shows payment method share trend over time)

FILTERS: order_year, order_month, customer_state, payment_type
SOURCES: fct_orders × dim_customers
*/

with orders as (
    select
        f.payment_type,
        extract(year  from f.order_date)::int as order_year,
        extract(month from f.order_date)::int as order_month,
        c.customer_state,
        f.total_revenue
    from {{ ref('fct_orders') }} f
    join {{ ref('dim_customers') }} c on f.customer_id = c.customer_id
    where f.payment_type is not null
)

select
    payment_type,
    order_year,
    order_month,
    make_date(order_year, order_month, 1) as order_month_start,
    customer_state,
    'BR-' || customer_state as state_iso_3166,

    count(*) as orders,
    round(sum(total_revenue)::numeric, 2) as total_revenue,
    round((sum(total_revenue) / nullif(count(*), 0))::numeric, 2) as avg_order_value

from orders
group by payment_type, order_year, order_month, customer_state
order by payment_type, order_year, order_month, customer_state
