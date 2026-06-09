{{
    config(
        materialized='view',
        tags=['staging', 'atomic']
    )
}}

/*
Source: raw.reviews
Entity: Order Review
Grain: one row per (review_id, order_id)

Note: review_id is not unique in the source (same review can appear on
      multiple orders). The composite PK mirrors the raw table definition.
*/

with source as (
    select * from {{ source('raw', 'reviews') }}
)

select
    -- Composite primary key
    review_id,
    order_id,

    -- Score
    review_score,

    -- Comment
    review_comment_title,
    review_comment_message,
    review_comment_title is not null
        or review_comment_message is not null   as has_comment,

    -- Timestamps
    review_creation_date,
    review_answer_timestamp

from source
