
  
  create view "pipeline"."main"."stg_tickers__dbt_tmp" as (
    -- Staging model: deduplicated ticker metadata
WITH raw AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        market_cap_rank,
        ingested_at
    FROM "pipeline"."main"."_raw_prices"
    WHERE symbol IS NOT NULL
    ORDER BY symbol, ingested_at DESC
)
SELECT
    MD5(CAST(symbol AS VARCHAR)) AS ticker_sk,
    symbol,
    'crypto' AS asset_type,
    market_cap_rank
FROM raw
  );
