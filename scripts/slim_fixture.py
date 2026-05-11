"""Slim down the captured HTML fixture to ~50KB.

Reads tests/fixtures/html/keyword_search_shoes.html (typically ~1.9 MB
from scripts/capture_html.py), extracts N representative ad cards via
the same selector strategy the scraper uses, and writes a slimmed
version back to the same path. Keep one fixture, not two.

Run from the repo root with the venv activated:
    python scripts/slim_fixture.py
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

FIXTURE = Path("tests/fixtures/html/keyword_search_shoes.html")
N_CARDS = 6

_STRIP_SRCSET = re.compile(r'\s+srcset="[^"]*"')
_STRIP_INLINE_STYLE = re.compile(r'\s+style="[^"]*"')
_STRIP_INLINE_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL)
_STRIP_NONCE = re.compile(r'\s+nonce="[^"]*"')
_STRIP_CLASS = re.compile(r'\s+class="[^"]*"')
_STRIP_DATA_VISUALIZATION = re.compile(r'\s+data-visualcompletion="[^"]*"')


def _strip_noise(html: str) -> str:
    html = _STRIP_INLINE_SCRIPT.sub("", html)
    html = _STRIP_SRCSET.sub("", html)
    html = _STRIP_INLINE_STYLE.sub("", html)
    html = _STRIP_NONCE.sub("", html)
    html = _STRIP_CLASS.sub("", html)
    html = _STRIP_DATA_VISUALIZATION.sub("", html)
    return html


async def main() -> None:
    raw = FIXTURE.read_text(encoding="utf-8")
    raw_size = len(raw)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        await page.set_content(raw)

        library_ids = page.get_by_text(re.compile(r"Library ID:\s*\d+"))
        count = await library_ids.count()
        print(f"found {count} Library ID anchors in source")
        if count == 0:
            raise SystemExit("source HTML has no Library ID anchors; cannot slim")

        n = min(count, N_CARDS)
        card_htmls: list[str] = []
        for i in range(n):
            id_text = library_ids.nth(i)
            card = id_text.locator("xpath=ancestor::div[.//img][1]")
            html = await card.evaluate("(el) => el.outerHTML")
            card_htmls.append(_strip_noise(html))

        await ctx.close()
        await browser.close()

    slim = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        "<title>Ad Library</title>\n"
        "</head>\n"
        "<body>\n"
        '<main role="main">\n' + "\n".join(card_htmls) + "\n</main>\n"
        "</body>\n"
        "</html>\n"
    )
    FIXTURE.write_text(slim, encoding="utf-8")
    print(f"slimmed: {raw_size:,} -> {len(slim):,} chars ({len(slim) / raw_size:.1%})")


if __name__ == "__main__":
    asyncio.run(main())
