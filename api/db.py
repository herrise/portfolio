"""Database connectors — DuckDB for batch, Redis for speed layer."""
import os
import json
import duckdb
import redis
import logging

log = logging.getLogger(__name__)

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/app/data/pipeline.duckdb")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_duckdb():
    return duckdb.connect(DUCKDB_PATH, read_only=True)


def get_speed_data():
    keys = r.keys("ticker:*")
    results = []
    for k in keys:
        raw = r.get(k)
        if raw:
            results.append(json.loads(raw))
    results.sort(key=lambda x: x.get("market_cap_rank") or 99999)
    return results


def get_batch_latest():
    con = get_duckdb()
    try:
        rows = con.execute("""
            WITH latest AS (
                SELECT DISTINCT ON (symbol)
                    symbol,
                    price_usd,
                    volume_24h,
                    market_cap,
                    price_change_24h_pct,
                    market_cap_rank,
                    ingested_at AS snapshot_ts
                FROM _raw_prices
                ORDER BY symbol, ingested_at DESC
            )
            SELECT * FROM latest ORDER BY COALESCE(market_cap_rank, 99999)
        """).fetchall()
    except Exception as e:
        log.warning("batch query failed: %s", e)
        rows = []
    con.close()
    return [
        {
            "symbol": r[0],
            "price_usd": r[1],
            "volume_24h": r[2],
            "market_cap": r[3],
            "price_change_24h_pct": r[4],
            "market_cap_rank": r[5],
            "snapshot_ts": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]


def get_merged_data():
    batch = {b["symbol"]: b for b in get_batch_latest()}
    speed = {s["symbol"]: s for s in get_speed_data()}

    merged = dict(batch)
    for sym, s in speed.items():
        merged[sym] = s

    return sorted(merged.values(), key=lambda x: x.get("market_cap_rank") or 99999)
