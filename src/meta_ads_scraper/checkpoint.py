"""SQLite-backed checkpoint store for scrape runs.

Records two flavours of state:

* **runs** — one row per scrape invocation. Stores the original
  ``SearchSpec`` JSON, lifecycle timestamps, and status
  (``in_progress`` / ``completed`` / ``aborted``).
* **scraped_ads** — composite-key (run_id, ad_library_id) so that
  re-running with the same ``run_id`` (resume) lets us skip already-
  scraped ads via ``scroll_and_collect``'s ``yielded_ids`` seam.

The store is intentionally a thin wrapper over ``sqlite3``: no ORM, no
migrations framework, no async. Each public method opens a short-lived
connection in autocommit mode (``isolation_level=None``), so a crash
mid-write loses at most one statement.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog

from .models import Ad, SearchSpec

logger = structlog.get_logger()

__all__ = [
    "DEFAULT_DB_PATH",
    "CheckpointStore",
    "RunSummary",
]


DEFAULT_DB_PATH = Path("data") / "runs.sqlite"
"""Default location for the checkpoint DB. ``data/`` is gitignored."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    search_spec_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL
        CHECK(status IN ('in_progress', 'completed', 'aborted'))
);

CREATE TABLE IF NOT EXISTS scraped_ads (
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    ad_library_id TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    PRIMARY KEY (run_id, ad_library_id)
);

CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at DESC);
"""


_STATUS_IN_PROGRESS = "in_progress"
_STATUS_COMPLETED = "completed"
_STATUS_ABORTED = "aborted"


@dataclass(frozen=True)
class RunSummary:
    """A single row of the runs table plus a denormalised ad count."""

    run_id: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    spec: SearchSpec
    ad_count: int


class CheckpointStore:
    """SQLite-backed run + ad checkpoint store.

    Concurrency: instances are intended for a single asyncio event loop.
    Each method opens its own connection so there is no shared cursor
    state. SQLite serialises writes at the file level.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
        logger.debug("checkpoint_store_ready", db_path=str(self._db_path))

    @property
    def db_path(self) -> Path:
        return self._db_path

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_run(self, spec: SearchSpec) -> str:
        """Persist a new run, return its uuid4 ``run_id``."""
        run_id = uuid.uuid4().hex
        now = _utcnow_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, search_spec_json, started_at, status)"
                " VALUES (?, ?, ?, ?)",
                (run_id, spec.model_dump_json(), now, _STATUS_IN_PROGRESS),
            )
        logger.info("run_started", run_id=run_id, mode=spec.mode, query=spec.query)
        return run_id

    def record_ad(self, run_id: str, ad: Ad) -> None:
        """Record one scraped ad. Idempotent on (run_id, ad_library_id)."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO scraped_ads (run_id, ad_library_id, scraped_at)"
                " VALUES (?, ?, ?)",
                (run_id, ad.ad_library_id, _utcnow_iso()),
            )

    def complete_run(self, run_id: str) -> None:
        """Mark a run as cleanly completed."""
        self._set_terminal_status(run_id, _STATUS_COMPLETED)
        logger.info("run_completed", run_id=run_id)

    def abort_run(self, run_id: str) -> None:
        """Mark a run as aborted (exception, signal, etc.)."""
        self._set_terminal_status(run_id, _STATUS_ABORTED)
        logger.info("run_aborted", run_id=run_id)

    # ------------------------------------------------------------------
    # Resume / inspection
    # ------------------------------------------------------------------

    def resume_run(self, run_id: str) -> tuple[SearchSpec, set[str]]:
        """Load the spec + already-scraped ad ids for ``run_id``.

        Re-marks the run as ``in_progress`` so a subsequent abort/complete
        records the new terminal state correctly.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT search_spec_json FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"no run with run_id={run_id!r}")
            spec = SearchSpec.model_validate_json(row[0])

            id_rows = conn.execute(
                "SELECT ad_library_id FROM scraped_ads WHERE run_id = ?", (run_id,)
            ).fetchall()
            scraped_ids = {r[0] for r in id_rows}

            conn.execute(
                "UPDATE runs SET status = ?, completed_at = NULL WHERE run_id = ?",
                (_STATUS_IN_PROGRESS, run_id),
            )

        logger.info(
            "run_resumed",
            run_id=run_id,
            mode=spec.mode,
            query=spec.query,
            already_scraped=len(scraped_ids),
        )
        return spec, scraped_ids

    def list_runs(self, limit: int = 20) -> list[RunSummary]:
        """Return the most recent runs, newest first."""
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit!r}")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.run_id, r.search_spec_json, r.started_at, r.completed_at,
                       r.status,
                       (SELECT COUNT(*) FROM scraped_ads s WHERE s.run_id = r.run_id)
                FROM runs r
                ORDER BY r.started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            RunSummary(
                run_id=row[0],
                spec=SearchSpec.model_validate_json(row[1]),
                started_at=_parse_iso(row[2]),
                completed_at=_parse_iso(row[3]) if row[3] is not None else None,
                status=row[4],
                ad_count=row[5],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()

    def _set_terminal_status(self, run_id: str, status: str) -> None:
        now = _utcnow_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE runs SET status = ?, completed_at = ? WHERE run_id = ?",
                (status, now, run_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"no run with run_id={run_id!r}")


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)
