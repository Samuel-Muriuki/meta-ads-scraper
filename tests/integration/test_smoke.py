from __future__ import annotations

from importlib.metadata import distribution


def test_distribution_metadata_present() -> None:
    dist = distribution("meta-ads-scraper")
    assert dist.metadata["Name"] == "meta-ads-scraper"
    assert dist.version
