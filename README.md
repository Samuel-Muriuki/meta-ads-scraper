# Meta Ads Scraper

<a href="https://www.buymeacoffee.com/elsamm"><img src="https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee" /></a>

> A Python command-line scraper for Meta's Ad Library. Search by keyword, Facebook page URL, or page slug. Returns structured ad data as CSV or JSON.

<a href="https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/workflows/ci.yml"><img src="https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status" /></a>
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

> 🚧 **This README is a placeholder.** The production README is generated during Phase 5 of `BUILD-PLAN.md`. While the build is in progress, read `PLANNING-BRIEF.md` for architectural decisions and `BUILD-PLAN.md` for the phase-by-phase build sequence.

## What this does

Given one of:
- A keyword (e.g., `"luxury watches"`)
- A Facebook page URL (e.g., `https://www.facebook.com/Nike`)
- A Facebook page slug (e.g., `Nike`)

It returns structured ad records from Meta's public Ad Library and writes them to CSV or JSON.

## What this doesn't do

- Solve CAPTCHAs (fails fast with a clear error)
- Bypass login walls
- Rotate proxies
- Scrape anything other than ads

## Quick start

```bash
# Clone
git clone https://github.com/Samuel-Muriuki/meta-ads-scraper.git
cd meta-ads-scraper

# Bootstrap (one-time)
bash bootstrap.sh

# Activate the virtualenv
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Verify the install
ruff check src/ tests/
pytest --no-cov -q
```

## Planned usage (post-build)

```bash
# Search by keyword
python -m meta_ads_scraper search --keyword "dental practices" --max-results 50 --format csv --out dental.csv

# Search by page slug
python -m meta_ads_scraper search --page-slug Nike --format json --out nike.json

# Search by page URL
python -m meta_ads_scraper search --page-url https://www.facebook.com/Nike --max-results 100

# Resume an interrupted run
python -m meta_ads_scraper resume <run-id>
```

## Repository structure

| Path | Purpose |
|---|---|
| `PLANNING-BRIEF.md` | Architectural decisions — **read first** |
| `BUILD-PLAN.md` | Phase-by-phase build prompts for  |
| `.project/ENGINEERING-MANUAL.md` |  operating manual |
| `.project/journal/JOURNAL.md` | Current build phase state and recent decisions |
| `.project/patterns/` | Reusable patterns for  (Playwright, Pydantic, pytest) |
| `docs/architecture/` | Subsystem deep-dive documentation (11 docs) |
| `docs/contracts/ad-data-schema.md` | The `Ad` Pydantic model contract — the data schema |
| `docs/conventions/` | Code style, commit format, testing discipline |
| `.github/workflows/ci.yml` | CI pipeline (lint, type-check, unit, integration replay) |
| `src/meta_ads_scraper/` | The Python package |
| `tests/` | Unit + integration tests |
| `examples/` | Real-world sample output files (CSV + JSON) |
| `bootstrap.sh` | One-shot project setup script |

## Why `docs/` and `.project/` are committed

These folders hold the architectural documentation and engineering context that make this project understandable to future contributors and reviewable by anyone reading the repo. They are deliberately public:

- `docs/` — Human-readable architecture, conventions, and contracts. Read these to understand *why* the code is structured the way it is.
- `.project/` — Operating context for internal tooling. Includes coding conventions, current phase state, and reusable skill modules.

Both folders are intentional repo artefacts, not local-only config.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Browser automation | Playwright |
| Data validation | Pydantic v2 |
| CLI framework | Typer |
| Retries | tenacity |
| Logging | structlog |
| HTTP client | httpx |
| Testing | pytest + playwright-pytest |
| Linting | ruff |
| Type checking | mypy (strict) |
| Checkpointing | SQLite (stdlib) |

See `PLANNING-BRIEF.md` §3 for the full rationale.

## Development workflow

This project follows a phase-gated build pattern. Each phase is a discrete focused implementation session with a specific prompt from `BUILD-PLAN.md`. Phases are not combined; each ships as its own pull request from `develop` to `main`.

Commits follow [gitmoji](https://gitmoji.dev/) conventions with mandatory scopes — see `docs/conventions/COMMIT-FORMAT.md`.

## Contributing

This is a job application deliverable, not an open-source project accepting contributions. Issues and pull requests will be closed.

## 💖 Support

If you find this project useful, please consider:

- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting new features
- ☕ [Buying me a coffee](https://www.buymeacoffee.com/elsamm)

## License

MIT — see `LICENSE` (TBD).

## Author

**Samuel Muriuki**
Nairobi, Kenya
[GitHub](https://github.com/Samuel-Muriuki) · [LinkedIn](https://www.linkedin.com/in/El-Samm) · [Portfolio](https://samuel-muriuki.vercel.app/)

<a href="https://www.buymeacoffee.com/elsamm"><img src="https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee" /></a>