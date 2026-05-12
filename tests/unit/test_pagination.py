from __future__ import annotations

from typing import Any

import pytest

from meta_ads_scraper.pagination import MAX_RESULTS_CEILING, scroll_and_collect


class _FakeCard:
    def __init__(self, ad_id: str) -> None:
        self.ad_id = ad_id

    async def inner_text(self, timeout: int | None = None) -> str:  # noqa: ASYNC109
        return f"Library ID: {self.ad_id}\nsome ad copy"


class _FakePage:
    """Simulates a paginated page. Each scroll reveals the next batch."""

    def __init__(
        self,
        batches: list[list[str]],
        *,
        has_container: bool = True,
        scroll_advances: bool = True,
    ) -> None:
        self._batches = batches
        self._has_container = has_container
        self._scroll_advances = scroll_advances
        self.scroll_idx = 0
        self.scroll_calls = 0

    def locator(self, selector: str) -> Any:
        if "main" in selector:
            return _FakeContainerLocator(self)
        return _FakeCardLocator(self)

    def _visible_ids(self) -> list[str]:
        visible: list[str] = []
        for batch in self._batches[: self.scroll_idx + 1]:
            visible.extend(batch)
        return visible

    def _on_scroll(self) -> None:
        self.scroll_calls += 1
        if self._scroll_advances and self.scroll_idx + 1 < len(self._batches):
            self.scroll_idx += 1

    async def evaluate(self, js: str) -> None:
        if "scrollTo" in js:
            self._on_scroll()

    async def wait_for_load_state(self, state: str, timeout: int | None = None) -> None:  # noqa: ASYNC109
        return None


class _FakeCardLocator:
    def __init__(self, page: _FakePage) -> None:
        self._page = page

    async def all(self) -> list[_FakeCard]:
        return [_FakeCard(aid) for aid in self._page._visible_ids()]


class _FakeContainerLocator:
    def __init__(self, page: _FakePage) -> None:
        self._page = page

    @property
    def first(self) -> Any:
        return _FakeContainerFirst(self._page)

    async def count(self) -> int:
        return 1 if self._page._has_container else 0


class _FakeContainerFirst:
    def __init__(self, page: _FakePage) -> None:
        self._page = page

    async def evaluate(self, js: str) -> None:
        if "scrollTo" in js:
            self._page._on_scroll()


async def _collect(page: _FakePage, **kwargs: Any) -> list[Any]:
    return [card async for card in scroll_and_collect(page, "div.card", **kwargs)]


class TestMaxResults:
    async def test_yields_exact_count_when_max_results_set(self):
        page = _FakePage([["1", "2", "3"], ["4", "5", "6"]])
        cards = await _collect(page, max_results=3, stall_threshold=10)
        assert len(cards) == 3

    async def test_yields_all_when_max_results_exceeds_available(self):
        page = _FakePage([["1", "2"], [], [], []])
        cards = await _collect(page, max_results=100, stall_threshold=3)
        assert len(cards) == 2

    async def test_max_results_zero_treated_as_unlimited(self):
        page = _FakePage([["1", "2", "3"], [], [], []])
        cards = await _collect(page, max_results=0, stall_threshold=3)
        assert len(cards) == 3

    async def test_max_results_above_ceiling_clamped(self):
        ids = [str(i) for i in range(1, 1101)]
        page = _FakePage([ids])
        cards = await _collect(page, max_results=1500, stall_threshold=3)
        assert len(cards) == MAX_RESULTS_CEILING == 1000

    async def test_max_results_none_clamped_to_ceiling(self):
        ids = [str(i) for i in range(1, 1101)]
        page = _FakePage([ids])
        cards = await _collect(page, max_results=None, stall_threshold=3)
        assert len(cards) == MAX_RESULTS_CEILING


class TestStallThreshold:
    async def test_stops_on_n_consecutive_no_progress_scrolls(self):
        page = _FakePage([["1", "2"]] + [[]] * 10, scroll_advances=True)
        cards = await _collect(page, max_results=100, stall_threshold=3)
        assert len(cards) == 2
        assert page.scroll_calls >= 2

    async def test_stall_resets_when_new_cards_arrive(self):
        page = _FakePage([["1"], [], [], ["2"], [], [], []], scroll_advances=True)
        cards = await _collect(page, max_results=100, stall_threshold=3)
        assert len(cards) == 2

    async def test_custom_stall_threshold(self):
        page = _FakePage([["1"]] + [[]] * 10, scroll_advances=True)
        cards = await _collect(page, max_results=100, stall_threshold=1)
        assert len(cards) == 1


class TestDedup:
    async def test_same_id_in_multiple_batches_yielded_once(self):
        page = _FakePage(
            [["1", "2"], ["1", "2", "3"], ["1", "2", "3", "4"], []],
            scroll_advances=True,
        )
        cards = await _collect(page, max_results=100, stall_threshold=10)
        ids = [c.ad_id for c in cards]
        assert ids == ["1", "2", "3", "4"]

    async def test_yielded_ids_parameter_prevents_re_yielding(self):
        page = _FakePage([["1", "2", "3", "4"]])
        cards = await _collect(
            page,
            max_results=100,
            stall_threshold=2,
            yielded_ids={"1", "3"},
        )
        ids = [c.ad_id for c in cards]
        assert ids == ["2", "4"]


class TestTimeout:
    async def test_returns_within_timeout_budget(self):
        import time

        page = _FakePage([[str(i) for i in range(1, 6)]])
        start = time.monotonic()
        cards = await _collect(page, max_results=100, timeout_seconds=2, stall_threshold=2)
        elapsed = time.monotonic() - start
        assert elapsed < 3, f"loop ran past timeout budget: {elapsed}s"
        assert len(cards) == 5

    async def test_zero_timeout_returns_immediately(self):
        page = _FakePage([["1", "2", "3", "4"]])
        cards = await _collect(page, max_results=100, timeout_seconds=0, stall_threshold=10)
        assert len(cards) == 0


class TestContainerFallback:
    async def test_falls_back_to_window_scroll_when_no_container(self):
        page = _FakePage([["1"], ["2"], []], scroll_advances=True, has_container=False)
        cards = await _collect(page, max_results=100, stall_threshold=2)
        ids = [c.ad_id for c in cards]
        assert ids == ["1", "2"]
        assert page.scroll_calls >= 1


class TestEdgeCases:
    async def test_empty_page_yields_nothing(self):
        page = _FakePage([[]], scroll_advances=False)
        cards = await _collect(page, max_results=10, stall_threshold=2)
        assert cards == []

    async def test_card_without_library_id_skipped(self):
        page = _FakePage([["7"]])

        class _BadCard:
            async def inner_text(self, timeout: int | None = None) -> str:  # noqa: ASYNC109
                return "no id here"

        original_locator = page.locator

        def locator_override(selector: str) -> Any:
            loc = original_locator(selector)
            if "main" not in selector:

                async def all_with_bad() -> list[Any]:
                    return [_BadCard(), _FakeCard("7")]

                loc.all = all_with_bad  # type: ignore[method-assign]
            return loc

        page.locator = locator_override  # type: ignore[method-assign]
        cards = await _collect(page, max_results=10, stall_threshold=2)
        assert len(cards) == 1


pytestmark = pytest.mark.asyncio
