from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from meta_ads_scraper.exceptions import PageResolutionError
from meta_ads_scraper.models import SearchSpec
from meta_ads_scraper.url_resolver import (
    _extract_slug,
    _slug_to_page_id,
    resolve_url,
)


def _query_params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


class TestKeywordMode:
    async def test_basic_keyword(self):
        spec = SearchSpec(mode="keyword", query="shoes")
        url = await resolve_url(spec)
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
        assert params["locale"] == ["en_US"]

    async def test_keyword_with_spaces_url_encoded(self):
        spec = SearchSpec(mode="keyword", query="luxury watches")
        url = await resolve_url(spec)
        assert "luxury+watches" in url or "luxury%20watches" in url
        assert _query_params(url)["q"] == ["luxury watches"]

    async def test_keyword_with_special_chars_encoded(self):
        spec = SearchSpec(mode="keyword", query="O'Brien & Co.")
        url = await resolve_url(spec)
        assert "O'Brien" not in url
        assert _query_params(url)["q"] == ["O'Brien & Co."]

    async def test_country_override(self):
        spec = SearchSpec(mode="keyword", query="dental", country="US")
        params = _query_params(await resolve_url(spec))
        assert params["country"] == ["US"]

    async def test_political_ad_type(self):
        spec = SearchSpec(mode="keyword", query="vote", ad_type="political_and_issue_ads")
        params = _query_params(await resolve_url(spec))
        assert params["ad_type"] == ["political_and_issue_ads"]

    async def test_active_status_filter(self):
        spec = SearchSpec(mode="keyword", query="x", active_status="active")
        params = _query_params(await resolve_url(spec))
        assert params["active_status"] == ["active"]


class TestExtractSlug:
    def test_simple_slug(self):
        assert _extract_slug("https://www.facebook.com/Nike") == "Nike"

    def test_trailing_slash(self):
        assert _extract_slug("https://www.facebook.com/Nike/") == "Nike"

    def test_first_path_segment_only(self):
        assert _extract_slug("https://www.facebook.com/Nike/about") == "Nike"

    def test_profile_php_returns_numeric_id(self):
        assert _extract_slug("https://www.facebook.com/profile.php?id=12345") == "12345"

    def test_mobile_subdomain(self):
        assert _extract_slug("https://m.facebook.com/Nike") == "Nike"

    def test_apex_domain(self):
        assert _extract_slug("https://facebook.com/Nike") == "Nike"

    def test_non_facebook_url_raises(self):
        with pytest.raises(PageResolutionError, match="not a Facebook URL"):
            _extract_slug("https://example.com/Nike")

    def test_root_url_raises(self):
        with pytest.raises(PageResolutionError, match="no slug segment"):
            _extract_slug("https://www.facebook.com/")

    def test_profile_php_missing_id_raises(self):
        with pytest.raises(PageResolutionError, match="missing"):
            _extract_slug("https://www.facebook.com/profile.php")


class TestSlugToPageId:
    async def test_numeric_slug_is_short_circuited(self):
        assert await _slug_to_page_id("12345") == "12345"

    @pytest.mark.parametrize(
        "reserved",
        ["groups", "marketplace", "watch", "events", "pages", "profile.php"],
    )
    async def test_reserved_slug_raises(self, reserved):
        with pytest.raises(PageResolutionError, match="reserved"):
            await _slug_to_page_id(reserved)

    async def test_reserved_slug_case_insensitive(self):
        with pytest.raises(PageResolutionError):
            await _slug_to_page_id("GROUPS")
