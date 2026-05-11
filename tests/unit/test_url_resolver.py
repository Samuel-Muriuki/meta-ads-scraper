from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from meta_ads_scraper.exceptions import PageResolutionError
from meta_ads_scraper.models import SearchSpec
from meta_ads_scraper.url_resolver import _extract_slug, resolve_url


def _query_params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def _make_resolver(*, returns: str = "111", calls: list[str] | None = None):
    async def _resolver(slug: str) -> str:
        if calls is not None:
            calls.append(slug)
        return returns

    return _resolver


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


class TestResolveUrlPageModes:
    async def test_page_slug_numeric_short_circuits(self):
        calls: list[str] = []
        spec = SearchSpec(mode="page_slug", query="555444333")
        url = await resolve_url(spec, page_id_resolver=_make_resolver(calls=calls))
        assert calls == [], "numeric slug must not call the resolver"
        assert "view_all_page_id=555444333" in url
        assert "locale=en_US" in url

    async def test_page_url_profile_php_short_circuits(self):
        calls: list[str] = []
        spec = SearchSpec(
            mode="page_url", query="https://www.facebook.com/profile.php?id=42"
        )
        url = await resolve_url(spec, page_id_resolver=_make_resolver(calls=calls))
        assert calls == []
        assert "view_all_page_id=42" in url

    async def test_page_slug_invokes_resolver(self):
        calls: list[str] = []
        spec = SearchSpec(mode="page_slug", query="Nike")
        url = await resolve_url(
            spec, page_id_resolver=_make_resolver(returns="77", calls=calls)
        )
        assert calls == ["Nike"]
        assert "view_all_page_id=77" in url

    async def test_page_url_extracts_then_invokes_resolver(self):
        calls: list[str] = []
        spec = SearchSpec(mode="page_url", query="https://www.facebook.com/Nike")
        url = await resolve_url(
            spec, page_id_resolver=_make_resolver(returns="88", calls=calls)
        )
        assert calls == ["Nike"]
        assert "view_all_page_id=88" in url

    async def test_page_url_mobile_host_extracts_slug(self):
        calls: list[str] = []
        spec = SearchSpec(mode="page_url", query="https://m.facebook.com/Nike")
        await resolve_url(
            spec, page_id_resolver=_make_resolver(returns="99", calls=calls)
        )
        assert calls == ["Nike"]

    @pytest.mark.parametrize(
        "reserved", ["groups", "marketplace", "watch", "events", "pages"]
    )
    async def test_reserved_slug_rejected_before_resolver(self, reserved: str):
        calls: list[str] = []
        spec = SearchSpec(mode="page_slug", query=reserved)
        with pytest.raises(PageResolutionError, match="reserved"):
            await resolve_url(spec, page_id_resolver=_make_resolver(calls=calls))
        assert calls == []

    async def test_reserved_slug_case_insensitive(self):
        spec = SearchSpec(mode="page_slug", query="GROUPS")
        with pytest.raises(PageResolutionError, match="reserved"):
            await resolve_url(spec, page_id_resolver=_make_resolver())

    async def test_page_slug_without_resolver_raises(self):
        spec = SearchSpec(mode="page_slug", query="Nike")
        with pytest.raises(PageResolutionError, match="requires a page_id_resolver"):
            await resolve_url(spec)

    async def test_resolver_value_used_in_url(self):
        spec = SearchSpec(mode="page_slug", query="Coca-Cola", country="US")
        url = await resolve_url(
            spec, page_id_resolver=_make_resolver(returns="987654321")
        )
        params = _query_params(url)
        assert params["view_all_page_id"] == ["987654321"]
        assert params["country"] == ["US"]
        assert "q" not in params  # page modes never use ?q=
