from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Ad(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
        extra="forbid",
    )

    ad_library_id: str = Field(..., min_length=1)
    page_id: str = Field(..., min_length=1)
    collected_at: datetime
    source_url: HttpUrl

    page_name: str | None = None
    page_url: HttpUrl | None = None
    page_profile_picture_url: HttpUrl | None = None

    ad_creative_text: str | None = None
    ad_creative_image_urls: list[HttpUrl] = Field(default_factory=list)
    ad_creative_video_url: HttpUrl | None = None
    landing_url: HttpUrl | None = None
    cta_type: str | None = None

    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None

    platforms: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)

    demographic_breakdown: dict[str, Any] | None = None
    total_reach_estimate: int | None = None


class SearchSpec(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
    )

    mode: Literal["keyword", "page_url", "page_slug"]
    query: str = Field(..., min_length=1)
    country: str = Field(default="ALL", description="ISO 3166-1 alpha-2 or 'ALL'")
    ad_type: Literal["all", "political_and_issue_ads"] = "all"
    active_status: Literal["all", "active", "inactive"] = "all"
