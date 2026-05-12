"""Capture a paginated HAR fixture against Meta's Ad Library.

One-shot script — run locally, commit the produced HAR (after scrubbing),
delete the script if it ever becomes redundant. Designed to be re-runnable
in case Meta's DOM changes and the fixture needs refreshing.

Usage::

    .venv\\Scripts\\Activate.ps1 ; python scripts/capture_pagination_har.py

The output lands at ``tests/fixtures/har/keyword_shoes_paginated.har``.
The script scrolls until at least 30 cards have loaded so the HAR
includes the scroll-driven XHR traffic for the pagination replay test.

CRITICAL: after the file is written, run ``scripts/scrub_har.py`` to
strip any Cookie or Authorization headers before committing.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, ViewportSize, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

OUTPUT_PATH = Path("tests/fixtures/har/keyword_shoes_paginated.har")
TARGET_URL = (
    "https://www.facebook.com/ads/library/"
    "?active_status=all&ad_type=all&country=ALL"
    "&q=shoes&search_type=keyword_unordered&locale=en_US"
)
TARGET_CARD_COUNT = 30
MAX_SCROLL_ROUNDS = 8
SCROLL_WAIT_MS = 3_000
LIBRARY_ID_RE = re.compile(r"Library ID:\s*\d+")
CONTAINER_SELECTOR = '[role="main"]'
VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}


async def _count_cards(page: Page) -> int:
    return await page.get_by_text(LIBRARY_ID_RE).count()


async def _scroll_main(page: Page) -> None:
    if await page.locator(CONTAINER_SELECTOR).count() > 0:
        await page.locator(CONTAINER_SELECTOR).first.evaluate(
            "(el) => el.scrollTo(0, el.scrollHeight)"
        )
    else:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")


async def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT,
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            record_har_path=str(OUTPUT_PATH),
            record_har_mode="full",
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60_000)
        # Dismiss optional cookie banner.
        cookie_button = page.get_by_role(
            "button", name=re.compile(r"Allow|Accept", re.IGNORECASE)
        ).first
        try:
            await cookie_button.click(timeout=3_000)
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"no cookie banner clicked: {exc}", file=sys.stderr)

        # Wait for first card.
        await page.get_by_text(LIBRARY_ID_RE).first.wait_for(state="visible", timeout=30_000)

        for round_no in range(MAX_SCROLL_ROUNDS):
            count = await _count_cards(page)
            print(f"round {round_no}: {count} cards visible", file=sys.stderr)
            if count >= TARGET_CARD_COUNT:
                break
            await _scroll_main(page)
            await page.wait_for_timeout(SCROLL_WAIT_MS)

        final = await _count_cards(page)
        print(f"final card count: {final}", file=sys.stderr)

        # Closing the context flushes the HAR to disk.
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
    size = OUTPUT_PATH.stat().st_size
    print(f"wrote HAR: {OUTPUT_PATH} ({size} bytes)", file=sys.stderr)
