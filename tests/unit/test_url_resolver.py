from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from meta_ads_scraper.models import SearchSpec
from meta_ads_scraper.url_resolver import resolve_url


def _query_params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


class TestKeywordMode:
    def test_basic_keyword(self):
        spec = SearchSpec(mode="keyword", query="shoes")
        url = resolve_url(spec)
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.facebook.com"
        assert parsed.path == "/ads/library/"
        params = _query_params(url)
        assert params["q"] == ["shoes"]
        assert params["search_type"] == ["keyword_unordered"]
        assert params["country"] == ["ALL"]
        assert params["ad_type"] == ["all"]
        assert params["active_status"] == ["all"]

    def test_keyword_with_spaces_url_encoded(self):
        spec = SearchSpec(mode="keyword", query="luxury watches")
        url = resolve_url(spec)
        assert "luxury+watches" in url or "luxury%20watches" in url
        assert _query_params(url)["q"] == ["luxury watches"]

    def test_keyword_with_special_chars_encoded(self):
        spec = SearchSpec(mode="keyword", query="O'Brien & Co.")
        url = resolve_url(spec)
        assert "O'Brien" not in url  # the apostrophe should be percent-encoded
        assert _query_params(url)["q"] == ["O'Brien & Co."]

    def test_country_override(self):
        spec = SearchSpec(mode="keyword", query="dental", country="US")
        assert _query_params(resolve_url(spec))["country"] == ["US"]

    def test_political_ad_type(self):
        spec = SearchSpec(mode="keyword", query="vote", ad_type="political_and_issue_ads")
        assert _query_params(resolve_url(spec))["ad_type"] == ["political_and_issue_ads"]

    def test_active_status_filter(self):
        spec = SearchSpec(mode="keyword", query="x", active_status="active")
        assert _query_params(resolve_url(spec))["active_status"] == ["active"]


class TestUnimplementedModes:
    def test_page_url_raises_not_implemented(self):
        spec = SearchSpec(mode="page_url", query="https://www.facebook.com/Nike")
        with pytest.raises(NotImplementedError, match="page_url"):
            resolve_url(spec)

    def test_page_slug_raises_not_implemented(self):
        spec = SearchSpec(mode="page_slug", query="Nike")
        with pytest.raises(NotImplementedError, match="page_slug"):
            resolve_url(spec)
