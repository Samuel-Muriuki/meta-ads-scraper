# 06 — Pagination Strategy

## The problem

Meta Ads Library uses **infinite scroll** — there's no page numbers, no "next" button. Ads load as you scroll the results container to its bottom.

## The algorithm

```
1. Navigate to the search URL
2. Wait for the results container to be visible
3. Count initial visible ad cards: `previous_count`
4. Begin loop:
   a. Locate all currently visible ad cards
   b. Yield each card that wasn't yielded before (track ad_library_ids in a set)
   c. Check stop conditions:
      - max_results reached
      - timeout exceeded
      - stall counter == stall_threshold
   d. Scroll the results container to its scroll-bottom
   e. Wait for either:
      - networkidle (Playwright)
      - "No more results" sentinel element to appear
      - 5-second timeout
   f. Count cards again: `current_count`
   g. If current_count > previous_count:
        - previous_count = current_count
        - reset stall counter
      Else:
        - increment stall counter
   h. Loop
```

## Stop conditions (any one ends the loop)

| Condition | Default | CLI flag |
|---|---|---|
| max_results yielded | None (unlimited, capped at 1000 hard ceiling) | `--max-results` |
| Total scrape time exceeded | 300s | `--timeout` |
| 3 consecutive scrolls produce no new cards | hardcoded | — |
| "No more ads" sentinel detected | — | — |
| User Ctrl+C | — | — |

## Why stall threshold, not just sentinel?

Meta's "no more ads" indicator is unreliable. Sometimes the sentinel appears immediately and disappears as more ads load. Sometimes it never appears even when no more ads exist.

The stall threshold is a fail-safe: if 3 consecutive scrolls each wait the full 5s and produce zero new ads, we conclude we're at the end.

## Graceful shutdown on Ctrl+C

The actual implementation does not register an explicit signal
handler. Instead `scroll_and_collect` runs inside a `try/except
asyncio.CancelledError` block; Python's default SIGINT handling
delivers `KeyboardInterrupt`, which propagates as `CancelledError`
through the asyncio scheduler into the generator:

```python
try:
    while True:
        # ... scroll / collect / yield ...
except asyncio.CancelledError:
    logger.info("shutdown_requested", yielded=len(yielded))
    raise  # propagate so the caller unwinds the browser context
```

The CLI's outermost `_typed_exit_codes` decorator catches the
resulting `KeyboardInterrupt` and exits with code 130. Already-yielded
ads are flushed by the exporter call that happens after the async-for
loop returns. Partial outputs are valid; we don't truncate.

## Dedup discipline

The yielded-set MUST be `ad_library_id` based, not card-object based. Reasons:

1. Meta sometimes re-renders the same card with a different DOM node after a scroll
2. Some cards appear in multiple "sections" of results (Active vs Past)
3. Re-running with `--resume` needs to skip ad_library_ids already in the checkpoint store

## Pseudocode for `scroll_and_collect`

```python
async def scroll_and_collect(
    page: Page,
    ad_card_selector: str,
    max_results: int | None = None,
    timeout_seconds: int = 300,
    stall_threshold: int = 3,
) -> AsyncIterator[Locator]:
    yielded_ids: set[str] = set()
    stall_count = 0
    start_time = time.time()

    while True:
        # Stop on timeout
        if time.time() - start_time > timeout_seconds:
            logger.info("pagination_timeout", yielded=len(yielded_ids))
            return

        # Stop on max
        if max_results is not None and len(yielded_ids) >= max_results:
            logger.info("max_results_reached", yielded=len(yielded_ids))
            return

        # Collect new cards
        cards = await page.locator(ad_card_selector).all()
        new_cards = 0
        for card in cards:
            ad_id = await _extract_ad_id(card)
            if ad_id and ad_id not in yielded_ids:
                yielded_ids.add(ad_id)
                new_cards += 1
                yield card
                if max_results is not None and len(yielded_ids) >= max_results:
                    return

        if new_cards == 0:
            stall_count += 1
            if stall_count >= stall_threshold:
                logger.info("pagination_stalled", yielded=len(yielded_ids))
                return
        else:
            stall_count = 0

        # Scroll
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_load_state("networkidle", timeout=5000).catch(lambda _: None)
```

## What `--max-results 0` means

Treated as "no limit" but with the hardcoded 1000 hard ceiling. We log a warning if the user passes 0:

```python
if max_results == 0:
    logger.warning("max_results_zero_treated_as_unlimited")
    max_results = None
```

## Resume semantics

When resuming via `--resume <run-id>`:

1. Load `yielded_ids` from the checkpoint store
2. Pass it as initial state to `scroll_and_collect`
3. The loop yields only ads with IDs not in the resumed set
4. Pagination still respects max_results — which counts NEW ads, not total
