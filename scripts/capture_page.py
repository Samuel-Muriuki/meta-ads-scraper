"""One-off helper to capture the rendered HTML of a Facebook page.

Used during Phase 2 to inspect what patterns Meta exposes for page-id
resolution. Run from the repo root with the venv activated:
    python scripts/capture_page.py Nike
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import ViewportSize, async_playwright
from playwright_stealth import Stealth

OUT_DIR = Path("tests/fixtures/html")


async def main(slug: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    url = f"https://www.facebook.com/{slug}"
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
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        await asyncio.sleep(5)
        html = await page.content()
        title = await page.title()
        await ctx.close()
        await browser.close()

    out_path = OUT_DIR / f"fb_page_{slug.replace('/', '_')}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"title={title!r}  html_chars={len(html):,}  saved={out_path}")
    print("\nGrep results for ID-like patterns:")
    for pattern in (
        r'"pageID"[^,]{0,40}',
        r'"page_id"[^,}]{0,40}',
        r'al:android[^"]{0,60}',
        r'fb://page[^"]{0,40}',
        r"page_id=\d+",
        r"pageID&quot;:[^,]{0,40}",
        r'"entity_id"[^,]{0,40}',
    ):
        matches = re.findall(pattern, html)[:3]
        if matches:
            print(f"  {pattern!r:50} -> {matches}")
        else:
            print(f"  {pattern!r:50} -> (no matches)")


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "Nike"
    asyncio.run(main(slug))
