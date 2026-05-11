# Meta Ads Scraper — Build Plan

> **How to use this file:** Each phase is one focused implementation session. Work through the prompt for the phase, review the diff, commit, move on. Do not skip phases. Do not combine phases.

**Prerequisites before Phase 0:**
- This repo is cloned/extracted on your machine
- You are in the repo root
- You have Python 3.11+ available
- You have Node.js available (for Playwright browsers install)

---

## Phase 0 — Bootstrap (target: 30 min)

**Goal:** Repo is set up, dependencies install, CI is green, baseline commit pushed to GitHub.

**Implementation prompt:**

```
Read these files in order:
  1. PLANNING-BRIEF.md
  2. .project/ENGINEERING-MANUAL.md
  3. .project/journal/JOURNAL.md
  4. docs/architecture/01-overview.md
  5. docs/architecture/02-architecture.md

Then do the following:

1. Run `bash bootstrap.sh` to set up git config, virtualenv, install dependencies, install Playwright browsers (Chromium only), and run `ruff check` + `pytest` to verify the empty scaffold works.

2. If bootstrap.sh fails, debug and fix. Common issues:
   - Python version: must be 3.11+
   - Playwright install: needs `playwright install chromium`
   - Missing system deps: `playwright install-deps chromium` (Linux) or skip on macOS

3. Verify pyproject.toml has all dependencies listed in §3 of PLANNING-BRIEF.md.

4. Verify .github/workflows/ci.yml exists and is correct.

5. Create the initial commit per gitmoji conventions:
   - "🎉 chore(repo): initial scaffold + dependencies + CI"

6. Push to GitHub. Create the repo as `meta-ads-scraper` (public) under Samuel-Muriuki.

7. Wait for CI to complete. It must be green. If red, fix and push.

8. Update STATUS.md with: Phase 0 complete, develop branch tip SHA, CI badge state.

Do NOT proceed to Phase 1. Stop after Phase 0 and report status.
```

**Definition of Done for Phase 0:**
- [ ] `pyproject.toml` lists all deps from §3 of PLANNING-BRIEF
- [ ] `pytest` runs (even if no tests yet, exits 0 or "no tests collected")
- [ ] `ruff check src/` exits 0
- [ ] `mypy src/` exits 0
- [ ] GitHub repo exists, public, CI badge green
- [ ] At least one commit pushed: `🎉 chore(repo): initial scaffold`

---

## Phase 1 — MVP Single Keyword Search (target: 4 hours)

**Goal:** Working end-to-end pipeline for keyword search → 1 page of results → JSON dump.

**Implementation prompt:**

