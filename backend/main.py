from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import json
import asyncio
import redis.asyncio as redis
from backend.database import get_db, init_db
from backend.models import MarketPrice, SentimentLog, TradeSignal
from backend import schemas
from backend.signals import SignalEngine
from backend.ticker_config import ASSET_CLASSES, get_cached_tickers, refresh_all_tickers, get_asset_class, get_ticker_info
from backend.forex import get_usd_inr_rate
from backend.security import (
    limiter,
    rate_limit_error_handler,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    get_allowed_origins,
)
from slowapi.errors import RateLimitExceeded
import os

# ═══════════════════════════════════════════════════════
#  FastAPI App Initialization with Security
# ═══════════════════════════════════════════════════════

app = FastAPI(
    title="TradeSentient API",
    version="4.0.0",
    description="Real-time market intelligence API with security hardening",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter state
app.state.limiter = limiter

# Add rate limit error handler
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)

# Add security headers middleware (OWASP best practices)
app.add_middleware(SecurityHeadersMiddleware)

# Add request size limit middleware (prevent large payload DoS)
app.add_middleware(RequestSizeLimitMiddleware, max_size=1_048_576)  # 1MB limit

# CORS middleware with restricted origins (security hardening)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),  # Restricted to specific domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit methods only
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
signal_engine = SignalEngine(short_window=10, long_window=30)


# ═══════════════════════════════════════════════════════
#  WebSocket Connection Manager
# ═══════════════════════════════════════════════════════

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str] | None] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = None

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.subscriptions.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, symbols: list[str]):
        self.subscriptions[websocket] = set(symbols)

    def subscribe_add(self, websocket: WebSocket, symbol: str):
        if self.subscriptions.get(websocket) is None:
            self.subscriptions[websocket] = set()
        self.subscriptions[websocket].add(symbol)

    async def broadcast(self, message: str, symbol: str | None = None):
        disconnected = []
        for connection in self.active_connections:
            try:
                subs = self.subscriptions.get(connection)
                if subs is None or symbol is None or symbol in subs:
                    await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()
use_redis = False
redis_client = None


async def check_redis():
    global use_redis, redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        use_redis = True
        print("✓ Connected to Redis")
    except Exception as e:
        use_redis = False
        print(f"✗ Redis unavailable ({e}), using in-memory broadcast")


@app.on_event("startup")
async def startup_event():
    print("→ Starting up TradeSentient Backend...")
    try:
        await init_db()
        print("  ✓ Database initialized")
    except Exception as e:
        print(f"  ✗ Database init failed: {e}")

    await check_redis()
    if use_redis:
        asyncio.create_task(redis_listener())

    # Refresh ticker caches on startup (runs in thread to avoid blocking)
    try:
        print("→ Triggering initial ticker refresh...")
        asyncio.get_event_loop().run_in_executor(None, refresh_all_tickers)
    except Exception as e:
        print(f"  ✗ Ticker refresh failed: {e}")

    # Schedule periodic refresh every 15 minutes
    asyncio.create_task(periodic_ticker_refresh())
    print("✓ Startup complete")


async def periodic_ticker_refresh():
    """Refresh ticker caches every 15 minutes."""
    while True:
        await asyncio.sleep(900)  # 15 minutes
        try:
            await asyncio.get_event_loop().run_in_executor(None, refresh_all_tickers)
            print("✓ Ticker caches refreshed")
        except Exception as e:
            print(f"✗ Ticker refresh error: {e}")


async def redis_listener():
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("market_updates", "sentiment_updates", "signal_updates")
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    symbol = data.get("symbol")
                    await manager.broadcast(message["data"], symbol=symbol)
                except Exception:
                    await manager.broadcast(message["data"])
    except Exception as e:
        print(f"Redis listener error: {e}")


async def publish_update(channel: str, message: str, symbol: str | None = None):
    try:
        if use_redis and redis_client:
            await redis_client.publish(channel, message)
        else:
            await manager.broadcast(message, symbol=symbol)
    except Exception as e:
        print(f"Publish error: {e}")


