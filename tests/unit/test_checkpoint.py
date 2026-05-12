"""Unit tests for `CheckpointStore`.

In-memory SQLite via ``tmp_path / 'runs.sqlite'`` per test — keeps each
test isolated and fast.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest

from meta_ads_scraper.checkpoint import CheckpointStore, RunSummary
from meta_ads_scraper.models import Ad, SearchSpec


@pytest.fixture
def store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(tmp_path / "runs.sqlite")


def _make_ad(ad_library_id: str = "12345") -> Ad:
    return Ad(
        ad_library_id=ad_library_id,
        page_id="100",
        collected_at=datetime.now().astimezone(),
        source_url="https://www.facebook.com/ads/library/?q=shoes",
    )


def _spec(query: str = "shoes") -> SearchSpec:
    return SearchSpec(mode="keyword", query=query)


# -------------------------------------------------------------------------
# Construction
# -------------------------------------------------------------------------


class TestConstruction:
    def test_schema_created(self, store: CheckpointStore) -> None:
        # Two tables exist after construction.
        # closing() actually .close()s the connection on exit; the bare
        # `with sqlite3.connect()` form only manages transactions.
        with closing(sqlite3.connect(store.db_path)) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        assert "runs" in tables
        assert "scraped_ads" in tables

    def test_construction_is_idempotent(self, tmp_path: Path) -> None:
        db = tmp_path / "runs.sqlite"
        CheckpointStore(db)
        # A second construction must not error or wipe the schema.
        CheckpointStore(db)

    def test_data_directory_is_created(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "subdir" / "runs.sqlite"
        CheckpointStore(nested)
        assert nested.parent.is_dir()


# -------------------------------------------------------------------------
# Lifecycle: start / record / complete / abort
# -------------------------------------------------------------------------


class TestRunLifecycle:
    def test_start_run_returns_uuid_hex(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        assert len(run_id) == 32
        assert all(c in "0123456789abcdef" for c in run_id)

    def test_two_start_runs_yield_distinct_ids(self, store: CheckpointStore) -> None:
        a = store.start_run(_spec("a"))
        b = store.start_run(_spec("b"))
        assert a != b

    def test_record_ad_persists(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        store.record_ad(run_id, _make_ad("aaa"))
        store.record_ad(run_id, _make_ad("bbb"))
        _spec_back, ids = store.resume_run(run_id)
        assert ids == {"aaa", "bbb"}

    def test_record_ad_is_idempotent(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        store.record_ad(run_id, _make_ad("dup"))
        store.record_ad(run_id, _make_ad("dup"))  # second call must not error
        _spec_back, ids = store.resume_run(run_id)
        assert ids == {"dup"}

    def test_complete_run_sets_status(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        store.complete_run(run_id)
        summary = _only(store.list_runs())
        assert summary.status == "completed"
        assert summary.completed_at is not None

    def test_abort_run_sets_status(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        store.abort_run(run_id)
        summary = _only(store.list_runs())
        assert summary.status == "aborted"
        assert summary.completed_at is not None

    def test_complete_run_unknown_id_raises(self, store: CheckpointStore) -> None:
        with pytest.raises(KeyError):
            store.complete_run("does-not-exist")

    def test_abort_run_unknown_id_raises(self, store: CheckpointStore) -> None:
        with pytest.raises(KeyError):
            store.abort_run("does-not-exist")


# -------------------------------------------------------------------------
# Resume
# -------------------------------------------------------------------------


class TestResume:
    def test_resume_returns_original_spec(self, store: CheckpointStore) -> None:
        original = SearchSpec(
            mode="page_slug",
            query="Nike",
            country="US",
            ad_type="all",
            active_status="active",
        )
        run_id = store.start_run(original)
        loaded, _ids = store.resume_run(run_id)
        assert loaded == original

    def test_resume_returns_scraped_ids(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        for i in range(3):
            store.record_ad(run_id, _make_ad(f"id-{i}"))
        _spec_back, ids = store.resume_run(run_id)
        assert ids == {"id-0", "id-1", "id-2"}

    def test_resume_resets_status_to_in_progress(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        store.complete_run(run_id)
        store.resume_run(run_id)
        summary = _only(store.list_runs())
        assert summary.status == "in_progress"
        assert summary.completed_at is None

    def test_resume_unknown_id_raises(self, store: CheckpointStore) -> None:
        with pytest.raises(KeyError):
            store.resume_run("missing")


# -------------------------------------------------------------------------
# list_runs
# -------------------------------------------------------------------------


class TestListRuns:
    def test_empty_store(self, store: CheckpointStore) -> None:
        assert store.list_runs() == []

    def test_newest_first(self, store: CheckpointStore) -> None:
        first = store.start_run(_spec("first"))
        # Allow the second timestamp to be strictly later than the first
        # so the ORDER BY started_at DESC has a deterministic outcome.
        time.sleep(0.01)
        second = store.start_run(_spec("second"))
        summaries = store.list_runs()
        assert [s.run_id for s in summaries] == [second, first]

    def test_limit_respected(self, store: CheckpointStore) -> None:
        for i in range(5):
            store.start_run(_spec(f"q-{i}"))
            time.sleep(0.001)
        summaries = store.list_runs(limit=3)
        assert len(summaries) == 3

    def test_invalid_limit_raises(self, store: CheckpointStore) -> None:
        with pytest.raises(ValueError, match="limit"):
            store.list_runs(limit=0)

    def test_ad_count_reflects_recorded_ads(self, store: CheckpointStore) -> None:
        run_id = store.start_run(_spec())
        for i in range(7):
            store.record_ad(run_id, _make_ad(f"id-{i}"))
        summary = _only(store.list_runs())
        assert summary.ad_count == 7


# -------------------------------------------------------------------------
# helpers
# -------------------------------------------------------------------------


def _only(summaries: list[RunSummary]) -> RunSummary:
    assert len(summaries) == 1, f"expected exactly one run, got {len(summaries)}"
    return summaries[0]