```
Phase 1: Build the MVP path for keyword search.

Read docs/architecture/04-scraping-strategy.md and docs/contracts/ad-data-schema.md
before writing any code.

Tasks:

1. src/meta_ads_scraper/models.py
   - Implement the Ad Pydantic v2 model per docs/contracts/ad-data-schema.md
   - Implement the SearchSpec Pydantic v2 model per §5 of PLANNING-BRIEF
   - Use `from __future__ import annotations`
   - Use `model_config = ConfigDict(str_strip_whitespace=True)`

2. src/meta_ads_scraper/url_resolver.py
   - Function: resolve_url(spec: SearchSpec) -> str
   - Maps a SearchSpec to the Meta Ads Library URL
   - For keyword: https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q=<URL-ENCODED-KEYWORD>&search_type=keyword_unordered
   - For page_url and page_slug: stubbed with NotImplementedError for now

3. src/meta_ads_scraper/scraper/base.py
   - Abstract class: BaseScraper
   - Method: async def search(spec: SearchSpec) -> AsyncIterator[Ad]
   - Method: async def __aenter__ / __aexit__ for resource management

4. src/meta_ads_scraper/scraper/playwright_scraper.py
   - class PlaywrightScraper(BaseScraper)
   - In __aenter__: launch chromium, apply playwright-stealth, create context with realistic viewport
   - In __aexit__: close browser cleanly
   - search() method:
     - Navigate to resolve_url(spec)
     - Handle cookie consent dialog if present
     - Wait for results container to appear (selector: TBD via reconnaissance)
     - Extract initial visible ad cards via locator
     - Yield Ad models one at a time
   - DO NOT implement pagination yet — just return first page

5. src/meta_ads_scraper/parsers/ad_card.py
   - Function: parse_ad_card(card_locator, source_url: str) -> Optional[Ad]
   - Extract: ad_library_id, page_id, page_name, ad_creative_text, ad_creative_image_urls, start_date, platforms
   - Other fields may be None at this phase
   - On parse failure: log warning, return None

6. src/meta_ads_scraper/cli.py
   - Typer app with one command: `search`
   - Args: --keyword (str), --format (csv|json, default json), --out (Path, default stdout)
   - For now: only --keyword works; --page-url and --page-slug raise NotImplementedError
   - Outputs first 10 ads as JSON to stdout or file

7. src/meta_ads_scraper/__main__.py
   - Enables `python -m meta_ads_scraper`

8. tests/unit/test_models.py
   - Verify Ad model: required fields enforced, optional fields default to None, list fields default to []
   - Verify SearchSpec model: mode must be one of three literals

9. tests/unit/test_url_resolver.py
   - For keyword mode: produces correct URL with URL-encoded query
   - For other modes: raises NotImplementedError (will be implemented in Phase 2)

10. tests/integration/test_playwright_scraper_mvp.py
    - Marked with @pytest.mark.live_test (skipped unless META_LIVE_TESTS=1)
    - Searches for "shoes", expects >= 5 ads, expects each Ad to have ad_library_id and page_id

Commit per atomic discipline:
- "✨ feat(models): add Ad and SearchSpec Pydantic models"
- "✨ feat(url): keyword search URL resolver"
- "✨ feat(scraper): MVP Playwright scraper for keyword search"
- "✨ feat(cli): basic Typer CLI with keyword search"
- "🧪 test: unit coverage for models and URL resolver"
- "🧪 test: smoke integration test for live Playwright (gated)"

After all commits:
- Open PR from develop to main, title: "Phase 1: MVP keyword search"
- DO NOT merge yet — Samuel reviews first
```

**Definition of Done for Phase 1:**
- [ ] `python -m meta_ads_scraper search --keyword "shoes"` returns ≥1 Ad as JSON
- [ ] All unit tests pass
- [ ] Smoke test passes when run with `META_LIVE_TESTS=1` locally
- [ ] CI green
- [ ] PR open for review

---

## Phase 2 — Three Search Paths Unified (target: 3 hours)

**Goal:** Keyword, page URL, and page slug all work through the same interface.

**Implementation prompt:**

```
Phase 2: Wire up page URL and page slug search modes.

Tasks:

1. Update src/meta_ads_scraper/url_resolver.py:
   - For page_url: parse the URL, extract the page slug, look up page_id via Graph API (httpx) OR via a Playwright navigation to the page (whichever is simpler — document the choice)
   - For page_slug: same as page_url, just skip the slug-extraction step
   - The final URL should use view_all_page_id=<PAGE_ID> in the Meta Ads Library URL

2. Add src/meta_ads_scraper/exporters/csv_exporter.py
   - Function: write_ads_csv(ads: Iterable[Ad], out: Path | TextIO) -> int
   - Uses csv.DictWriter
   - Flattens list fields with semicolon-join (e.g. platforms: "FACEBOOK;INSTAGRAM")
   - UTF-8 with BOM for Excel compatibility
   - Returns count written

3. Add src/meta_ads_scraper/exporters/json_exporter.py
   - Function: write_ads_json(ads: Iterable[Ad], out: Path | TextIO) -> int
   - Indented, ISO 8601 datetimes
   - Returns count written

4. Update CLI:
   - --page-url and --page-slug now work
   - --format flag dispatches to the correct exporter
   - Validate mutual exclusion of the three input flags (use Typer's callback)

5. Tests:
   - Unit tests for each exporter using a fixture of 3 sample Ads
   - Unit test for CLI mutual exclusion (use CliRunner)
   - Update integration test to cover all three search modes (gated)

Commits:
- "✨ feat(url): support page_url and page_slug search modes"
- "✨ feat(exporters): CSV and JSON exporters"
- "✨ feat(cli): wire up three search modes and exporters"
- "🧪 test: exporter and CLI coverage"

PR: "Phase 2: Three search paths + exporters"
```

