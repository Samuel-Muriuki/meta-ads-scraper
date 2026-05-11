# 04 — Scraping Strategy

## The decision: Path B primary, Path A future

Three access paths exist to Meta Ads Library data. We pick Path B for MVP. Here's why.

## Path A — Official Meta Ad Library API

**Endpoint:** `https://graph.facebook.com/v18.0/ads_archive`

**What you need:**
- Meta developer account
- Facebook app registered
- "Ad Library API Access" approval — requires verified journalist/researcher status
- Kenya is NOT on the approved country list for full political ad data

**What it returns:**
- Political and social issue ads in approved countries — full data
- Commercial ads — very limited data; mostly just `id`, `page_id`, `page_name`. No creatives, no targeting info.

**Verdict for Hoski:** Hoski serves jewelry, dental, automotive, home services. These are all **commercial** advertisers. The official API doesn't give us what their clients need.

## Path B — Playwright on the public UI

**URL pattern:**
```
https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q=<KEYWORD>&search_type=keyword_unordered
```

**What you need:**
- Playwright with Chromium
- Stealth posture (see `05-anti-detection.md`)
- Patience (rate limits)

**What it returns:**
- Full commercial ad data: creatives (image/video URLs), CTA, landing URL, platforms
- Political ad data (when present)
- Page metadata (name, profile pic, page URL)
- Demographic breakdown (for political ads only — Meta restricts this for commercial)

**Difficulty:**
- Heavy JavaScript SPA — must render to scrape
- Infinite scroll pagination
- Anti-bot fingerprinting
- Aggressive rate limiting (estimated ~1 req/sec sustainable; bursts get blocked)
- DOM selectors change without notice (Meta uses obfuscated class names)

**Verdict:** This is the realistic primary path.

## Path C — Hybrid

Use Path A when:
- You have credentials
- You're looking for political/issue ads in approved countries
- You want demographic breakdown data

Use Path B for everything else.

**Verdict for MVP:** Out of scope. Architect Path A as a swappable backend (see `02-architecture.md` on `BaseScraper`), but don't build Path A for the submission.

## Why this choice signals seniority to Antonio

Junior engineers will:
- Use the official API and silently fail to return useful data for commercial advertisers
- Or — try to scrape but fold at the first anti-bot wall

Senior engineers will:
- Read the docs, realize the API doesn't cover commercial ads
- Build Path B with discipline (stealth, jitter, rate limit, fail-fast on CAPTCHA)
- Document the trade-off explicitly in `APPROACH.md`

Antonio is reading for the second mindset.

## DOM Selectors (Reconnaissance Notes)

> **IMPORTANT:** These selectors WILL change. Meta uses generated class names (`x1a2b3c4`). Use stable signals where possible: text content, ARIA roles, `data-testid` if present, structural relationships.

The reconnaissance task in Phase 0 includes:

1. Open https://www.facebook.com/ads/library/?q=shoes manually
2. Open DevTools, inspect:
   - The results container (likely a `div` with role=`main` or a specific aria-label)
   - Individual ad cards (look for stable wrappers, usually `div[role="article"]`)
   - The "Library ID" text inside each card
   - The page name link
   - The creative image (`<img>` with specific aspect ratio)
   - The "See ad details" CTA
3. Record the selectors in `tests/fixtures/selectors.md` for documentation
4. Build the parser around the MOST STABLE signals (text content + structural traversal beats class-name matching)

**Selector strategy:**
- Prefer Playwright's `getByRole`, `getByText`, `getByLabel`
- Fall back to CSS only when role/text fails
- NEVER use exact class names like `.x1a2b3c4` — they break weekly

## What to do when blocked

If you encounter:

| Signal | Action |
|---|---|
| Cookie consent dialog | Auto-accept (cookies are required to view the page) |
| Login wall | Fail fast with `ScraperBlockedError`. We don't have credentials. |
| CAPTCHA | Fail fast with `ScraperBlockedError`. We don't solve CAPTCHAs. |
| Empty results | Validate the URL is correct, log warning, return empty list (legitimate case) |
| "No more ads" sentinel | Stop pagination cleanly |
| HTTP 429 | Honor `Retry-After` header, exponential backoff |
| Network timeout | Retry per `retry.py` policy |
| DOM selector miss | Log warning, dump page HTML to `data/debug/<timestamp>.html`, fail |
