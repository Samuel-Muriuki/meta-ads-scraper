"""Asyncio rate limiter for the scraper.

Combines two knobs:

* ``requests_per_second`` — minimum spacing between successful acquires.
  Enforced via ``asyncio.sleep`` on a monotonic clock.
* ``max_concurrency`` — number of acquires that may overlap. Backed by
  ``asyncio.Semaphore``. Hard-clamped to ``MAX_CONCURRENCY_CEILING`` so a
  caller cannot accidentally pour traffic at the upstream.

Usage:

    limiter = RateLimiter(requests_per_second=2.0, max_concurrency=1)
    await limiter.acquire()
    # ... do one request worth of work

The limiter is intended for use within a single asyncio event loop;
it makes no thread-safety claims.
"""

from __future__ import annotations

import asyncio
import time

import structlog

logger = structlog.get_logger()

__all__ = [
    "MAX_CONCURRENCY_CEILING",
    "RateLimiter",
]

MAX_CONCURRENCY_CEILING = 3
"""Hard cap on concurrent in-flight acquires.

Per `PLANNING-BRIEF.md` §6: ``Configurable concurrency (default 1, max 3)``.
The limiter clamps any request above this and logs a warning.
"""

_MIN_REQUESTS_PER_SECOND = 1e-3
"""Floor on the configured rate to avoid divide-by-zero / pathological waits."""


class RateLimiter:
    """Token-pacing rate limiter with a concurrency ceiling."""

    def __init__(
        self,
        requests_per_second: float = 1.0,
        max_concurrency: int = 1,
    ) -> None:
        if requests_per_second < _MIN_REQUESTS_PER_SECOND:
            raise ValueError(
                f"requests_per_second must be >= {_MIN_REQUESTS_PER_SECOND}, "
                f"got {requests_per_second!r}"
            )
        if max_concurrency < 1:
            raise ValueError(f"max_concurrency must be >= 1, got {max_concurrency!r}")

        if max_concurrency > MAX_CONCURRENCY_CEILING:
            logger.warning(
                "rate_limit_concurrency_clamped",
                requested=max_concurrency,
                clamped_to=MAX_CONCURRENCY_CEILING,
            )
            max_concurrency = MAX_CONCURRENCY_CEILING

        self._requests_per_second = requests_per_second
        self._max_concurrency = max_concurrency
        self._min_interval = 1.0 / requests_per_second
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._lock = asyncio.Lock()
        self._last_acquire_monotonic: float | None = None

    @property
    def requests_per_second(self) -> float:
        return self._requests_per_second

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency

    # Note: this implementation serialises the timed wait under a lock, so
    # max_concurrency provides queue-depth bounding rather than parallel
    # execution. Single-coroutine scrape path is the supported case.
    # Revisit if introducing concurrent scraping across multiple SearchSpecs.
    async def acquire(self) -> None:
        """Block until both a concurrency slot and the next pace-tick are
        available. The slot is held for the duration of this call only;
        callers do not need to call a release().
        """
        await self._semaphore.acquire()
        try:
            async with self._lock:
                now = time.monotonic()
                if self._last_acquire_monotonic is not None:
                    elapsed = now - self._last_acquire_monotonic
                    wait = self._min_interval - elapsed
                    if wait > 0:
                        await asyncio.sleep(wait)
                self._last_acquire_monotonic = time.monotonic()
        finally:
            self._semaphore.release()