**Definition of Done for Phase 2:**
- [ ] `python -m meta_ads_scraper search --page-slug "Nike" --format csv --out nike.csv` writes valid CSV
- [ ] `python -m meta_ads_scraper search --page-url "https://www.facebook.com/Nike" --format json` works
- [ ] Mutual exclusion enforced (running with 0 or 2+ input flags exits non-zero)
- [ ] CI green

---

## Phase 3 — Pagination (target: 4 hours)

**Goal:** Scrape until natural end OR `--max-results` reached OR `--timeout` exceeded.

**Implementation prompt:**

```
Phase 3: Infinite-scroll pagination.

Read docs/architecture/06-pagination.md before coding.

Tasks:

1. Add src/meta_ads_scraper/pagination.py:
   - async def scroll_and_collect(
       page,
       ad_card_selector: str,
       max_results: int | None,
       timeout_seconds: int = 300,
       stall_threshold: int = 3,
     ) -> AsyncIterator[Locator]
   - Implements the scroll loop per §7 of PLANNING-BRIEF
   - Yields newly-appeared card locators (not previously yielded)
   - Stops on max_results, timeout, or stall_threshold consecutive no-progress scrolls

2. Update PlaywrightScraper.search() to use scroll_and_collect

3. Update CLI: add --max-results (int, default None=unlimited but enforce reasonable cap of 1000), --timeout (int seconds, default 300)

4. Tests:
   - Unit test pagination logic using a mock page object (no Playwright)
   - Update smoke test to verify pagination yields >first-page results when --max-results=30

Commits:
- "✨ feat(pagination): scroll-and-collect with stop conditions"
- "✨ feat(scraper): integrate pagination into Playwright scraper"
- "🧪 test: pagination unit tests with mock page"

PR: "Phase 3: Pagination"
```

---

## Phase 4 — Resilience (target: 4 hours)

**Goal:** Retries, error handling, rate limiting, structured logging.

**Implementation prompt:**

```
Phase 4: Production-grade resilience.

Read docs/architecture/07-retry-policy.md before coding.

Tasks:

1. src/meta_ads_scraper/retry.py
   - Tenacity policies per §8 of PLANNING-BRIEF
   - Exported as decorators: @retry_network, @retry_rate_limited, @retry_dom

2. src/meta_ads_scraper/rate_limit.py
   - class RateLimiter using asyncio.Semaphore + asyncio.sleep
   - Default: 1 request/second, max concurrency 1
   - Configurable via CLI: --rate-limit (float req/s), --concurrency (int)

3. src/meta_ads_scraper/logging_config.py
   - structlog setup: JSON output by default, pretty-print with -v flag
   - Levels: -v=INFO, -vv=DEBUG

4. Apply retry decorators throughout scraper module

5. Wire rate limiter into PlaywrightScraper

6. Update CLI: --rate-limit, --concurrency, -v, -vv flags

7. Tests:
   - Unit test retry behaviour using a mock function that fails N times then succeeds
   - Unit test rate limiter timing
   - Smoke test: verify logs are JSON-parseable

Commits:
- "✨ feat(retry): tenacity policies for network and DOM failures"
- "✨ feat(rate-limit): configurable rate limiter"
- "✨ feat(logging): structlog config with verbosity levels"
- "♻️ refactor(scraper): apply retry and rate limit decorators"
- "🧪 test: retry and rate limit coverage"

PR: "Phase 4: Resilience layer"
```

---

## Phase 5 — CLI Polish & Resume (target: 3 hours)

**Goal:** Production-feeling CLI. Resume capability via SQLite checkpoint.

**Implementation prompt:**

```
Phase 5: CLI polish and resume capability.

Tasks:

1. src/meta_ads_scraper/checkpoint.py
   - SQLite-backed checkpoint store
   - Schema: runs(run_id, search_spec_json, started_at, completed_at), scraped_ads(run_id, ad_library_id, scraped_at)
   - Functions: start_run, record_ad, complete_run, resume_run

2. Update PlaywrightScraper to skip already-scraped ad_library_ids when resuming

3. Add CLI command: meta-ads-scraper resume <RUN_ID>

4. Add rich progress bar to scraping loop (toggleable with --no-progress)

5. Write README.md (the production one, not the placeholder):
   - Installation
   - Quick start with 3 examples (one per search mode)
   - All CLI flags documented
   - Architecture overview (link to PLANNING-BRIEF.md and docs/architecture/)
   - Known limitations (CAPTCHA, rate limits, official API not used)
   - Contributing / license

6. Add `examples/` folder:
   - examples/dental_practices_us.csv (real run output)
   - examples/Nike_ads.json (real run output)

Commits:
- "✨ feat(checkpoint): SQLite-backed resume capability"
- "✨ feat(cli): rich progress bar and resume command"
- "📝 docs(readme): production README"
- "📝 docs(examples): sample output files"

PR: "Phase 5: Polish and resume"
```

