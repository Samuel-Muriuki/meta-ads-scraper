"""Tenacity retry policies for the scraper.

Three named policies cover the transient failure modes we expect against
Meta's Ad Library:

* ``@retry_network`` — transport-level failures across both ``httpx`` and
  Playwright. Playwright is included via a message-signature predicate so
  that genuine selector timeouts (which belong to ``@retry_dom``) are not
  swept in.
* ``@retry_rate_limited`` — HTTP 429 / explicit throttling. Honours
  ``RateLimitedError.retry_after`` when the server provided a hint.
* ``@retry_dom`` — Playwright selector timeouts. Fixed short wait,
  reraise on exhaustion so the caller still sees the original exception.

Anything not listed here is intentionally non-retryable. See
``docs/architecture/07-retry-policy.md`` for the rationale matrix.
"""

from __future__ import annotations

import logging
import random

import httpx
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

from .exceptions import RateLimitedError

__all__ = [
    "retry_dom",
    "retry_network",
    "retry_rate_limited",
]

_logger = logging.getLogger("meta_ads_scraper.retry")

# Message-signature predicate for Playwright errors that look like a
# transport blip rather than a code/DOM mismatch. Lowercased for
# case-insensitive matching.
_RETRYABLE_PLAYWRIGHT_SIGNATURES: tuple[str, ...] = (
    "net::err",
    "navigation timeout",
    "page closed",
    "target closed",
)


def _is_retryable_playwright_error(exc: BaseException) -> bool:
    """Return True iff ``exc`` is a Playwright error that smells transient.

    The PlaywrightError class hierarchy is shared by genuine code/DOM
    mismatches (which we must NOT retry) and transport-layer blips (which
    we should). The signature list filters to the latter — extend it if
    Phase 5+ live testing surfaces additional transient message patterns.
    """
    if not isinstance(exc, PlaywrightError):
        return False
    msg = str(exc).lower()
    return any(sig in msg for sig in _RETRYABLE_PLAYWRIGHT_SIGNATURES)


def _wait_for_retry_after(retry_state: RetryCallState) -> float:
    """Wait strategy for ``@retry_rate_limited``.

    Respects ``RateLimitedError.retry_after`` if the server set it,
    otherwise falls back to 60s + jitter to stay polite under sustained
    throttling.
    """
    exc: BaseException | None = None
    if retry_state.outcome is not None:
        exc = retry_state.outcome.exception()
    if isinstance(exc, RateLimitedError) and exc.retry_after is not None:
        # Jitter is non-cryptographic; stdlib random is fine here.
        return float(exc.retry_after) + random.uniform(0.0, 5.0)  # noqa: S311
    return 60.0 + random.uniform(0.0, 10.0)  # noqa: S311


retry_network = retry(
    retry=(
        retry_if_exception_type(
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
            )
        )
        | retry_if_exception(_is_retryable_playwright_error)
    ),
    wait=wait_exponential(multiplier=1, min=1, max=16),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(_logger, logging.INFO),
)
"""Retry transport-level failures across httpx and Playwright.

Schedule: exponential backoff (1s, 2s, 4s, 8s, 16s), 5 attempts total.
The httpx side catches the documented network exceptions; the Playwright
side uses :func:`_is_retryable_playwright_error` so only transport-shaped
messages are retried (genuine selector timeouts fall through to
``@retry_dom``).
"""


retry_rate_limited = retry(
    retry=retry_if_exception_type(RateLimitedError),
    wait=_wait_for_retry_after,
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(_logger, logging.WARNING),
)
"""Retry explicit rate-limit signals.

Honours ``RateLimitedError.retry_after`` when present, otherwise waits
60s + jitter. 3 attempts total — beyond that, the upstream genuinely
wants us gone and we should propagate.
"""


retry_dom = retry(
    retry=retry_if_exception_type(PlaywrightTimeoutError),
    wait=wait_fixed(2),
    stop=stop_after_attempt(2),
    reraise=True,
    before_sleep=before_sleep_log(_logger, logging.INFO),
)
"""Retry Playwright selector timeouts.

Fixed 2s wait, 2 attempts total, ``reraise=True`` so the caller observes
the original ``PlaywrightTimeoutError`` after exhaustion instead of a
``RetryError`` wrapper.
"""
