# Meta Ads Scraper

<a href="https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/workflows/ci.yml"><img src="https://github.com/Samuel-Muriuki/meta-ads-scraper/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status" /></a>
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python command-line scraper for Meta's Ad Library. Takes a keyword, a
Facebook page slug, or a Facebook page URL; returns structured ad
records as JSON or CSV. Built on Playwright with stealth, structlog
JSON output, tenacity retries, an asyncio rate limiter, and a SQLite
checkpoint so interrupted runs can resume from where they stopped.

## What it does

Given one of three inputs, the scraper opens a stealthed Chromium
session against `https://www.facebook.com/ads/library/`, paginates
through the infinite-scroll DOM, parses each ad card into a Pydantic
model, and writes the result to a file or stdout. Each ad carries its
`ad_library_id`, `page_id`, page metadata, creative text, image URLs,
start/end dates, and platform/country fields when Meta exposes them.

The scraper is designed for short, polite runs from a single machine —
target a vertical or competitor, pull tens to a few hundred ads, hand
the file off to the next step (analysis, CRM, an LLM, whatever). It is
not designed for sustained scraping at industrial scale. Default
spacing is one request per second; the hard concurrency ceiling is
three.

A SQLite checkpoint records every ad as it streams in. If a run is
interrupted — Ctrl+C, browser crash, or Meta serving a transient error
through every retry — the next `resume <run-id>` continues with the
already-scraped ads de-duplicated.

## Quick start

Clone the repo:

```bash
git clone https://github.com/Samuel-Muriuki/meta-ads-scraper.git
cd meta-ads-scraper
```

### macOS / Linux

```bash
bash bootstrap.sh        # interactive — prompts for git author on first run
source .venv/bin/activate
```

The bootstrap script creates a virtualenv, installs all dependencies,
installs Playwright's Chromium browser, and verifies the setup. It
prompts for your git author name and email on first run if they are
not already configured for the repository.

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
playwright install chromium
```

The `bootstrap.sh` script is not Windows-compatible (bash + LF-only).
The four commands above produce the same end state.

### First run

```bash
python -m meta_ads_scraper search --keyword "running shoes" --max-results 10
```

Output goes to stdout by default. To write to a file:

```bash
python -m meta_ads_scraper search --keyword "running shoes" \
    --max-results 10 --out shoes.json
```

The file lands at `outputs/shoes.json` — bare filenames are auto-prefixed
with `outputs/`, which is created automatically and gitignored. Pass a
full path (`--out /tmp/x.json` or `--out data/x.json`) to override.

The first run takes ~30 seconds for a keyword search, ~60 seconds for a
page-slug search (one extra navigation to resolve the slug to a
page_id). Logs go to stderr; the JSON or CSV payload goes to stdout
when `--out` is omitted. The `run-id` printed to stderr is a
32-character hex string (uuid4 with dashes stripped); it's the handle
for `resume <run-id>` later.

### Demo runs

The `examples/` folder ships with real output from a controlled set
of live runs against Meta's Ad Library — three vertical demos
(jewelry, dental, automotive) plus a 500-ad sustained-load
demonstration. Read `examples/README.md` for the exact commands,
durations, and run-ids. Use those files to see what the schema looks
like populated without spending your own rate-limit budget. New runs
that you launch yourself default to writing under `outputs/` (see
[First run](#first-run)).

## Commands

```
meta-ads-scraper search [options]     # start a fresh scrape
meta-ads-scraper resume <run-id>      # continue an interrupted scrape
meta-ads-scraper runs                 # list recent runs
```

### `search` options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--keyword`, `-k` | str | — | Free-text keyword search |
| `--page-url` | str | — | Facebook page URL (`https://www.facebook.com/Nike`) |
| `--page-slug` | str | — | Facebook page slug (`Nike`) |
| `--format` | `json` \| `csv` | `json` | Output format |
| `--out` | path | stdout | Output file path |
| `--max-results` | int | unlimited (1000 ceiling) | Cap on ads returned |
| `--timeout` | int | 300 | Wall-clock budget in seconds |
| `--rate-limit` | float | 1.0 | Requests per second (range 0.1–10.0) |
| `--concurrency` | int | 1 | Max in-flight scroll iterations (ceiling 3) |
| `--no-progress` | flag | off | Suppress the progress bar |
| `-v`, `-vv` | count | 0 | `-v`=INFO, `-vv`=DEBUG with pretty console |

Exactly one of `--keyword`, `--page-url`, `--page-slug` is required.

### `resume <run-id>` options

