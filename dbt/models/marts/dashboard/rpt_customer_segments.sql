{{
    config(tags=['dashboard'])
}}

/*
PURPOSE:
Dashboard: Customer Value — segment distribution and revenue contribution.
Grain: one row per (customer_state, customer_segment).

Segment logic (consistent with mart_customers in marts/ai):
  new       → total_orders = 1
  returning → total_orders = 2 or 3
  loyal     → total_orders >= 4

CHART TYPE (1): Pie Chart  — DIMENSION: customer_segment, METRIC: SUM(customer_count)
                             (answers: what % of customers are new vs loyal?)
CHART TYPE (2): Bar Chart  — X: customer_segment,
                             METRICS: SUM(customer_count), SUM(segment_revenue)
                             (answers: loyal = few customers but majority of revenue?)
CHART TYPE (3): Bar Chart  — X: customer_segment, Y: AVG(avg_total_revenue)
                             (answers: how much does a loyal customer spend vs new?)
CHART TYPE (4): Pivot Table — ROWS: customer_state, COLUMNS: customer_segment,
                              VALUES: SUM(customer_count)

FILTERS: customer_state, customer_segment
SOURCES: fct_orders × dim_customers
*/

with customer_metrics as (
    select
        c.customer_id,
        c.customer_state,
        count(f.order_id) as total_orders,
        sum(f.total_revenue) as total_revenue,
        avg(f.review_score) as avg_review_score
    from {{ ref('fct_orders') }} f
    join {{ ref('dim_customers') }} c on f.customer_id = c.customer_id
    group by c.customer_id, c.customer_state
),

segmented as (
    select
        customer_id,
        customer_state,
        total_orders,
        total_revenue,
        avg_review_score,
        case
            when total_orders = 1 then 'new'
            when total_orders between 2 and 3 then 'returning'
            else 'loyal'
        end as customer_segment
    from customer_metrics
),

aggregated as (
    select
        customer_state,
        customer_segment,
        count(customer_id) as customer_count,
        sum(total_revenue) as segment_revenue,
        avg(total_revenue) as avg_total_revenue,
        avg(total_orders) as avg_order_count,
        avg(avg_review_score) as avg_review_score
    from segmented
    group by customer_state, customer_segment
)

select
    customer_state,
    customer_segment,

    -- Volume
    customer_count,
    round(
        100.0 * customer_count / nullif(sum(customer_count) over (), 0), 1
    ) as customer_share_pct,

    -- Revenue
    round(segment_revenue::numeric, 2) as segment_revenue,
    round(
        100.0 * segment_revenue / nullif(sum(segment_revenue) over (), 0), 1
    ) as revenue_share_pct,

    -- Per-customer metrics
    round(avg_total_revenue::numeric, 2) as avg_total_revenue,
    round(avg_order_count::numeric, 1) as avg_order_count,
    round(avg_review_score::numeric, 2) as avg_review_score

from aggregated
order by customer_state, customer_segment
