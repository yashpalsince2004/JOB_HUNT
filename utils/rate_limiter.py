"""
Token-bucket rate limiter for controlling API call frequency.

Supports per-domain rate limiting to respect different API quotas
(e.g., Gemini free tier, Google Sheets 300 req/min, scraper politeness).
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger("rate_limiter")


@dataclass
class RateLimiter:
    """
    Simple token-bucket rate limiter.

    Args:
        requests_per_minute: Maximum allowed requests per minute.
        name: Identifier for logging purposes.
    """

    requests_per_minute: float
    name: str = "default"
    _timestamps: list[float] = field(default_factory=list, repr=False)

    @property
    def _window(self) -> float:
        """Time window in seconds (always 60s = 1 minute)."""
        return 60.0

    def _clean_old_timestamps(self) -> None:
        """Remove timestamps older than the rate window."""
        cutoff = time.monotonic() - self._window
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    def wait_sync(self) -> None:
        """Block synchronously until a request slot is available."""
        while True:
            self._clean_old_timestamps()
            if len(self._timestamps) < self.requests_per_minute:
                self._timestamps.append(time.monotonic())
                return
            # Calculate how long to wait for the oldest request to expire
            wait_time = self._timestamps[0] + self._window - time.monotonic()
            if wait_time > 0:
                logger.debug(f"[{self.name}] Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)

    async def wait_async(self) -> None:
        """Yield control asynchronously until a request slot is available."""
        while True:
            self._clean_old_timestamps()
            if len(self._timestamps) < self.requests_per_minute:
                self._timestamps.append(time.monotonic())
                return
            wait_time = self._timestamps[0] + self._window - time.monotonic()
            if wait_time > 0:
                logger.debug(f"[{self.name}] Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)


class MultiRateLimiter:
    """
    Manages multiple rate limiters keyed by domain/service name.

    Usage:
        limiter = MultiRateLimiter()
        limiter.register("gemini", requests_per_minute=10)
        limiter.register("sheets", requests_per_minute=60)

        await limiter.wait("gemini")
        # ... make API call ...
    """

    def __init__(self) -> None:
        self._limiters: dict[str, RateLimiter] = {}

    def register(self, name: str, requests_per_minute: float) -> None:
        """Register a new rate limiter for a named service."""
        self._limiters[name] = RateLimiter(
            requests_per_minute=requests_per_minute, name=name
        )
        logger.debug(f"Registered rate limiter: {name} ({requests_per_minute} rpm)")

    def wait_sync(self, name: str) -> None:
        """Synchronously wait for the named limiter."""
        if name in self._limiters:
            self._limiters[name].wait_sync()

    async def wait_async(self, name: str) -> None:
        """Asynchronously wait for the named limiter."""
        if name in self._limiters:
            await self._limiters[name].wait_async()

    def get(self, name: str) -> RateLimiter | None:
        """Get a specific rate limiter by name."""
        return self._limiters.get(name)


# Global rate limiter instance — register services at startup
rate_limiter = MultiRateLimiter()
