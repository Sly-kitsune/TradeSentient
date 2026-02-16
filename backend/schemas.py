from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# --- Market Price ---

class MarketPriceBase(BaseModel):
    symbol: str
    price: float
    asset_class: Optional[str] = None      # crypto, us_stock, in_stock
    exchange: Optional[str] = None
    volume: Optional[float] = None
    currency: Optional[str] = "INR"

class MarketPriceCreate(MarketPriceBase):
    pass

class MarketPrice(MarketPriceBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Sentiment Log ---

class SentimentLogBase(BaseModel):
    source: str
    sentiment_score: float
    raw_text: str
    symbol: Optional[str] = None           # optional: tie sentiment to a symbol

class SentimentLogCreate(SentimentLogBase):
    pass

class SentimentLog(SentimentLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Trade Signal ---

class TradeSignalBase(BaseModel):
    signal_type: str
    symbol: str
    details: Optional[str] = None
    asset_class: Optional[str] = None

class TradeSignalCreate(TradeSignalBase):
    pass

class TradeSignal(TradeSignalBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Ticker Info (for GET /tickers) ---

class TickerInfo(BaseModel):
    symbol: str
    name: str
    asset_class: str
    exchange: str
    currency: str