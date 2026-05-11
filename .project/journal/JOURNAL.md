# Engineering Journal

> Single source of truth for the project's current state. Update this every session. Read this on every session start.

---

## Current Phase

**Phase 0 — Bootstrap** (not yet started)

**Develop tip:** (none yet)
**Last commit:** (none yet)
**CI status:** (no workflow runs yet)
**Open PRs:** (none)

---

## Recent Decisions

### 2026-05-11 — Project kickoff

- **Stack locked.** Python 3.11+, Playwright, Pydantic v2, Typer, tenacity, structlog. See `PLANNING-BRIEF.md` §3.
- **Path B (Playwright on public UI) is primary.** Path A (official API) is post-MVP enhancement. Rationale: official API doesn't cover commercial ads, which is what Hoski clients need.
- **No CAPTCHA solving.** If blocked, fail fast with clear error. Don't enter an arms race with Meta.
- **Repo name: `meta-ads-scraper`** — not `hoski-` prefixed. This is portfolio-ready, not single-purpose.
- **Submission window TBC.** Either before the Mon 9 PM Nairobi call or by EOD Mon Montreal.

---

## Known Blockers

(none yet)

---

## Followups Logged Not Filed

- After MVP works, add a stealth-mode toggle (--stealth on/off) for debugging
- Consider exposing Path A as a fallback for political ads in Phase 8+
- Add `--screenshot-on-error` flag to dump page state when scraping fails
- Investigate whether Meta exposes a GraphQL endpoint we could use instead of DOM scraping (Phase 8+)

---

## Phase Completion Log

| Phase | Started | Completed | PR | Notes |
|---|---|---|---|---|
| 0 — Bootstrap | — | — | — | — |
| 1 — MVP Keyword | — | — | — | — |
| 2 — Three Search Paths | — | — | — | — |
| 3 — Pagination | — | — | — | — |
| 4 — Resilience | — | — | — | — |
| 5 — CLI Polish & Resume | — | — | — | — |
| 6 — Tests & CI | — | — | — | — |
| 7 — APPROACH & Demo | — | — | — | — |

---

## Active Worktree State

- Branch: (none yet)
- Uncommitted edits: (none)
- Stash: (none)

---

**END OF JOURNAL**
