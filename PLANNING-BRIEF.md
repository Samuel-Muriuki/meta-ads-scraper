# Meta Ads Scraper — Planning Brief

> **READ THIS FIRST.** This is the architectural decision document. Every file in this repo is downstream of these decisions. If you change something here, propagate the change everywhere else.

**Author:** Samuel Muriuki
**Reviewer:** Antonio Boccanfuso (Hoski)
**Date:** 11 May 2026
**Submission deadline:** Mon 11 May (window TBC with Antonio)

---

## 1. Context & Stakes

**Who:** Hoski (hoski.ca), Montreal-based Creative Performance Agency. Founder: Antonio Boccanfuso.

**Why this task exists:** Filter test for the Python Developer — Internal Systems & Automation role. Sent to "shortlisted candidates" only after Antonio reviewed the Loom video application.

**What success looks like:**
- A working Python scraper for Meta Ads Library
- Three search inputs supported (keyword, Facebook page URL, page slug)
- Structured ad data output (CSV + JSON)
- Pagination + retry + error handling
- Clean code organisation
- GitHub repo + Loom walkthrough + short approach explanation

**What Antonio is grading (in order):**
1. **Scraping ability** — does it actually work against a hard target?
2. **Problem solving** — did you make smart trade-offs when faced with friction?
3. **Code quality** — is this code you'd want next to on a 3-person team?

The third is where seniority signals live. Comments, structure, type discipline, error handling, tests, README quality. Code quality is the part Antonio can audit at leisure without running anything.

---

## 2. The Hard Truth About Meta Ads Library

Three access paths exist. Each has trade-offs.

### Path A — Official Meta Ad Library API
- Endpoint: `https://graph.facebook.com/v18.0/ads_archive`
- **Requirement:** Meta developer account + app + "Ad Library API Access" approval
- **Approval gate:** Requires verified journalist/researcher status in approved countries; Kenya is not on the approved list for full political ad data
- **What it returns:** Mostly **political and social issue ads** for approved countries — limited commercial ad data
- **Verdict:** Not viable as the primary path. Commercial ads are what Hoski clients care about.

### Path B — Playwright on the public UI (https://www.facebook.com/ads/library/)
- **What it returns:** Full commercial + political ad data, including creatives, CTA, landing URLs, platforms
- **Difficulty:** Heavy JS SPA, anti-bot detection, infinite scroll, rate limits
- **Verdict:** This is the realistic primary path.

### Path C — Hybrid
- Use Path A where credentials and ad types align
- Use Path B for everything else
- **Verdict:** Phase 2+ enhancement. Not MVP.

**LOCKED DECISION:** Build Path B first. Architect Path A as a swappable scraper backend so it can be added without refactoring. Ship MVP with Path B alone.

---

## 3. Stack — Locked

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Antonio's stated requirement |
| Browser automation | Playwright (Python) | JD lists it; strictly better than Selenium |
| HTTP | httpx | Async-first, modern alternative to requests |
| Validation | Pydantic v2 | Type discipline as a signal |
| CLI | Typer | Pydantic-aligned, cleaner than argparse |
| Retries | tenacity | Production standard |
| Logging | structlog | JSON-able, production-grade |
| CLI UX | rich | Tables, progress bars, polish |
| Tests | pytest + playwright-pytest | Standard |
| Checkpointing | SQLite (stdlib) | No infra burden |
| Packaging | `pyproject.toml` (PEP 621) | Modern Python |
| Linting | ruff | Fast, replaces flake8+isort+black |
| Typing | mypy strict | Pair with Pydantic |

**Deliberately rejected:**
- **Scrapy** — overkill for a browser-required target
- **Selenium** — Playwright is strictly better in 2026
- **BeautifulSoup** — Playwright's locator API handles DOM extraction natively
- **Pandas** — stdlib `csv` is enough; reduces deps and install time
- **Poetry** — `uv` or `pip` + `pyproject.toml` is enough for this scope

---

## 4. The Data Model

One Pydantic model: `Ad`. Every field nullable except identifiers and metadata.

