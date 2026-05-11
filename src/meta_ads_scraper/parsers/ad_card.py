from __future__ import annotations

import re
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import structlog
from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import ValidationError

from ..models import Ad

logger = structlog.get_logger()

_LIBRARY_ID_RE = re.compile(r"Library ID:\s*(\d+)")
_LIBRARY_ID_TEXT_RE = re.compile(r"Library ID:\s*\d+")
_PROFILE_ID_RE = re.compile(r"profile\.php\?id=(\d+)")
_PAGE_SLUG_RE = re.compile(r"facebook\.com/([^/?#]+)")
_START_DATE_RE = re.compile(
    r"(?:Started running on|Active since)\s+(\w+)\s+(\d+),\s+(\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_KNOWN_PLATFORMS = ("Facebook", "Instagram", "Messenger", "Audience Network")


async def iter_visible_ads(page: Page, source_url: str) -> AsyncIterator[Ad]:
    library_ids = page.get_by_text(_LIBRARY_ID_TEXT_RE)
    count = await library_ids.count()
    logger.info("ads_visible", count=count)
    for i in range(count):
        id_text = library_ids.nth(i)
        card = id_text.locator("xpath=ancestor::div[.//img][1]")
        ad = await parse_ad_card(card, source_url=source_url)
        if ad is not None:
            yield ad


async def parse_ad_card(card: Locator, source_url: str) -> Ad | None:
    ad_id = await _extract_library_id(card)
    if not ad_id:
        return None

    page_id, page_name, page_url = await _extract_page_info(card)
    if not page_id:
        logger.debug("ad_skipped_no_page_id", ad_library_id=ad_id)
        return None

    try:
        return Ad(
            ad_library_id=ad_id,
            page_id=page_id,
            collected_at=datetime.now(UTC),
            source_url=source_url,  # type: ignore[arg-type]
            page_name=page_name,
            page_url=page_url,  # type: ignore[arg-type]
            ad_creative_text=await _extract_creative_text(card),
            ad_creative_image_urls=await _extract_image_urls(card),  # type: ignore[arg-type]
            start_date=await _extract_start_date(card),
            platforms=await _extract_platforms(card),
        )
    except ValidationError as e:
        logger.warning("ad_validation_failed", ad_library_id=ad_id, errors=e.errors())
        return None


async def _extract_library_id(card: Locator) -> str | None:
    try:
        text = await card.get_by_text(_LIBRARY_ID_RE).first.inner_text(timeout=2_000)
    except PlaywrightTimeoutError:
        return None
    match = _LIBRARY_ID_RE.search(text)
    return match.group(1) if match else None


async def _extract_page_info(card: Locator) -> tuple[str | None, str | None, str | None]:
    try:
        link = card.locator("a[href*='facebook.com/']").first
        href = await link.get_attribute("href", timeout=2_000)
        name = await link.inner_text(timeout=2_000)
    except PlaywrightTimeoutError:
        return None, None, None
    if not href:
        return None, None, None
    if (m := _PROFILE_ID_RE.search(href)) is not None:
        page_id: str | None = m.group(1)
    elif (m := _PAGE_SLUG_RE.search(href)) is not None:
        page_id = m.group(1)
    else:
        page_id = None
    return page_id, (name or "").strip() or None, href


async def _extract_creative_text(card: Locator) -> str | None:
    try:
        text = await card.inner_text(timeout=2_000)
    except PlaywrightTimeoutError:
        return None
    cleaned = _LIBRARY_ID_RE.sub("", text).strip()
    return cleaned or None


async def _extract_image_urls(card: Locator) -> list[str]:
    images = card.locator("img")
    try:
        count = await images.count()
    except PlaywrightTimeoutError:
        return []
    urls: list[str] = []
    for i in range(count):
        try:
            src = await images.nth(i).get_attribute("src", timeout=2_000)
        except PlaywrightTimeoutError:
            continue
        if src and src.startswith("https://"):
            urls.append(src)
    return urls


async def _extract_start_date(card: Locator) -> date | None:
    try:
        text = await card.inner_text(timeout=2_000)
    except PlaywrightTimeoutError:
        return None
    match = _START_DATE_RE.search(text)
    if not match:
        return None
    month = _MONTHS.get(match.group(1).lower()[:3])
    if not month:
        return None
    try:
        return date(int(match.group(3)), month, int(match.group(2)))
    except ValueError:
        return None


async def _extract_platforms(card: Locator) -> list[str]:
    platforms: list[str] = []
    for label in _KNOWN_PLATFORMS:
        icon = card.locator(f"[aria-label='{label}'], [alt='{label}']").first
        if await icon.is_visible(timeout=500):
            platforms.append(label.upper().replace(" ", "_"))
    return platforms
