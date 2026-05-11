# Ad Data Schema — Contract

> This is the source of truth for the `Ad` Pydantic model. Code in `src/meta_ads_scraper/models.py` MUST match this contract.

## The `Ad` model

```python
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Ad(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,  # immutable after construction
        extra="forbid",  # reject unknown fields
    )

    # ─── Required identifiers ──────────────────────────────────────
    ad_library_id: str = Field(..., min_length=1, description="Meta's internal library ID for this ad")
    page_id: str = Field(..., min_length=1, description="Facebook page ID that ran the ad")
    collected_at: datetime = Field(..., description="UTC timestamp when this ad was scraped")
    source_url: HttpUrl = Field(..., description="The Meta Ads Library URL we collected from")

    # ─── Page info ────────────────────────────────────────────────
    page_name: Optional[str] = None
    page_url: Optional[HttpUrl] = None
    page_profile_picture_url: Optional[HttpUrl] = None

    # ─── Creative ─────────────────────────────────────────────────
    ad_creative_text: Optional[str] = None
    ad_creative_image_urls: list[HttpUrl] = Field(default_factory=list)
    ad_creative_video_url: Optional[HttpUrl] = None
    landing_url: Optional[HttpUrl] = None
    cta_type: Optional[str] = None  # SHOP_NOW, LEARN_MORE, SIGN_UP, etc.

    # ─── Lifecycle ────────────────────────────────────────────────
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

    # ─── Distribution ─────────────────────────────────────────────
    platforms: list[str] = Field(default_factory=list)  # FACEBOOK, INSTAGRAM, MESSENGER, AUDIENCE_NETWORK
    languages: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)

    # ─── Performance (mostly political ads only) ──────────────────
    demographic_breakdown: Optional[dict[str, Any]] = None
    total_reach_estimate: Optional[int] = None
```

## Field semantics

### Required vs Optional

**Required** (would be a parse failure if missing):
- `ad_library_id` — without it we have no identity
- `page_id` — without it we can't dedupe by advertiser
- `collected_at` — set at scrape time, always present
- `source_url` — set at scrape time, always present

**Optional** (commonly missing from commercial ads):
- Demographic and reach data — Meta restricts this to political ads
- End date — active ads have none
- Video URL — image-only ads have none
- Landing URL — some ads have no click destination

### Why `frozen=True`

Ads are scraped, validated, exported. We never mutate them after construction. Freezing catches accidental mutation in tests and gives us hashability (useful for dedup sets).

### Why `extra="forbid"`

If Meta adds a new field to their DOM (e.g., `boost_score`), we want our parser to FAIL loudly, not silently drop the field. The forbidden-extra config forces us to update the schema when reality changes.

### Why `HttpUrl` not `str` for URLs

Pydantic v2's `HttpUrl` validates that the URL parses, has a scheme, has a host. Garbage URLs raise `ValidationError` at construction. This is the "fail at the boundary" pattern — better to lose a single bad ad than to ship invalid URLs to a CSV that a client opens in Excel.

### Why `date` not `str` for dates

Same reason. Type-safety at the boundary. The parser converts Meta's display strings ("Mar 15, 2026") to `date` objects before construction.

## Serialization

For CSV export, lists are joined with `;`:
```
platforms: "FACEBOOK;INSTAGRAM"
ad_creative_image_urls: "https://...jpg;https://...jpg"
```

For JSON export, lists are native arrays:
```json
{
  "platforms": ["FACEBOOK", "INSTAGRAM"],
  "ad_creative_image_urls": ["https://...jpg", "https://...jpg"]
}
```

Dates serialize as ISO 8601 strings: `"2026-03-15"`.
Datetimes serialize as ISO 8601 with timezone: `"2026-05-11T15:30:00+00:00"`.

## The `SearchSpec` model

```python
class SearchSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["keyword", "page_url", "page_slug"]
    query: str = Field(..., min_length=1)
    country: str = Field(default="ALL", description="ISO 3166-1 alpha-2 or 'ALL'")
    ad_type: Literal["all", "political_and_issue_ads"] = "all"
    active_status: Literal["all", "active", "inactive"] = "all"
```

`country` should be validated against a known set of codes plus `ALL` — but for MVP, accept any 2-letter or `ALL` and let Meta reject invalid ones.

## Test fixtures

`tests/fixtures/ads/` contains example JSON files for fixture-based testing:

- `commercial_minimal.json` — only required fields populated
- `commercial_full.json` — all commercial fields populated
- `political_full.json` — includes demographic_breakdown and reach
- `malformed.json` — for negative-path testing (should raise ValidationError)

The Pydantic model is tested against each fixture in `tests/unit/test_models.py`.
