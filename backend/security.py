"""
Security utilities and middleware for TradeSentient API
Implements OWASP best practices, rate limiting, and input validation
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re
import html
import os


# ═══════════════════════════════════════════════════════
#  Rate Limiter Configuration
# ═══════════════════════════════════════════════════════

def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses IP address as the primary identifier.
    """
    # Get real IP from X-Forwarded-For header (for proxies/load balancers)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_identifier,
    default_limits=["100/minute"],  # Default: 100 requests per minute per IP
    storage_uri="memory://",  # Use in-memory storage (upgrade to Redis for production)
)


# ═══════════════════════════════════════════════════════
#  Input Sanitization & Validation
# ═══════════════════════════════════════════════════════

def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent XSS and injection attacks.
    
    Args:
        text: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        HTTPException: If input is invalid
    """
    if not isinstance(text, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input must be a string"
        )
    
    # Trim to max length
    if len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input exceeds maximum length of {max_length} characters"
        )
    
    # Escape HTML to prevent XSS
    sanitized = html.escape(text.strip())
    
    return sanitized


def validate_symbol(symbol: str) -> str:
    """
    Validate trading symbol format.
    Allows only alphanumeric characters, hyphens, and underscores.
    
    Args:
        symbol: Trading symbol to validate
        
    Returns:
        Validated symbol in uppercase
        
    Raises:
        HTTPException: If symbol format is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol is required and must be a string"
        )
    
    # Check length (1-20 characters)
    if len(symbol) < 1 or len(symbol) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol must be between 1 and 20 characters"
        )
    
    # Allow only alphanumeric, hyphens, and underscores
    if not re.match(r'^[A-Za-z0-9_-]+$', symbol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol can only contain letters, numbers, hyphens, and underscores"
        )
    
    return symbol.upper()


def validate_price(price: float) -> float:
    """
    Validate price value.
    
    Args:
        price: Price to validate
        
    Returns:
        Validated price
        
    Raises:
        HTTPException: If price is invalid
    """
    if not isinstance(price, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price must be a number"
        )
    
    if price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price must be greater than zero"
        )
    
    # Prevent unrealistic values (max 1 billion)
    if price > 1_000_000_000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price value is unrealistic"
        )
    
    return float(price)


def validate_sentiment_score(score: float) -> float:
    """
    Validate sentiment score (-1 to 1 range).
    
    Args:
        score: Sentiment score to validate
        
    Returns:
        Validated score
        
    Raises:
        HTTPException: If score is out of range
    """
    if not isinstance(score, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sentiment score must be a number"
        )
    
    if score < -1 or score > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sentiment score must be between -1 and 1"
        )
    
    return float(score)


# ═══════════════════════════════════════════════════════
#  Security Headers Middleware
# ═══════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses following OWASP best practices.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (basic)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HTTPS enforcement (only if running on HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# ═══════════════════════════════════════════════════════
#  Request Size Limit Middleware
# ═══════════════════════════════════════════════════════

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limits request body size to prevent large payload DoS attacks.
    """
    
    def __init__(self, app, max_size: int = 1_048_576):  # Default: 1MB
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "Request body too large",
                    "max_size_bytes": self.max_size,
                    "max_size_mb": self.max_size / 1_048_576
                }
            )
        
        return await call_next(request)


# ═══════════════════════════════════════════════════════
#  Graceful Rate Limit Error Handler
# ═══════════════════════════════════════════════════════

async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    Returns graceful 429 response with Retry-After header.
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please slow down and try again later.",
            "retry_after_seconds": 60
        },
        headers={
            "Retry-After": "60"
        }
    )


# ═══════════════════════════════════════════════════════
#  Environment-based Configuration
# ═══════════════════════════════════════════════════════

def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def get_allowed_origins() -> list[str]:
    """
    Get allowed CORS origins from environment.
    Defaults to localhost for development.
    """
    origins_env = os.getenv("ALLOWED_ORIGINS", "")
    
    if origins_env:
        # Parse comma-separated list from environment
        return [origin.strip() for origin in origins_env.split(",")]
    
    # Default origins for development
    if is_production():
        return [
            "https://tradesentient.netlify.app",
        ]
    else:
        return [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://tradesentient.netlify.app",
        ]
