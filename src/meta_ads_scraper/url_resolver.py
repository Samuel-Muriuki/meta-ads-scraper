from __future__ import annotations

from urllib.parse import urlencode

from .models import SearchSpec

_LIBRARY_BASE = "https://www.facebook.com/ads/library/"


def resolve_url(spec: SearchSpec) -> str:
    if spec.mode == "keyword":
        return _build_keyword_url(spec)
    raise NotImplementedError(f"{spec.mode!r} mode is implemented in Phase 2")


def _build_keyword_url(spec: SearchSpec) -> str:
    params = {
        "active_status": spec.active_status,
        "ad_type": spec.ad_type,
        "country": spec.country,
        "q": spec.query,
        "search_type": "keyword_unordered",
        "locale": "en_US",
    }
    return f"{_LIBRARY_BASE}?{urlencode(params)}"
