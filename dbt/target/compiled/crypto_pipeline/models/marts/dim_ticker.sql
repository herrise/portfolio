-- Dimension: unique tickers with surrogate keys
WITH stg AS (
    SELECT * FROM "pipeline"."main"."stg_tickers"
)
SELECT
    ticker_sk,
    symbol,
    asset_type,
    market_cap_rank,
    CASE
        WHEN market_cap_rank <= 10 THEN 'Top 10'
        WHEN market_cap_rank <= 50 THEN 'Top 50'
        WHEN market_cap_rank <= 100 THEN 'Top 100'
        ELSE 'Other'
    END AS rank_tier
FROM stg