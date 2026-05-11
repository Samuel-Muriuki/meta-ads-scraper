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

from ..exceptions import ScraperBlockedError
from ..models import Ad, SearchSpec
from ..parsers.ad_card import parse_ad_card
from ..url_resolver import resolve_url
from .base import BaseScraper

logger = structlog.get_logger()

_VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
_LIBRARY_ID_TEXT_RE = re.compile(r"Library ID:\s*\d+")
_COOKIE_ACCEPT_RE = re.compile(r"Allow|Accept", re.IGNORECASE)
_LOGIN_PROMPT_RE = re.compile(r"Log in", re.IGNORECASE)


class PlaywrightScraper(BaseScraper):
    def __init__(self, *, headless: bool | None = None) -> None:
        if headless is None:
            headless = os.environ.get("PLAYWRIGHT_HEADLESS", "1") != "0"
        self._headless = headless
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
        url = resolve_url(spec)
        logger.info("scrape_start", url=url, mode=spec.mode, query=spec.query)

        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await self._dismiss_cookie_consent(page)

        if not await self._wait_for_first_card(page):
            if await self._looks_blocked(page):
                raise ScraperBlockedError(f"login wall or block at {url}")
            logger.warning("no_ads_visible", url=url)
            return

        library_ids = page.get_by_text(_LIBRARY_ID_TEXT_RE)
        count = await library_ids.count()
        logger.info("ads_visible_first_page", count=count)

        for i in range(count):
            id_text = library_ids.nth(i)
            card = id_text.locator("xpath=ancestor::div[.//img][1]")
            ad = await parse_ad_card(card, source_url=url)
            if ad is not None:
                yield ad

    async def _dismiss_cookie_consent(self, page: Page) -> None:
        try:
            btn = page.get_by_role("button", name=_COOKIE_ACCEPT_RE).first
            await btn.click(timeout=3_000)
            logger.info("cookie_consent_dismissed")
        except PlaywrightTimeoutError:
            logger.debug("no_cookie_consent_dialog")

    async def _wait_for_first_card(self, page: Page) -> bool:
        try:
            await page.get_by_text(_LIBRARY_ID_TEXT_RE).first.wait_for(
                state="visible", timeout=30_000
            )
            return True
        except PlaywrightTimeoutError:
            return False

    async def _looks_blocked(self, page: Page) -> bool:
        title = (await page.title()).lower()
        if "log in" in title or "facebook" not in title:
            return True
        login_button = page.get_by_role("button", name=_LOGIN_PROMPT_RE).first
        return await login_button.is_visible(timeout=1_000)
