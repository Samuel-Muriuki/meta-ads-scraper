# Engineering Journal

> Single source of truth for the project's current state. Update this every session. Read this on every session start.

---

## Current Phase

**Phase 1 — MVP Single Keyword Search** (not yet started)

**Develop tip:** `620cc07` — `📝 docs(readme): align CI badge with PROJECT-TEMPLATE format (branch=main)`
**Main tip:** `3abfb3d` — `Merge pull request #1 from Samuel-Muriuki/develop` (Phase 0 boundary)
**Last commit:** 2026-05-11 — Phase 0 closeout merged via [PR #1](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/1)
**CI status:** ✅ green on both branches
  - main: https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/runs/25662863044
  - develop: https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/runs/25661828608
**Open PRs:** (none)

---

## Recent Decisions

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
- **Tooling tidy:** ruff warns `ANN101` / `ANN102` are deprecated rules; the `pyproject.toml` mypy override for `playwright.*` / `playwright_stealth.*` / `tenacity.*` is currently unused. Clean both up when those modules are first imported (Phase 1).

---

## Phase Completion Log

| Phase | Started | Completed | PR | Notes |
|---|---|---|---|---|
| 0 — Bootstrap | 2026-05-11 | 2026-05-11T09:48Z | [#1](https://github.com/Samuel-Muriuki/meta-ads-scraper/pull/1) | Coverage gate deferred to Phase 6; two smoke tests cleared pytest exit-5 on empty scaffold; funding/sponsor surface added per template §4.3. Merged develop→main via `--merge` strategy at main SHA `3abfb3d`. |
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
