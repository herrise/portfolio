"""Price endpoints — speed, batch, merged views + history."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from db import get_speed_data, get_batch_latest, get_merged_data, get_duckdb
import logging

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.get("/latest")
def latest_prices(view: str = Query("merged", pattern="^(speed|batch|merged)$")):
    if view == "speed":
        return {"view": "speed", "data": get_speed_data()}
    elif view == "batch":
        return {"view": "batch", "data": get_batch_latest()}
    else:
        return {"view": "merged", "data": get_merged_data()}


@router.get("/{symbol}/history")
def price_history(symbol: str, hours: int = Query(24, ge=1, le=168)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    con = get_duckdb()
    try:
        rows = con.execute("""
            SELECT price_usd, volume_24h, market_cap, price_change_24h_pct, ingested_at
            FROM _raw_prices
            WHERE symbol = ?
              AND ingested_at >= ?
            ORDER BY ingested_at
        """, [symbol, cutoff]).fetchall()
    except Exception as e:
        log.warning("history query failed for %s: %s", symbol, e)
        rows = []
    con.close()
    return {
        "symbol": symbol,
        "hours": hours,
        "data": [
            {
                "price_usd": r[0],
                "volume_24h": r[1],
                "market_cap": r[2],
                "price_change_24h_pct": r[3],
                "snapshot_ts": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ],
    }
