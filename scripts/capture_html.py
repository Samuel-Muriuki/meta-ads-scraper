"""One-off helper to capture the rendered HTML of a keyword search.

Run from the repo root with the venv activated:
    python scripts/capture_html.py

Saves HTML and a full-page PNG to tests/fixtures/html/ for Phase 2
selector reconnaissance.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import ViewportSize, async_playwright
from playwright_stealth import Stealth

URL = (
    "https://www.facebook.com/ads/library/"
    "?active_status=all&ad_type=all&country=ALL&q=shoes"
    "&search_type=keyword_unordered&locale=en_US"
)
OUT_DIR = Path("tests/fixtures/html")


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        viewport: ViewportSize = {"width": 1920, "height": 1080}
        ctx = await browser.new_context(
            viewport=viewport,
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = await ctx.new_page()
        await Stealth().apply_stealth_async(page)
        await page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        await asyncio.sleep(15)
        html = await page.content()
        title = await page.title()
        (OUT_DIR / "keyword_search_shoes.html").write_text(html, encoding="utf-8")
        await page.screenshot(
            path=str(OUT_DIR / "keyword_search_shoes.png"), full_page=True
        )
        await ctx.close()
        await browser.close()
        print(f"title={title!r}")
        print(f"html_chars={len(html)}")


if __name__ == "__main__":
    asyncio.run(main())