Loads the original `SearchSpec` from the checkpoint and continues the
scrape, skipping ads already recorded. Accepts the same I/O and pacing
flags as `search`. The output file contains **new ads only**; merge
with the original output yourself if you need a combined file.

### `runs` options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--limit` | int | 20 | Number of recent runs to show |

Prints a Rich table to stderr with Run ID, Mode, Query, Started,
Status, and Ads.

### Worked examples

```bash
# Keyword search, write CSV (lands at outputs/dental.csv)
python -m meta_ads_scraper search --keyword "dental practices" \
    --max-results 50 --format csv --out dental.csv

# Page slug, JSON to a file (lands at outputs/nike.json)
python -m meta_ads_scraper search --page-slug Nike --format json \
    --out nike.json
```

`jq` is a popular JSON-processing tool installed separately via your
system package manager (`brew install jq` on macOS, `sudo apt install
jq` on Ubuntu/Debian, `choco install jq` on Windows, or download from
<https://stedolan.github.io/jq/>). If it is installed, you can pipe
the scraper's JSON output straight into it:

```bash
# Page URL, stream JSON through jq
python -m meta_ads_scraper search \
    --page-url https://www.facebook.com/Nike | jq '.[].ad_library_id'
```

If `jq` is not installed, a Python one-liner does the same job:

```bash
python -m meta_ads_scraper search --page-url https://www.facebook.com/Nike \
  | python -c "import json,sys; print('\n'.join(a['ad_library_id'] for a in json.load(sys.stdin)))"
```

## Architecture

Three Pydantic models gate the data flow: `SearchSpec` (the three input
modes plus country/ad_type/active_status filters), `Ad` (the schema
defined in `docs/contracts/ad-data-schema.md`), and a small
`RunSummary` for the runs listing. A `BaseScraper` abstract class is
the seam between the CLI and the backend; today `PlaywrightScraper` is
the only implementation. The deep-dive docs in `docs/architecture/`
cover each subsystem.

```
src/meta_ads_scraper/
├── cli.py                       # Typer entrypoint (search / resume / runs)
├── checkpoint.py                # SQLite-backed run + ad store
├── constants.py                 # AD_CARD_SELECTOR / AD_CARD_BOUNDARY_XPATH
├── exceptions.py                # MetaAdsScraperError hierarchy
├── logging_config.py            # structlog + stdlib bridge
├── models.py                    # Ad, SearchSpec
├── pagination.py                # scroll_and_collect async generator
├── parsers/ad_card.py           # DOM locator -> Ad
├── rate_limit.py                # asyncio.Semaphore-based limiter
├── retry.py                     # tenacity policies (@retry_network / _rate_limited / _dom)
├── scraper/
│   ├── base.py                  # BaseScraper abstract
│   └── playwright_scraper.py    # Path B (public UI via Playwright)
├── url_resolver.py              # SearchSpec -> Meta URL
└── exporters/
    ├── csv_exporter.py
    └── json_exporter.py
```

## Configuration

| Knob | How to set | Default | Notes |
|---|---|---|---|
| Rate limit | `--rate-limit 0.5` | 1.0 req/sec | Honest pacing. Sustained > 5 req/sec eventually trips Meta's rate limits. |
| Concurrency | `--concurrency 2` | 1 | Hard-clamped to 3. Single-coroutine is the supported case; higher values queue rather than parallelise. |
| Headless | `PLAYWRIGHT_HEADLESS=0` env | `1` (headless) | Set to `0` to watch the browser during development. |
| Verbosity | `-v` / `-vv` | 0 (WARNING) | `-v` → INFO JSON, `-vv` → DEBUG pretty console. |
| Checkpoint DB | (not configurable) | `data/runs.sqlite` | `data/` is gitignored. Delete the file to clear history. |
| Output folder | `--out <filename>` | `outputs/<filename>` | Bare filenames auto-prefix with `outputs/`. Full paths (`--out /tmp/x.json`) override. `outputs/` is gitignored. |

### Optional system tools

These are not required to run the scraper but can be useful for
post-processing output:

- **`jq`** — JSON query/transformation tool. Install via your system
  package manager (`brew install jq` / `apt install jq` /
  `choco install jq`). All `jq` examples in this README can be
  replaced with Python one-liners if not installed.

### Locale forcing

Meta's Ad Library localises by GeoIP. From outside the US/EU the page
renders in a non-English locale and the English text anchors fail
silently. The scraper forces `en_US` on every request via three
layers: `BrowserContext.locale="en-US"`, an `Accept-Language: en-US`
header, and a `&locale=en_US` URL parameter. Resolved URLs in the
`source_url` field carry the parameter so the source is reproducible.

## Output formats

### JSON

One JSON array, indented, ISO 8601 datetimes:

```json
[
  {
    "ad_library_id": "933016365009192",
    "page_id": "15087023444",
    "collected_at": "2026-05-12T10:18:47.733923Z",
    "source_url": "https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=15087023444&locale=en_US",
    "page_name": "Nike",
    "page_url": "https://web.facebook.com/nike/",
    "ad_creative_text": "Mar 1, 2024 - Jun 1, 2025\nNike\nSponsored\nA shoe is forever ...",
    "ad_creative_image_urls": ["https://scontent.fmba5-1.fna.fbcdn.net/..."],
    "start_date": "2024-03-01",
    "end_date": "2025-06-01",
    "is_active": null
  }
]
```

See `examples/keyword_shoes.json` for a real ten-row sample.

### CSV

UTF-8 with BOM (so Excel opens it correctly). List fields are joined
with semicolons. Header row, then one ad per row:

```csv
ad_library_id,page_id,collected_at,source_url,page_name,page_url, ...
933016365009192,15087023444,2026-05-12T10:18:47.733923Z,https://...,Nike,https://web.facebook.com/nike/,...
```

See `examples/page_slug_nike.csv` for a real ten-row sample.

## Resume from interruption

Every `search` creates a checkpoint entry. The `run-id` is printed to
stderr at the top of the run. If a scrape is interrupted, find the id
via `runs` and continue with `resume`:

```bash
# Start a long run
python -m meta_ads_scraper search --keyword "dental" --max-results 500 --out dental.json
# run-id: 7c4a2e5f0a8b4d83b6c1b40d7e1a2c3d
# ... Ctrl+C around ad 120 ...

# Look up the run
python -m meta_ads_scraper runs
#   Run ID                            Mode      Query    Started           Status        Ads
#   7c4a2e5f0a8b4d83b6c1b40d7e1a2c3d  keyword   dental   2026-05-12 10:18  aborted       120

# Continue — writes new ads only
python -m meta_ads_scraper resume 7c4a2e5f0a8b4d83b6c1b40d7e1a2c3d --out dental-rest.json
```

The original spec is rehydrated from the checkpoint, so the resume run
uses the same keyword, country, and filters. Ads already recorded
(by `ad_library_id`) are skipped at the pagination level.

## Known limitations

- **No CAPTCHA solving.** If Meta serves a login wall, the scraper
  raises `ScraperBlockedError` and exits non-zero. Re-running later
  from a different IP usually clears it.
- **DOM-coupled.** The card-boundary selector
  (`text=/Library ID:\s*\d+/ >> xpath=ancestor::div[.//img][1]`) is
  the result of empirical work against Meta's current React DOM. If
  Meta restructures, the offline parser test against
  `tests/fixtures/html/keyword_search_shoes.html` will flag the
  regression and a re-capture cycle is needed.
- **Polite-stealth, not adversarial.** Stealth fingerprint hides
  obvious headless tells; there is no proxy rotation, no header
  forgery beyond what `playwright-stealth` does, no CAPTCHA workaround.
- **Sustained load is untested.** The 1000-ad ceiling is hardcoded in
  `pagination.py` but has not been run end-to-end at that volume. The
  rate limiter exists so we can finally try it safely.
- **`ad_creative_text` contains Meta's layout artifacts** (zero-width
  spaces, `Active`/`Sponsored` markers, platform headers). A
  post-processor in `parsers/ad_card.py` is logged as deferred polish
  in `.project/journal/JOURNAL.md`.

## Development

```bash
bash bootstrap.sh          # one-shot setup
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

ruff check src/ tests/     # lint
ruff format src/ tests/    # format
mypy src/                  # strict type check
pytest -m "not live_test"  # unit + offline integration tests
```

Live tests against real Meta are gated behind `META_LIVE_TESTS=1` and
the `workflow_dispatch` CI trigger, so CI does not burn rate-limit
budget on every push. Run them locally with:

```bash
META_LIVE_TESTS=1 pytest -m live_test
```

Project conventions live in `.project/ENGINEERING-MANUAL.md`:
gitmoji commit format with mandatory scopes, atomic commits, solo
authorship, the hard rules around `print()`, secret leakage, and
local working files. The phase-by-phase build sequence is in
`BUILD-PLAN.md`.

## License

MIT — see `LICENSE`.

## Author

**Samuel Muriuki**, Nairobi, Kenya.
[GitHub](https://github.com/Samuel-Muriuki) · [LinkedIn](https://www.linkedin.com/in/El-Samm) · [Portfolio](https://samuel-muriuki.vercel.app/)
