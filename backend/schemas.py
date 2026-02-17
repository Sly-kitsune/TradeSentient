from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
import re


# --- Market Price ---

class MarketPriceBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    price: float = Field(..., gt=0, le=1_000_000_000, description="Price in INR (must be positive)")
    asset_class: Optional[str] = Field(None, max_length=50, description="crypto, us_stock, in_stock")
    exchange: Optional[str] = Field(None, max_length=100, description="Exchange name")
    volume: Optional[float] = Field(None, ge=0, description="Trading volume (non-negative)")
    currency: Optional[str] = Field("INR", max_length=10, description="Currency code")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol contains only alphanumeric, hyphens, underscores."""
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Symbol can only contain letters, numbers, hyphens, and underscores")
        return v.upper()
    
    @field_validator('asset_class')
    @classmethod
    def validate_asset_class(cls, v: Optional[str]) -> Optional[str]:
        """Validate asset class is one of the allowed values."""
        if v is not None:
            allowed = ['crypto', 'us_stock', 'in_stock']
            if v not in allowed:
                raise ValueError(f"Asset class must be one of: {', '.join(allowed)}")
        return v

class MarketPriceCreate(MarketPriceBase):
    pass

class MarketPrice(MarketPriceBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Sentiment Log ---

class SentimentLogBase(BaseModel):
    source: str = Field(..., min_length=1, max_length=100, description="Source of sentiment")
    sentiment_score: float = Field(..., ge=-1, le=1, description="Sentiment score (-1 to 1)")
    raw_text: str = Field(..., min_length=1, max_length=5000, description="Sentiment text")
    symbol: Optional[str] = Field(None, min_length=1, max_length=20, description="Related symbol")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: Optional[str]) -> Optional[str]:
        """Validate symbol format if provided."""
        if v is not None and not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Symbol can only contain letters, numbers, hyphens, and underscores")
        return v.upper() if v else None
    
    @field_validator('raw_text')
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Sanitize text to prevent XSS."""
        import html
        return html.escape(v.strip())

class SentimentLogCreate(SentimentLogBase):
    pass

class SentimentLog(SentimentLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Trade Signal ---

class TradeSignalBase(BaseModel):
    signal_type: str = Field(..., min_length=1, max_length=50, description="Signal type")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    details: Optional[str] = Field(None, max_length=1000, description="Signal details")
    asset_class: Optional[str] = Field(None, max_length=50, description="Asset class")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Symbol can only contain letters, numbers, hyphens, and underscores")
        return v.upper()
    
    @field_validator('signal_type')
    @classmethod
    def validate_signal_type(cls, v: str) -> str:
        """Validate signal type is one of the allowed values."""
        allowed = ['BUY', 'SELL', 'HOLD', 'GOLDEN_CROSS', 'DEATH_CROSS']
        if v.upper() not in allowed:
            raise ValueError(f"Signal type must be one of: {', '.join(allowed)}")
        return v.upper()

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