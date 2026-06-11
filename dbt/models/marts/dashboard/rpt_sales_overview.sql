{{
    config(tags=['dashboard'])
}}

/*
PURPOSE:
Dashboard: Sales Overview — GMV, order volume, and payment mix.
Grain: one row per (order_year, order_month, customer_state).

CHART TYPE (1): Big Number (×3) — METRICS: SUM(gross_revenue), SUM(orders_placed), AVG(avg_order_value)
CHART TYPE (2): Line Chart     — X: order_month_start (TEMPORAL), Y: SUM(gross_revenue)
CHART TYPE (3): Country Map    — ENTITY: state_iso_3166, METRIC: SUM(orders_placed)
CHART TYPE (4): Big Number (×3)— METRICS: AVG(credit_card_share), AVG(boleto_share), AVG(voucher_share)
                                  → for Pie Chart use rpt_payment_mix instead

FILTERS: order_year, order_month, customer_state
SOURCES: fct_orders × dim_customers
*/

with orders as (
    select
        extract(year  from f.order_date)::int as order_year,
        extract(month from f.order_date)::int as order_month,
        c.customer_state,
        f.gross_revenue,
        f.total_revenue,
        f.is_delivered,
        f.payment_type
    from {{ ref('fct_orders') }} f
    join {{ ref('dim_customers') }} c on f.customer_id = c.customer_id
)

select
    order_year,
    order_month,
    make_date(order_year, order_month, 1) as order_month_start,
    customer_state,
    'BR-' || customer_state                                                as state_iso_3166,

    -- Volume
    count(*) as orders_placed,
    sum(case when is_delivered then 1 else 0 end) as orders_delivered,

    -- Revenue
    round(sum(gross_revenue)::numeric, 2) as gross_revenue,
    round(sum(total_revenue)::numeric, 2) as total_revenue,
    round((sum(total_revenue) / nullif(count(*), 0))::numeric, 2) as avg_order_value,

    -- Payment method share (% of orders by count)
    round(
        100.0 * sum(case when payment_type = 'credit_card' then 1 else 0 end)
        / nullif(count(*), 0), 1
    ) as credit_card_share,
    round(
        100.0 * sum(case when payment_type = 'boleto' then 1 else 0 end)
        / nullif(count(*), 0), 1
    ) as boleto_share,
    round(
        100.0 * sum(case when payment_type = 'voucher' then 1 else 0 end)
        / nullif(count(*), 0), 1
    ) as voucher_share

from orders
group by order_year, order_month, customer_state
order by order_year, order_month, customer_state
