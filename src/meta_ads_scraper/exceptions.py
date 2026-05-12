from __future__ import annotations


class MetaAdsScraperError(Exception):
    pass


class ScraperBlockedError(MetaAdsScraperError):
    pass


class ParseError(MetaAdsScraperError):
    pass


class RateLimitedError(MetaAdsScraperError):
    """Raised when the upstream returns HTTP 429 or an explicit throttle.

    Carries an optional `retry_after` value (seconds) so the
    `@retry_rate_limited` policy can honour the server's hint instead of
    falling back to the default backoff.
    """

    def __init__(self, message: str = "", *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class PageResolutionError(MetaAdsScraperError):
    pass
