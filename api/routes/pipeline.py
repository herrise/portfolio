"""Pipeline status — dual-layer health, logs, triggers, run history, architecture."""
from fastapi import APIRouter, Query
from db import get_duckdb, r
import json
import logging

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _normalize_ts(entry: dict) -> float:
    ts = entry.get("ts", 0)
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(ts)).timestamp()
    except Exception:
        return 0


@router.get("/status")
def pipeline_status():
    result = {"batch_layer": {}, "speed_layer": {}}

    con = get_duckdb()
    try:
        last_run = con.execute("""
            SELECT run_id, started_at, ended_at, rows_ingested, status
            FROM pipeline_runs ORDER BY run_id DESC LIMIT 1
        """).fetchone()
    except Exception:
        last_run = None

    batch_rows = 0
    try:
        batch_rows = con.execute("SELECT COUNT(*) FROM _raw_prices").fetchone()[0]
    except Exception:
        pass

    dbt_info = None
    try:
        dbt_row = con.execute("""
            SELECT event, status, detail, ts FROM pipeline_log
            WHERE layer = 'batch' AND event LIKE 'dbt_%'
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        if dbt_row:
            dbt_info = {
                "last_event": dbt_row[0],
                "status": dbt_row[1],
                "detail": dbt_row[2][:300] if dbt_row[2] else None,
                "at": dbt_row[3].isoformat() if dbt_row[3] else None,
            }
    except Exception:
        pass
    con.close()

    batch_redis_health = r.get("pipeline:batch:health")
    batch_redis = json.loads(batch_redis_health) if batch_redis_health else {}

    result["batch_layer"] = {
        "healthy": last_run is not None and last_run[4] == "success",
        "last_run_id": last_run[0] if last_run else None,
        "last_run_at": last_run[1].isoformat() if last_run and last_run[1] else None,
        "rows_ingested_total": batch_rows,
        "status": last_run[4] if last_run else "no_data",
        "triggered_by": batch_redis.get("triggered_by", "scheduler"),
        "dbt": dbt_info or {
            "last_event": batch_redis.get("dbt_status", "unknown"),
            "status": batch_redis.get("dbt_status", "unknown"),
            "detail": f"tests: {batch_redis.get('dbt_tests_passed', '?')}/{batch_redis.get('dbt_tests_total', '?')}",
            "at": batch_redis.get("last_run"),
        },
    }

    speed_keys = len(r.keys("ticker:*"))
    speed_health_raw = r.get("pipeline:speed:health")
    speed_health = json.loads(speed_health_raw) if speed_health_raw else {}

    result["speed_layer"] = {
        "healthy": speed_keys > 0,
        "tickers_in_cache": speed_keys,
        "redis_connected": True,
        "last_log": {
            "last_event": speed_health.get("last_event", "unknown"),
            "status": speed_health.get("status", "unknown"),
            "detail": speed_health.get("detail", ""),
            "at": speed_health.get("updated_at"),
        } if speed_health else None,
    }

    return result


@router.post("/trigger/{layer}")
def trigger_ingest(layer: str):
    """Manually trigger an immediate ingest on the speed or batch layer."""
    if layer not in ("speed", "batch"):
        return {"ok": False, "error": "layer must be 'speed' or 'batch'"}

    channel = f"pipeline:trigger:{layer}"
    receivers = r.publish(channel, f"manual trigger via API")
    log.info("trigger sent to %s — %d subscribers", channel, receivers)

    return {
        "ok": True,
        "layer": layer,
        "channel": channel,
        "subscribers_reached": receivers,
        "message": f"Trigger sent. {layer} layer will execute immediately.",
    }


@router.get("/runs")
def run_history(limit: int = Query(20, ge=1, le=100)):
    con = get_duckdb()
    try:
        rows = con.execute("""
            SELECT run_id, started_at, ended_at, rows_ingested, status, error_message
            FROM pipeline_runs ORDER BY run_id DESC LIMIT ?
        """, [limit]).fetchall()
    except Exception:
        rows = []
    con.close()
    return {
        "count": len(rows),
        "runs": [
            {
                "run_id": r[0],
                "started_at": r[1].isoformat() if r[1] else None,
                "ended_at": r[2].isoformat() if r[2] else None,
                "rows_ingested": r[3],
                "status": r[4],
                "error_message": r[5],
            }
            for r in rows
        ],
    }


@router.get("/logs")
def pipeline_logs(
    layer: str = Query("all", pattern="^(all|speed|batch)$"),
    limit: int = Query(50, ge=5, le=200),
):
    raw_logs = []

    if layer in ("all", "speed"):
        speed_raw = r.lrange("pipeline:logs:speed", 0, limit - 1)
        for entry in speed_raw:
            try:
                obj = json.loads(entry)
                obj["source"] = "redis"
                raw_logs.append(obj)
            except Exception:
                pass

    if layer in ("all", "batch"):
        batch_raw = r.lrange("pipeline:logs:batch", 0, limit - 1)
        for entry in batch_raw:
            try:
                obj = json.loads(entry)
                obj["source"] = "redis"
                raw_logs.append(obj)
            except Exception:
                pass

        con = get_duckdb()
        try:
            db_rows = con.execute("""
                SELECT ts, layer, event, status, detail, rows_affected
                FROM pipeline_log
                ORDER BY id DESC LIMIT ?
            """, [limit]).fetchall()
            for row in db_rows:
                raw_logs.append({
                    "ts": row[0].isoformat() if row[0] else None,
                    "layer": row[1],
                    "event": row[2],
                    "status": row[3],
                    "detail": row[4],
                    "rows_affected": row[5],
                    "source": "duckdb",
                })
        except Exception:
            pass
        con.close()

    raw_logs.sort(key=_normalize_ts, reverse=True)

    seen = set()
    deduped = []
    for entry in raw_logs:
        key = (entry.get("layer"), entry.get("event"), str(entry.get("detail", ""))[:80])
        if key not in seen:
            seen.add(key)
            ts_val = entry.get("ts")
            if isinstance(ts_val, (int, float)):
                from datetime import datetime, timezone as tz
                entry["ts"] = datetime.fromtimestamp(ts_val, tz=tz.utc).isoformat()
            deduped.append(entry)

    return {"layer": layer, "count": len(deduped[:limit]), "logs": deduped[:limit]}


@router.get("/architecture")
def architecture():
    return {
        "layers": [
            {
                "name": "Speed Layer",
                "color": "#F59E0B",
                "storage": "Redis",
                "latency": "Every 2 seconds",
                "accuracy": "Real-time (approximate, Brownian motion)",
                "description": "Stream ingester generates ticker prices every 2s, "
                               "publishes to Redis pub/sub. Heartbeat logs every 60s. "
                               "Manual trigger via pipeline:trigger:speed channel.",
                "tech": ["Simulated + CoinGecko API", "Redis pub/sub", "Redis lists (logs)", "Pub/sub triggers"],
                "endpoints": ["GET /api/prices/latest?view=speed", "WS /ws/live",
                             "GET /api/pipeline/logs?layer=speed", "POST /api/pipeline/trigger/speed"],
                "log_events": ["startup", "heartbeat", "manual_trigger"],
            },
            {
                "name": "Batch Layer",
                "color": "#3B82F6",
                "storage": "DuckDB + dbt",
                "latency": "Every 5 minutes",
                "accuracy": "Historical (authoritative, tested)",
                "description": "Batch ingester: (1) Ingest, (2) dbt build (staging → marts with tests), "
                               "(3) Dual-logs every phase. Manual trigger via pipeline:trigger:batch channel.",
                "tech": ["DuckDB", "dbt (duckdb adapter)", "APScheduler", "Redis+DuckDB dual logging", "Pub/sub triggers"],
                "endpoints": ["GET /api/prices/latest?view=batch", "GET /api/prices/{symbol}/history",
                             "GET /api/pipeline/logs?layer=batch", "GET /api/pipeline/runs",
                             "POST /api/pipeline/trigger/batch"],
                "log_events": ["startup", "ingest_started", "api_fetch", "ingest_done",
                              "dbt_build_started", "dbt_build_done", "error"],
            },
            {
                "name": "Serving Layer",
                "color": "#10B981",
                "storage": "FastAPI",
                "latency": "< 50ms",
                "accuracy": "Merged (speed + batch)",
                "description": "FastAPI merges speed+batch views, shows dbt test results, "
                               "unified logs from Redis + DuckDB. Manual trigger endpoints "
                               "let users initiate pipeline runs from the dashboard.",
                "tech": ["FastAPI", "WebSocket bridge", "DuckDB + Redis", "Trigger API"],
                "endpoints": ["GET /api/prices/latest?view=merged", "GET /api/pipeline/status",
                             "GET /api/pipeline/logs?layer=all", "POST /api/pipeline/trigger/speed",
                             "POST /api/pipeline/trigger/batch", "WS /ws/live"],
            },
        ]
    }
