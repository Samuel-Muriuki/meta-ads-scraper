# Engineering Journal

> Single source of truth for the project's current state. Update this every session. Read this on every session start.

---

## Current Phase

**Phase 1 — MVP Keyword Search** (in review)

**Feature branch:** `feat/phase-1-mvp-keyword` — open PR [#2](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/2)
**Develop tip:** `d9e1622` — `🔨 chore(memory): record Phase 0 PR #1 merge`
**Main tip:** `3abfb3d` — `Merge pull request #1 from Samuel-Muriuki/develop` (Phase 0 boundary)
**Last commit on feat branch:** `6cde660` — `🧪 test: smoke integration test for live Playwright (gated)`
**CI status (PR #2):** ✅ green — https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/runs/25666937201
**Open PRs:** [#2 — Phase 1: MVP keyword search](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/2)

---

## Recent Decisions

### 2026-05-11 — Phase 1 in review

- **Meta Ad Library localizes by GeoIP** — running from Kenya, the page renders entirely in Swahili (`Maktaba ya Matangazo` instead of "Ad Library"). The `getByText("Library ID:")` anchor never matches because the literal text doesn't exist. Confirmed: the HTML fixture at `tests/fixtures/html/keyword_search_shoes.html` contains 26 long numeric library IDs and ~50 visible ad cards (see `tests/fixtures/html/keyword_search_shoes.png`, gitignored). Cards render correctly; the parser just can't find them with English-only selectors. **Action for Phase 2/4:** either force English locale (set `Accept-Language: en-US` header + `?locale=en_US` query param) or build locale-agnostic selectors (e.g. anchor on `data-ad-preview-id` data attributes, or regex over visible numeric IDs).
- **`playwright-stealth` 1.x bumped to 2.x.** 1.x imports `pkg_resources` and crashes on Python 3.13 where setuptools is not pre-installed. 2.x exposes `Stealth().apply_stealth_async(page)`. PLANNING-BRIEF §3 names the dep without a version, so this is a pin-loosening, not a stack change.
- **`_looks_blocked` heuristic narrowed to "Log in" button only.** Original check `"facebook" not in title.lower()` false-positived on every wait-for-card timeout because the Ad Library title is "Ad Library" (or "Maktaba ya Matangazo"), not "Facebook".

### 2026-05-11 — Phase 0 closeout

- **PR merge strategy: always `--merge`, never squash.** For every PR (feature→develop, develop→main), use `gh pr merge <N> --merge` to preserve atomic gitmoji history and add a boundary marker commit. Established during the Phase 0 closeout PR — Samuel: "follow that going forward!!!". Also captured in shared notes at `~/.project/projects/.../memory/feedback_merge_strategy.md`.
- **Phase 0 closed via [PR #1](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/1).** 8 atomic commits, merged with `--merge` strategy → main at `3abfb3d`. Post-merge CI green on main.
- **Coverage gate deferred to Phase 6.** `--cov-fail-under=60` was removed from `pyproject.toml` `addopts` because the empty Phase 0 scaffold would have it fail unconditionally. BUILD-PLAN.md already schedules the coverage gate at Phase 6 ("expand unit coverage"), so this is a deferral, not a change of intent. Coverage reports themselves remain on.
- **Two smoke tests added at Phase 0.** `tests/unit/test_package.py` (asserts `__version__` is exposed) and `tests/integration/test_smoke.py` (asserts distribution metadata is present). Both exist primarily to keep pytest from returning exit-5 ("no tests collected") on the empty scaffold while still being real tests that catch packaging breakage. They'll stay as packaging guards even after Phase 1+ tests land.
- **`__version__` sourced from installed distribution.** `src/meta_ads_scraper/__init__.py` reads via `importlib.metadata.version("meta-ads-scraper")`, keeping `pyproject.toml` as the single source of truth.
- **Funding/sponsor surface added per `PROJECT-TEMPLATE` §4.3.** `.github/FUNDING.yml` (github + custom buymeacoffee), Buy Me a Coffee shield-badge anchored under H1 and as last line of README, `## 💖 Support` section before License, CI badge aligned to `?branch=main` form.

### 2026-05-11 — Project kickoff

- **Stack locked.** Python 3.11+, Playwright, Pydantic v2, Typer, tenacity, structlog. See `PLANNING-BRIEF.md` §3.
- **Path B (Playwright on public UI) is primary.** Path A (official API) is post-MVP enhancement. Rationale: official API doesn't cover commercial ads, which is what Hoski clients need.
- **No CAPTCHA solving.** If blocked, fail fast with clear error. Don't enter an arms race with Meta.
- **Repo name: `meta-ads-scraper`** — not `hoski-` prefixed. This is portfolio-ready, not single-purpose.
- **Submission window TBC.** Either before the Mon 9 PM Nairobi call or by EOD Mon Montreal.

---

## Known Blockers

(none)

---

## Followups Logged Not Filed

- After MVP works, add a stealth-mode toggle (--stealth on/off) for debugging
- Consider exposing Path A as a fallback for political ads in Phase 8+
- Add `--screenshot-on-error` flag to dump page state when scraping fails
- Investigate whether Meta exposes a GraphQL endpoint we could use instead of DOM scraping (Phase 8+)
- **Phase 2 prep:** decide `page_url` → `page_id` resolution mechanism (Graph API call via `httpx` vs. Playwright navigation to the page). BUILD-PLAN Phase 2 leaves this open ("whichever is simpler — document the choice").
- **CI maintenance:** GitHub deprecated Node.js 20 for actions. `actions/checkout@v4` and `actions/setup-python@v5` will be forced to Node.js 24 from 2026-06-02 and Node.js 20 removed 2026-09-16. Bump action versions or set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` before then.
- **Tooling tidy:** ruff warns `ANN101` / `ANN102` are deprecated rules. The `pyproject.toml` mypy override for `tenacity.*` is currently unused (Phase 4 retry policies will make it live).
- **`docs/contracts/ad-data-schema.md` claim about hashability is wrong.** `frozen=True` only auto-hashes when every field is hashable, and `Ad` has list fields. Fix the contract doc when revisiting it at Phase 6 (tests & coverage tightening).
- **`.project/patterns/pytest-patterns/README.md` line 191** still says `pyproject.toml enforces --cov-fail-under=60`. Phase 0 deferred that to Phase 6 — sweep this and any other stale claims when Phase 6 re-adds the gate.
- **Phase 2 — locale forcing.** First bug Phase 2 must fix: append `&locale=en_US` to the URL (or set `Accept-Language: en-US,en;q=0.9` on the BrowserContext) so the parser's English text anchors actually match. Without this, scraping from any non-English locale returns 0 ads.
- **Phase 2 — re-tune selectors using the HTML fixture.** `tests/fixtures/html/keyword_search_shoes.html` is the deterministic test bed. Open it in a browser or `bs4`/`lxml` and find the card-level wrapper, the ad-ID anchor, the page-name link, and the creative image — then encode those as `data-*` attribute selectors if Meta provides them, or as locale-agnostic structural traversals otherwise.

---

## Phase Completion Log

| Phase | Started | Completed | PR | Notes |
|---|---|---|---|---|
| 0 — Bootstrap | 2026-05-11 | 2026-05-11T09:48Z | [#1](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/1) | Coverage gate deferred to Phase 6; two smoke tests cleared pytest exit-5 on empty scaffold; funding/sponsor surface added per template §4.3. Merged develop→main via `--merge` strategy at main SHA `3abfb3d`. |
| 1 — MVP Keyword | 2026-05-11 | (in review) | [#2](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/2) | 8 atomic commits on `feat/phase-1-mvp-keyword`. Live smoke against real Meta returned 0 ads — page rendered in Swahili (geo-locale to Kenya), English `"Library ID:"` text anchor never matched. HTML fixture captured to `tests/fixtures/html/keyword_search_shoes.html` for Phase 2 selector reconnaissance. PR CI green. |
| 2 — Three Search Paths | — | — | — | — |
| 3 — Pagination | — | — | — | — |
| 4 — Resilience | — | — | — | — |
| 5 — CLI Polish & Resume | — | — | — | — |
| 6 — Tests & CI | — | — | — | — |
| 7 — APPROACH & Demo | — | — | — | — |

---

## Active Worktree State

- Branch: `feat/phase-1-mvp-keyword`
- Uncommitted edits: (none — about to commit this MEMORY update + HTML fixture + capture script)
- Stash: (none)

---

**END OF JOURNAL**
