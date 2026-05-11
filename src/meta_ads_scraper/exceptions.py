from __future__ import annotations


class MetaAdsScraperError(Exception):
    pass


class ScraperBlockedError(MetaAdsScraperError):
    pass


class ParseError(MetaAdsScraperError):
    pass


class RateLimitedError(MetaAdsScraperError):
    pass


class PageResolutionError(MetaAdsScraperError):
    pass
