from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self

import structlog
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    ViewportSize,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from ..exceptions import PageResolutionError, ScraperBlockedError
from ..models import Ad, SearchSpec
from ..pagination import scroll_and_collect
from ..parsers.ad_card import parse_ad_card
from ..url_resolver import PAGE_ID_PATTERNS, resolve_url
from .base import BaseScraper

logger = structlog.get_logger()

_VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
_LOCALE = "en-US"
_TIMEZONE = "America/New_York"
_EXTRA_HEADERS = {"Accept-Language": "en-US,en;q=0.9"}
_LIBRARY_ID_TEXT_RE = re.compile(r"Library ID:\s*\d+")
_COOKIE_ACCEPT_RE = re.compile(r"Allow|Accept", re.IGNORECASE)
_LOGIN_PROMPT_RE = re.compile(r"Log in", re.IGNORECASE)
_DEFAULT_NAV_TIMEOUT = 60_000
_CARD_WAIT_TIMEOUT = 30_000
_COOKIE_TIMEOUT = 3_000
_LOGIN_PROBE_TIMEOUT = 1_000
_PAGE_ID_NAV_TIMEOUT = 30_000
_DEFAULT_SCRAPE_TIMEOUT_S = 300
_AD_CARD_XPATH = (
    "xpath=//div"
    "[.//text()[contains(., 'Library ID:')] and .//img]"
    "[not(.//div[.//text()[contains(., 'Library ID:')]])]"
)


class PlaywrightScraper(BaseScraper):
    def __init__(
        self,
        *,
        headless: bool | None = None,
        max_results: int | None = None,
        timeout_seconds: int = _DEFAULT_SCRAPE_TIMEOUT_S,
    ) -> None:
        if headless is None:
            headless = os.environ.get("PLAYWRIGHT_HEADLESS", "1") != "0"
        self._headless = headless
        self._max_results = max_results
        self._timeout_seconds = timeout_seconds
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> Self:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._context = await self._browser.new_context(
            viewport=_VIEWPORT,
            user_agent=_USER_AGENT,
            locale=_LOCALE,
            timezone_id=_TIMEZONE,
            extra_http_headers=_EXTRA_HEADERS,
        )
        self._page = await self._context.new_page()
        await Stealth().apply_stealth_async(self._page)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def search(self, spec: SearchSpec) -> AsyncIterator[Ad]:
        if self._page is None:
            raise RuntimeError("PlaywrightScraper not entered — use `async with`")
        page = self._page
        url = await resolve_url(spec, page_id_resolver=self._resolve_page_id)
        logger.info("scrape_start", url=url, mode=spec.mode, query=spec.query)

        await page.goto(url, wait_until="domcontentloaded", timeout=_DEFAULT_NAV_TIMEOUT)
        await self._dismiss_cookie_consent(page)

        if not await self._wait_for_first_card(page):
            if await self._looks_blocked(page):
                raise ScraperBlockedError(f"login wall or block at {url}")
            logger.warning("no_ads_visible", url=url)
            return

        async for card in scroll_and_collect(
            page,
            _AD_CARD_XPATH,
            max_results=self._max_results,
            timeout_seconds=self._timeout_seconds,
        ):
            ad = await parse_ad_card(card, source_url=url)
            if ad is not None:
                yield ad

    async def _dismiss_cookie_consent(self, page: Page) -> None:
        try:
            btn = page.get_by_role("button", name=_COOKIE_ACCEPT_RE).first
            await btn.click(timeout=_COOKIE_TIMEOUT)
            logger.info("cookie_consent_dismissed")
        except PlaywrightTimeoutError:
            logger.debug("no_cookie_consent_dialog")

    async def _wait_for_first_card(self, page: Page) -> bool:
        try:
            await page.get_by_text(_LIBRARY_ID_TEXT_RE).first.wait_for(
                state="visible", timeout=_CARD_WAIT_TIMEOUT
            )
            return True
        except PlaywrightTimeoutError:
            return False

    async def _looks_blocked(self, page: Page) -> bool:
        login_button = page.get_by_role("button", name=_LOGIN_PROMPT_RE).first
        return await login_button.is_visible(timeout=_LOGIN_PROBE_TIMEOUT)

    async def _resolve_page_id(self, slug: str) -> str:
        if self._page is None:
            raise RuntimeError("PlaywrightScraper not entered — use `async with`")
        page = self._page
        fb_url = f"https://www.facebook.com/{slug}"
        logger.info("page_id_resolve_start", slug=slug, url=fb_url)
        await page.goto(fb_url, wait_until="domcontentloaded", timeout=_PAGE_ID_NAV_TIMEOUT)
        await self._dismiss_cookie_consent(page)
        html = await page.content()
        for pattern in PAGE_ID_PATTERNS:
            if (m := pattern.search(html)) is not None:
                page_id = m.group(1)
                logger.info("page_id_resolved", slug=slug, page_id=page_id)
                return page_id
        raise PageResolutionError(
            f"could not extract page_id from {fb_url}; "
            f"page may require login or use unrecognized markup"
        )
