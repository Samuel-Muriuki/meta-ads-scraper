from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

from meta_ads_scraper.parsers.ad_card import iter_visible_ads

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "html" / "keyword_search_shoes.html"
_SOURCE_URL = "https://www.facebook.com/ads/library/?q=shoes&locale=en_US"


async def test_parser_extracts_ads_from_fixture():
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        await page.goto(FIXTURE.as_uri(), wait_until="domcontentloaded")
        ads = [ad async for ad in iter_visible_ads(page, source_url=_SOURCE_URL)]
        await ctx.close()
        await browser.close()

    assert len(ads) >= 5, f"expected >= 5 ads from fixture, got {len(ads)}"
    for ad in ads:
        assert ad.ad_library_id, "ad_library_id required"
        assert ad.page_id, "page_id required"

    creatives = [ad for ad in ads if ad.ad_creative_text]
    assert creatives, "expected at least one ad with ad_creative_text populated"
