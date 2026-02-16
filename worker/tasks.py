from worker.celery_app import celery_app
import requests
import random
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.ticker_config import (
    get_cached_tickers, get_coingecko_map,
    get_all_symbols, ASSET_CLASSES, refresh_all_tickers,
)
from backend.forex import convert_to_inr, get_usd_inr_rate

API_URL = os.getenv("API_URL", "http://localhost:8000")
COINGECKO_URL = "https://api.coingecko.com/api/v3"


# ═══════════════════════════════════════════════════════
#  CoinGecko — Crypto prices in INR (no conversion needed)
# ═══════════════════════════════════════════════════════

def fetch_crypto_prices_inr() -> dict | None:
    """Fetch crypto prices in INR directly from CoinGecko."""
    cg_map = get_coingecko_map()
    if not cg_map:
        return None
    try:
        # CoinGecko allows up to 250 ids per request
        ids = ",".join(cg_map.values())
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
                prices[symbol] = {
                    "price": round(data[cg_id]["inr"], 2),
                    "volume": data[cg_id].get("inr_24h_vol"),
                }
        return prices if prices else None
    except Exception as e:
        print(f"  ⚠ CoinGecko error: {e}")
        return None


# ═══════════════════════════════════════════════════════
#  yfinance — US stock prices in USD → convert to INR
# ═══════════════════════════════════════════════════════

def fetch_us_stock_prices_inr() -> dict | None:
    """Fetch US stock prices via yfinance, convert to INR."""
    try:
        import yfinance as yf

        symbols = get_all_symbols("us_stock")
        if not symbols:
            return None

        # Process in batches of 10 to avoid timeouts
        prices = {}
        for i in range(0, len(symbols), 10):
            batch = symbols[i:i + 10]
            tickers_str = " ".join(batch)
            try:
                data = yf.download(tickers_str, period="1d", interval="1m", progress=False)
                if data.empty:
                    continue
                for sym in batch:
                    try:
                        if len(batch) == 1:
                            usd_price = float(data["Close"].iloc[-1])
                            vol = float(data["Volume"].iloc[-1])
                        else:
                            usd_price = float(data["Close"][sym].iloc[-1])
                            vol = float(data["Volume"][sym].iloc[-1])
                        inr_price = convert_to_inr(usd_price)
                        prices[sym] = {"price": inr_price, "volume": vol}
                    except Exception:
                        continue
            except Exception as e:
                print(f"  ⚠ yfinance batch error: {e}")
                continue

        return prices if prices else None
    except ImportError:
        print("  ⚠ yfinance not installed")
        return None
    except Exception as e:
        print(f"  ⚠ yfinance error: {e}")
        return None


# ═══════════════════════════════════════════════════════
#  Indian Stocks — already in INR
# ═══════════════════════════════════════════════════════

def fetch_indian_stock_prices_inr() -> dict | None:
    """Fetch NSE stock prices (already in INR)."""
    try:
        from jugaad_data.nse import stock_df
        from datetime import date, timedelta

        symbols = get_all_symbols("in_stock")
        if not symbols:
            return None

        today = date.today()
        start = today - timedelta(days=5)

        prices = {}
        for sym in symbols:
            try:
                df = stock_df(symbol=sym, from_date=start, to_date=today)
                if not df.empty:
                    last_close = float(df["CLOSE"].iloc[-1])
                    volume = float(df["TOTAL TRADE QUANTITY"].iloc[-1]) if "TOTAL TRADE QUANTITY" in df.columns else None
                    prices[sym] = {"price": round(last_close, 2), "volume": volume}
            except Exception as e:
                print(f"  ⚠ NSE {sym}: {e}")
                continue

        return prices if prices else None
    except ImportError:
        print("  ⚠ jugaad-data not installed")
        return None
    except Exception as e:
        print(f"  ⚠ Indian stock error: {e}")
        return None


# ═══════════════════════════════════════════════════════
#  Mock fallbacks — all prices in INR
# ═══════════════════════════════════════════════════════

MOCK_BASE_INR = {
    # Crypto (approx INR)
    "BTC": 5_500_000, "ETH": 210_000, "SOL": 12_000, "ADA": 42,
    "XRP": 46, "DOGE": 7, "MATIC": 67, "BNB": 52_000,
    "AVAX": 3_000, "DOT": 600,
    # US Stocks (approx in INR after conversion)
    "AAPL": 14_600, "GOOGL": 11_700, "TSLA": 20_900, "MSFT": 31_700,
    "AMZN": 15_000, "NFLX": 40_000, "NVDA": 75_000, "META": 42_000,
    # Indian Stocks (already INR)
    "RELIANCE": 2_500, "TCS": 3_800, "INFY": 1_500, "HDFCBANK": 1_550,
    "ICICIBANK": 1_100, "HINDUNILVR": 2_400, "ITC": 440, "SBIN": 750,
    "BHARTIARTL": 1_500, "KOTAKBANK": 1_800,
}

