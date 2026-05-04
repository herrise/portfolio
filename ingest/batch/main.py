"""Batch Layer — ingests data, logs to both DuckDB and Redis, runs dbt on demand."""
import os
import json
import time
import random
import subprocess
import threading
import logging
import duckdb
import requests
import redis
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [batch] %(message)s")
log = logging.getLogger(__name__)

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/app/data/pipeline.duckdb")
BATCH_INTERVAL_MIN = int(os.getenv("BATCH_INTERVAL_MINUTES", 5))
DBT_PROJECT_DIR = "/app/dbt"
DBT_PROFILES_DIR = "/app/dbt"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

BASE_TICKERS = [
    {"symbol": "bitcoin", "base": 68000, "vol": 28e9, "mcap": 1.35e12, "rank": 1},
    {"symbol": "ethereum", "base": 3400, "vol": 15e9, "mcap": 410e9, "rank": 2},
    {"symbol": "solana", "base": 145, "vol": 3.5e9, "mcap": 68e9, "rank": 5},
    {"symbol": "cardano", "base": 0.45, "vol": 450e6, "mcap": 16.5e9, "rank": 10},
    {"symbol": "polkadot", "base": 7.20, "vol": 200e6, "mcap": 10.1e9, "rank": 15},
    {"symbol": "chainlink", "base": 14.50, "vol": 380e6, "mcap": 8.8e9, "rank": 18},
]

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

_run_count = 0


def write_batch_log(event, status, detail=None, rows_affected=None):
    entry = json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "layer": "batch",
        "event": event,
        "status": status,
        "detail": str(detail)[:500] if detail else None,
        "rows_affected": rows_affected,
    })
    r.lpush("pipeline:logs:batch", entry)
    r.ltrim("pipeline:logs:batch", 0, 99)

    try:
        con = duckdb.connect(DUCKDB_PATH)
        con.execute("""
            INSERT INTO pipeline_log (layer, event, status, detail, rows_affected)
            VALUES (?, ?, ?, ?, ?)
        """, ["batch", event, status, str(detail)[:1000] if detail else None, rows_affected])
        con.close()
    except Exception:
        pass


