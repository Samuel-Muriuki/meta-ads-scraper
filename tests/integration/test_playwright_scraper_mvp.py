from __future__ import annotations

import pytest

from meta_ads_scraper.models import SearchSpec
from meta_ads_scraper.scraper.playwright_scraper import PlaywrightScraper


@pytest.mark.live_test
@pytest.mark.parametrize(
    "spec",
    [
        SearchSpec(mode="keyword", query="shoes"),
        SearchSpec(mode="page_slug", query="Nike"),
        SearchSpec(mode="page_url", query="https://www.facebook.com/Nike"),
    ],
    ids=["keyword=shoes", "page_slug=Nike", "page_url=Nike"],
)
async def test_search_returns_ads(spec: SearchSpec):
    ads = []
    async with PlaywrightScraper() as scraper:
        async for ad in scraper.search(spec):
            ads.append(ad)
            if len(ads) >= 20:
                break
    assert len(ads) >= 5, f"expected >= 5 ads for {spec.mode}={spec.query!r}, got {len(ads)}"
    for ad in ads:
        assert ad.ad_library_id, "ad_library_id required"
        assert ad.page_id, "page_id required"
