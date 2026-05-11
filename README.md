# Meta Ads Scraper

> A Python scraper for Meta's Ad Library — search by keyword, Facebook page URL, or page slug. Returns structured ad data as CSV or JSON.

[![CI](https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/workflows/ci.yml)

---

> 🚧 **This README is the placeholder.** The production README is generated in Phase 5 of `BUILD-PLAN.md`. For now, read `PLANNING-BRIEF.md` for architecture decisions and `BUILD-PLAN.md` for the build sequence.

## Quick start (after Phase 0)

```bash
# Clone
git clone https://github.com/Samuel-Muriuki/meta-ads-scraper.git
cd meta-ads-scraper

# Bootstrap
bash bootstrap.sh

# Activate the virtualenv
source .venv/bin/activate

# Verify
pytest --no-cov -q
ruff check src/ tests/
```

## Repository structure

| Path | Purpose |
|---|---|
| `PLANNING-BRIEF.md` | Architectural decisions — read first |
| `BUILD-PLAN.md` | Phase-by-phase build prompts for  |
| `.project/ENGINEERING-MANUAL.md` |  operating manual |
| `.project/journal/JOURNAL.md` | Current phase state |
| `docs/architecture/` | Subsystem deep-dive docs |
| `docs/contracts/ad-data-schema.md` | The Ad model contract |
| `src/meta_ads_scraper/` | The package |
| `tests/` | Unit + integration tests |
| `examples/` | Sample output files |

## License

MIT
