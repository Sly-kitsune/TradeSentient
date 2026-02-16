"""
Signal Generation Engine — SMA Crossover on live price data.

Maintains a rolling price window per symbol and generates BUY/SELL
signals when the short-term SMA crosses the long-term SMA.
"""

from collections import defaultdict, deque
from datetime import datetime


class SignalEngine:
    """
    Real-time SMA crossover signal generator.

    For each symbol, keeps the last `long_window` prices and computes
    a short SMA vs long SMA. On crossover events, emits a signal dict.
    """

    def __init__(self, short_window: int = 10, long_window: int = 30):
        self.short_window = short_window
        self.long_window = long_window
        # symbol -> deque of prices
        self.prices: dict[str, deque] = defaultdict(lambda: deque(maxlen=long_window + 5))
        # symbol -> last signal direction (1 = bullish, -1 = bearish, 0 = neutral)
        self.last_signal: dict[str, int] = defaultdict(int)

    def _sma(self, prices: list[float], window: int) -> float | None:
        if len(prices) < window:
            return None
        return sum(prices[-window:]) / window

    def on_price(self, symbol: str, price: float) -> dict | None:
        """
        Feed a new price tick. Returns a signal dict if a crossover
        occurred, or None if no signal.
        """
        self.prices[symbol].append(price)
        price_list = list(self.prices[symbol])

        short_sma = self._sma(price_list, self.short_window)
        long_sma = self._sma(price_list, self.long_window)

        if short_sma is None or long_sma is None:
            return None  # Not enough data yet

        # Determine current stance
        if short_sma > long_sma:
            current = 1  # Bullish
        elif short_sma < long_sma:
            current = -1  # Bearish
        else:
            current = 0

        prev = self.last_signal[symbol]
        self.last_signal[symbol] = current

        # Signal on crossover only
        if prev != 0 and current != prev:
            signal_type = "BUY" if current == 1 else "SELL"
            return {
                "signal_type": signal_type,
                "symbol": symbol,
                "price": round(price, 2),
                "short_sma": round(short_sma, 2),
                "long_sma": round(long_sma, 2),
                "details": f"{signal_type} — SMA{self.short_window} ({short_sma:.2f}) crossed {'above' if current == 1 else 'below'} SMA{self.long_window} ({long_sma:.2f})",
                "timestamp": datetime.utcnow().isoformat(),
            }

        return None
