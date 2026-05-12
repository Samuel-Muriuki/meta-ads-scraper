# APPROACH — Meta Ad Library Scraper

## Problem statement

Hoski needs a way to pull structured ad data from Meta's public Ad
Library so analysts can run competitive-intelligence sweeps on a
client's vertical without scrolling the UI by hand. The catch: Meta's
official Graph API covers political and social-issue ads only — the
commercial inventory clients actually compete in is exposed solely
through the public web UI at `facebook.com/ads/library/`. There is no
sanctioned machine-readable path.

## Solution overview

Two paths were on the table. Path A — the official `ads_archive` API —
is clean, supported, and rate-limited to a polite default. It is also
useless for this brief because it does not return the commercial ads
Hoski cares about, and approval gating for full political-ad access in
Kenya is not available. Path B — Playwright-driven scraping of the
public UI — exposes the full inventory at the cost of carrying the
brittleness of a React DOM that can change between Tuesdays.

Path B was chosen and built. To keep the choice from being a dead end,
`scraper/base.py` defines an abstract `BaseScraper` so a future
`ApiScraper` (Path A) can drop in without touching the CLI, exporters,
or downstream code. Anti-detection posture is deliberately
polite-not-adversarial: `playwright-stealth` hides the obvious headless
fingerprints, the rate limiter caps sustained traffic at one request
per second, and a `ScraperBlockedError` fail-fast covers the
login-wall case. No CAPTCHA solving, no proxy rotation.

## Architecture

Three Pydantic v2 models gate the data flow — `SearchSpec` (the three
input modes plus filter fields), `Ad` (the canonical schema in
`docs/contracts/ad-data-schema.md`), and a frozen `RunSummary` for the
runs listing. The CLI parses one `SearchSpec`, hands it to a
`PlaywrightScraper` opened as an async context manager, and streams
the resulting `Ad` instances through either the CSV or JSON exporter.
A SQLite `CheckpointStore` records each yielded ad before the caller
sees it so an interrupted run is resumable.

The README's module map covers the file layout; deeper subsystem docs
live under `docs/architecture/` (11 deep-dives covering scraping
strategy, pagination, retry policy, CLI design, and more). The
dependency rule is strict and enforced by import discipline: parsers,
pagination, retry, rate-limit, models, and exporters never depend on
`scraper/*` or `cli.py`. That keeps the leaves testable in isolation.

## Engineering decisions that matter

### Selector strategy (Phase 3)

A purely xpath card-boundary expression like
`//div[has-library-id-descendant and has-img-descendant and
no-inner-library-id-div]` returned zero matches against Meta's live
React DOM. The pattern that works is two-step: anchor on the
`Library ID:` text node, then walk up to the closest `<div>` containing
an `<img>`. In Playwright that becomes the chained
`text=/Library ID:\s*\d+/ >> xpath=ancestor::div[.//img][1]` selector,
now exported from `src/meta_ads_scraper/constants.py` so the parser
and the scraper share one source of truth.

### Locale forcing (Phase 2)

From a Kenyan IP, the Ad Library renders in Swahili and every
English text anchor fails silently. One layer of locale forcing is
not enough; the working fix is three: `BrowserContext.locale="en-US"`,
an `Accept-Language: en-US,en;q=0.9` extra header, and `&locale=en_US`
appended to the URL itself. The resolved URL carries the parameter so
the recorded `source_url` field is reproducible.

### Resilience layer (Phase 4)

Three named tenacity decorators cover the transient failure modes.
`@retry_network` exponentially backs off on httpx transport errors
*and* on Playwright transport-shaped failures, filtered by a
message-signature predicate (`net::err`, `navigation timeout`,
`page closed`, `target closed`) so genuine selector misses are not
swept up. `@retry_rate_limited` honours `RateLimitedError.retry_after`
when set. `@retry_dom` retries Playwright selector timeouts once with
`reraise=True`. The `RateLimiter` lives inside `scroll_and_collect` so
each scroll iteration is paced, not just the scrape as a whole.

### Checkpoint and resume (Phase 5)

The `CheckpointStore` is a thin sqlite3 wrapper with two tables —
`runs` and `scraped_ads` — and autocommit-mode connections so a crash
mid-write loses at most one row. The `search` command always
checkpoints; `resume <run-id>` rehydrates the original `SearchSpec`
and passes the already-scraped ad-id set into `scroll_and_collect`'s
existing `yielded_ids` seam. Resume output contains new ads only —
storing full `Ad` objects in the checkpoint to support a full-set
rewrite was an obvious win on user-experience but a clear loss on
schema complexity; the merge-yourself trade-off was the right call.

### Test discipline (Phase 6)

The longest-running gap was offline coverage of the scroll-XHR-driven
pagination loop. Phase 6 closed it with a HAR fixture captured against
live Meta, slimmed and scrubbed via `scripts/slim_har.py` (cookies,
auth, and `X-Fb-*` headers redacted), replayed through
`scroll_and_collect` by `tests/integration/test_pagination_har_replay.py`.
The coverage gate landed at 78% — one point under the current 79.12%
floor — with the gate enforced in the integration job that has the
full code surface visible. Unit-only coverage cannot reach 78% because
`playwright_scraper.py` is mostly exercised by integration tests; the
asymmetry is documented.

## What I'd build next

- An `ad_creative_text` post-processor stripping Meta's layout
  artifacts (zero-width spaces, `Active` / `Sponsored` markers,
  platform headers).
- Path A wired in if Meta ever opens commercial ads to the Graph API,
  or as a fallback path for political-ad jurisdictions where the
  approval gate is reachable.
- Distributed scraping with proxy rotation and a multi-machine work
  queue for production-scale runs against many verticals concurrently.

## What I deliberately didn't build

- CAPTCHA solving. Hit a wall, fail fast, re-run later from a
  different IP.
- Cloud hosting. Data-centre IPs draw Meta blocks aggressively; this
  scraper is correctly a local CLI run on demand.
- A web UI. The Rich-rendered CLI plus JSON / CSV output is the right
  surface for an internal analyst tool.

## Time + tools

About 30 hours over a weekend, against a Monday-evening deadline.
Python 3.12, Playwright with stealth, Pydantic v2, Typer, structlog,
tenacity, pytest with asyncio, ruff, mypy strict, GitHub Actions, and
the `gh` CLI. Used Claude Code in the loop for drafts and accelerated
iteration; every line was reviewed and every architectural decision is
recorded in `.project/journal/JOURNAL.md` and the per-phase Completion
Reports.

## License

MIT.
