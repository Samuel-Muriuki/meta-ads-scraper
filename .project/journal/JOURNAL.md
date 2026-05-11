# Engineering Journal

> Single source of truth for the project's current state. Update this every session. Read this on every session start.

---

## Current Phase

**Phase 1 — MVP Single Keyword Search** (not yet started)

**Develop tip:** `9e1f511` — `🧪 test: integration smoke for package distribution`
**Last commit:** 2026-05-11 — Phase 0 closeout
**CI status:** ✅ green — https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/runs/25661199881
**Open PRs:** (none)

---

## Recent Decisions

### 2026-05-11 — Phase 0 closeout

- **Coverage gate deferred to Phase 6.** `--cov-fail-under=60` was removed from `pyproject.toml` `addopts` because the empty Phase 0 scaffold would have it fail unconditionally. BUILD-PLAN.md already schedules the coverage gate at Phase 6 ("expand unit coverage"), so this is a deferral, not a change of intent. Coverage reports themselves remain on.
- **Two smoke tests added at Phase 0.** `tests/unit/test_package.py` (asserts `__version__` is exposed) and `tests/integration/test_smoke.py` (asserts distribution metadata is present). Both exist primarily to keep pytest from returning exit-5 ("no tests collected") on the empty scaffold while still being real tests that catch packaging breakage. They'll stay as packaging guards even after Phase 1+ tests land.
- **`__version__` sourced from installed distribution.** `src/meta_ads_scraper/__init__.py` reads via `importlib.metadata.version("meta-ads-scraper")`, keeping `pyproject.toml` as the single source of truth.

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
- **Tooling tidy:** ruff warns `ANN101` / `ANN102` are deprecated rules; the `pyproject.toml` mypy override for `playwright.*` / `playwright_stealth.*` / `tenacity.*` is currently unused. Clean both up when those modules are first imported (Phase 1).

---

## Phase Completion Log

| Phase | Started | Completed | PR | Notes |
|---|---|---|---|---|
| 0 — Bootstrap | 2026-05-11 | 2026-05-11T09:15Z | n/a (direct on develop) | Coverage gate deferred to Phase 6; two smoke tests added to clear pytest exit-5 on empty scaffold. CI green at SHA `9e1f511`. |
| 1 — MVP Keyword | — | — | — | — |
| 2 — Three Search Paths | — | — | — | — |
| 3 — Pagination | — | — | — | — |
| 4 — Resilience | — | — | — | — |
| 5 — CLI Polish & Resume | — | — | — | — |
| 6 — Tests & CI | — | — | — | — |
| 7 — APPROACH & Demo | — | — | — | — |

---

## Active Worktree State

- Branch: `develop`
- Uncommitted edits: (none — about to commit this MEMORY update)
- Stash: (none)

---

**END OF JOURNAL**
