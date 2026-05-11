from __future__ import annotations

import pytest

from meta_ads_scraper.models import SearchSpec
from meta_ads_scraper.scraper.playwright_scraper import PlaywrightScraper


@pytest.mark.live_test
async def test_keyword_search_shoes_returns_ads():
    spec = SearchSpec(mode="keyword", query="shoes")
    ads = []
    async with PlaywrightScraper() as scraper:
        async for ad in scraper.search(spec):
            ads.append(ad)
            if len(ads) >= 20:
                break
    assert len(ads) >= 5, f"expected ≥ 5 ads for 'shoes', got {len(ads)}"
    for ad in ads:
        assert ad.ad_library_id, "ad_library_id required"
        assert ad.page_id, "page_id required"
