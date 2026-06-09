{{
    config(tags=['core', 'dim'])
}}

/*
PURPOSE:
One row per product. Holds category and physical attributes.
English category name (product_category_name_english) is the primary filter dimension
used by BI tool and AI mart layer.

GRAIN: one row per product_id

SOURCES:
- stg__products: product attributes + English category translation (already joined)

USAGE:
Referenced by fct_order_items (marts/core) via product_id FK.
*/

with products as (
    select * from {{ ref('stg__products') }}
)

select
    product_id,
    product_category_name,
    product_category_name_english,
    product_weight_g,
    product_photos_qty,
    product_length_cm,
    product_height_cm,
    product_width_cm
from products
