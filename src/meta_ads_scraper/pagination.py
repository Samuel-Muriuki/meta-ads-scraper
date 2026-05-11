from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator, Iterable

import structlog
from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

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
) -> AsyncIterator[Locator]:
    effective_max = _normalize_max_results(max_results)
    yielded: set[str] = set(yielded_ids) if yielded_ids else set()
    stall_count = 0
    start = time.monotonic()

    try:
        while True:
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
                await page.wait_for_load_state("networkidle", timeout=_SCROLL_WAIT_TIMEOUT_MS)
            except PlaywrightTimeoutError:
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


async def _scroll_to_bottom(page: Page) -> None:
    container_count = await page.locator(_CONTAINER_SELECTOR).count()
    if container_count > 0:
        await page.locator(_CONTAINER_SELECTOR).first.evaluate(
            "(el) => el.scrollTo(0, el.scrollHeight)"
        )
    else:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")


async def _extract_card_id(card: Locator) -> str | None:
    try:
        text = await card.inner_text(timeout=_INNER_TEXT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return None
    match = _LIBRARY_ID_RE.search(text)
    return match.group(1) if match else None