def init_db():
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS _raw_prices (
            symbol VARCHAR,
            price_usd DOUBLE,
            volume_24h DOUBLE,
            market_cap DOUBLE,
            price_change_24h_pct DOUBLE,
            market_cap_rank INTEGER,
            ingested_at TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id INTEGER PRIMARY KEY,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            rows_ingested INTEGER,
            status VARCHAR,
            error_message VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_log (
            id INTEGER PRIMARY KEY,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            layer VARCHAR,
            event VARCHAR,
            status VARCHAR,
            detail VARCHAR,
            rows_affected INTEGER
        )
    """)
    con.execute("CREATE SEQUENCE IF NOT EXISTS seq_run_id START 1")
    con.close()
    log.info("database initialized")


def _try_real_api():
    ids = ",".join([t["symbol"] for t in BASE_TICKERS])
    try:
        resp = requests.get(COINGECKO_URL, params={
            "ids": ids, "vs_currencies": "usd",
            "include_24hr_vol": "true", "include_24hr_change": "true",
            "include_market_cap": "true",
        }, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            out = {}
            for sym, vals in data.items():
                if vals.get("usd"):
                    out[sym] = vals
            if out:
                return out
    except Exception:
        pass
    return None


def run_dbt():
    try:
        result = subprocess.run(
            ["dbt", "build", "--project-dir", DBT_PROJECT_DIR,
             "--profiles-dir", DBT_PROFILES_DIR],
            capture_output=True, text=True, timeout=120,
        )
        output = result.stdout + "\n" + result.stderr
        success = result.returncode == 0

        tests_passed = output.count("PASS")
        tests_failed = output.count("FAIL")
        tests_total = tests_passed + tests_failed

        lines = []
        for line in output.split("\n"):
            if any(kw in line for kw in ["Done", "PASS", "FAIL", "OK", "ERROR", "WARN", "model", "test", "Completed"]):
                lines.append(line.strip())

        summary = "\n".join(lines[-20:]) if lines else output[-500:]
        return success, summary, tests_passed, tests_total
    except subprocess.TimeoutExpired:
        return False, "dbt timed out after 120s", 0, 0
    except FileNotFoundError:
        return False, "dbt command not found in PATH", 0, 0
    except Exception as e:
        return False, str(e), 0, 0


def fetch_and_store(triggered_by="scheduler"):
    global _run_count
    _run_count += 1

    started = datetime.now(timezone.utc)
    source_label = f"run {_run_count} ({triggered_by})"
    write_batch_log("ingest_started", "running", f"{source_label} started", 0)

    try:
        con = duckdb.connect(DUCKDB_PATH)
        run_id = con.execute("SELECT nextval('seq_run_id')").fetchone()[0]
        now_ts = datetime.now(timezone.utc)
        count = 0

        real_data = _try_real_api() if _run_count % 3 == 0 else None
        if real_data:
            write_batch_log("api_fetch", "success", f"real CoinGecko data ({len(real_data)} coins)", len(real_data))

        for t in BASE_TICKERS:
            sym = t["symbol"]
            if real_data and sym in real_data:
                v = real_data[sym]
                price = v.get("usd", t["base"])
                vol = v.get("usd_24h_vol", t["vol"])
                mcap = v.get("usd_market_cap", t["mcap"])
                change = v.get("usd_24h_change", 0)
            else:
                drift = random.gauss(0, 0.003)
                price = t["base"] * (1 + drift)
                vol = t["vol"] * (0.8 + random.random() * 0.4)
                mcap = price / t["base"] * t["mcap"]
                change = ((price - t["base"]) / t["base"]) * 100

            con.execute(
                """INSERT INTO _raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [sym, price, vol, mcap, change, t["rank"], now_ts],
            )
            count += 1

        con.execute(
            """INSERT INTO pipeline_runs VALUES (?, ?, ?, ?, ?, ?)""",
            [run_id, started, datetime.now(timezone.utc), count, "success", None],
        )
        con.close()
        write_batch_log("ingest_done", "success", f"{count} rows ingested ({triggered_by})", count)
        log.info("run %d done — %d rows (%s)", run_id, count, triggered_by)

        write_batch_log("dbt_build_started", "running", "dbt build executing", 0)
        dbt_ok, dbt_summary, tests_ok, tests_total = run_dbt()
        dbt_status = "success" if dbt_ok else "failed"
        write_batch_log("dbt_build_done", dbt_status,
                        f"tests: {tests_ok}/{tests_total} passed | {dbt_summary}", tests_total)
        log.info("run %d dbt: %s (tests %d/%d)", run_id, dbt_status, tests_ok, tests_total)

        for t in BASE_TICKERS:
            msg = json.dumps({
                "symbol": t["symbol"],
                "price_usd": round(t["base"] * (0.98 + random.random() * 0.04), 2),
                "volume_24h": round(t["vol"] * (0.8 + random.random() * 0.4), 0),
                "market_cap": round(t["mcap"] * (0.98 + random.random() * 0.04), 0),
                "change_24h_pct": round(random.uniform(-5, 5), 2),
                "market_cap_rank": t["rank"],
                "ts": now_ts.timestamp(),
            })
            r.setex(f"ticker:{t['symbol']}", 600, msg)

        r.set("pipeline:batch:health", json.dumps({
            "last_run": started.isoformat(), "status": "success",
            "runs": run_id, "rows": count,
            "dbt_status": dbt_status,
            "dbt_tests_passed": tests_ok, "dbt_tests_total": tests_total,
            "triggered_by": triggered_by,
        }))

    except Exception as e:
        write_batch_log("error", "failed", str(e), 0)
        try:
            con = duckdb.connect(DUCKDB_PATH)
            con.execute(
                """INSERT INTO pipeline_runs VALUES (?, ?, ?, ?, ?, ?)""",
                [0, started, datetime.now(timezone.utc), 0, "failed", str(e)[:500]],
            )
            con.close()
        except Exception:
            pass
        log.error("batch run failed: %s", e)


def trigger_listener():
    """Listen for manual trigger signals on Redis pub/sub."""
    pubsub = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    sub = pubsub.pubsub()
    sub.subscribe("pipeline:trigger:batch")
    log.info("trigger listener started on channel pipeline:trigger:batch")
    for msg in sub.listen():
        if msg["type"] == "message":
            payload = msg["data"] or "manual"
            log.info("manual trigger received: %s", payload)
            fetch_and_store(triggered_by=f"manual: {payload}")


if __name__ == "__main__":
    log.info("batch layer starting — interval %d min, db %s", BATCH_INTERVAL_MIN, DUCKDB_PATH)
    init_db()
    write_batch_log("startup", "success", "batch layer daemon started", 0)

    fetch_and_store(triggered_by="startup")

    trigger_thread = threading.Thread(target=trigger_listener, daemon=True)
    trigger_thread.start()

    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store, "interval", minutes=BATCH_INTERVAL_MIN, id="batch_ingest")
    scheduler.start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
