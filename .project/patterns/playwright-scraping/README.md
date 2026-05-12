# Playwright Scraping Patterns

When writing or modifying scraping code in this project, follow these patterns.

## 1. Always use async Playwright

```python
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="...",  # set explicitly
    )
    page = await context.new_page()
    # ...
    await context.close()
    await browser.close()
```

Never use the sync API. Never mix.

## 2. Apply stealth before navigation

```python
from playwright_stealth import Stealth

page = await context.new_page()
await Stealth().apply_stealth_async(page)
# ONLY THEN navigate
await page.goto(url, wait_until="networkidle")
```

Note: `playwright-stealth` 1.x exposed `stealth_async(page)` as a
free function but imports `pkg_resources` and crashes on Python 3.13.
We pin 2.x in `pyproject.toml` (`playwright-stealth>=2.0,<3.0`),
which uses the class-based API above.

## 3. Prefer Locator API over query_selector

❌ Don't:
```python
elements = await page.query_selector_all(".x1a2b3c4")
```

✅ Do:
```python
ads = page.locator('[role="article"]')
count = await ads.count()
for i in range(count):
    ad = ads.nth(i)
    text = await ad.locator('text=Library ID').inner_text()
```

Why: Locators are lazy, auto-wait, and survive DOM re-renders. `query_selector` returns a snapshot that goes stale.

## 4. Selector priority (most stable → least stable)

1. `getByRole("button", name="Submit")`
2. `getByLabel("Email address")`
3. `getByText("Library ID")`
4. `getByTestId("ad-card")`
5. Structural traversal: `page.locator('main').locator('article')`
6. CSS selectors: only as last resort, NEVER with obfuscated class names

## 5. Always wait explicitly

❌ Don't:
```python
await page.click(".btn-submit")
await asyncio.sleep(2)  # hoping the page loaded
```

✅ Do:
```python
await page.click(".btn-submit")
await page.wait_for_load_state("networkidle", timeout=10_000)
```

Or wait for a specific element:
```python
await page.wait_for_selector('[data-testid="results"]', state="visible")
```

## 6. Handle cookie consent

Meta shows a cookie dialog on first visit. Detect and dismiss:

```python
try:
    accept_btn = page.get_by_role("button", name=re.compile("Allow|Accept", re.I))
    await accept_btn.click(timeout=3_000)
except PlaywrightTimeoutError:
    pass  # no dialog, fine
```

Do this BEFORE the main scraping logic.

## 7. Persist storage state

To survive page reloads and avoid re-doing cookie consent every run:

```python
# First run: save state after consent
await context.storage_state(path="auth-state.json")

# Subsequent runs: load it
context = await browser.new_context(
    storage_state="auth-state.json",
    viewport={"width": 1920, "height": 1080},
)
```

Add `auth-state.json` to `.gitignore`.

## 8. Scroll within a container, not the page

Meta's results are in a scrollable container, not the whole page:

```python
# Find the scrollable ancestor of results
container = page.locator('[role="main"]')
await container.evaluate("(el) => el.scrollTo(0, el.scrollHeight)")
```

Page-level scroll won't trigger Meta's lazy loading.

## 9. Catch Playwright-specific exceptions

```python
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

try:
    await page.click("button")
except PlaywrightTimeoutError:
    # selector not found in time
except PlaywrightError as e:
    # other playwright failure (e.g., browser crashed)
```

## 10. Resource cleanup in finally

```python
browser = None
try:
    browser = await p.chromium.launch()
    # ... work
finally:
    if browser:
        await browser.close()
```

The `async with` context manager handles this, but in code with conditional cleanup, be explicit.

## 11. Don't block the event loop

Scraping is I/O-bound. Always `await`. Never call `time.sleep()` — use `asyncio.sleep()`.

## 12. Headless = production, headed = debugging

```python
import os
headless = os.environ.get("PLAYWRIGHT_HEADLESS", "1") != "0"
browser = await p.chromium.launch(headless=headless)
```

Run `PLAYWRIGHT_HEADLESS=0 python -m meta_ads_scraper ...` to debug visually.

## 13. Screenshot on error

When scraping fails, dump state for forensics:

```python
try:
    # scrape logic
except PlaywrightError as e:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    screenshot_path = Path(f"data/debug/{timestamp}.png")
    html_path = Path(f"data/debug/{timestamp}.html")
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(screenshot_path))
    html_path.write_text(await page.content())
    logger.error("scrape_failed", error=str(e), screenshot=str(screenshot_path))
    raise
```

Gated behind a `--screenshot-on-error` flag in production.
