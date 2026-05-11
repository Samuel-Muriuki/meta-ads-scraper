from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from meta_ads_scraper.models import Ad, SearchSpec

_BASE = {
    "ad_library_id": "12345",
    "page_id": "67890",
    "collected_at": datetime(2026, 5, 11, 9, 0, 0, tzinfo=UTC),
    "source_url": "https://www.facebook.com/ads/library/?id=12345",
}


class TestAd:
    def test_required_fields_only_populates_defaults(self):
        ad = Ad(**_BASE)
        assert ad.ad_library_id == "12345"
        assert ad.page_id == "67890"
        assert str(ad.source_url).startswith("https://")
        assert ad.platforms == []
        assert ad.languages == []
        assert ad.countries == []
        assert ad.ad_creative_image_urls == []
        assert ad.page_name is None
        assert ad.start_date is None

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            Ad(
                page_id="67890",
                collected_at=datetime.now(UTC),
                source_url="https://example.com",
            )

    def test_frozen_model_rejects_mutation(self):
        ad = Ad(**_BASE)
        with pytest.raises(ValidationError):
            ad.ad_library_id = "different"

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            Ad(**_BASE, unknown_field="value")

    def test_full_optional_fields(self):
        ad = Ad(
            **_BASE,
            page_name="Nike",
            page_url="https://www.facebook.com/Nike",
            ad_creative_text="Just do it",
            ad_creative_image_urls=[
                "https://cdn.fb.com/img1.jpg",
                "https://cdn.fb.com/img2.jpg",
            ],
            start_date=date(2026, 1, 1),
            platforms=["FACEBOOK", "INSTAGRAM"],
        )
        assert ad.page_name == "Nike"
        assert len(ad.ad_creative_image_urls) == 2
        assert "FACEBOOK" in ad.platforms

    def test_invalid_url_raises(self):
        with pytest.raises(ValidationError):
            Ad(
                ad_library_id="1",
                page_id="2",
                collected_at=datetime.now(UTC),
                source_url="not-a-url",
            )

    def test_blank_library_id_rejected(self):
        with pytest.raises(ValidationError):
            Ad(**{**_BASE, "ad_library_id": ""})

    def test_string_whitespace_stripped(self):
        ad = Ad(**{**_BASE, "ad_library_id": "  123  "})
        assert ad.ad_library_id == "123"


class TestSearchSpec:
    def test_keyword_mode_defaults(self):
        spec = SearchSpec(mode="keyword", query="shoes")
        assert spec.mode == "keyword"
        assert spec.country == "ALL"
        assert spec.ad_type == "all"
        assert spec.active_status == "all"

    def test_page_url_mode(self):
        spec = SearchSpec(mode="page_url", query="https://www.facebook.com/Nike")
        assert spec.mode == "page_url"

    def test_page_slug_mode(self):
        spec = SearchSpec(mode="page_slug", query="Nike")
        assert spec.mode == "page_slug"

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValidationError):
            SearchSpec(mode="something_else", query="x")

    def test_blank_query_rejected(self):
        with pytest.raises(ValidationError):
            SearchSpec(mode="keyword", query="")

    def test_country_override(self):
        spec = SearchSpec(mode="keyword", query="shoes", country="US")
        assert spec.country == "US"

    def test_ad_type_political(self):
        spec = SearchSpec(mode="keyword", query="vote", ad_type="political_and_issue_ads")
        assert spec.ad_type == "political_and_issue_ads"

    def test_invalid_ad_type_rejected(self):
        with pytest.raises(ValidationError):
            SearchSpec(mode="keyword", query="x", ad_type="political")

    def test_invalid_active_status_rejected(self):
        with pytest.raises(ValidationError):
            SearchSpec(mode="keyword", query="x", active_status="paused")
