from __future__ import annotations

from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from meta_ads_scraper import url_resolver
from meta_ads_scraper.exceptions import PageResolutionError
from meta_ads_scraper.models import SearchSpec
from meta_ads_scraper.url_resolver import (
    _extract_slug,
    _scrape_page_id,
    _slug_to_page_id,
    resolve_url,
)


def _patch_httpx(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    transport = httpx.MockTransport(handler)
    real = url_resolver.httpx.AsyncClient

    class _Patched(real):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(url_resolver.httpx, "AsyncClient", _Patched)


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


class TestScrapePageId:
    async def test_extracts_from_al_android_meta_tag(self, monkeypatch):
        html = '<html><meta property="al:android:url" content="fb://page/?id=98765"/></html>'
        _patch_httpx(monkeypatch, lambda _req: httpx.Response(200, text=html))
        assert await _scrape_page_id("Nike") == "98765"

    async def test_extracts_from_page_id_json_string(self, monkeypatch):
        html = 'window.SOMETHING = {"pageID":"12345","other":"x"};'
        _patch_httpx(monkeypatch, lambda _req: httpx.Response(200, text=html))
        assert await _scrape_page_id("Nike") == "12345"

    async def test_extracts_from_page_id_json_number(self, monkeypatch):
        html = '"page_id":555444333'
        _patch_httpx(monkeypatch, lambda _req: httpx.Response(200, text=html))
        assert await _scrape_page_id("Nike") == "555444333"

    async def test_404_raises_page_resolution_error(self, monkeypatch):
        _patch_httpx(monkeypatch, lambda _req: httpx.Response(404))
        with pytest.raises(PageResolutionError, match="network"):
            await _scrape_page_id("ThisPageDoesNotExist")

    async def test_no_match_raises(self, monkeypatch):
        _patch_httpx(monkeypatch, lambda _req: httpx.Response(200, text="<html>nothing</html>"))
        with pytest.raises(PageResolutionError, match="could not extract"):
            await _scrape_page_id("Nike")

    async def test_request_targets_facebook_page_url(self, monkeypatch):
        captured: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(str(request.url))
            return httpx.Response(200, text='"pageID":"1"')

        _patch_httpx(monkeypatch, handler)
        await _scrape_page_id("Nike")
        assert captured[0].startswith("https://www.facebook.com/Nike")


class TestResolveUrlPageModes:
    async def test_page_slug_numeric_short_circuits(self, monkeypatch):
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(str(request.url))
            return httpx.Response(200, text="should not be called")

        _patch_httpx(monkeypatch, handler)
        spec = SearchSpec(mode="page_slug", query="555444333")
        url = await resolve_url(spec)
        assert calls == [], "numeric slugs must not trigger a network call"
        assert "view_all_page_id=555444333" in url

    async def test_page_slug_resolves_via_scrape(self, monkeypatch):
        _patch_httpx(monkeypatch, lambda _req: httpx.Response(200, text='"pageID":"77"'))
        spec = SearchSpec(mode="page_slug", query="Nike")
        url = await resolve_url(spec)
        assert "view_all_page_id=77" in url
        assert "locale=en_US" in url

    async def test_page_url_extracts_slug_then_resolves(self, monkeypatch):
        _patch_httpx(monkeypatch, lambda _req: httpx.Response(200, text='"pageID":"88"'))
        spec = SearchSpec(mode="page_url", query="https://www.facebook.com/Nike")
        url = await resolve_url(spec)
        assert "view_all_page_id=88" in url

    async def test_page_url_profile_php_short_circuits(self, monkeypatch):
        calls: list[str] = []
        _patch_httpx(
            monkeypatch,
            lambda req: (calls.append(str(req.url)), httpx.Response(200, text=""))[1],
        )
        spec = SearchSpec(mode="page_url", query="https://www.facebook.com/profile.php?id=42")
        url = await resolve_url(spec)
        assert calls == [], "profile.php?id=N must not trigger a scrape"
        assert "view_all_page_id=42" in url
