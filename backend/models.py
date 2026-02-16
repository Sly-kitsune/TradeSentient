from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from backend.database import Base


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    asset_class = Column(String, index=True)       # crypto, us_stock, in_stock
    exchange = Column(String, default="global")     # NASDAQ/NYSE, NSE, global
    price = Column(Float)
    volume = Column(Float, nullable=True)           # 24h volume when available
    currency = Column(String, default="INR")        # Always INR
    timestamp = Column(DateTime, default=datetime.utcnow)


class SentimentLog(Base):
    __tablename__ = "sentiment_logs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=True)  # optional: tie to asset
    source = Column(String)       # reddit, twitter, news, coingecko
    sentiment_score = Column(Float)   # -1.0 to 1.0
    raw_text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class TradeSignal(Base):
    __tablename__ = "trade_signals"

    id = Column(Integer, primary_key=True, index=True)
    signal_type = Column(String)      # BUY, SELL
    symbol = Column(String, index=True)
    asset_class = Column(String, nullable=True)
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)