import time
import requests
import random
import os
import sys

"""
Standalone ingest script — runs WITHOUT Celery/Redis.
Fetches dynamic top-50 tickers across all asset classes.
ALL prices normalized to INR.

Usage:
    python -m worker.ingest_script
"""

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.ticker_config import (
    get_cached_tickers, get_coingecko_map,
    get_all_symbols, ASSET_CLASSES, refresh_all_tickers,
)
from backend.forex import convert_to_inr, get_usd_inr_rate

API_URL = os.getenv("API_URL", "http://localhost:8000")
COINGECKO_URL = "https://api.coingecko.com/api/v3"

# Mock base prices (all INR)
MOCK_BASE_INR = {
    "BTC": 5_500_000, "ETH": 210_000, "SOL": 12_000, "ADA": 42,
    "XRP": 46, "DOGE": 7, "MATIC": 67, "BNB": 52_000,
    "AVAX": 3_000, "DOT": 600,
    "AAPL": 14_600, "GOOGL": 11_700, "TSLA": 20_900, "MSFT": 31_700,
    "AMZN": 15_000, "NFLX": 40_000, "NVDA": 75_000, "META": 42_000,
    "RELIANCE": 2_500, "TCS": 3_800, "INFY": 1_500, "HDFCBANK": 1_550,
    "ICICIBANK": 1_100, "HINDUNILVR": 2_400, "ITC": 440, "SBIN": 750,
}

sim_prices = {}

MOCK_SENTIMENT = [
    ("Bitcoin is going to the moon!", "twitter", 0.9, "BTC"),
    ("Ethereum upgrade will be huge for DeFi.", "reddit", 0.8, "ETH"),
    ("AAPL earnings report shows strong growth.", "news", 0.7, "AAPL"),
    ("Solana DeFi TVL hits new record!", "twitter", 0.85, "SOL"),
    ("Tesla deliveries beat expectations.", "news", 0.75, "TSLA"),
    ("Reliance Jio subscriber growth accelerates.", "news", 0.7, "RELIANCE"),
    ("TCS wins $2B deal with US bank.", "news", 0.8, "TCS"),
    ("NVIDIA AI chip demand surging.", "news", 0.9, "NVDA"),
    ("Crypto regulation fears spreading.", "news", -0.6, None),
    ("HDFC Bank Q3 NPA rises.", "news", -0.5, "HDFCBANK"),
    ("Microsoft Copilot adoption booms.", "news", 0.8, "MSFT"),
]


def get_mock_inr(symbol):
    base = MOCK_BASE_INR.get(symbol, 1000)
    if symbol not in sim_prices:
        sim_prices[symbol] = base + random.random() * base * 0.01
    sim_prices[symbol] += (random.random() - 0.5) * base * 0.005
    return round(sim_prices[symbol], 2)


