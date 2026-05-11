# 01 — System Overview

## What this is

A Python command-line scraper that collects structured ad data from Meta's Ad Library (the public site at https://www.facebook.com/ads/library/).

## What it does

Given one of:
- A keyword (e.g., `"luxury watches"`)
- A Facebook page URL (e.g., `https://www.facebook.com/Nike`)
- A Facebook page slug (e.g., `Nike`)

It returns structured `Ad` records and writes them to CSV or JSON.

## What it doesn't do

- It does NOT solve CAPTCHAs
- It does NOT bypass paywalls or login gates
- It does NOT rotate proxies
- It does NOT scrape user profiles, posts, comments, or any non-ad content
- It does NOT use the Meta Graph API for political ads (that's a future enhancement; see `04-scraping-strategy.md`)

## High-level flow

```
CLI args
  → SearchSpec
    → url_resolver
      → Meta Ads Library URL
        → PlaywrightScraper
          → Pagination loop
            → Ad card extraction
              → Pydantic Ad validation
                → CSV / JSON exporter
                  → File on disk OR stdout
```

## Quick start (post-build)

```bash
# Install
pip install -e .
playwright install chromium

# Search by keyword
python -m meta_ads_scraper search --keyword "dental practices" --max-results 50 --format csv --out dental.csv

# Search by page slug
python -m meta_ads_scraper search --page-slug "Nike" --format json --out nike.json

# Resume a previous run
python -m meta_ads_scraper resume <run-id>
```

## Related docs

- `02-architecture.md` — Module structure
- `03-data-model.md` — The `Ad` Pydantic model
- `04-scraping-strategy.md` — Path A vs Path B; why we chose Playwright
- `05-anti-detection.md` — Stealth, jitter, rate limiting
- `06-pagination.md` — Infinite-scroll handling
- `07-retry-policy.md` — When to retry, when to fail
- `08-cli-design.md` — Typer CLI surface
- `09-output-formats.md` — CSV and JSON serialization
- `10-testing-strategy.md` — Unit, integration replay, live smoke
- `11-deployment-and-running.md` — How to run in CI, on a server, in cron
