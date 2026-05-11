from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TextIO

from ..models import Ad

_CSV_FIELDS: tuple[str, ...] = (
    "ad_library_id",
    "page_id",
    "collected_at",
    "source_url",
    "page_name",
    "page_url",
    "page_profile_picture_url",
    "ad_creative_text",
    "ad_creative_image_urls",
    "ad_creative_video_url",
    "landing_url",
    "cta_type",
    "start_date",
    "end_date",
    "is_active",
    "platforms",
    "languages",
    "countries",
    "demographic_breakdown",
    "total_reach_estimate",
)

_LIST_FIELDS: frozenset[str] = frozenset(
    {"ad_creative_image_urls", "platforms", "languages", "countries"}
)


def write_ads_csv(ads: Iterable[Ad], out: Path | TextIO) -> int:
    if isinstance(out, Path):
        with out.open("w", encoding="utf-8-sig", newline="") as fh:
            return _write_rows(ads, fh)
    return _write_rows(ads, out)


def _write_rows(ads: Iterable[Ad], fh: TextIO) -> int:
    writer = csv.DictWriter(fh, fieldnames=list(_CSV_FIELDS))
    writer.writeheader()
    count = 0
    for ad in ads:
        writer.writerow(_row_for(ad))
        count += 1
    return count


def _row_for(ad: Ad) -> dict[str, Any]:
    raw = ad.model_dump(mode="json")
    row: dict[str, Any] = {}
    for field in _CSV_FIELDS:
        value = raw.get(field)
        if value is None:
            row[field] = ""
        elif field in _LIST_FIELDS:
            row[field] = ";".join(str(v) for v in value) if value else ""
        elif isinstance(value, dict):
            row[field] = json.dumps(value, separators=(",", ":"))
        else:
            row[field] = value
    return row
