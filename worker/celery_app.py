from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    # Crypto — every 2 seconds
    "fetch-crypto-data-every-2s": {
        "task": "worker.tasks.fetch_crypto_data",
        "schedule": 2.0,
    },
    # US Stocks — every 5 seconds
    "fetch-us-stock-data-every-5s": {
        "task": "worker.tasks.fetch_us_stock_data",
        "schedule": 5.0,
    },
    # Indian Stocks — every 10 seconds
    "fetch-in-stock-data-every-10s": {
        "task": "worker.tasks.fetch_in_stock_data",
        "schedule": 10.0,
    },
    # Sentiment — every 5 seconds
    "fetch-sentiment-data-every-5s": {
        "task": "worker.tasks.fetch_sentiment_data",
        "schedule": 5.0,
    },
    # Ticker cache refresh — every 15 minutes
    "refresh-ticker-cache-every-15m": {
        "task": "worker.tasks.refresh_ticker_cache",
        "schedule": 900.0,
    },
}
