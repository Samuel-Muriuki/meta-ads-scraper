# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Initial repository scaffolding from PROJECT-TEMPLATE
- Architectural planning brief
- Phase-by-phase build plan
- Engineering manual + project journal
- CI pipeline (lint, type-check, unit tests, integration replay)
- `retry.py` with `@retry_network`, `@retry_rate_limited`, `@retry_dom` tenacity policies
- `_is_retryable_playwright_error` predicate covering `net::err`, `navigation timeout`, `page closed`, `target closed` signatures so `@retry_network` spans httpx and Playwright transport failures
- `rate_limit.py` with `RateLimiter` (`asyncio.Semaphore` + monotonic-clock pacing) and `MAX_CONCURRENCY_CEILING = 3`
- `logging_config.py` exposing `configure_logging(verbosity)` with stdlib bridge for Playwright/httpx/tenacity logs
- `RateLimitedError.retry_after` attribute for honouring server `Retry-After` hints
- `PlaywrightScraper` accepts `rate_limit` and `concurrency` kwargs; RateLimiter gates each scroll iteration
- `@retry_dom` applied to `_scroll_to_bottom` and the new `_wait_for_networkidle` helper in `pagination.py`
- `@retry_network` applied to `_goto_with_retry` and `@retry_dom` to `_resolve_page_id` in `playwright_scraper.py`
- CLI flags: `--rate-limit`, `--concurrency`, `-v` / `--verbose` (count-style for `-vv`)
- Unit tests: 13 in `tests/unit/test_retry.py`, 8 in `tests/unit/test_rate_limit.py`, 1 JSON shape smoke in `tests/unit/test_logging.py`
- `checkpoint.py` with `CheckpointStore` (SQLite-backed `runs` + `scraped_ads` tables, autocommit isolation, default path `data/runs.sqlite`)
- `PlaywrightScraper` accepts `checkpoint`, `run_id`, `yielded_ids` kwargs; records each yielded `Ad` to the checkpoint inline
- CLI subcommands: `search` (always checkpoints), `resume <run-id>` (continues with deduped `yielded_ids`), `runs` (rich.Table of recent runs to stderr)
- CLI flag `--no-progress`; rich.progress bar auto-suppresses when stderr is not a TTY
- 20 unit tests in `tests/unit/test_checkpoint.py`; 11 new CLI tests in `tests/unit/test_cli.py`
- Production `README.md` replacing the Phase 0 placeholder
- `examples/keyword_shoes.json` and `examples/page_slug_nike.csv` from controlled live runs at 0.5 req/sec

---

## Phase Tags (added as phases complete)

- `phase-0-bootstrap` — Initial scaffold
- `phase-1-mvp` — Single keyword search MVP
- `phase-2-three-paths` — Page URL and page slug search
- `phase-3-pagination` — Infinite-scroll pagination
- `phase-4-resilience` — Retries, rate limit, structured logging
- `phase-5-polish` — CLI polish, resume capability, README
- `phase-6-tests` — Test coverage + CI hardening
- `phase-7-submission` — APPROACH.md + demo data
- `v1.0.0` — Submission to Hoski