---

## Phase 6 — Tests & CI Hardening (target: 3 hours)

**Goal:** Comprehensive test coverage. CI runs all gated tests on workflow_dispatch.

**Implementation prompt:**

```
Phase 6: Test coverage and CI hardening.

Tasks:

1. Record HAR fixtures:
   - tests/fixtures/keyword_search_shoes.har (using Playwright record mode)
   - tests/fixtures/page_slug_nike.har

2. Add tests/integration/test_replay.py:
   - Replays HAR fixtures via Playwright's HAR mode
   - Deterministic, runs in CI
   - Verifies parser extracts expected fields

3. Increase unit test coverage to >= 80% on parsers, models, exporters, retry, pagination

4. Update .github/workflows/ci.yml:
   - Push trigger: unit tests + replay tests
   - workflow_dispatch trigger: full smoke tests with META_LIVE_TESTS=1
   - Cache pip and playwright browsers

5. Add coverage badge to README

Commits:
- "🧪 test: HAR fixtures for deterministic replay"
- "🧪 test: integration tests via HAR replay"
- "🧪 test: expand unit coverage"
- "👷 ci: workflow_dispatch for live smoke tests + caching"
- "📝 docs(readme): coverage badge"

PR: "Phase 6: Test coverage and CI"
```

---

## Phase 7 — APPROACH.md and Demo Data (target: 2 hours)

**Goal:** Antonio's required deliverables. The 1-page approach explanation + sample outputs.

**Implementation prompt:**

```
Phase 7: Final deliverable docs.

Tasks:

1. Write APPROACH.md (the one Antonio asked for as "short explanation of your approach"):
   - Max 1 page when rendered (~ 600 words)
   - Sections:
     - What I built (3 sentences)
     - The hardest decision and how I made it (Path A vs B)
     - Trade-offs I made deliberately
     - What I'd add next if this went to production
     - Known limitations
   - Tone: direct, no fluff, Antonio-aligned

2. Run the scraper for real against 3 keywords relevant to Hoski's verticals:
   - "dental practices"
   - "luxury jewelry"  
   - "automotive services"
   - Save outputs to examples/ as both CSV and JSON

3. Update README with link to APPROACH.md

Commits:
- "📝 docs(approach): one-pager approach explanation"
- "📝 docs(examples): real-world demo runs for Hoski verticals"

PR: "Phase 7: Submission docs"
Merge all phase PRs to main.
Tag release v1.0.0.
```

---

## Final Submission Steps (target: 2 hours)

**Not an in-code task — do this yourself.**

1. **Record Loom walkthrough** (5–8 min):
   - 0:00–0:30 Intro: who you are, what you built, time taken
   - 0:30–2:00 Live demo: run the scraper for one of Hoski's verticals
   - 2:00–4:30 Code walkthrough: open `scraper/playwright_scraper.py`, `models.py`, show the structure
   - 4:30–6:00 Trade-offs: why Path B over Path A, why no CAPTCHA solving, why these tests
   - 6:00–7:00 What's next: Path A integration, async concurrency, monitoring
   - 7:00–7:30 Close: how to clone, run, what to look at first

2. **WhatsApp Antonio:**
   ```
   Done. Submission:
   
   Repo: github.com/Samuel-Muriuki/meta-ads-scraper
   Loom: [URL]
   Approach doc: github.com/Samuel-Muriuki/meta-ads-scraper/blob/main/APPROACH.md
   
   ~22 hours total over the weekend. Built Playwright-first since the
   official API doesn't cover commercial ads. Happy to walk through any
   part of it on the call Monday.
   
   — Samuel
   ```

3. **Update Job_Tracker.csv** with submission timestamp.

---

**END OF BUILD PLAN**
