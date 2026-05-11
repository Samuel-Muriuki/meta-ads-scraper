from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import structlog

from .exceptions import PageResolutionError
from .models import SearchSpec

logger = structlog.get_logger()

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
_DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
_PAGE_ID_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'content="fb://page/?\?id=(\d+)"'),
    re.compile(r'"pageID":"(\d+)"'),
    re.compile(r'"page_id":(\d+)'),
    re.compile(r'al:android:url" content="fb://page/(\d+)"'),
)


async def resolve_url(spec: SearchSpec) -> str:
    if spec.mode == "keyword":
        return _build_keyword_url(spec)
    if spec.mode == "page_slug":
        page_id = await _slug_to_page_id(spec.query)
    else:  # page_url
        slug = _extract_slug(spec.query)
        page_id = await _slug_to_page_id(slug)
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


async def _slug_to_page_id(slug: str) -> str:
    if slug.isdigit():
        return slug
    if slug.lower() in _RESERVED_SLUGS:
        raise PageResolutionError(f"reserved Facebook path segment, not a page slug: {slug!r}")
    return await _scrape_page_id(slug)


async def _scrape_page_id(slug: str) -> str:
    headers = {"User-Agent": _DESKTOP_UA, "Accept-Language": "en-US,en;q=0.9"}
    url = f"https://www.facebook.com/{slug}"
    logger.info("page_id_scrape_start", slug=slug, url=url)
    try:
        async with httpx.AsyncClient(
            headers=headers, follow_redirects=True, timeout=30.0
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        raise PageResolutionError(f"network failure resolving slug {slug!r}: {e}") from e
    for pattern in _PAGE_ID_PATTERNS:
        if (m := pattern.search(html)) is not None:
            page_id = m.group(1)
            logger.info("page_id_resolved", slug=slug, page_id=page_id)
            return page_id
    raise PageResolutionError(
        f"could not extract page_id from {url}; page may require login or use unrecognized markup"
    )
