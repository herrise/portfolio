-- Dimension: time dimension built from staged timestamps
WITH time_src AS (
    SELECT DISTINCT
        DATE_TRUNC('hour', ingested_at) AS timestamp_utc
    FROM "pipeline"."main"."stg_prices"
    WHERE ingested_at IS NOT NULL
)
SELECT
    CAST(MD5(CAST(timestamp_utc AS VARCHAR)) AS VARCHAR) AS time_sk,
    timestamp_utc,
    EXTRACT(HOUR FROM timestamp_utc) AS hour,
    EXTRACT(DAY FROM timestamp_utc) AS day,
    EXTRACT(MONTH FROM timestamp_utc) AS month,
    EXTRACT(YEAR FROM timestamp_utc) AS year,
    EXTRACT(DOW FROM timestamp_utc) AS weekday
FROM time_src