from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator, Iterable

import structlog
from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .rate_limit import RateLimiter
from .retry import retry_dom

logger = structlog.get_logger()

MAX_RESULTS_CEILING = 1000

_LIBRARY_ID_RE = re.compile(r"Library ID:\s*(\d+)")
_SCROLL_WAIT_TIMEOUT_MS = 5_000
_INNER_TEXT_TIMEOUT_MS = 2_000
_CONTAINER_SELECTOR = '[role="main"]'


async def scroll_and_collect(
    page: Page,
    ad_card_selector: str,
    *,
    max_results: int | None = None,
    timeout_seconds: int = 300,
    stall_threshold: int = 3,
    yielded_ids: Iterable[str] | None = None,
    rate_limiter: RateLimiter | None = None,
) -> AsyncIterator[Locator]:
    """Yield ad-card locators across Meta's infinite-scroll DOM.

    The optional ``rate_limiter`` gates the **top** of every iteration of
    the scroll loop, so each tick of card collection + scroll + idle-wait
    obeys the configured requests-per-second + concurrency caps. Default
    ``None`` preserves the pre-Phase-4 behaviour and keeps the existing
    unit tests free of timing dependencies.
    """
    effective_max = _normalize_max_results(max_results)
    yielded: set[str] = set(yielded_ids) if yielded_ids else set()
    stall_count = 0
    start = time.monotonic()

    try:
        while True:
            if rate_limiter is not None:
                await rate_limiter.acquire()

            if time.monotonic() - start > timeout_seconds:
                logger.info(
                    "pagination_timeout",
                    yielded=len(yielded),
                    elapsed=time.monotonic() - start,
                )
                return

            if effective_max is not None and len(yielded) >= effective_max:
                logger.info("max_results_reached", yielded=len(yielded))
                return

            cards = await page.locator(ad_card_selector).all()
            new_in_iteration = 0
            for card in cards:
                ad_id = await _extract_card_id(card)
                if not ad_id or ad_id in yielded:
                    continue
                yielded.add(ad_id)
                new_in_iteration += 1
                yield card
                if effective_max is not None and len(yielded) >= effective_max:
                    logger.info("max_results_reached", yielded=len(yielded))
                    return

            if new_in_iteration == 0:
                stall_count += 1
                logger.debug("pagination_stall_tick", stall_count=stall_count)
                if stall_count >= stall_threshold:
                    logger.info(
                        "pagination_stalled",
                        yielded=len(yielded),
                        stall_count=stall_count,
                    )
                    return
            else:
                stall_count = 0

            await _scroll_to_bottom(page)
            try:
                await _wait_for_networkidle(page, _SCROLL_WAIT_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                # Networkidle never arrived even after the retry; that's a
                # signal the page is still streaming chatter, not a fatal
                # error. Continue the scroll loop.
                pass
    except asyncio.CancelledError:
        logger.info("shutdown_requested", yielded=len(yielded))
        raise


def _normalize_max_results(max_results: int | None) -> int | None:
    if max_results is None:
        return MAX_RESULTS_CEILING
    if max_results == 0:
        logger.warning("max_results_zero_treated_as_unlimited")
        return MAX_RESULTS_CEILING
    if max_results > MAX_RESULTS_CEILING:
        logger.warning(
            "max_results_above_ceiling",
            requested=max_results,
            clamped_to=MAX_RESULTS_CEILING,
        )
        return MAX_RESULTS_CEILING
    return max_results


@retry_dom
async def _scroll_to_bottom(page: Page) -> None:
    """Scroll the results container (or window) to the bottom.

    Wrapped in ``@retry_dom`` so a transient ``PlaywrightTimeoutError``
    on the locator count / evaluate step gets one retry with a 2s wait
    before propagating. Non-timeout Playwright errors propagate
    immediately — they indicate a deeper problem (frame detached, page
    closed) that scroll-loop retry cannot fix.
    """
    container_count = await page.locator(_CONTAINER_SELECTOR).count()
    if container_count > 0:
        await page.locator(_CONTAINER_SELECTOR).first.evaluate(
            "(el) => el.scrollTo(0, el.scrollHeight)"
        )
    else:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")


@retry_dom
async def _wait_for_networkidle(page: Page, timeout_ms: int) -> None:
    """Wait for the network to go idle after a scroll.

    Wrapped in ``@retry_dom`` so a stalled ``networkidle`` (which surfaces
    as ``PlaywrightTimeoutError``) gets a single 2s-spaced retry before
    propagating. The caller swallows the final exception — networkidle
    failing twice in a row is informational, not fatal.
    """
    await page.wait_for_load_state("networkidle", timeout=timeout_ms)


async def _extract_card_id(card: Locator) -> str | None:
    try:
        text = await card.inner_text(timeout=_INNER_TEXT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return None
    match = _LIBRARY_ID_RE.search(text)
    return match.group(1) if match else None
