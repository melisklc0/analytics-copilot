{{
    config(tags=['dashboard'])
}}

/*
PURPOSE:
Dashboard: Category Performance — revenue, quality, and delivery breakdown by product category.
Grain: one row per product_category_name_english.

CHART TYPE (1): Bar Chart (horizontal) — X: product_category_name_english, Y: gross_revenue
                                          LIMIT 10, sorted DESC
                                          (answers: which categories drive the most revenue?)
CHART TYPE (2): Bar Chart (horizontal) — X: product_category_name_english, Y: avg_review_score
                                          sorted ASC (worst first)
                                          (answers: which categories have quality/satisfaction issues?)
CHART TYPE (3): Bar Chart (horizontal) — X: product_category_name_english, Y: on_time_delivery_rate
                                          sorted ASC (worst first)
                                          (answers: which categories have delivery problems?)
CHART TYPE (4): Scatter Plot           — X: avg_review_score, Y: gross_revenue,
                                          SERIES: product_category_name_english
                                          (answers: high revenue but low quality = risk categories)

FILTERS: product_category_name_english
SOURCES: fct_order_items × fct_orders × dim_products
*/

with items as (
    select
        fi.order_id,
        fi.product_id,
        fi.price,
        fi.item_revenue,
        fo.is_delivered,
        fo.is_on_time,
        fo.review_score
    from {{ ref('fct_order_items') }} fi
    join {{ ref('fct_orders') }} fo on fi.order_id = fo.order_id
),

enriched as (
    select
        coalesce(p.product_category_name_english, 'uncategorized') as product_category_name_english,
        i.order_id,
        i.price,
        i.item_revenue,
        i.is_delivered,
        i.is_on_time,
        i.review_score
    from items i
    left join {{ ref('dim_products') }} p on i.product_id = p.product_id
)

select
    product_category_name_english,

    -- Volume
    count(distinct order_id) as total_orders,
    count(*) as total_items_sold,

    -- Revenue
    round(sum(price)::numeric, 2) as gross_revenue,
    round(sum(item_revenue)::numeric, 2) as total_revenue,
    round(avg(price)::numeric, 2) as avg_price,
    round(
        100.0 * sum(item_revenue) / nullif(sum(sum(item_revenue)) over (), 0), 1
    ) as revenue_share_pct,

    -- Quality
    round(avg(review_score)::numeric, 2) as avg_review_score,

    -- Delivery
    round(
        100.0 * sum(case when is_on_time then 1 else 0 end)
        / nullif(sum(case when is_delivered then 1 else 0 end), 0), 1
    ) as on_time_delivery_rate

from enriched
group by product_category_name_english
order by gross_revenue desc
