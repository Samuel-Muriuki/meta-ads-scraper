# 10 — Testing Strategy

See `.project/patterns/pytest-patterns/README.md` for patterns.

## Test pyramid

```
       ┌────────────────────┐
       │   Live Smoke (1-2) │   manual only
       └────────────────────┘
      ┌──────────────────────┐
      │ Integration Replay   │   CI, deterministic
      └──────────────────────┘
    ┌──────────────────────────┐
    │       Unit Tests          │   fast, every push
    └──────────────────────────┘
```

## Unit tests (target: 80%+ coverage of leaf modules)

Cover:
- `models.py` — Pydantic validation, serialization, edge cases
- `url_resolver.py` — every search mode + edge cases (special chars in keywords)
- `parsers/` — DOM-fixture-based; given a known HTML snippet, expect a specific Ad
- `exporters/` — given an Ad list, expect specific CSV/JSON output
- `retry.py` — verify backoff timing with mocks
- `pagination.py` — verify stop conditions with mock page
- `cli.py` — argument parsing, mutual exclusion, exit codes via Typer's CliRunner

## Integration replay (deterministic)

Use Playwright's HAR replay mode:

```python
context = await browser.new_context()
await context.route_from_har("tests/fixtures/har/keyword_shoes.har", update=False)
```

This means CI doesn't need internet to run integration tests. The HAR is captured once locally and committed.

## Live smoke (gated)

```python
@pytest.mark.live_test
async def test_real_meta_keyword_search():
    async with PlaywrightScraper() as scraper:
        ads = []
        async for ad in scraper.search(SearchSpec(mode="keyword", query="shoes")):
            ads.append(ad)
            if len(ads) >= 5:
                break
    assert len(ads) == 5
```

Gated by `META_LIVE_TESTS=1`. CI runs only on `workflow_dispatch`.

## What we don't test

- Playwright itself — trust the library
- Meta's HTML — outside our control
- Network failures of third-party services — mocked via HAR

## When tests are flaky

Live smoke tests CAN be flaky (network, rate limits, DOM changes). Replay tests MUST NOT be flaky.

If a replay test starts failing, the HAR is stale. Re-record.