# ═══════════════════════════════════════════════════════
#  WebSocket endpoint
# ═══════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue
            try:
                msg = json.loads(data)
                if msg.get("action") == "subscribe":
                    symbols = msg.get("symbols", [])
                    if isinstance(symbols, list) and len(symbols) > 0:
                        manager.subscribe(websocket, symbols)
                        await websocket.send_text(json.dumps({"type": "subscribed", "symbols": symbols}))
                elif msg.get("action") == "subscribe_add":
                    symbol = msg.get("symbol", "")
                    if symbol:
                        manager.subscribe_add(websocket, symbol)
                        await websocket.send_text(json.dumps({"type": "subscribed", "symbol": symbol}))
                elif msg.get("action") == "subscribe_all":
                    manager.subscriptions[websocket] = None
                    await websocket.send_text(json.dumps({"type": "subscribed", "symbols": "all"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════
#  API Endpoints (with rate limiting)
# ═══════════════════════════════════════════════════════

@app.get("/")
@limiter.limit("100/minute")  # Public endpoint: 100 req/min per IP
async def root(request: Request):
    """Root endpoint - API status and information"""
    return {
        "name": "TradeSentient API",
        "version": "4.0.0",
        "status": "running",
        "security": "hardened",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "tickers": "/tickers",
            "forex": "/forex/usd-inr",
            "market_data": "/market-data/{symbol}",
            "sentiment": "/sentiment-data",
            "signals": "/signals",
            "websocket": "/ws"
        }
    }

@app.get("/tickers")
@limiter.limit("100/minute")  # Public endpoint: 100 req/min per IP
async def get_tickers(request: Request):
    """Return top 50 tickers per asset class (from Redis cache)."""
    result = {}
    for cls_key, cls_meta in ASSET_CLASSES.items():
        tickers = get_cached_tickers(cls_key)
        result[cls_key] = {
            "label": cls_meta["label"],
            "exchange": cls_meta["exchange"],
            "currency": "INR",
            "count": len(tickers),
            "assets": [
                {"symbol": t["symbol"], "name": t.get("name", t["symbol"])}
                for t in tickers
            ],
        }
    return result


@app.get("/forex/usd-inr")
@limiter.limit("100/minute")  # Public endpoint: 100 req/min per IP
async def get_forex_rate(request: Request):
    """Return the current cached USD→INR rate."""
    rate = get_usd_inr_rate()
    return {"usd_inr": rate, "currency": "INR"}


@app.get("/market-data/{symbol}", response_model=List[schemas.MarketPrice])
@limiter.limit("100/minute")  # Public endpoint: 100 req/min per IP
async def get_market_data(
    request: Request,
    symbol: str,
    asset_class: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = select(MarketPrice).where(MarketPrice.symbol == symbol)
    if asset_class:
        query = query.where(MarketPrice.asset_class == asset_class)
    query = query.order_by(MarketPrice.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/sentiment-data", response_model=List[schemas.SentimentLog])
@limiter.limit("100/minute")  # Public endpoint: 100 req/min per IP
async def get_sentiment_data(
    request: Request,
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(SentimentLog)
    if symbol:
        query = query.where(SentimentLog.symbol == symbol)
    query = query.order_by(SentimentLog.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/signals", response_model=List[schemas.TradeSignal])
@limiter.limit("100/minute")  # Public endpoint: 100 req/min per IP
async def get_signals(
    request: Request,
    asset_class: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(TradeSignal)
    if asset_class:
        query = query.where(TradeSignal.asset_class == asset_class)
    query = query.order_by(TradeSignal.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/signals/{symbol}", response_model=List[schemas.TradeSignal])
@limiter.limit("100/minute")  # Public endpoint: 100 req/min per IP
async def get_signals_by_symbol(request: Request, symbol: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TradeSignal).where(TradeSignal.symbol == symbol)
        .order_by(TradeSignal.timestamp.desc()).limit(20)
    )
    return result.scalars().all()


# ═══════════════════════════════════════════════════════
#  Ingestion endpoints — ALL prices stored in INR
#  Higher rate limits for worker (1000/min)
# ═══════════════════════════════════════════════════════

@app.post("/ingest/market", response_model=schemas.MarketPrice)
@limiter.limit("1000/minute")  # Ingestion endpoint: 1000 req/min for worker
async def ingest_market_data(request: Request, data: schemas.MarketPriceCreate, db: AsyncSession = Depends(get_db)):
    asset_class = data.asset_class or get_asset_class(data.symbol)
    ticker_info = get_ticker_info(data.symbol)

    new_entry = MarketPrice(
        symbol=data.symbol,
        price=data.price,  # Already in INR (workers convert before posting)
        asset_class=asset_class,
        exchange=data.exchange or (ticker_info["exchange"] if ticker_info else "unknown"),
        volume=data.volume,
        currency="INR",  # Always INR
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    msg = json.dumps({
        "type": "market",
        "symbol": new_entry.symbol,
        "price": new_entry.price,
        "asset_class": new_entry.asset_class,
        "exchange": new_entry.exchange,
        "currency": "INR",
        "volume": new_entry.volume,
        "timestamp": str(new_entry.timestamp),
    })
    await publish_update("market_updates", msg, symbol=new_entry.symbol)

    signal = signal_engine.on_price(data.symbol, data.price)
    if signal:
        new_signal = TradeSignal(
            signal_type=signal["signal_type"],
            symbol=signal["symbol"],
            asset_class=asset_class,
            details=signal["details"],
        )
        db.add(new_signal)
        await db.commit()
        await db.refresh(new_signal)

        signal_msg = json.dumps({
            "type": "signal",
            "signal_type": signal["signal_type"],
            "symbol": signal["symbol"],
            "asset_class": asset_class,
            "price": signal["price"],
            "short_sma": signal["short_sma"],
            "long_sma": signal["long_sma"],
            "details": signal["details"],
            "timestamp": str(new_signal.timestamp),
        })
        await publish_update("signal_updates", signal_msg, symbol=signal["symbol"])

    return new_entry


@app.post("/ingest/sentiment", response_model=schemas.SentimentLog)
@limiter.limit("1000/minute")  # Ingestion endpoint: 1000 req/min for worker
async def ingest_sentiment(request: Request, data: schemas.SentimentLogCreate, db: AsyncSession = Depends(get_db)):
    new_entry = SentimentLog(
        source=data.source,
        sentiment_score=data.sentiment_score,
        raw_text=data.raw_text,
        symbol=data.symbol,
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    msg = json.dumps({
        "type": "sentiment",
        "source": new_entry.source,
        "score": new_entry.sentiment_score,
        "text": new_entry.raw_text,
        "symbol": new_entry.symbol,
        "timestamp": str(new_entry.timestamp),
    })
    await publish_update("sentiment_updates", msg, symbol=new_entry.symbol)

    return new_entry