_sim_prices = {}


def get_mock_price_inr(symbol: str) -> dict:
    """Random walk mock price in INR."""
    base = MOCK_BASE_INR.get(symbol, 1000)
    if symbol not in _sim_prices:
        _sim_prices[symbol] = base + random.random() * base * 0.01
    _sim_prices[symbol] += (random.random() - 0.5) * base * 0.005
    return {"price": round(_sim_prices[symbol], 2), "volume": None}


MOCK_SENTIMENT = [
    ("Bitcoin is going to the moon!", "twitter", 0.9, "BTC"),
    ("Market crash imminent due to inflation.", "news", -0.8, None),
    ("AAPL earnings report shows strong growth.", "news", 0.7, "AAPL"),
    ("Ethereum upgrade will be huge for DeFi.", "reddit", 0.8, "ETH"),
    ("Solana DeFi TVL hits new record!", "twitter", 0.85, "SOL"),
    ("Tesla deliveries beat expectations.", "news", 0.75, "TSLA"),
    ("Reliance Jio subscriber growth accelerates.", "news", 0.7, "RELIANCE"),
    ("TCS wins $2B deal with US bank.", "news", 0.8, "TCS"),
    ("NVIDIA AI chip demand surging.", "news", 0.9, "NVDA"),
    ("HDFC Bank Q3 results disappoint.", "news", -0.5, "HDFCBANK"),
    ("Microsoft Copilot adoption booms.", "news", 0.8, "MSFT"),
    ("Crypto regulation fears spreading.", "news", -0.6, None),
    ("XRP lawsuit verdict drives rally.", "twitter", 0.9, "XRP"),
    ("Amazon AWS growth decelerates.", "news", -0.4, "AMZN"),
    ("Infosys guidance lowered for FY25.", "news", -0.6, "INFY"),
]


# ═══════════════════════════════════════════════════════
#  Celery Tasks — all prices ingested in INR
# ═══════════════════════════════════════════════════════

def _ingest_prices(prices: dict, asset_class: str):
    """Post price data (in INR) to the backend API."""
    exchange = ASSET_CLASSES[asset_class]["exchange"]

    for symbol, data in prices.items():
        payload = {
            "symbol": symbol,
            "price": data["price"],
            "asset_class": asset_class,
            "exchange": exchange,
            "currency": "INR",
            "volume": data.get("volume"),
        }
        try:
            response = requests.post(f"{API_URL}/ingest/market", json=payload, timeout=30)
            if response.status_code != 200:
                print(f"  ✗ {symbol}: {response.text[:100]}")
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")


@celery_app.task
def fetch_crypto_data():
    """Fetch crypto prices in INR from CoinGecko."""
    prices = fetch_crypto_prices_inr()
    if prices:
        _ingest_prices(prices, "crypto")
    else:
        symbols = get_all_symbols("crypto")[:20]  # Limit mock to 20
        mock = {sym: get_mock_price_inr(sym) for sym in symbols}
        _ingest_prices(mock, "crypto")


@celery_app.task
def fetch_us_stock_data():
    """Fetch US stock prices, convert USD→INR."""
    prices = fetch_us_stock_prices_inr()
    if prices:
        _ingest_prices(prices, "us_stock")
    else:
        symbols = get_all_symbols("us_stock")[:20]
        mock = {sym: get_mock_price_inr(sym) for sym in symbols}
        _ingest_prices(mock, "us_stock")


@celery_app.task
def fetch_in_stock_data():
    """Fetch Indian stock prices (already INR)."""
    prices = fetch_indian_stock_prices_inr()
    if prices:
        _ingest_prices(prices, "in_stock")
    else:
        symbols = get_all_symbols("in_stock")[:20]
        mock = {sym: get_mock_price_inr(sym) for sym in symbols}
        _ingest_prices(mock, "in_stock")


@celery_app.task
def fetch_sentiment_data():
    """Ingest sentiment data."""
    text, source, score, symbol = random.choice(MOCK_SENTIMENT)
    try:
        requests.post(
            f"{API_URL}/ingest/sentiment",
            json={"source": source, "sentiment_score": score, "raw_text": text, "symbol": symbol},
            timeout=5,
        )
    except Exception as e:
        print(f"  ✗ sentiment: {e}")


@celery_app.task
def refresh_ticker_cache():
    """Periodic task to refresh ticker caches from APIs."""
    refresh_all_tickers()


# Legacy compatibility
@celery_app.task
def fetch_market_data():
    fetch_crypto_data()
    fetch_us_stock_data()
    fetch_in_stock_data()
