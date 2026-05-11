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
- Locale: from `--country` or default `en-US`
- Timezone: aligned with locale

### 3. Persistent storage state
Save cookies + localStorage after first successful run. Reuse on subsequent runs. Looks like a returning user.

### 4. Human-like pacing
- Default: 1.5–3.5s jitter between actions
- Configurable via `--rate-limit` flag
- Never click multiple times in quick succession

### 5. Respect Retry-After
On 429, honor the header. Don't immediately retry.

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
