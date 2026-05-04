-- Fact table: price snapshots with surrogate key references
WITH stg AS (
    SELECT * FROM {{ ref('stg_prices') }}
)
SELECT
    dt.ticker_sk,
    dtm.time_sk,
    stg.price_usd,
    stg.volume_24h,
    stg.market_cap,
    stg.price_change_24h_pct,
    stg.ingested_at AS snapshot_ts
FROM stg
LEFT JOIN {{ ref('dim_ticker') }} dt ON stg.symbol = dt.symbol
LEFT JOIN {{ ref('dim_time') }} dtm
    ON DATE_TRUNC('hour', stg.ingested_at) = dtm.timestamp_utc
WHERE dt.ticker_sk IS NOT NULL
