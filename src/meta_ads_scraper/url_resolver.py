from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs, urlencode, urlparse

from .exceptions import PageResolutionError
from .models import SearchSpec

_LIBRARY_BASE = "https://www.facebook.com/ads/library/"
_FACEBOOK_HOSTS = frozenset({"www.facebook.com", "m.facebook.com", "facebook.com"})
_RESERVED_SLUGS = frozenset(
    {
        "profile.php",
        "groups",
        "marketplace",
        "watch",
        "events",
        "pages",
        "sharer.php",
        "ads",
        "business",
        "help",
        "policies",
        "legal",
        "login",
        "signup",
        "recover",
    }
)
PAGE_ID_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'"delegate_page":\{"id":"(\d+)"'),
    re.compile(r'"associated_page_id":"(\d+)"'),
    re.compile(r'\\"page_id\\":\\"(\d+)\\"'),
    re.compile(r'"page_id":"(\d+)"'),
    re.compile(r'"pageID":"(\d+)"'),
    re.compile(r'content="fb://page/?\?id=(\d+)"'),
    re.compile(r'al:android:url" content="fb://page/(\d+)"'),
)

PageIdResolver = Callable[[str], Awaitable[str]]


async def resolve_url(spec: SearchSpec, *, page_id_resolver: PageIdResolver | None = None) -> str:
    if spec.mode == "keyword":
        return _build_keyword_url(spec)
    slug = spec.query if spec.mode == "page_slug" else _extract_slug(spec.query)
    if slug.isdigit():
        page_id = slug
    elif slug.lower() in _RESERVED_SLUGS:
        raise PageResolutionError(f"reserved Facebook path segment, not a page slug: {slug!r}")
    else:
        if page_id_resolver is None:
            raise PageResolutionError(
                f"resolving slug {slug!r} requires a page_id_resolver callable"
            )
        page_id = await page_id_resolver(slug)
    return _build_page_library_url(page_id, spec)


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


def _build_page_library_url(page_id: str, spec: SearchSpec) -> str:
    params = {
        "active_status": spec.active_status,
        "ad_type": spec.ad_type,
        "country": spec.country,
        "view_all_page_id": page_id,
        "locale": "en_US",
    }
    return f"{_LIBRARY_BASE}?{urlencode(params)}"


def _extract_slug(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname not in _FACEBOOK_HOSTS:
        raise PageResolutionError(f"not a Facebook URL: {url!r}")
    path = parsed.path.rstrip("/")
    if path == "/profile.php":
        ids = parse_qs(parsed.query).get("id", [])
        if not ids:
            raise PageResolutionError(f"profile.php URL missing ?id=: {url!r}")
        return ids[0]
    parts = path.strip("/").split("/")
    if not parts or not parts[0]:
        raise PageResolutionError(f"no slug segment in URL: {url!r}")
    return parts[0]
