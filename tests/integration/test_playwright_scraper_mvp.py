from __future__ import annotations

import time

import pytest

from meta_ads_scraper.models import SearchSpec
from meta_ads_scraper.scraper.playwright_scraper import PlaywrightScraper


@pytest.mark.live_test
@pytest.mark.parametrize(
    "spec,max_results,min_ads",
    [
        (SearchSpec(mode="keyword", query="shoes"), 30, 20),
        (SearchSpec(mode="page_slug", query="Nike"), 10, 5),
        (SearchSpec(mode="page_url", query="https://www.facebook.com/Nike"), 10, 5),
    ],
    ids=["keyword=shoes-paginated", "page_slug=Nike", "page_url=Nike"],
)
async def test_search_returns_ads(spec: SearchSpec, max_results: int, min_ads: int):
    start = time.monotonic()
    async with PlaywrightScraper(max_results=max_results, timeout_seconds=180) as scraper:
        ads = [ad async for ad in scraper.search(spec)]
    elapsed = time.monotonic() - start

    assert len(ads) >= min_ads, (
        f"expected >= {min_ads} ads for {spec.mode}={spec.query!r}, got {len(ads)}"
    )
    for ad in ads:
        assert ad.ad_library_id, "ad_library_id required"
        assert ad.page_id, "page_id required"

    # Pagination smoke: the keyword=30 test must actually trigger scroll-and-collect.
    # First-page render is ~26 cards, so reaching 30 requires at least one scroll batch,
    # which puts elapsed comfortably above the single-page baseline.
    if spec.mode == "keyword" and max_results >= 30:
        assert elapsed > 15, (
            f"max_results={max_results} returned {len(ads)} ads in {elapsed:.1f}s — "
            f"scroll loop likely did not trigger"
        )
