{{
    config(
        materialized='view',
        tags=['staging', 'atomic']
    )
}}

/*
Source: raw.products + raw.category_translation
Entity: Product
Grain: one row per product_id

Purpose:
- Fix upstream typos: product_name_lenght → product_name_length,
  product_description_lenght → product_description_length
- Enrich with English category name via lookup join (1:1, grain unchanged)
*/

with source as (
    select * from {{ source('raw', 'products') }}
),

category as (
    select * from {{ source('raw', 'category_translation') }}
)

select
    -- Primary key
    p.product_id,

    -- Category (Portuguese kept for reference, English used downstream)
    p.product_category_name,
    c.product_category_name_english,

    -- Dimensions (typos corrected)
    p.product_name_lenght           as product_name_length,
    p.product_description_lenght    as product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm

from source p
left join category c
    on p.product_category_name = c.product_category_name
