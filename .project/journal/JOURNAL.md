# Engineering Journal

> Single source of truth for the project's current state. Update on each phase boundary and after material decisions.

---

## Current Phase

**Phase 4 — Resilience** (not yet started)

**Phase 3 merge commit:** `d7b28b9` — `Merge pull request #2 from Samuel-Muriuki/feat/phase-3-pagination`
**Main tip:** `9598b78` — Phase 0 closeout
**Build path:** full BUILD-PLAN through Phase 7 (no scope cuts)
**Submission deadline:** Monday 2026-05-13 9 PM Nairobi

---

## Recent Decisions

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

---

## Phase Completion Log

| Phase | Started | Completed | PR | Notes |
|---|---|---|---|---|
| 0 — Bootstrap | 2026-05-11 | 2026-05-11T09:48Z | [#1](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/1) | Coverage gate deferred to Phase 6; two smoke tests cleared pytest exit-5 on empty scaffold; funding/sponsor surface added per template §4.3. Merged develop→main via `--merge` strategy at main SHA `3abfb3d`. |
| 1 — MVP Keyword | 2026-05-11 | 2026-05-11T11:53Z | [#2](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/2) | 11 atomic commits. Live keyword smoke 0 ads (Swahili locale). HTML fixture captured for Phase 2 reconnaissance. Merged to develop. |
| 2 — Three Search Paths | 2026-05-11 | 2026-05-11T21:24Z | (closed-and-replaced after history rewrite; merged on fresh repo) | 10 atomic commits, three pre-conditions + feature + mid-phase httpx→Playwright refactor. Live verified across all 3 modes. |
| 3 — Pagination | 2026-05-12 | 2026-05-12T04:45Z | [#2](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/2) | 7 atomic commits. Pagination module + 15 unit tests + scraper integration + CLI flags + live smoke for multi-page + mid-phase selector fix. Merged at develop SHA `d7b28b9`. |
| 4 — Resilience | — | — | — | Next phase. Tenacity retries, RateLimiter, structlog config, CLI flags `--rate-limit` / `--concurrency` / `-v` / `-vv`. |
| 5 — CLI Polish & Resume | — | — | — | — |
| 6 — Tests & CI | — | — | — | — |
| 7 — APPROACH & Demo | — | — | — | — |

---

## Active Worktree State

- Branch: `develop`
- Uncommitted edits: this journal update + BUILD-PLAN index
- Stash: (none)

---

**END OF JOURNAL**
