"""
TradeSentient — Dynamic Ticker Configuration

Fetches top 50 assets per asset class from live APIs.
Results are cached in Redis with 15-minute TTL.
No hardcoded ticker lists — everything is API-driven.
"""

import os
import json
import time
import requests

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = 900  # 15 minutes

COINGECKO_URL = "https://api.coingecko.com/api/v3"

# ─── Asset class metadata ───
ASSET_CLASSES = {
    "crypto": {
        "label": "Crypto",
        "exchange": "global",
        "currency": "INR",
    },
    "us_stock": {
        "label": "US Stocks",
        "exchange": "NASDAQ/NYSE",
        "currency": "INR",   # stored in INR after conversion
    },
    "in_stock": {
        "label": "Indian Stocks",
        "exchange": "NSE",
        "currency": "INR",
    },
}

# ─── In-memory cache fallback ───
_mem_cache: dict[str, dict] = {}


def _get_redis():
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1, socket_connect_timeout=1)
        r.ping()
        return r
    except Exception:
        return None


def _set_cache(key: str, data: list[dict], ttl: int = CACHE_TTL):
    """Cache ticker list in Redis + in-memory."""
    _mem_cache[key] = {"data": data, "expires": time.time() + ttl}
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(data))
        except Exception:
            pass


def _get_cache(key: str) -> list[dict] | None:
    """Read from Redis, fall back to in-memory."""
    r = _get_redis()
    if r:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
    mem = _mem_cache.get(key)
    if mem and time.time() < mem["expires"]:
        return mem["data"]
    return None


# ═══════════════════════════════════════════════════════
#  CRYPTO — CoinGecko top 50 by market cap
# ═══════════════════════════════════════════════════════

CRYPTO_SEED = [
    {"symbol": "BTC", "name": "Bitcoin", "coingecko_id": "bitcoin"},
    {"symbol": "ETH", "name": "Ethereum", "coingecko_id": "ethereum"},
    {"symbol": "BNB", "name": "BNB", "coingecko_id": "binancecoin"},
    {"symbol": "SOL", "name": "Solana", "coingecko_id": "solana"},
    {"symbol": "XRP", "name": "Ripple", "coingecko_id": "ripple"},
    {"symbol": "ADA", "name": "Cardano", "coingecko_id": "cardano"},
    {"symbol": "DOGE", "name": "Dogecoin", "coingecko_id": "dogecoin"},
    {"symbol": "AVAX", "name": "Avalanche", "coingecko_id": "avalanche-2"},
    {"symbol": "DOT", "name": "Polkadot", "coingecko_id": "polkadot"},
    {"symbol": "MATIC", "name": "Polygon", "coingecko_id": "matic-network"},
]


def fetch_top_crypto(limit: int = 50) -> list[dict]:
    """Fetch top N crypto by market cap from CoinGecko (INR prices)."""
    try:
        print(f"  ? Fetching top {limit} crypto from CoinGecko...")
        resp = requests.get(
            f"{COINGECKO_URL}/coins/markets",
            params={
                "vs_currency": "inr",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  ? CoinGecko error {resp.status_code}: {resp.text[:100]}")
            return CRYPTO_SEED

        coins = resp.json()
        if not coins:
            print("  ? CoinGecko returned empty list")
            return CRYPTO_SEED

        result = []
        for coin in coins:
            result.append({
                "symbol": coin["symbol"].upper(),
                "name": coin["name"],
                "coingecko_id": coin["id"],
                "market_cap": coin.get("market_cap", 0),
                "current_price": coin.get("current_price"),
            })
        print(f"  ? Fetched {len(result)} crypto assets")
        return result
    except Exception as e:
        print(f"  ? CoinGecko fetch exception: {e}")
        return CRYPTO_SEED


# ═══════════════════════════════════════════════════════
#  US STOCKS — S&P 500 from Wikipedia, top 50
# ═══════════════════════════════════════════════════════

US_STOCK_SEED = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corp."},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corp."},
    {"symbol": "META", "name": "Meta Platforms Inc."},
    {"symbol": "TSLA", "name": "Tesla Inc."},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway"},
    {"symbol": "JPM", "name": "JPMorgan Chase"},
    {"symbol": "V", "name": "Visa Inc."},
]


def fetch_top_us_stocks(limit: int = 50) -> list[dict]:
    """Scrape S&P 500 constituents from Wikipedia, return top N."""
    try:
        from bs4 import BeautifulSoup
        print("  ? Fetching S&P 500 from Wikipedia...")

        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            timeout=15,
            headers={"User-Agent": "TradeSentient/3.0"},
        )
        if resp.status_code != 200:
            print(f"  ? Wikipedia error {resp.status_code}")
            return US_STOCK_SEED

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table", {"id": "constituents"})

        if not table:
            print("  ? Wikipedia S&P 500 table not found")
            return US_STOCK_SEED

        rows = table.find_all("tr")[1:]  # skip header
        result = []
        for row in rows[:limit]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                symbol = cols[0].get_text(strip=True).replace(".", "-")
                name = cols[1].get_text(strip=True)
                result.append({"symbol": symbol, "name": name})

        count = len(result)
        if count < 10:
            print(f"  ? Wikipedia scrape returned only {count} stocks, using SEED")
            return US_STOCK_SEED
        
        print(f"  ? Fetched {count} US stocks")
        return result
    except ImportError:
        print("  ? beautifulsoup4 not installed — using seed US stocks")
        return US_STOCK_SEED
    except Exception as e:
        print(f"  ? Wikipedia scrape exception: {e}")
        return US_STOCK_SEED