```python
class Ad(BaseModel):
    # Identifiers (required)
    ad_library_id: str
    page_id: str
    collected_at: datetime
    source_url: str  # the Meta Ads Library URL we collected from

    # Page info
    page_name: Optional[str]
    page_url: Optional[str]
    page_profile_picture_url: Optional[str]

    # Creative
    ad_creative_text: Optional[str]
    ad_creative_image_urls: list[str] = []
    ad_creative_video_url: Optional[str]
    landing_url: Optional[str]
    cta_type: Optional[str]  # SHOP_NOW, LEARN_MORE, etc.

    # Lifecycle
    start_date: Optional[date]
    end_date: Optional[date]
    is_active: Optional[bool]

    # Distribution
    platforms: list[str] = []  # FACEBOOK, INSTAGRAM, MESSENGER, AUDIENCE_NETWORK
    languages: list[str] = []
    countries: list[str] = []

    # Performance (when available — usually only for political ads)
    demographic_breakdown: Optional[dict[str, Any]]
    total_reach_estimate: Optional[int]
```

**Principle:** Missing data is acceptable. Lying about it (defaulting to empty string instead of None) is not. Every nullable field is `Optional[T] = None`.

---

## 5. Three Search Paths, One Interface

Antonio explicitly requires keyword, Facebook page URL, AND page slug as inputs. Pattern:

```python
class SearchSpec(BaseModel):
    mode: Literal["keyword", "page_url", "page_slug"]
    query: str
    country: str = "ALL"  # ISO 3166-1 alpha-2 or "ALL"
    ad_type: Literal["all", "political_and_issue_ads"] = "all"
    active_status: Literal["all", "active", "inactive"] = "all"
```

The scraper takes one `SearchSpec`, returns an iterable of `Ad`. Translation from spec → Meta URL happens in a single `resolve_url(spec)` function. This is the seam Antonio will look at — it's where the abstraction either holds or leaks.

---

## 6. Anti-Detection Posture

Decision: respectful, not adversarial.

**Do:**
- Use `playwright-stealth` to mask obvious headless fingerprints
- Persist storage state across runs (cookies, localStorage)
- Randomized jitter between actions (1.5–3.5s default)
- Realistic viewport (1920x1080, not 800x600)
- Respect Retry-After headers on 429
- Configurable concurrency (default 1, max 3)

**Don't:**
- Solve CAPTCHAs — if hit, fail fast with a clear error
- Rotate proxies — out of scope, signals scraping farm
- Forge headers beyond what stealth provides
- Run faster than ~1 request/second sustained

**Rationale for Antonio:** If Meta wants to block scrapers, that's Meta's right. Our job is to be a polite, identifiable scraper that handles being blocked gracefully — not to win an arms race. This shows judgment.

---

## 7. Pagination Strategy

Meta uses infinite scroll. The loop:

```
1. Render initial results
2. Count ad cards in DOM (`previous_count`)
3. Scroll the results container to bottom
4. Wait for either:
   - Network idle (Playwright wait_for_load_state)
   - "No more results" sentinel element
   - 5s timeout
5. Count again (`current_count`)
6. If current_count > previous_count: continue
   If current_count == previous_count: increment stall counter
   If stall_counter == 3: stop
7. Check stop conditions:
   - Max results reached (--max-results flag)
   - Total time exceeded (--timeout flag)
   - User Ctrl+C (graceful shutdown)
8. Extract newly added cards, append to results, repeat
```

---

## 8. Retry Policy (tenacity)

| Failure Mode | Action |
|---|---|
| `httpx.TimeoutError`, `httpx.ConnectError` | Exponential backoff (1s, 2s, 4s, 8s, 16s), max 5 retries |
| HTTP 5xx | Same as above |
| HTTP 429 (rate limit) | Respect `Retry-After` header; if absent, 60s + jitter, max 3 retries |
| HTTP 4xx (non-429) | Fail fast, no retry |
| Playwright `TimeoutError` on selector | Re-navigate + retry once, then fail |
| `PlaywrightError` (browser crashed) | Restart browser, retry once, then fail |
| Pydantic `ValidationError` on parsed ad | Log warning, skip the ad, continue |

