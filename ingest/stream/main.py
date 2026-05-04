"""Speed Layer — simulated prices with realistic drift + Redis-based health logging."""
import os
import json
import time
import random
import threading
import logging
import requests
import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [stream] %(message)s")
log = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 2))
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

TICKERS = [
    {"symbol": "bitcoin", "base": 68000, "vol": 28e9, "mcap": 1.35e12},
    {"symbol": "ethereum", "base": 3400, "vol": 15e9, "mcap": 410e9},
    {"symbol": "solana", "base": 145, "vol": 3.5e9, "mcap": 68e9},
    {"symbol": "cardano", "base": 0.45, "vol": 450e6, "mcap": 16.5e9},
    {"symbol": "polkadot", "base": 7.20, "vol": 200e6, "mcap": 10.1e9},
    {"symbol": "chainlink", "base": 14.50, "vol": 380e6, "mcap": 8.8e9},
]

STATE = {t["symbol"]: {"price": t["base"], "change": 0.0} for t in TICKERS}

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
REAL_API_EVERY_N = 20
_start_time = time.time()
_manual_trigger = threading.Event()


def write_speed_log(event, status, detail=None):
    entry = json.dumps({
        "ts": time.time(),
        "layer": "speed",
        "event": event,
        "status": status,
        "detail": detail,
    })
    r.lpush("pipeline:logs:speed", entry)
    r.ltrim("pipeline:logs:speed", 0, 99)
    r.set("pipeline:speed:health", json.dumps({
        "last_event": event,
        "status": status,
        "detail": detail,
        "updated_at": time.time(),
    }))


def tick_once(tick: int):
    # Try real API periodically
    if tick % REAL_API_EVERY_N == 0:
        ids = ",".join([t["symbol"] for t in TICKERS])
        try:
            resp = requests.get(COINGECKO_URL, params={
                "ids": ids, "vs_currencies": "usd",
                "include_24hr_vol": "true", "include_24hr_change": "true",
                "include_market_cap": "true",
            }, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for sym, vals in data.items():
                    if vals.get("usd"):
                        STATE[sym]["price"] = vals["usd"]
                        STATE[sym]["change"] = vals.get("usd_24h_change") or 0
                log.info("used real API data for this tick")
        except Exception:
            pass

    now = time.time()
    out = []
    for t in TICKERS:
        sym = t["symbol"]
        prev = STATE[sym]["price"]
        drift = random.gauss(0, 0.001)
        new_price = prev * (1 + drift)
        new_change = ((new_price - t["base"]) / t["base"]) * 100

        STATE[sym]["price"] = new_price
        STATE[sym]["change"] = new_change

        msg = {
            "symbol": sym,
            "price_usd": round(new_price, 2),
            "volume_24h": round(t["vol"] * (0.7 + random.random() * 0.6), 0),
            "market_cap": round(new_price / t["base"] * t["mcap"], 0),
            "change_24h_pct": round(new_change, 2),
            "market_cap_rank": None,
            "ts": now,
        }
        r.setex(f"ticker:{sym}", 120, json.dumps(msg))
        out.append(msg)

    r.publish("prices:live", json.dumps(out))

    if tick % 30 == 0:
        elapsed = int(time.time() - _start_time)
        write_speed_log("heartbeat", "healthy",
                        f"tick {tick} (uptime {elapsed}s): {len(out)} tickers, {len(r.keys('ticker:*'))} in cache")


def trigger_listener():
    """Listen for manual trigger signals on Redis pub/sub."""
    pubsub = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    sub = pubsub.pubsub()
    sub.subscribe("pipeline:trigger:speed")
    log.info("trigger listener started on channel pipeline:trigger:speed")
    for msg in sub.listen():
        if msg["type"] == "message":
            log.info("manual trigger received: %s", msg["data"])
            write_speed_log("manual_trigger", "success", f"user triggered: {msg['data']}")
            _manual_trigger.set()


if __name__ == "__main__":
    log.info("speed layer started — tick interval %ds", POLL_INTERVAL)
    write_speed_log("startup", "success", "speed layer daemon started")

    # Start trigger listener in background thread
    trigger_thread = threading.Thread(target=trigger_listener, daemon=True)
    trigger_thread.start()

    tick = 0
    while True:
        tick_once(tick)
        tick += 1
        sleep_end = time.time() + POLL_INTERVAL
        while time.time() < sleep_end:
            if _manual_trigger.is_set():
                _manual_trigger.clear()
                log.info("firing manual tick now")
                break
            time.sleep(0.1)
