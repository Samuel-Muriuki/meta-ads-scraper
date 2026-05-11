from __future__ import annotations

import meta_ads_scraper


def test_package_exposes_version() -> None:
    assert isinstance(meta_ads_scraper.__version__, str)
    assert meta_ads_scraper.__version__
