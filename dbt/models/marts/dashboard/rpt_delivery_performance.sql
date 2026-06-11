{{
    config(tags=['dashboard'])
}}

/*
PURPOSE:
Dashboard: Delivery Performance — operational KPI breakdown by time and geography.
Grain: one row per (order_year, order_month, customer_state).

CHART TYPE (1): Line Chart — X: order_month_start (TEMPORAL), Y: AVG(on_time_delivery_rate)
CHART TYPE (2): Bar Chart  — X: customer_state,
                              METRICS: avg_review_score_on_time, avg_review_score_late
                              (2 metrics on same chart → Superset renders as grouped bars automatically)
CHART TYPE (3): Bar Chart  — X: customer_state (horizontal), Y: AVG(avg_delivery_days)
                              → Country Map alternative: ENTITY: state_iso_3166, METRIC: AVG(avg_delivery_days)
CHART TYPE (4): Line Chart — X: order_month_start (TEMPORAL), Y: AVG(avg_days_from_estimate)
                              (positive = late, negative = early — reference line at 0)

FILTERS: order_year, order_month, customer_state
SOURCES: fct_orders × dim_customers
*/

with orders as (
    select
        extract(year from f.order_date)::int as order_year,
        extract(month from f.order_date)::int as order_month,
        c.customer_state,
        f.is_delivered,
        f.is_on_time,
        f.delivery_days,
        f.days_from_estimate,
        f.review_score
    from {{ ref('fct_orders') }} f
    join {{ ref('dim_customers') }} c on f.customer_id = c.customer_id
)

select
    order_year,
    order_month,
    make_date(order_year, order_month, 1) as order_month_start,
    customer_state,
    'BR-' || customer_state as state_iso_3166,

    -- Volume
    sum(case when is_delivered then 1 else 0 end) as delivered_orders,

    -- On-time rate (% of delivered orders that arrived on or before estimate)
    round(
        100.0 * sum(case when is_on_time then 1 else 0 end)
        / nullif(sum(case when is_delivered then 1 else 0 end), 0),
        1
    ) as on_time_delivery_rate,

    -- Delivery timing — delivered orders only
    round(avg(case when is_delivered then delivery_days end)::numeric, 1) as avg_delivery_days,
    round(avg(case when is_delivered then days_from_estimate end)::numeric, 1) as avg_days_from_estimate,

    -- Review score split: on-time vs late
    round(avg(case when is_on_time then review_score end)::numeric, 2) as avg_review_score_on_time,
    round(avg(case when is_delivered and not is_on_time then review_score end)::numeric, 2) as avg_review_score_late

from orders
group by order_year, order_month, customer_state
order by order_year, order_month, customer_state
