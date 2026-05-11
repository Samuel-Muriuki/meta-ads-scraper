# Pytest Patterns

## Test file structure

```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_url_resolver.py
│   ├── test_parsers.py
│   ├── test_exporters.py
│   ├── test_retry.py
│   ├── test_pagination.py
│   └── test_cli.py
├── integration/
│   ├── test_replay.py          # HAR-based, runs in CI
│   └── test_live_smoke.py      # Live Meta, gated
├── fixtures/
│   ├── ads/                    # JSON fixtures for models
│   ├── html/                   # HTML fixtures for parser
│   └── har/                    # HAR files for replay
└── conftest.py                 # shared fixtures
```

## Async test pattern

```python
# pyproject.toml already has asyncio_mode = "auto"
async def test_scraper_yields_ads():
    async with PlaywrightScraper() as scraper:
        ads = [ad async for ad in scraper.search(spec)]
    assert len(ads) > 0
```

## Markers

```python
import pytest

@pytest.mark.live_test
async def test_real_meta_keyword_search():
    """Smoke test against live Meta. Skipped unless META_LIVE_TESTS=1."""
    pass

@pytest.mark.slow
def test_pagination_full_run():
    """Takes >30s. Skipped unless --runslow."""
    pass
```

Mark in `pyproject.toml`:
```toml
markers = [
    "live_test: requires real Meta access (gated by META_LIVE_TESTS=1)",
    "slow: deselected by default",
]
```

Conditional skip in `conftest.py`:
```python
import os
import pytest

def pytest_collection_modifyitems(config, items):
    if os.environ.get("META_LIVE_TESTS") != "1":
        skip_live = pytest.mark.skip(reason="META_LIVE_TESTS=1 not set")
        for item in items:
            if "live_test" in item.keywords:
                item.add_marker(skip_live)
```

## Fixtures for the scraper

```python
# conftest.py
import pytest
from datetime import UTC, datetime
from meta_ads_scraper.models import Ad

@pytest.fixture
def sample_ad():
    return Ad(
        ad_library_id="123456789",
        page_id="987654321",
        collected_at=datetime.now(UTC),
        source_url="https://www.facebook.com/ads/library/?id=123456789",
        page_name="Nike",
        platforms=["FACEBOOK", "INSTAGRAM"],
    )

@pytest.fixture
def sample_ads(sample_ad):
    return [
        sample_ad,
        sample_ad.model_copy(update={"ad_library_id": "987654321"}),
    ]
```

## Testing the CLI

```python
from typer.testing import CliRunner
from meta_ads_scraper.cli import app

runner = CliRunner()

def test_keyword_search_requires_keyword():
    result = runner.invoke(app, ["search"])
    assert result.exit_code != 0
    assert "keyword" in result.output.lower()

def test_mutual_exclusion():
    result = runner.invoke(app, [
        "search",
        "--keyword", "shoes",
        "--page-slug", "Nike",
    ])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower()
```

## Testing retry logic

```python
import asyncio
import httpx
from meta_ads_scraper.retry import retry_network

async def test_retry_network_succeeds_after_failures():
    attempts = []

    @retry_network
    async def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise httpx.TimeoutException("simulated")
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert len(attempts) == 3
```

## HAR replay testing

```python
async def test_keyword_search_replay(page, har_path):
    # Playwright supports HAR replay via context option
    context = await browser.new_context(
        record_har_path=None,
        service_workers="block",
    )
    await context.route_from_har(har_path, update=False)
    page = await context.new_page()

    async with PlaywrightScraper(page=page) as scraper:
        ads = [ad async for ad in scraper.search(SearchSpec(mode="keyword", query="shoes"))]

    assert len(ads) >= 5
    assert all(ad.ad_library_id for ad in ads)
```

Record HARs once:
```python
context = await browser.new_context(record_har_path="tests/fixtures/har/keyword_shoes.har")
# ... run scrape ...
await context.close()  # writes HAR
```

## What to assert

- ✅ Result has the right shape (correct fields, types)
- ✅ Edge cases produce expected errors
- ✅ Side effects happened (file written, count returned)
- ❌ Don't assert on log message content (brittle)
- ❌ Don't assert on internal state (test through the interface)

## Coverage targets

| Module | Target |
|---|---|
| models.py | ≥95% |
| url_resolver.py | ≥95% |
| parsers/ | ≥80% |
| exporters/ | ≥95% |
| retry.py | ≥90% |
| pagination.py | ≥80% |
| cli.py | ≥70% |
| scraper/playwright_scraper.py | ≥50% (rest via integration) |

`pyproject.toml` enforces `--cov-fail-under=60` overall.