def fetch_crypto_prices_inr():
    """Fetch crypto prices in INR from CoinGecko."""
    cg_map = get_coingecko_map()
    if not cg_map:
        return None
    try:
        ids = ",".join(list(cg_map.values())[:50])
        resp = requests.get(
            f"{COINGECKO_URL}/simple/price",
            params={"ids": ids, "vs_currencies": "inr", "include_24hr_vol": "true"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        prices = {}
        for symbol, cg_id in cg_map.items():
            if cg_id in data and "inr" in data[cg_id]:
                prices[symbol] = data[cg_id]["inr"]
        return prices if prices else None
    except Exception as e:
        print(f"  ⚠ CoinGecko error: {e}")
        return None


def fetch_us_prices_inr():
    """Fetch US stock prices via yfinance, convert to INR."""
    try:
        import yfinance as yf
        symbols = get_all_symbols("us_stock")[:20]  # Limit batch size
        if not symbols:
            return None
        data = yf.download(" ".join(symbols), period="1d", interval="1m", progress=False)
        if data.empty:
            return None
        prices = {}
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    usd = float(data["Close"].iloc[-1])
                else:
                    usd = float(data["Close"][sym].iloc[-1])
                prices[sym] = convert_to_inr(usd)
            except Exception:
                continue
        return prices or None
    except ImportError:
        return None
    except Exception as e:
        print(f"  ⚠ yfinance error: {e}")
        return None


def ingest_loop():
    # Refresh tickers on startup
    print("  Refreshing ticker caches...")
    refresh_all_tickers()

    # Print header
    rate = get_usd_inr_rate()
    total = sum(len(get_cached_tickers(c)) for c in ASSET_CLASSES)

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║   TradeSentient Dynamic Multi-Asset Ingest Loop  ║")
    print(f"║  API: {API_URL:<43}║")
    print(f"║  USD/INR: ₹{rate:<38}║")
    print(f"║  Total tickers: {total:<33}║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    for cls_key in ASSET_CLASSES:
        tickers = get_cached_tickers(cls_key)
        count = len(tickers)
        print(f"  {ASSET_CLASSES[cls_key]['label']}: Found {count} tickers")
        if count < 50:
             print(f"    ⚠ Warning: Wanted 50, got {count}. Check API/logs.")
        syms = [t["symbol"] for t in tickers[:10]]
        more = count - 10
        suffix = f" +{more} more" if more > 0 else ""
        print(f"    Samples: {', '.join(syms)}{suffix}")

    print("\n  All prices in ₹ INR")
    print("  Press Ctrl+C to stop\n")

    tick = 0
    real_crypto_cache = {}

    while True:
        tick += 1
        print(f"── Tick #{tick} ─────────────────────────────────")

        # ──────── CRYPTO (every tick) ────────
        if tick % 5 == 1:
            real_crypto = fetch_crypto_prices_inr()
            if real_crypto:
                real_crypto_cache = real_crypto

        crypto_syms = get_all_symbols("crypto")[:15]  # Ingest top 15 per tick
        for sym in crypto_syms:
            price = real_crypto_cache.get(sym, get_mock_inr(sym))
            if isinstance(price, dict):
                price = price.get("inr", get_mock_inr(sym))
            payload = {
                "symbol": sym, "price": round(price, 2),
                "asset_class": "crypto", "exchange": "global", "currency": "INR",
            }
            try:
                r = requests.post(f"{API_URL}/ingest/market", json=payload, timeout=30)
                s = "✓" if r.status_code == 200 else "✗"
                print(f"  {s} {sym:<10} ₹{price:>14,.2f}  (crypto)")
            except Exception as e:
                print(f"  ✗ {sym}: {e}")

        # ──────── US STOCKS (every 3rd tick) ────────
        if tick % 3 == 0:
            us_real = fetch_us_prices_inr()
            us_syms = get_all_symbols("us_stock")[:15]
            for sym in us_syms:
                price = us_real.get(sym, get_mock_inr(sym)) if us_real else get_mock_inr(sym)
                payload = {
                    "symbol": sym, "price": round(price, 2),
                    "asset_class": "us_stock", "exchange": "NASDAQ/NYSE", "currency": "INR",
                }
                try:
                    r = requests.post(f"{API_URL}/ingest/market", json=payload, timeout=30)
                    s = "✓" if r.status_code == 200 else "✗"
                    print(f"  {s} {sym:<10} ₹{price:>14,.2f}  (us_stock)")
                except Exception as e:
                    print(f"  ✗ {sym}: {e}")

        # ──────── INDIAN STOCKS (every 5th tick) ────────
        if tick % 5 == 0:
            in_syms = get_all_symbols("in_stock")[:15]
            for sym in in_syms:
                price = get_mock_inr(sym)
                payload = {
                    "symbol": sym, "price": round(price, 2),
                    "asset_class": "in_stock", "exchange": "NSE", "currency": "INR",
                }
                try:
                    r = requests.post(f"{API_URL}/ingest/market", json=payload, timeout=30)
                    s = "✓" if r.status_code == 200 else "✗"
                    print(f"  {s} {sym:<10} ₹{price:>14,.2f}  (in_stock)")
                except Exception as e:
                    print(f"  ✗ {sym}: {e}")

        # ──────── SENTIMENT (every 3rd tick) ────────
        if tick % 3 == 0:
            text, source, score, symbol = random.choice(MOCK_SENTIMENT)
            try:
                requests.post(
                    f"{API_URL}/ingest/sentiment",
                    json={"source": source, "sentiment_score": score, "raw_text": text, "symbol": symbol},
                    timeout=30,
                )
                print(f"  💬 [{source}] {text[:55]}...")
            except Exception as e:
                print(f"  ✗ sentiment: {e}")

        # ──────── TICKER REFRESH (every 450 ticks ≈ 15 min) ────
        if tick % 450 == 0:
            print("  🔄 Refreshing ticker caches...")
            refresh_all_tickers()

        print()
        time.sleep(2)


if __name__ == "__main__":
    ingest_loop()
