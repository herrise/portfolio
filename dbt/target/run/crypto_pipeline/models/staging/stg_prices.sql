
  
  create view "pipeline"."main"."stg_prices__dbt_tmp" as (
    -- Staging model: deduplicate and type-cast raw prices
WITH raw AS (
    SELECT
        symbol,
        price_usd,
        volume_24h,
        market_cap,
        price_change_24h_pct,
        market_cap_rank,
        ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY symbol, DATE_TRUNC('minute', ingested_at)
            ORDER BY ingested_at DESC
        ) AS rn
    FROM "pipeline"."main"."_raw_prices"
    WHERE price_usd IS NOT NULL
)
SELECT
    symbol,
    price_usd,
    COALESCE(volume_24h, 0) AS volume_24h,
    COALESCE(market_cap, 0) AS market_cap,
    price_change_24h_pct,
    market_cap_rank,
    ingested_at
FROM raw
WHERE rn = 1
  );
