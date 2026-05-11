# 02 — Architecture

## Module Map

```
src/meta_ads_scraper/
├── __main__.py              # entrypoint: python -m meta_ads_scraper
├── cli.py                   # Typer app, argument parsing, dispatches to scraper
├── config.py                # pydantic-settings: env vars, defaults
├── exceptions.py            # Custom exception hierarchy
├── logging_config.py        # structlog setup
├── models.py                # Ad, SearchSpec
├── url_resolver.py          # SearchSpec → Meta Ads Library URL
├── checkpoint.py            # SQLite-backed resume store
├── retry.py                 # tenacity policies
├── rate_limit.py            # asyncio.Semaphore-based limiter
├── pagination.py            # scroll_and_collect generator
├── scraper/
│   ├── base.py              # abstract BaseScraper
│   ├── playwright_scraper.py # Path B impl (primary)
│   └── api_scraper.py       # Path A impl (stub, future)
├── parsers/
│   └── ad_card.py           # DOM locator → Ad
└── exporters/
    ├── csv_exporter.py
    └── json_exporter.py
```

## Dependency Direction (strict)

```
cli.py
  ↓ depends on
  ├─ scraper/*
  │    ↓ depends on
  │    ├─ parsers/*
  │    ├─ pagination
  │    ├─ retry
  │    ├─ rate_limit
  │    └─ models
  ├─ exporters/*
  │    ↓ depends on
  │    └─ models
  ├─ checkpoint
  │    ↓ depends on
  │    └─ models
  ├─ url_resolver
  │    ↓ depends on
  │    └─ models
  └─ logging_config, config, exceptions (used everywhere)
```

**Rule:** parsers, pagination, retry, rate_limit, models, exporters MUST NOT depend on `scraper/*` or `cli.py`. Keep the leaf modules dependency-free so they're testable in isolation.

## Why `scraper/base.py` is abstract

Today: only `PlaywrightScraper` exists.
Tomorrow: `ApiScraper` (Path A) might join, then maybe a `ScrapfishScraper` (third-party API).

The `BaseScraper` interface is the seam Antonio will look at. If the abstraction holds (i.e., you can swap implementations without touching the CLI), it signals senior judgment.

```python
class BaseScraper(ABC):
    @abstractmethod
    async def __aenter__(self) -> BaseScraper: ...

    @abstractmethod
    async def __aexit__(self, *args) -> None: ...

    @abstractmethod
    def search(self, spec: SearchSpec) -> AsyncIterator[Ad]: ...
```

The CLI uses `async with build_scraper(config) as scraper:` and never knows which implementation it got.

## State Flow

```
1. User invokes CLI
2. CLI builds SearchSpec from args
3. CLI builds a scraper via factory (config decides which)
4. Scraper context enters: launches browser, applies stealth
5. Scraper.search() is an async generator yielding Ad
6. CLI feeds the generator into the exporter
7. Exporter writes to disk or stdout, returning count
8. Scraper context exits: closes browser, flushes logs
9. CLI exits with appropriate code
```

## Configuration Layers

In order of precedence (highest wins):

1. **CLI flags** — `--max-results 100`
2. **Environment variables** — `META_ADS_MAX_RESULTS=100`
3. **`.env` file** — same vars, loaded by pydantic-settings
4. **Hardcoded defaults** — defined in `config.py`

Use `pydantic-settings` `BaseSettings` to wire all four together.

## What's NOT in the architecture (and why)

- **No database for storing scraped ads** — the deliverable is files on disk. SQLite is used only for resume checkpointing, not data storage.
- **No web UI** — Antonio asked for a CLI deliverable. Don't over-build.
- **No proxy management** — out of scope, signals scraping farm.
- **No notification system** — out of scope.
- **No multi-machine coordination** — out of scope.
