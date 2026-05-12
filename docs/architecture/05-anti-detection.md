# 05 — Anti-Detection Posture

## Principle

Respectful, not adversarial. We want to look like a normal browser at slow human pace, not a bot fleet.

## Layers

### 1. Stealth plugin
`playwright-stealth` masks the obvious headless fingerprints:
- `navigator.webdriver` flag
- Chrome runtime detection
- Languages, plugins, permissions

### 2. Realistic browser context
- Viewport: 1920x1080 (most common desktop)
- User agent: real Chrome version, no "HeadlessChrome"
- Locale: hard-coded `en-US` plus `Accept-Language: en-US,en;q=0.9`
  plus `&locale=en_US` in every Meta URL. Triple-layered to defeat
  Meta's GeoIP localisation (without it, Kenyan IPs render in
  Swahili). `--country` was reserved on the `SearchSpec` model but
  not wired through the URL resolver; not currently a knob.
- Timezone: hard-coded `America/New_York` to align with the en-US
  locale.

### 3. Persistent storage state (NOT implemented today)
The original plan was to save cookies + localStorage after the first
run and reuse on subsequent runs. This is not currently implemented;
each run launches a fresh Chromium context. Revisit if rate-limit
penalties surface during sustained operation.

### 4. Steady pacing via `RateLimiter`
- Default: 1.0 req/sec, max concurrency 1 (hard ceiling 3).
- Configurable via `--rate-limit` (clamped `[0.1, 10.0]`) and
  `--concurrency`.
- The limiter sits **inside** `scroll_and_collect` so each scroll
  iteration is paced -- not just the scrape as a whole.

### 5. Respect Retry-After
The `@retry_rate_limited` tenacity policy honours
`RateLimitedError.retry_after` when set; otherwise it falls back to
60s + jitter.

## What we don't do

| Technique | Why not |
|---|---|
| CAPTCHA solving | Arms race, expensive, brittle. Fail fast. |
| Proxy rotation | Signals "scraping farm" intent. Out of scope. |
| User agent rotation | Stealth + one good UA beats random rotation. |
| Cookie forging | Meta detects forged cookies easily. |
| Browser fingerprint randomization | Beyond stealth's defaults. Diminishing returns. |

## Signals we send Antonio

When he reviews the code and sees:
- We use stealth (smart)
- We don't solve CAPTCHAs (judgment)
- We respect Retry-After (professionalism)
- We document the boundary clearly (honesty)

That's senior judgment showing up in code. Junior engineers try to win the cat-and-mouse game. Senior engineers know when to fold.
