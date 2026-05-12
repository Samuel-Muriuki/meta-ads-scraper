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
- HAR-replay integration test (`tests/integration/test_pagination_har_replay.py`) covering the scroll loop offline
- `scripts/capture_pagination_har.py` + `scripts/slim_har.py` reproducers for the HAR fixture
- Typed CLI exit codes (0, 1, 2, 3, 4, 5, 130) wired via `_typed_exit_codes` decorator per `docs/architecture/08-cli-design.md`
- Coverage gate enforced at 78% on CI (current: 79.12%); coverage XML uploaded as a CI artifact

### Changed
- `AD_CARD_SELECTOR` and `AD_CARD_BOUNDARY_XPATH` extracted to `src/meta_ads_scraper/constants.py`; parser and scraper now reference the same definition
- `docs/architecture/08-cli-design.md` reconciled with the implemented CLI surface (search/resume/runs + the exit-code table)
- `docs/architecture/02-architecture.md` module map: removed stale `config.py` reference, added `constants.py`, dropped non-existent `scraper/api_scraper.py`

### Fixed
- `[[tool.mypy.overrides]]` narrowed to `playwright_stealth.*` only (playwright and tenacity now ship `py.typed`); "unused section" mypy note resolved
- `.claude/` runtime state directory added to `.gitignore` (audit confirmed no historical contamination; forward-looking fix)

---

### Phase 7 — submission deliverables (2026-05-12)

#### Added
- `APPROACH.md` submission narrative at the repo root (968 words)
- Three vertical demo outputs in `examples/` (jewelry, dental, automotive) plus `examples/demo_runs.log`
- `examples/stress_test_500ads.json` + annotated `examples/stress_test.log` from the 500-ad sustained-load demonstration

#### Notes
- Coverage gate remains at 78%. Local measurement is 79.12% (below the 80% lift threshold); raising the gate requires additional unit coverage on `playwright_scraper.py` and is deferred

---

### Post-release portability fixes (2026-05-12)

#### Fixed
- `bootstrap.sh` no longer hardcodes git author identity; prompts for name and email on first run if `git config user.name` / `user.email` are unset for the repository
- Cross-platform line endings enforced via `.gitattributes` (Windows clones no longer fail `bash bootstrap.sh` due to CRLF on shell scripts)
- README Quick start now documents a Windows-native PowerShell path so users without bash can install without `bootstrap.sh`

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
