# Engineering Manual

> **READ THIS FIRST.** This is the master operating manual for the project. It is the contract.

---

## 1. Project Identity

- **Name:** Meta Ads Scraper
- **Purpose:** A Python scraper for Meta's Ad Library (https://www.facebook.com/ads/library/) supporting search by keyword, Facebook page URL, or page slug.
- **Why it exists:** Job application deliverable for Hoski's Python Developer role.
- **Owner:** Samuel Muriuki (`sammkimberly@gmail.com`)
- **Stakes:** This is being evaluated for a job. Code quality is graded.

---

## 2. Authoritative Documents (read order)

When starting work on the project, read these in order:

1. **`PLANNING-BRIEF.md`** — architectural decisions, the source of truth for *why*
2. **`.project/ENGINEERING-MANUAL.md`** — this file
3. **`.project/journal/JOURNAL.md`** — current phase, recent decisions, known blockers
4. **`BUILD-PLAN.md`** — the phase currently in flight
5. **`docs/architecture/`** — deep-dive docs for the specific subsystem you're touching
6. **`docs/contracts/`** — data model contracts

If anything in this repo conflicts with `PLANNING-BRIEF.md`, `PLANNING-BRIEF.md` wins. If you need to deviate, update `PLANNING-BRIEF.md` first and explain why in the commit message.

---

## 3. Git Discipline — Non-Negotiable

### 3.1 Author identity
```bash
git config user.name "Samuel Muriuki"
git config user.email "sammkimberly@gmail.com"
```
Set on every fresh clone. `bootstrap.sh` handles this.

### 3.2 Author identity

All commits in this repository are authored solely by Samuel Muriuki
<sammkimberly@gmail.com>. Do not add Co-Authored-By trailers, alternate
attributions, or third-party identities to commit messages, PR titles,
or PR descriptions. Solo authorship is the project's standard and is
non-negotiable.

### 3.3 Gitmoji commit format
```
<emoji> <type>(<scope>): <short description>
```

| Emoji | Type | Use |
|---|---|---|
| ✨ | feat | New feature |
| 🐛 | fix | Bug fix |
| 📝 | docs | Documentation only |
| ♻️ | refactor | Code restructure, no behaviour change |
| ⚡️ | perf | Performance improvement |
| 🧪 | test | Adding or fixing tests |
| 🔧 | build | Build system, deps |
| 👷 | ci | CI/CD configuration |
| 🔨 | chore | Tooling, scripts, config |
| 🔒️ | security | Security fix |
| 🚀 | deploy | Deployment config |
| 🎨 | ui | UI/CLI presentation change |
| 🔥 | remove | Deleting code or files |
| 🎉 | init | Initial setup |

**Scopes (use these consistently):**
`repo`, `models`, `url`, `scraper`, `parser`, `cli`, `exporters`, `pagination`, `retry`, `rate-limit`, `logging`, `checkpoint`, `tests`, `ci`, `readme`, `approach`, `examples`.

### 3.4 Atomic commits
- ONE logical change per commit
- Commit body explains WHY, not WHAT (the diff shows what)
- If you're tempted to use "and" in a commit subject, it should be two commits

### 3.5 Branching
- `main` — protected, only PR merges
- `develop` — integration branch, all phases land here first
- Feature branches off `develop`: `feat/<scope>-<short-name>`
- PR from feature → develop, then develop → main at phase boundaries

---

## 4. Code Standards

### 4.1 Python conventions
- Python 3.11+ syntax (use match/case, PEP 695 type params where they fit)
- `from __future__ import annotations` at the top of every module
- Type hints on every public function and class
- Pydantic v2 for any data structure that crosses a module boundary
- No `print()` — use `structlog` logger
- No bare `except:` — always except specific types
- No `Any` unless absolutely forced (and comment why)

### 4.2 Async-first
- The scraper is async. All I/O is awaited.
- Use `async def` and `await`, not `asyncio.run()` inside library code
- CLI entrypoint wraps with `asyncio.run()` once