# ═══════════════════════════════════════════════════════
#  INDIAN STOCKS — NIFTY 50 from NSE / Wikipedia
# ═══════════════════════════════════════════════════════

IN_STOCK_SEED = [
    {"symbol": "RELIANCE", "name": "Reliance Industries"},
    {"symbol": "TCS", "name": "Tata Consultancy Services"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank"},
    {"symbol": "INFY", "name": "Infosys"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever"},
    {"symbol": "ITC", "name": "ITC Limited"},
    {"symbol": "SBIN", "name": "State Bank of India"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank"},
]


def fetch_top_in_stocks(limit: int = 50) -> list[dict]:
    """Fetch NIFTY 50 constituents from Wikipedia."""
    try:
        from bs4 import BeautifulSoup
        print("  ? Fetching NIFTY 50 from Wikipedia...")

        resp = requests.get(
            "https://en.wikipedia.org/wiki/NIFTY_50",
            timeout=15,
            headers={"User-Agent": "TradeSentient/3.0"},
        )
        if resp.status_code != 200:
            print(f"  ? Wikipedia error {resp.status_code}")
            return IN_STOCK_SEED

        soup = BeautifulSoup(resp.text, "lxml")

        # Find the constituents table
        tables = soup.find_all("table", class_="wikitable")
        result = []
        for table in tables:
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            if any("symbol" in h or "ticker" in h or "company" in h for h in headers):
                rows = table.find_all("tr")[1:]
                for row in rows[:limit]:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        # Try to extract symbol and name from the columns
                        symbol = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                        name = cols[0].get_text(strip=True)
                        # Clean up — sometimes symbol has .NS suffix
                        symbol = symbol.replace(".NS", "").replace(".BO", "").strip()
                        if symbol and name:
                            result.append({"symbol": symbol, "name": name})
                if result:
                    break

        count = len(result)
        if count < 10:
            print(f"  ? Wikipedia NIFTY 50 scrape returned only {count} stocks, using SEED")
            return IN_STOCK_SEED

        print(f"  ? Fetched {count} Indian stocks")
        return result
    except ImportError:
        print("  ? beautifulsoup4 not installed — using seed Indian stocks")
        return IN_STOCK_SEED
    except Exception as e:
        print(f"  ? NIFTY 50 scrape exception: {e}")
        return IN_STOCK_SEED


# ═══════════════════════════════════════════════════════
#  Public API — get tickers with caching
# ═══════════════════════════════════════════════════════

FETCHERS = {
    "crypto": fetch_top_crypto,
    "us_stock": fetch_top_us_stocks,
    "in_stock": fetch_top_in_stocks,
}


def get_cached_tickers(asset_class: str) -> list[dict]:
    """Get tickers for an asset class (from cache or live API)."""
    cache_key = f"tickers:{asset_class}"

    # Try cache first
    cached = _get_cache(cache_key)
    if cached:
        return cached

    # Fetch from API
    fetcher = FETCHERS.get(asset_class)
    if not fetcher:
        return []

    tickers = fetcher()
    _set_cache(cache_key, tickers)
    return tickers


def refresh_all_tickers():
    """Force-refresh all ticker caches. Called by Celery beat or on startup."""
    for asset_class in ASSET_CLASSES:
        print(f"  Refreshing {asset_class} tickers...")
        fetcher = FETCHERS.get(asset_class)
        if fetcher:
            tickers = fetcher()
            _set_cache(f"tickers:{asset_class}", tickers)
            print(f"    → {len(tickers)} tickers cached")


def get_all_symbols(asset_class: str | None = None) -> list[str]:
    """Return flat list of all ticker symbols (optionally filtered by class)."""
    if asset_class:
        return [t["symbol"] for t in get_cached_tickers(asset_class)]
    symbols = []
    for cls in ASSET_CLASSES:
        symbols.extend(t["symbol"] for t in get_cached_tickers(cls))
    return symbols


def get_coingecko_map() -> dict[str, str]:
    """Return {symbol: coingecko_id} for all cached crypto tickers."""
    tickers = get_cached_tickers("crypto")
    return {
        t["symbol"]: t["coingecko_id"]
        for t in tickers
        if "coingecko_id" in t
    }


def get_asset_class(symbol: str) -> str | None:
    """Look up which asset class a symbol belongs to."""
    for cls in ASSET_CLASSES:
        symbols = [t["symbol"] for t in get_cached_tickers(cls)]
        if symbol in symbols:
            return cls
    return None


def get_ticker_info(symbol: str) -> dict | None:
    """Return full metadata for a symbol."""
    for cls_key, cls_meta in ASSET_CLASSES.items():
        for t in get_cached_tickers(cls_key):
            if t["symbol"] == symbol:
                return {
                    "symbol": symbol,
                    "asset_class": cls_key,
                    "exchange": cls_meta["exchange"],
                    "currency": cls_meta["currency"],
                    **t,
                }
    return None