---

## 9. CLI Surface

```bash
# Search by keyword
meta-ads-scraper --keyword "luxury watches" --country US --max-results 100 --format csv --out ads.csv

# Search by page URL
meta-ads-scraper --page-url "https://www.facebook.com/Nike" --format json --out nike_ads.json

# Search by page slug
meta-ads-scraper --page-slug "Nike" --max-results 50 --format csv

# Resume an interrupted run
meta-ads-scraper --resume ./data/last-run.sqlite

# Dry run (don't write output)
meta-ads-scraper --keyword "dental" --dry-run

# Verbose / debug
meta-ads-scraper --keyword "test" -vv
```

**Mutually exclusive:** exactly one of `--keyword`, `--page-url`, `--page-slug` (Typer enforces).

---

## 10. Test Strategy

| Layer | Tool | What it covers |
|---|---|---|
| Unit — parsers | pytest | DOM → `Ad` model conversion against recorded HAR/HTML fixtures |
| Unit — models | pytest | Pydantic validation, nullable handling, serialization |
| Unit — CLI | pytest + typer.testing.CliRunner | Argument parsing, mutual exclusion, exit codes |
| Smoke — live | pytest + playwright | One end-to-end run against real Meta. Gated by `META_LIVE_TESTS=1` env var; CI skips by default. |
| Integration — replay | pytest + playwright | Full pipeline against recorded HAR; deterministic, runs in CI |

**CI strategy:** Fast tests on every push, smoke gated to manual workflow dispatch only (rate-limit-friendly).

---

## 11. Submission Checklist

- [ ] GitHub repo public at `github.com/Samuel-Muriuki/meta-ads-scraper`
- [ ] README with: install, usage, examples, architecture notes, known limitations
- [ ] `examples/` folder with real output samples (CSV + JSON)
- [ ] `CHANGELOG.md` with phase markers
- [ ] CI green on the default branch
- [ ] Loom walkthrough (5–8 min): demo a run, walk through code structure, explain trade-offs
- [ ] `APPROACH.md` — the one-pager Antonio asked for ("short explanation of your approach")
- [ ] WhatsApp message to Antonio: repo link, Loom link, one-paragraph framing

---

## 12. What Antonio Will Probably Audit

Predicting the audit so we build to it:

1. **Run `python -m meta_ads_scraper --keyword "dental" --max-results 10`** — does it work cold?
2. **Read the README** — does it match what the code does?
3. **Look at `src/meta_ads_scraper/scraper/playwright_scraper.py`** — does the abstraction hold?
4. **Check `tests/`** — are there tests, do they pass, do they actually test the right things?
5. **Run `ruff check && mypy src/`** — does it lint clean?
6. **Look at commit history** — atomic commits with gitmoji, or one giant "init" dump?
7. **Trigger an error case** (bad page URL, network blip) — what happens?
8. **Watch the Loom** — does Samuel sound like he made the trade-offs deliberately?

**Build to that audit. Don't optimize for invisible things.**

---

## 13. Timeline & Phases

See `BUILD-PLAN.md` for phase-by-phase implementation prompts.

| Day | Hours | Phases |
|---|---|---|
| Sat | 0–12 | 0 (bootstrap), 1 (MVP), 2 (3 search paths) |
| Sun | 12–28 | 3 (pagination), 4 (resilience), 5 (CLI polish), 6 (tests) |
| Mon | 32–38 | 7 (README & demo data), Loom, submission |

---

## 14. Decision Log

Append to this section as decisions get made or reversed.

- **2026-05-11**: Locked stack (see §3). No Java despite Antonio's question — he asked, you said "open to learning if needed," but the task is Python-only.
- **2026-05-11**: Path B (Playwright on public UI) is primary. Path A (official API) is post-MVP enhancement.
- **2026-05-11**: Repo is public, named `meta-ads-scraper`, not `hoski-` prefixed (avoid signalling this was built only for one application).

---

**END OF PLANNING BRIEF**