### 4.3 Errors
- Define custom exceptions in `src/meta_ads_scraper/exceptions.py`:
  - `MetaAdsScraperError` (base)
  - `ScraperBlockedError` (CAPTCHA, login wall)
  - `ParseError` (DOM didn't match expectations)
  - `RateLimitedError` (429)
- Catch broad → re-raise narrow with context. Never silently swallow.

### 4.4 Linting & typing
- `ruff check src/ tests/` — must pass before any commit
- `ruff format src/ tests/` — must pass before any commit
- `mypy src/` — strict mode, must pass

### 4.5 Imports
- stdlib first, third-party second, first-party last
- `ruff` handles ordering automatically

---

## 5. Test Discipline

### 5.1 Test categories
- **Unit tests** (`tests/unit/`) — fast, no I/O, run on every push
- **Integration replay** (`tests/integration/test_replay.py`) — uses HAR fixtures, deterministic, runs on every push
- **Live smoke** (`tests/integration/test_*_live.py`) — hits real Meta, gated by `META_LIVE_TESTS=1`, manual only

### 5.2 What to test (in priority order)
1. Pydantic models — validation, nullable handling, serialization
2. URL resolver — every search mode produces the expected URL
3. Parser — DOM fixture → Ad model
4. Exporters — Ad list → CSV/JSON
5. Pagination logic — stop conditions
6. Retry decorators — failure modes
7. CLI — argument parsing, mutual exclusion, exit codes
8. End-to-end — replay HAR fixture through the whole pipeline

### 5.3 Test markers
```python
@pytest.mark.live_test  # skipped unless META_LIVE_TESTS=1
@pytest.mark.slow       # skipped unless --runslow
```

---

## 6. File Organization

```
meta-ads-scraper/
├── docs/                         # Architecture and convention docs
│   ├── conventions/              # How we write code
│   ├── architecture/             # Subsystem deep dives
│   └── contracts/                # Data model contracts
├── .project/                     # Project ops manual + journal
│   ├── ENGINEERING-MANUAL.md     # This file
│   ├── journal/JOURNAL.md        # Current phase + recent decisions
│   └── patterns/                 # Reusable code patterns
├── .github/
│   └── workflows/ci.yml          # CI pipeline
├── src/
│   └── meta_ads_scraper/         # The package
│       ├── __init__.py
│       ├── __main__.py           # python -m meta_ads_scraper
│       ├── cli.py                # Typer CLI
│       ├── config.py             # Settings via pydantic-settings
│       ├── exceptions.py         # Custom exception hierarchy
│       ├── logging_config.py     # structlog setup
│       ├── models.py             # Ad, SearchSpec
│       ├── url_resolver.py       # SearchSpec → URL
│       ├── checkpoint.py         # SQLite resume store
│       ├── retry.py              # tenacity policies
│       ├── rate_limit.py         # Token bucket
│       ├── pagination.py         # Scroll-and-collect
│       ├── scraper/
│       │   ├── __init__.py
│       │   ├── base.py           # BaseScraper abstract
│       │   ├── playwright_scraper.py
│       │   └── api_scraper.py    # Stub, future Path A
│       ├── parsers/
│       │   ├── __init__.py
│       │   └── ad_card.py        # DOM → Ad
│       └── exporters/
│           ├── __init__.py
│           ├── csv_exporter.py
│           └── json_exporter.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/                 # HAR files, sample HTML
├── data/                         # gitignored runtime outputs
├── examples/                     # committed sample outputs
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── BUILD-PLAN.md                 # Phase-by-phase build prompts
├── PLANNING-BRIEF.md             # Architectural decisions
├── APPROACH.md                   # Antonio's submission deliverable
└── bootstrap.sh
```

---

## 7. Hard Rules — Don't Break These

1. **Never commit `.env` or anything in `data/`**
2. **Never commit Playwright auth state files** — they contain session cookies
3. **Never solve CAPTCHAs** — fail fast with `ScraperBlockedError`
4. **Never bypass rate limiting in production code** — only in tests with mocks
5. **Never use `print()`** — use the structlog logger
6. **Never log raw cookies or session tokens**
7. **Never push to main directly** — always via PR
8. **Never combine phases** — one phase per PR
9. **Never skip the `bootstrap.sh` verification on a fresh clone**
10. **Never commit local working files, personal notes, or scratch artifacts.** These live in `.ai/` (gitignored) or external notes. The repo contains only production artifacts: code, tests, architecture docs, conventions, and changelog entries.

---

## 8. When You're Stuck

- Read the relevant `docs/architecture/` file end-to-end
- Read `PLANNING-BRIEF.md` again
- Stop and think rather than guessing and shipping
- Document the decision in `.project/journal/JOURNAL.md` once resolved

---

## 9. Done Means Done

A phase is not "done" until:
- [ ] All code compiles + type-checks
- [ ] All tests pass locally
- [ ] CI is green on the feature branch
- [ ] README updated if user-facing behaviour changed
- [ ] CHANGELOG entry added under "Unreleased"
- [ ] JOURNAL.md updated with phase completion state
- [ ] PR opened with a description that maps to the BUILD-PLAN phase

---

**END OF MANUAL**
