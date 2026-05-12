"""Unit tests for tenacity retry policies in `meta_ads_scraper.retry`.

Strategy: each test defines a local async function decorated with the
policy under test, swaps `<fn>.retry.sleep` with a no-op recorder, and
exercises the policy against an instrumented body. This isolates the
schedule contract from real wall-clock sleep — no asyncio.sleep, no
flakiness, no Windows clock-resolution noise.

Per the Phase 4 prompt stop condition: if these timing assertions ever
go flaky from tenacity-internal changes to its sleep dispatch, mark
`@pytest.mark.flaky` and surface; do not tune thresholds silently.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import RetryError

from meta_ads_scraper.exceptions import RateLimitedError, ScraperBlockedError
from meta_ads_scraper.retry import retry_dom, retry_network, retry_rate_limited


class _SleepRecorder:
    """Async no-op sleep that records wait values."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(float(seconds))


# -------------------------------------------------------------------------
# @retry_network
# -------------------------------------------------------------------------


class TestRetryNetwork:
    async def test_succeeds_after_three_failures(self) -> None:
        attempts = 0

        @retry_network
        async def flaky() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 4:
                raise httpx.ConnectError("simulated")
            return "ok"

        recorder = _SleepRecorder()
        flaky.retry.sleep = recorder
        result = await flaky()
        assert result == "ok"
        assert attempts == 4
        # Three retries before the fourth (successful) attempt.
        assert len(recorder.calls) == 3

    async def test_exponential_schedule(self) -> None:
        attempts = 0

        @retry_network
        async def always_fails() -> None:
            nonlocal attempts
            attempts += 1
            raise httpx.ConnectError("simulated")

        recorder = _SleepRecorder()
        always_fails.retry.sleep = recorder
        with pytest.raises((RetryError, httpx.ConnectError)):
            await always_fails()
        # 5 attempts -> 4 sleeps. wait_exponential(multiplier=1, min=1, max=16)
        # produces 1, 2, 4, 8 before the 5th attempt is allowed.
        assert recorder.calls == [1.0, 2.0, 4.0, 8.0]
        assert attempts == 5

    async def test_propagates_after_max_attempts(self) -> None:
        @retry_network
        async def always_fails() -> None:
            raise httpx.ConnectError("simulated")

        always_fails.retry.sleep = _SleepRecorder()
        # Default reraise=False on @retry_network -> tenacity wraps in RetryError.
        with pytest.raises(RetryError):
            await always_fails()

    async def test_non_retryable_error_propagates_immediately(self) -> None:
        attempts = 0

        @retry_network
        async def raises_blocked() -> None:
            nonlocal attempts
            attempts += 1
            raise ScraperBlockedError("login wall")

        recorder = _SleepRecorder()
        raises_blocked.retry.sleep = recorder
        with pytest.raises(ScraperBlockedError):
            await raises_blocked()
        assert attempts == 1
        assert recorder.calls == []

    async def test_value_error_propagates_immediately(self) -> None:
        attempts = 0

        @retry_network
        async def raises_value() -> None:
            nonlocal attempts
            attempts += 1
            raise ValueError("logic bug")

        recorder = _SleepRecorder()
        raises_value.retry.sleep = recorder
        with pytest.raises(ValueError, match="logic bug"):
            await raises_value()
        assert attempts == 1
        assert recorder.calls == []

    async def test_retries_playwright_transport_signature(self) -> None:
        """Playwright errors whose message matches a transport signature
        (net::err, navigation timeout, page closed, target closed) must
        be retried via the predicate.
        """
        attempts = 0

        @retry_network
        async def net_err() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise PlaywrightError("net::ERR_CONNECTION_RESET")
            return "ok"

        recorder = _SleepRecorder()
        net_err.retry.sleep = recorder
        result = await net_err()
        assert result == "ok"
        assert attempts == 2

    async def test_skips_playwright_non_transport_error(self) -> None:
        """A generic PlaywrightError without a transport signature must
        propagate immediately so it does not mask DOM-shaped bugs.
        """
        attempts = 0

        @retry_network
        async def selector_miss() -> None:
            nonlocal attempts
            attempts += 1
            raise PlaywrightError("Selector did not resolve to a DOM node")

        recorder = _SleepRecorder()
        selector_miss.retry.sleep = recorder
        with pytest.raises(PlaywrightError):
            await selector_miss()
        assert attempts == 1
        assert recorder.calls == []


# -------------------------------------------------------------------------
# @retry_rate_limited
# -------------------------------------------------------------------------


class TestRetryRateLimited:
    async def test_respects_retry_after_header(self) -> None:
        attempts = 0

        @retry_rate_limited
        async def throttled() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RateLimitedError("429", retry_after=30)
            return "ok"

        recorder = _SleepRecorder()
        throttled.retry.sleep = recorder
        result = await throttled()
        assert result == "ok"
        # retry_after=30 plus uniform jitter [0, 5].
        assert len(recorder.calls) == 1
        assert 30.0 <= recorder.calls[0] <= 35.0

    async def test_defaults_to_sixty_seconds_plus_jitter(self) -> None:
        attempts = 0

        @retry_rate_limited
        async def throttled() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RateLimitedError("429 with no header")
            return "ok"

        recorder = _SleepRecorder()
        throttled.retry.sleep = recorder
        result = await throttled()
        assert result == "ok"
        # Default base of 60s plus uniform jitter [0, 10].
        assert len(recorder.calls) == 1
        assert 60.0 <= recorder.calls[0] <= 70.0

    async def test_stops_after_three_attempts(self) -> None:
        attempts = 0

        @retry_rate_limited
        async def always_throttled() -> None:
            nonlocal attempts
            attempts += 1
            raise RateLimitedError("429", retry_after=1)

        recorder = _SleepRecorder()
        always_throttled.retry.sleep = recorder
        with pytest.raises((RetryError, RateLimitedError)):
            await always_throttled()
        assert attempts == 3


# -------------------------------------------------------------------------
# @retry_dom
# -------------------------------------------------------------------------


class TestRetryDom:
    async def test_reraises_after_two_attempts(self) -> None:
        attempts = 0

        @retry_dom
        async def always_times_out() -> None:
            nonlocal attempts
            attempts += 1
            raise PlaywrightTimeoutError("selector timeout")

        recorder = _SleepRecorder()
        always_times_out.retry.sleep = recorder
        # reraise=True -> the original PlaywrightTimeoutError, not RetryError.
        with pytest.raises(PlaywrightTimeoutError):
            await always_times_out()
        assert attempts == 2
        assert recorder.calls == [2.0]

    async def test_succeeds_on_second_attempt(self) -> None:
        attempts = 0

        @retry_dom
        async def flaky_selector() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise PlaywrightTimeoutError("first try")
            return "found"

        recorder = _SleepRecorder()
        flaky_selector.retry.sleep = recorder
        result = await flaky_selector()
        assert result == "found"
        assert attempts == 2
        assert recorder.calls == [2.0]

    async def test_does_not_retry_non_timeout_playwright_error(self) -> None:
        attempts = 0

        @retry_dom
        async def crashes() -> None:
            nonlocal attempts
            attempts += 1
            raise PlaywrightError("frame detached")

        recorder = _SleepRecorder()
        crashes.retry.sleep = recorder
        with pytest.raises(PlaywrightError):
            await crashes()
        assert attempts == 1
        assert recorder.calls == []
