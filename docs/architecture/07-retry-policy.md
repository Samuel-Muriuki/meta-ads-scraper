# 07 — Retry Policy

## Principle

Retry on **transient** failures. Fail fast on **permanent** ones. Never silently swallow errors.

## Tenacity policies

Three named decorators exported from `src/meta_ads_scraper/retry.py`:

### `@retry_network`

For HTTP and connection errors.

```python
@retry(
    retry=retry_if_exception_type((
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadError,
    )),
    wait=wait_exponential(multiplier=1, min=1, max=16),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
async def fetch_with_retry(...): ...
```

### `@retry_rate_limited`

For HTTP 429.

```python
def _wait_for_retry_after(retry_state):
    exc = retry_state.outcome.exception()
    if isinstance(exc, RateLimitedError) and exc.retry_after:
        return exc.retry_after + random.uniform(0, 5)
    return wait_exponential(multiplier=10, max=120)(retry_state)

@retry(
    retry=retry_if_exception_type(RateLimitedError),
    wait=_wait_for_retry_after,
    stop=stop_after_attempt(3),
)
async def with_rate_limit_retry(...): ...
```

### `@retry_dom`

For Playwright selector misses.

```python
@retry(
    retry=retry_if_exception_type(PlaywrightTimeoutError),
    wait=wait_fixed(2),
    stop=stop_after_attempt(2),
    reraise=True,
)
async def wait_for_results(page): ...
```

## What we DO NOT retry

| Error | Why no retry |
|---|---|
| `ScraperBlockedError` (CAPTCHA, login wall) | Permanent — retrying doesn't help |
| HTTP 4xx (non-429) | Bad request — retrying gives same result |
| `ParseError` (DOM didn't match) | Schema drift — needs code fix |
| `ValidationError` (Pydantic) | Logic error — needs code fix |
| `KeyboardInterrupt` | User intent |
| `asyncio.CancelledError` | Cancellation propagation |

## Logging during retries

Every retry attempt logs:

```json
{
  "event": "retry_attempted",
  "function": "fetch_with_retry",
  "attempt": 2,
  "max_attempts": 5,
  "wait_seconds": 2,
  "exception_type": "TimeoutException",
  "exception_message": "...",
}
```

This lets us see in production logs (or CI test output) exactly which calls are flaky.

## Circuit breaker (future enhancement)

Not in MVP. If we observed too many failures in a window, we'd open a circuit. For this scraper's scope (single user, low concurrency), tenacity alone is enough.

## Testing retry behaviour

Unit tests use a mock function:

```python
async def test_retry_network_succeeds_after_3_failures():
    calls = []
    @retry_network
    async def flaky():
        calls.append(time.time())
        if len(calls) < 4:
            raise httpx.TimeoutException("simulated")
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert len(calls) == 4
```

Verify wait times are roughly exponential (`abs(call[1]-call[0] - 1) < 0.5`, etc.).

## When retries make things worse

A retry that hits the same rate-limited endpoint immediately makes the rate limit worse. The decorators above use jitter and respect `Retry-After` to avoid this. **Never bypass the rate limiter when retrying.**
