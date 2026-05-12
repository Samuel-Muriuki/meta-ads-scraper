# Pydantic v2 Model Patterns

## Always use Pydantic v2 syntax

```python
from pydantic import BaseModel, ConfigDict, Field

class Ad(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
        extra="forbid",
    )

    ad_library_id: str = Field(..., min_length=1)
```

NOT v1 syntax (no `class Config:`, no `Config = ...`).

## Required vs optional fields

```python
# Required: no default
ad_library_id: str

# Optional with explicit None default
page_name: Optional[str] = None

# Optional with factory for mutable defaults
platforms: list[str] = Field(default_factory=list)
```

NEVER use mutable defaults directly: `platforms: list[str] = []` is a bug.

## Validation at the boundary

The Pydantic model is the schema firewall. Validate on construction; never trust upstream:

```python
def parse_ad_card(card, source_url: str) -> Optional[Ad]:
    try:
        return Ad(
            ad_library_id=ad_id,
            page_id=page_id,
            collected_at=datetime.now(UTC),
            source_url=source_url,
            page_name=page_name,
            # ...
        )
    except ValidationError as e:
        logger.warning("ad_validation_failed", error=e.errors())
        return None
```

Return `None` (skip the ad) rather than crashing the whole scrape.

## Serialization

```python
# To dict (for CSV/JSON exporters)
data = ad.model_dump(mode="json")  # ISO datetime strings, list as list

# To JSON string
json_str = ad.model_dump_json(indent=2)

# Custom field exclusion
data = ad.model_dump(exclude={"demographic_breakdown"})
```

## Frozen models

```python
model_config = ConfigDict(frozen=True)
```

Benefits:
- Catches accidental mutation bugs at runtime
- Documents intent: this is a snapshot, not a live object
- Auto-hashable IFF every field is itself hashable

Note on hashability: a frozen model with list / dict / set fields is
**not** auto-hashable -- Pydantic's auto-`__hash__` requires every
field to be hashable. The project's `Ad` model has list fields
(`platforms`, `ad_creative_image_urls`, etc.), so `hash(ad)` raises
`TypeError`. Use the natural-key field (`ad.ad_library_id`) as the
dedup key in sets / dict keys, which is what `scroll_and_collect`
and `CheckpointStore` do.

## Strict types where it matters

```python
from pydantic import HttpUrl, EmailStr, AwareDatetime

source_url: HttpUrl  # validates scheme + host
collected_at: AwareDatetime  # rejects naive datetimes
```

Better to fail at construction than to ship invalid data to CSV.

## Custom validators

For cross-field or complex validation:

```python
from pydantic import field_validator, model_validator

class SearchSpec(BaseModel):
    mode: Literal["keyword", "page_url", "page_slug"]
    query: str

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be blank")
        return v

    @model_validator(mode="after")
    def validate_url_format(self) -> "SearchSpec":
        if self.mode == "page_url" and not self.query.startswith("http"):
            raise ValueError("page_url mode requires a full URL")
        return self
```

## Settings via pydantic-settings (not used today)

The original planning brief reserved `pydantic-settings` as the
configuration layer. The project never grew the surface to justify
it -- configuration enters through two channels only:

1. CLI flags (`--rate-limit`, `--concurrency`, `--max-results`,
   `--timeout`, `-v`) parsed by Typer at the CLI boundary and passed
   down as constructor kwargs.
2. A small set of environment variables (`PLAYWRIGHT_HEADLESS`,
   `META_LIVE_TESTS`) read at the relevant call site.

If a future deployment needs `.env` files or layered precedence, the
pattern below is the path. For now this is documented for completeness.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="META_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    rate_limit: float = 1.0
    concurrency: int = 1
    default_max_results: int | None = None
    default_timeout: int = 300
```

See `docs/architecture/02-architecture.md` -> "Configuration" for
the design rationale.

## Why we use Pydantic for this project

Antonio will read the models file. If `models.py` is:
- Two flat dataclasses with no validation → looks junior
- Pydantic v2 with `frozen=True`, `extra="forbid"`, `HttpUrl`, custom validators → looks senior

This is a signal, not a perf optimization. Take the time.
