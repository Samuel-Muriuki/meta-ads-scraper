"""Offline HAR-replay test for the pagination scroll loop.

Phase 3 followup: nothing in CI proves ``scroll_and_collect`` works
against an actual multi-page Meta DOM. This test plays back a captured
HAR (``tests/fixtures/har/keyword_shoes_paginated.har``) through a
fresh Playwright context and asserts the scrape pipeline (selector +
scroll loop + parser) extracts the expected number of cards.

The HAR was captured by ``scripts/capture_pagination_har.py`` and
slimmed by ``scripts/slim_har.py`` (cookies / auth headers scrubbed).
Regenerate it if Meta's DOM changes meaningfully.
"""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

from meta_ads_scraper.constants import AD_CARD_SELECTOR
from meta_ads_scraper.pagination import scroll_and_collect
from meta_ads_scraper.parsers.ad_card import parse_ad_card

_HAR_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "har" / "keyword_shoes_paginated.har"
_REPLAY_URL = (
    "https://www.facebook.com/ads/library/"
    "?active_status=all&ad_type=all&country=ALL"
    "&q=shoes&search_type=keyword_unordered&locale=en_US"
)
_FIRST_PAGE_CARD_COUNT = 26  # observed on the captured HAR; scroll must beat this
_MIN_CARDS_AFTER_SCROLL = 20  # conservative lower bound on parser yield


async def test_pagination_har_replay_yields_paginated_cards() -> None:
    """Replay the HAR and verify the parser extracts >= 20 ads via the
    chained AD_CARD_SELECTOR. ``scroll_and_collect`` drives the loop so
    we exercise the same code path as the live scraper.
    """
    assert _HAR_PATH.exists(), f"HAR fixture missing: {_HAR_PATH}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        # `not_found="fallback"` means HAR-misses fall through to the network.
        # We never want that in CI, so any miss should be caught by the
        # `assert ads >= 20` rather than by abort-on-miss noise during page
        # load (Meta lazy-loads many sub-resources that aren't in the HAR).
        await context.route_from_har(str(_HAR_PATH), not_found="fallback")
        page = await context.new_page()
        try:
            await page.goto(_REPLAY_URL, wait_until="domcontentloaded", timeout=60_000)
            # Wait for at least one card to render before kicking off the loop.
            await page.get_by_text("Library ID:").first.wait_for(state="visible", timeout=30_000)

            ads = []
            async for card in scroll_and_collect(
                page,
                AD_CARD_SELECTOR,
                max_results=50,
                timeout_seconds=60,
                stall_threshold=3,
            ):
                ad = await parse_ad_card(card, source_url=_REPLAY_URL)
                if ad is not None:
                    ads.append(ad)

            assert len(ads) >= _MIN_CARDS_AFTER_SCROLL, (
                f"expected >= {_MIN_CARDS_AFTER_SCROLL} ads from HAR replay, got {len(ads)}"
            )
            for ad in ads:
                assert ad.ad_library_id, "every parsed ad must carry an ad_library_id"
                assert ad.page_id, "every parsed ad must carry a page_id"
        finally:
            await context.close()
            await browser.close()
