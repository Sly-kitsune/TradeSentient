"""
TradeSentient — Forex Conversion Utility

Fetches and caches the USD→INR exchange rate using multiple free APIs.
Redis cache with 15-minute TTL to avoid rate limits.
"""

import os
import json
import requests
import time

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
FOREX_CACHE_KEY = "forex:usd_inr"
FOREX_TTL = 900  # 15 minutes

# Fallback rate if all APIs fail (updated periodically)
FALLBACK_USD_INR = 83.50

# In-memory cache for when Redis is unavailable
_mem_cache = {"rate": None, "expires": 0}


def _fetch_from_exchangerate_api() -> float | None:
    """Primary: exchangerate-api.com (free, no key required)."""
    try:
        resp = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") == "success":
            return float(data["rates"]["INR"])
    except Exception as e:
        print(f"  ⚠ exchangerate-api error: {e}")
    return None


def _fetch_from_frankfurter() -> float | None:
    """Backup: Frankfurter API (ECB rates, free, no key)."""
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest?from=USD&to=INR",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["rates"]["INR"])
    except Exception as e:
        print(f"  ⚠ frankfurter error: {e}")
    return None


def _get_redis():
    """Get Redis client, or None if unavailable."""
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1, socket_connect_timeout=1)
        r.ping()
        return r
    except Exception:
        return None


def get_usd_inr_rate() -> float:
    """
    Get the current USD→INR exchange rate.
    Priority: Redis cache → API → in-memory cache → fallback constant.
    """
    # 1. Try Redis cache
    r = _get_redis()
    if r:
        try:
            cached = r.get(FOREX_CACHE_KEY)
            if cached:
                return float(cached)
        except Exception:
            pass

    # 2. Try in-memory cache
    if _mem_cache["rate"] and time.time() < _mem_cache["expires"]:
        return _mem_cache["rate"]

    # 3. Fetch from APIs
    rate = _fetch_from_exchangerate_api()
    if rate is None:
        rate = _fetch_from_frankfurter()
    if rate is None:
        rate = FALLBACK_USD_INR
        print(f"  ⚠ Using fallback USD/INR rate: {rate}")

    # 4. Cache in Redis + memory
    if r:
        try:
            r.setex(FOREX_CACHE_KEY, FOREX_TTL, str(rate))
        except Exception:
            pass
    _mem_cache["rate"] = rate
    _mem_cache["expires"] = time.time() + FOREX_TTL

    return rate


def convert_to_inr(value_usd: float) -> float:
    """Convert a USD value to INR using the cached exchange rate."""
    rate = get_usd_inr_rate()
    return round(value_usd * rate, 2)
