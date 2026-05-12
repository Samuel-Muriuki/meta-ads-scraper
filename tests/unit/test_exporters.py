from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime

import pytest

from meta_ads_scraper.exporters import write_ads_csv, write_ads_json
from meta_ads_scraper.models import Ad

_NOW = datetime(2026, 5, 11, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_ads() -> list[Ad]:
    return [
        Ad(
            ad_library_id="111",
            page_id="222",
            collected_at=_NOW,
            source_url="https://www.facebook.com/ads/library/?id=111",
            page_name="Nike",
            ad_creative_text="Just do it",
            ad_creative_image_urls=[
                "https://cdn.fb.com/a.jpg",
                "https://cdn.fb.com/b.jpg",
            ],
            start_date=date(2026, 1, 1),
            platforms=["FACEBOOK", "INSTAGRAM"],
            countries=["US"],
        ),
        Ad(
            ad_library_id="333",
            page_id="444",
            collected_at=_NOW,
            source_url="https://www.facebook.com/ads/library/?id=333",
        ),
    ]


class TestJsonExporter:
    def test_writes_array_to_textio(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        count = write_ads_json(sample_ads, buf)
        assert count == 2
        data = json.loads(buf.getvalue())
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["ad_library_id"] == "111"
        assert data[0]["platforms"] == ["FACEBOOK", "INSTAGRAM"]

    def test_writes_to_path(self, sample_ads: list[Ad], tmp_path):
        out = tmp_path / "ads.json"
        count = write_ads_json(sample_ads, out)
        assert count == 2
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 2

    def test_indented_two_spaces(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        write_ads_json(sample_ads, buf)
        assert "\n  " in buf.getvalue()

    def test_iso_8601_datetimes(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        write_ads_json(sample_ads, buf)
        data = json.loads(buf.getvalue())
        assert data[0]["collected_at"].startswith("2026-05-11T12:00:00")
        assert data[0]["start_date"] == "2026-01-01"

    def test_empty_iterable(self):
        buf = io.StringIO()
        count = write_ads_json([], buf)
        assert count == 0
        assert buf.getvalue() == "[]"

    def test_none_preserved_as_null(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        write_ads_json(sample_ads, buf)
        data = json.loads(buf.getvalue())
        assert data[1]["page_name"] is None
        assert data[1]["platforms"] == []


class TestCsvExporter:
    def test_writes_header_and_rows(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        count = write_ads_csv(sample_ads, buf)
        assert count == 2
        rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
        assert len(rows) == 2
        assert rows[0]["ad_library_id"] == "111"
        assert rows[0]["page_name"] == "Nike"

    def test_writes_to_path_with_bom(self, sample_ads: list[Ad], tmp_path):
        out = tmp_path / "ads.csv"
        count = write_ads_csv(sample_ads, out)
        assert count == 2
        raw = out.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf"), "expected UTF-8 BOM"

    def test_list_fields_semicolon_joined(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        write_ads_csv(sample_ads, buf)
        rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
        assert rows[0]["platforms"] == "FACEBOOK;INSTAGRAM"
        assert rows[0]["ad_creative_image_urls"] == (
            "https://cdn.fb.com/a.jpg;https://cdn.fb.com/b.jpg"
        )

    def test_none_renders_empty_cell(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        write_ads_csv(sample_ads, buf)
        rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
        assert rows[1]["page_name"] == ""
        assert rows[1]["platforms"] == ""

    def test_iso_8601_datetimes(self, sample_ads: list[Ad]):
        buf = io.StringIO()
        write_ads_csv(sample_ads, buf)
        rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
        assert rows[0]["collected_at"].startswith("2026-05-11T12:00:00")
        assert rows[0]["start_date"] == "2026-01-01"

    def test_empty_iterable_writes_header_only(self):
        buf = io.StringIO()
        count = write_ads_csv([], buf)
        assert count == 0
        text = buf.getvalue()
        assert "ad_library_id" in text
        assert text.count("\n") == 1
