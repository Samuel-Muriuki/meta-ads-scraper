# Engineering Journal

> Single source of truth for the project's current state. Update on each phase boundary and after material decisions.

---

## Current Phase

**Phase 7 — APPROACH & Demo** (not yet started)

**Phase 6 merge commit:** `91926c7` — `Merge pull request #5 from Samuel-Muriuki/feat/phase-6-tests-ci-hardening`
**Develop tip:** `91926c7` (will advance after this journal commit)
**Main tip:** `9598b78` — Phase 0 closeout (unchanged; develop → main merge happens at submission)
**Last completed phase:** Phase 6 — Tests & CI Hardening
**Build path:** full BUILD-PLAN through Phase 7 (no scope cuts)
**Submission deadline:** Monday 2026-05-13 9 PM Nairobi

---

## Recent Decisions

### 2026-05-12 — Phase 6 closeout

- **Shared constants module instead of in-file duplication.** `src/meta_ads_scraper/constants.py` exports `AD_CARD_SELECTOR` and `AD_CARD_BOUNDARY_XPATH`. The chained selector is derived from the boundary xpath so the two cannot drift. Module docstring captures the Phase 3 hard-won selector history (xpath-only forms returned zero matches on Meta's live React DOM) so future maintainers don't relearn it.
- **`_typed_exit_codes` as a decorator, not an inline wrapper.** Wraps each `@app.command` function (search, resume, runs). Cleaner than threading try/except blocks through each command body. Uses `ParamSpec` + `TypeVar` for proper generic typing — mypy strict + ruff `ANN401` both green, no `Any` in the *args/**kwargs signature.
- **HAR-replay test uses `not_found="fallback"`.** Meta's page references CDN assets we did not capture; aborting on miss would fail the page load. The substantive assertion (≥ 20 ads parsed) catches the failure modes we care about. Caveat documented in the test docstring and surfaced as a Phase 6 followup.
- **HAR fixture left at 11.5 MB.** Dropping the JS bundles (8 MB total) would break replay fidelity — Meta's React app needs them to render and trigger scroll-loaded ads. GitHub allows the size; clone cost accepted. `scripts/slim_har.py` filters by host + MIME type and scrubs `Cookie` / `Set-Cookie` / `Authorization` / `X-Fb-*` headers (85 values redacted).
- **Coverage gate at 78% (one below current 79.12%).** Per the Phase 6 prompt's "current floor minus 1" rule for the 70-79% range. Leaves breathing room for incidental drops; followup logged to lift to 80% in Phase 7 once `playwright_scraper.py` coverage rises above its current 33%.
- **Coverage gate enforced in `integration-replay` job, not `unit-tests`.** Unit-only coverage doesn't reach 78% (most of `playwright_scraper.py` is exercised only by integration tests). The fast-feedback unit-tests job passes `--cov-fail-under=0` to override the pyproject gate; the slow integration job runs the full non-live suite and inherits the 78% gate. Tests run twice across jobs but execute in parallel.
- **`mypy.overrides` narrowed to `playwright_stealth.*` only.** Empirically verified via `py.typed` markers: `playwright` and `tenacity` ship type stubs and don't need the override; `playwright_stealth` doesn't. Inline comment in `pyproject.toml` explains the asymmetry so the next maintainer doesn't repeat the investigation.
- **`02-architecture.md` Option (a) chosen** (remove `config.py` rather than build a settings module). `pydantic-settings` adds dependency weight without clear value at the current single-machine deployment scope. The two-channel configuration model (CLI flags + env vars) is documented honestly. Stale `scraper/api_scraper.py` reference also removed; the abstract `BaseScraper` exists for the future Path A swap.

### 2026-05-12 — Phase 5 closeout

- **Checkpoint ownership split between scraper and CLI.** The scraper calls `record_ad` inline as it yields; the CLI owns `start_run` / `complete_run` / `abort_run` around `asyncio.run`. Async generators do not give the inside-function a clean signal of "consumer finished normally vs aborted by exception", so terminal-status writes belong to the caller. Documented in commit `93ab9b4`'s body.
- **Inline (synchronous) `record_ad` from inside an async loop.** SQLite writes are sub-10ms on local disk; an `asyncio.to_thread` hop per ad would cost more than it gains. The Phase 5 prompt stop condition (`>100ms per ad`) was monitored during the live runs and stayed clear.
- **Resume writes new ads only; combined output is the caller's problem.** Alternative would have been to refetch + write the full set, which requires storing the entire `Ad` object (not just `ad_library_id`) in the checkpoint — a much larger schema. Trade-off documented prominently in `resume --out` help text and the README's "Resume from interruption" section.
- **`search` always checkpoints.** No opt-out flag. Every search creates a row in `data/runs.sqlite`. The DB is gitignored and small (~1 KB per run row + scraped_ads); users can `rm data/runs.sqlite` to wipe. `--db-path` is a one-liner if needed in Phase 6+.
- **Progress bar uses `Progress(disable=...)` instead of branching code paths.** Single scrape code path differentiated only by the `disable` flag, computed from `(not show_progress) or (not console.is_terminal)`. Rich's documented way to make the entire context a silent no-op.
- **`runs` table renders via `Console(stderr=True)`.** Same stderr discipline as the rest of the CLI: stdout reserved for JSON/CSV payloads, stderr for diagnostics. Architectural test only — Click 8.2 removed `mix_stderr=False`, so behavioural tests on stdout/stderr separation are deferred to Phase 6 subprocess-based coverage.
- **`RunSummary` is a frozen dataclass, not a Pydantic model.** It's a read-only projection of the `runs` row plus a denormalised `ad_count`. No validation needed, no cross-module serialisation — a dataclass is the lighter fit.
- **Phase 4's deferred live smoke ran here as Task 6.** One keyword search + one page-slug scrape, 10 ads each, at 0.5 req/sec. Both committed as `examples/keyword_shoes.json` and `examples/page_slug_nike.csv`. DOM unchanged from Phase 3; the chained card selector and the `delegate_page` page-id pattern both still work.

### 2026-05-12 — Phase 4 closeout

- **Option A predicate refinement for `@retry_network`.** The decorator catches httpx transport errors (`TimeoutException`, `ConnectError`, `ReadError`) AND Playwright errors filtered by `_is_retryable_playwright_error`. The predicate matches `str(exc).lower()` against `(net::err, navigation timeout, page closed, target closed)` so that genuine selector misses (which belong to `@retry_dom`) do not slip through. One decorator, two stacks; selector-shape failures still flow to the right policy.
- **`_resolve_page_id` wrapped with `@retry_dom` per the Phase 4 prompt's pure-Playwright branch.** The method has been pure Playwright navigation since the Phase 2 httpx→Playwright refactor. `@retry_dom` retries only `PlaywrightTimeoutError`; non-timeout `PlaywrightError` (e.g. `net::ERR_*`) propagates without retry. Asymmetric with `_goto_with_retry` which uses `@retry_network`. Flagged for Phase 5+ review — if live runs surface `net::ERR_*` from the slug page, switch to `@retry_network` for symmetry.
- **`RateLimiter` installed INSIDE `scroll_and_collect`, not wrapped around the whole scrape.** Each scroll iteration calls `rate_limiter.acquire()` at the top of the loop body. `wait_for_load_state`'s natural pacing is not sustained-load defense; per-iteration acquire is. Default kwarg `None` keeps the 15 existing pagination tests timing-free.
- **structlog stdlib bridge enabled in `logging_config.py`.** Logs from Playwright, httpx, and tenacity (`before_sleep_log`) flow through the same processor chain and emit in the chosen renderer (JSON default, pretty console at `-vv`). Stable log event names locked in the module docstring: `scrape_start`, `no_cookie_consent_dialog`, `cookie_consent_dismissed`, `no_ads_visible`, `max_results_reached`, `pagination_stalled`, `pagination_timeout`, `pagination_stall_tick`, `shutdown_requested`, `page_id_resolve_start`, `page_id_resolved`, `max_results_zero_treated_as_unlimited`, `max_results_above_ceiling`, `rate_limit_concurrency_clamped` (14 names). No renames without a PR-level Architectural Decisions entry.
- **`RateLimiter` concurrency-vs-queue-depth tradeoff documented inline.** Pre-merge calibration: a four-line comment above `acquire()` notes that the internal lock serialises the timed wait, so `max_concurrency > 1` provides queue-depth bound rather than parallel execution. Single-coroutine scrape path is the supported case. Lands in the rate-limit feature commit (`705a46e` post-rebase) rather than as a follow-up — preserves atomic discipline.
- **No live smoke this phase per the Phase 4 directive.** Phase 4 is infrastructure, not capability. Budget preserved for Phase 5/7 demo runs against Hoski-relevant verticals. CI's `Live Smoke (Manual Only)` job stayed `SKIPPED` as designed (gated behind `META_LIVE_TESTS=1` + `workflow_dispatch`).

### 2026-05-12 — Phase 3 closeout

- **Pure xpath card-boundary expressions FAIL on Meta's nested React DOM.** Initial selector returned 0 ads live. The working pattern is Playwright's **chained `text=/Library ID:\s*\d+/ >> xpath=ancestor::div[.//img][1]`** — anchor on the Library ID text node, walk up to the closest div containing an img. Same approach used by `iter_visible_ads` and validated by the offline parser test.
- **Manual E2E confirmed.** `python -m meta_ads_scraper search --keyword shoes --max-results 10 --format json` returned 10 ads cleanly in ~41s. Real verticals observed: Nike, Amazon India, Level Shoes, FirstCry, schuh, Temu, animal-rights ads, music artist promos. Proves the scraper handles realistic Hoski-relevant traffic mix.
- **Locale fix (Phase 2) still working.** Resolved URL includes `&locale=en_US`, output is English, "Library ID:" anchor matches. The Swahili-collapse failure mode from Phase 1 is fully eliminated.
- **Pagination ceiling untested at 1000 ads.** Phase 4 RateLimiter must come before any sustained-load test against the ceiling — currently we'd risk Meta rate-limiting us out mid-test.
- **Live test runtime ~3 min per keyword.** CI gated correctly behind `META_LIVE_TESTS=1` + `workflow_dispatch`; never runs on push. Important to keep this gate strict.
- **Branch protection on main works** correctly with `gh pr merge --merge` strategy. The ruleset "Protect main" (16255967) blocks force-push and direct push; PRs merge cleanly via the standard `--merge` path.

### 2026-05-12 — Phase 3 in review

- **scroll_and_collect lives as a leaf module** (`src/meta_ads_scraper/pagination.py`). No deps on `scraper/*` or `cli`. Driven by the scraper, consumed via `async for card in scroll_and_collect(...)`. 15 unit tests cover max_results / stall / dedup / timeout / container-fallback / edge cases against a `_FakePage` mock.
- **MAX_RESULTS_CEILING = 1000.** `--max-results=0` and `--max-results=None` both map to the ceiling. `--max-results > 1000` logs a warning and clamps. The 1000 figure matches `docs/architecture/06-pagination.md`.
- **Card selector switched mid-phase from xpath-only to chained text→xpath.** The xpath `//div[Library-ID-descendant and img-descendant and no-inner-Library-ID-div]` returned zero matches on the live Meta DOM. Replaced with `text=/Library ID:\s*\d+/ >> xpath=ancestor::div[.//img][1]` — same two-step pattern that powers `iter_visible_ads` and the offline parser test. Live smoke recovered from 0 ads to 20+.
- **Pagination smoke proves end-to-end.** `tests/integration/test_playwright_scraper_mvp.py[keyword=shoes-paginated]` with `max_results=30` returns 20+ ads in ~207s against real Meta. Elapsed-time assertion (>15s) catches "scroll didn't trigger" failure mode.
- **Graceful shutdown.** `scroll_and_collect` catches `asyncio.CancelledError`, logs `shutdown_requested` with the yielded count, then re-raises so the caller's exporter can still flush partial output.

### 2026-05-11 — Phase 2 in review

- **Three search modes all live end-to-end.** `keyword=shoes`, `page_slug=Nike`, `page_url=https://www.facebook.com/Nike` each return ≥ 5 valid `Ad` records against real Meta. 3 parametrized live tests pass in 273s combined (gated by `META_LIVE_TESTS=1`).
- **Page-id resolution mechanism switched mid-phase.** Initial httpx-based scrape (commit `61834ff`) returned 400 Bad Request from live Meta despite passing all unit tests with `httpx.MockTransport`. Refactored to use the existing Playwright BrowserContext (commit `7c174ad`) — same stealth chromium fingerprint that works for the keyword scrape, so Meta serves the real page. httpx import removed from `url_resolver` entirely; `resolve_url` now takes an injectable `page_id_resolver` callable. **Lesson:** unit tests against mock transport were technically passing while production was completely broken. Don't trust mock-transport coverage for anti-bot-prone endpoints — verify against live before declaring done.
- **Updated PAGE_ID_PATTERNS for current Meta DOM.** Verified against a live Nike page capture: `"delegate_page":{"id":"N"}` is the canonical pattern; `"associated_page_id":"N"` and escaped-JSON `\"page_id\":\"N\"` are secondary. Legacy `"pageID":"N"` and `fb://page/?id=N` patterns kept as a safety net.
- **Three Pre-Conditions all delivered before feature work.** Locale forcing makes the page render in English (was Swahili from Kenya GeoIP). Fixture slimmed 1.89 MB → 30 KB. Offline parser integration test asserts ≥ 5 cards parse cleanly from `keyword_search_shoes.html` — runs on every push in CI, closes Phase 1's "ships green but unverified against real DOM" gap.
- **CI ANSI gotcha.** Typer/Click + Rich emit ANSI escape codes on Linux CI runners but not in local Windows PowerShell. Substring assertions against `result.output` need to strip `\x1b\[...m` first; fixed via a `_plain()` helper in `test_cli.py`.

### 2026-05-11 — Phase 1 in review

- **Meta Ad Library localizes by GeoIP** — running from Kenya, the page renders entirely in Swahili (`Maktaba ya Matangazo` instead of "Ad Library"). The `getByText("Library ID:")` anchor never matches because the literal text doesn't exist. Confirmed: the HTML fixture at `tests/fixtures/html/keyword_search_shoes.html` contains 26 long numeric library IDs and ~50 visible ad cards (see `tests/fixtures/html/keyword_search_shoes.png`, gitignored). Cards render correctly; the parser just couldn't find them with English-only selectors. Resolved in Phase 2 by forcing English locale on every Meta request.
- **`playwright-stealth` 1.x bumped to 2.x.** 1.x imports `pkg_resources` and crashes on Python 3.13 where setuptools is not pre-installed. 2.x exposes `Stealth().apply_stealth_async(page)`. PLANNING-BRIEF §3 names the dep without a version, so this is a pin-loosening, not a stack change.
- **`_looks_blocked` heuristic narrowed to "Log in" button only.** Original check `"facebook" not in title.lower()` false-positived on every wait-for-card timeout because the Ad Library title is "Ad Library" (or "Maktaba ya Matangazo"), not "Facebook".

### 2026-05-11 — Phase 0 closeout

- **PR merge strategy: always `--merge`, never squash.** For every PR (feature→develop, develop→main), use `gh pr merge <N> --merge` to preserve atomic gitmoji history and add a boundary marker commit. Established during the Phase 0 closeout PR.
- **Phase 0 closed via [PR #1](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/1).** 8 atomic commits, merged with `--merge` strategy → main at `3abfb3d`. Post-merge CI green on main.
- **Coverage gate deferred to Phase 6.** `--cov-fail-under=60` was removed from `pyproject.toml` `addopts` because the empty Phase 0 scaffold would have it fail unconditionally. BUILD-PLAN.md already schedules the coverage gate at Phase 6 ("expand unit coverage"), so this is a deferral, not a change of intent. Coverage reports themselves remain on.
- **Two smoke tests added at Phase 0.** `tests/unit/test_package.py` (asserts `__version__` is exposed) and `tests/integration/test_smoke.py` (asserts distribution metadata is present). Both exist primarily to keep pytest from returning exit-5 ("no tests collected") on the empty scaffold while still being real tests that catch packaging breakage. They stay as packaging guards even after Phase 1+ tests land.
- **`__version__` sourced from installed distribution.** `src/meta_ads_scraper/__init__.py` reads via `importlib.metadata.version("meta-ads-scraper")`, keeping `pyproject.toml` as the single source of truth.
- **Funding/sponsor surface added per `PROJECT-TEMPLATE` §4.3.** `.github/FUNDING.yml` (github + custom buymeacoffee), Buy Me a Coffee shield-badge anchored under H1 and as last line of README, `## 💖 Support` section before License, CI badge aligned to `?branch=main` form.

### 2026-05-11 — Project kickoff

- **Stack locked.** Python 3.11+, Playwright, Pydantic v2, Typer, tenacity, structlog. See `PLANNING-BRIEF.md` §3.
- **Path B (Playwright on public UI) is primary.** Path A (official API) is post-MVP enhancement. Rationale: official API doesn't cover commercial ads, which is what Hoski clients need.
- **No CAPTCHA solving.** If blocked, fail fast with clear error. Don't enter an arms race with Meta.
- **Repo name: `meta-ads-scraper`** — not `hoski-` prefixed. Portfolio-ready, not single-purpose.

---

## Known Blockers

(none)

---

## Followups Logged Not Filed

### Phase 2 Pre-Conditions — DELIVERED in PR #3

All three pre-conditions shipped:
1. ✅ Locale forcing: `a91bf73` — BrowserContext.locale="en-US" + Accept-Language header + timezone + `&locale=en_US` URL param. Page renders in English; live keyword smoke 0 → ≥ 5 ads.
2. ✅ Slim fixture: `5881980` — 1.89 MB → 30 KB. `scripts/slim_fixture.py` reproducer committed.
3. ✅ Offline parser test: `954c6df` — `tests/integration/test_parser_offline.py` asserts ≥ 5 ads parse cleanly from the slim fixture. Runs on every CI push.

### Other followups

- After MVP works, add a stealth-mode toggle (--stealth on/off) for debugging
- Consider exposing Path A as a fallback for political ads in Phase 8+
- Add `--screenshot-on-error` flag to dump page state when scraping fails
- Investigate whether Meta exposes a GraphQL endpoint that could replace DOM scraping (Phase 8+)
- **CI maintenance:** GitHub deprecated Node.js 20 for actions. `actions/checkout@v4` and `actions/setup-python@v5` will be forced to Node.js 24 from 2026-06-02 and Node.js 20 removed 2026-09-16. Bump action versions or set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` before then.
- **Tooling tidy:** ruff warns `ANN101` / `ANN102` are deprecated rules. The `pyproject.toml` mypy override for `tenacity.*` is currently unused (Phase 4 retry policies will make it live).
- **`docs/contracts/ad-data-schema.md` claim about hashability is wrong.** `frozen=True` only auto-hashes when every field is hashable, and `Ad` has list fields. Fix the contract doc when revisiting it at Phase 6 (tests & coverage tightening).
- **`.project/patterns/pytest-patterns/README.md` line 191** still says `pyproject.toml enforces --cov-fail-under=60`. Phase 0 deferred that to Phase 6 — sweep this and any other stale claims when Phase 6 re-adds the gate.
- **Phase 5 polish:** `ad_creative_text` includes Meta's layout artifacts (zero-width spaces `​`, "Active"/"Inactive" label, "Started running on…" metadata, "Sponsored" marker, "Platforms" header). Real ad copy starts after "Sponsored\n". Strip these via a post-processor in `parsers/ad_card.py` for cleaner CSV/JSON output. Low priority — current output is functional and contains the right information, just verbose.
- **Selector coupling between parser and scraper.** Both `iter_visible_ads` and the scraper's `_AD_CARD_SELECTOR` use the same text+xpath pattern. They must stay in sync. Phase 4 or Phase 6 should extract a shared constant.
- **HAR-replay test for pagination** — currently nothing in CI proves `scroll_and_collect` works against actual scroll-XHR-driven DOM. Phase 6 should record HAR with scroll events and add an offline pagination test.
- **`stall_threshold=3` is hardcoded** as a kwarg default, not CLI-exposed. If Meta's network is slow, premature stall is possible. Consider exposing as `--stall-threshold` flag in Phase 4 or making it adaptive to the rate-limiter.

### Phase 4 followups (logged 2026-05-12)

- **`_resolve_page_id` retry policy asymmetry.** Wrapped with `@retry_dom` per the Phase 4 prompt's pure-Playwright conditional, but the call shape (page.goto navigation) is identical to `_goto_with_retry` which uses `@retry_network`. Non-timeout `PlaywrightError` from the slug page (e.g. `net::ERR_*`) propagates without retry. If Phase 5+ live runs surface this, switch to `@retry_network` for symmetry.
- **`_wait_for_first_card` is a natural `@retry_dom` candidate** that was deliberately not decorated in Phase 4 (stop condition honoured). It currently converts a `PlaywrightTimeoutError` into a clean "no ads" path. If live testing in Phase 5+ shows flaky first-card waits, decorate it then.
- **`RateLimiter` concurrency semantics.** The internal lock serialises the timed wait, so `max_concurrency > 1` provides queue-depth bound rather than parallel execution. Reconsider the design if Phase 5+ introduces concurrent scraping across multiple `SearchSpec`s.
- **`tenacity.*` mypy override is now live** — Phase 4 imports tenacity in production code. The earlier "currently unused" followup is cleared.
- **Pre-existing followup remains:** `playwright_stealth.*` mypy override generates an "unused section" note (informational, not blocking). Sweep at Phase 6 along with the other mypy housekeeping.

### Phase 5 followups (logged 2026-05-12)

- **Resume produces "new ads only" output.** The resume command does not rewrite the original `--out` file; merging the two output files is the caller's job. Document in `APPROACH.md` or add a `--merge-with` flag in Phase 6+ if usability feedback requests it.
- **Checkpoint DB path is not CLI-configurable.** Defaults to `data/runs.sqlite`. Add `--db-path` if Phase 6+ tests need to point at a per-test sandbox, or if a Hoski deployment needs the DB on a different filesystem.
- ✅ **`docs/architecture/08-cli-design.md` is stale.** ~~Reconcile during Phase 6.~~ Done in Phase 6 commit `ea813aa`.
- ✅ **`docs/architecture/02-architecture.md` lists `config.py`** in the module map. ~~Either delete the reference or actually add pydantic-settings in Phase 6.~~ Done in Phase 6 commit `4f88f4a` — Option (a), reference removed.
- **`Click 8.2` removed `mix_stderr=False`** on `CliRunner`, so the test suite can no longer assert "X went to stderr only". The runs-to-stderr discipline is enforced architecturally via `Console(stderr=True)`. If Phase 6 wants behavioural coverage, switch to subprocess-based tests for the few stderr/stdout split assertions.

### Phase 6 followups (logged 2026-05-12)

- **Coverage gate set at 78% (one below current 79.12%).** Raise to 80% in Phase 7 once additional `playwright_scraper.py` paths are covered. The current 33% on that module is the biggest remaining gap; live tests cover it end-to-end but not at the unit level.
- **HAR replay test uses `not_found="fallback"`.** Missing entries fall through to the live network. If a CI runner ever loses public-internet egress, the test starts producing flakes; switch to `not_found="abort"` then and recapture the HAR to be self-contained.
- **HAR fixture is keyword-mode only.** Page-slug and page-url paths have no offline replay coverage. Capture additional HARs in Phase 7 if Loom demo recording surfaces any flakiness on those paths.
- **`scripts/api_scraper.py` is referenced in `BaseScraper` docstrings as a future Path A.** No concrete plan to build it. Either delete the references when Path A is formally killed, or wire it up post-submission as a portfolio enhancement.
- **`coverage.xml` is uploaded as a CI artifact** but not consumed anywhere. Hook up Codecov or a similar trending service when an account exists.

---

## Phase Completion Log

| Phase | Started | Completed | PR | Notes |
|---|---|---|---|---|
| 0 — Bootstrap | 2026-05-11 | 2026-05-11T09:48Z | [#1](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/1) | Coverage gate deferred to Phase 6; two smoke tests cleared pytest exit-5 on empty scaffold; funding/sponsor surface added per template §4.3. Merged develop→main via `--merge` strategy at main SHA `3abfb3d`. |
| 1 — MVP Keyword | 2026-05-11 | 2026-05-11T11:53Z | [#2](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/2) | 11 atomic commits. Live keyword smoke 0 ads (Swahili locale). HTML fixture captured for Phase 2 reconnaissance. Merged to develop. |
| 2 — Three Search Paths | 2026-05-11 | 2026-05-11T21:24Z | (closed-and-replaced after history rewrite; merged on fresh repo) | 10 atomic commits, three pre-conditions + feature + mid-phase httpx→Playwright refactor. Live verified across all 3 modes. |
| 3 — Pagination | 2026-05-12 | 2026-05-12T04:45Z | [#2](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/2) | 7 atomic commits. Pagination module + 15 unit tests + scraper integration + CLI flags + live smoke for multi-page + mid-phase selector fix. Merged at develop SHA `d7b28b9`. |
| 4 — Resilience | 2026-05-12 | merged at `ed74e1d` | [#3](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/3) | 9 atomic commits, retry + rate-limit + logging layer, no live smoke per Phase 4 directive. Mid-phase rebase to bake the rate-limiter concurrency-vs-queue-depth comment into the rate-limit commit (`891b286` → `705a46e`). |
| 5 — CLI Polish & Resume | 2026-05-12 | merged at `6eb9e27` | [#4](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/4) | 10 atomic commits, checkpoint + resume + runs + progress bar + production README, two live runs to `examples/`. |
| 6 — Tests & CI Hardening | 2026-05-12 | merged at `91926c7` | [#5](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/5) | 9 atomic commits, shared constants + typed exit codes + HAR replay + 78% coverage gate + mypy and doc cleanup. |
| 7 — APPROACH & Demo | — | — | — | — |

---

## Active Worktree State

- Branch: `develop` after Phase 6 merge (`91926c7`)
- Uncommitted edits: this Phase 6 closeout journal update
- Stash: (none)

---

**END OF JOURNAL**
