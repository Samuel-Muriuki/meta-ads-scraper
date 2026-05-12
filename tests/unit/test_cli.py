from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import pytest
import typer
from tenacity import RetryError
from typer.testing import CliRunner

from meta_ads_scraper.checkpoint import CheckpointStore
from meta_ads_scraper.cli import (
    EXIT_BLOCKED,
    EXIT_INTERRUPT,
    EXIT_NETWORK,
    EXIT_TIMEOUT,
    _typed_exit_codes,
    app,
)
from meta_ads_scraper.exceptions import ScraperBlockedError
from meta_ads_scraper.models import Ad, SearchSpec

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_RE.sub("", text)


@pytest.fixture
def in_tmp_cwd(tmp_path: Path) -> Path:
    """Run the CLI inside ``tmp_path`` so the default ``data/runs.sqlite``
    location is per-test isolated.
    """
    original = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(original)


def _seed_run(tmp: Path, query: str = "shoes") -> str:
    """Create a checkpoint store at the default location and return a
    fresh run_id with one ad already recorded.
    """
    store = CheckpointStore(tmp / "data" / "runs.sqlite")
    run_id = store.start_run(SearchSpec(mode="keyword", query=query))
    store.record_ad(
        run_id,
        Ad(
            ad_library_id="seed-001",
            page_id="100",
            collected_at=datetime.now().astimezone(),
            source_url="https://www.facebook.com/ads/library/?q=shoes",
        ),
    )
    return run_id


# -------------------------------------------------------------------------
# search: input validation (existing tests)
# -------------------------------------------------------------------------


class TestMutualExclusion:
    def test_no_input_flags_rejected(self) -> None:
        result = runner.invoke(app, ["search"])
        assert result.exit_code != 0
        assert "exactly one" in _plain(result.output).lower()

    def test_keyword_and_page_url_rejected(self) -> None:
        result = runner.invoke(
            app,
            ["search", "--keyword", "shoes", "--page-url", "https://www.facebook.com/Nike"],
        )
        assert result.exit_code != 0
        combined = _plain(result.output).lower()
        assert "mutually exclusive" in combined
        assert "--keyword" in combined
        assert "--page-url" in combined

    def test_keyword_and_page_slug_rejected(self) -> None:
        result = runner.invoke(
            app,
            ["search", "--keyword", "shoes", "--page-slug", "Nike"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in _plain(result.output).lower()

    def test_all_three_rejected(self) -> None:
        result = runner.invoke(
            app,
            [
                "search",
                "--keyword",
                "shoes",
                "--page-url",
                "https://www.facebook.com/Nike",
                "--page-slug",
                "Nike",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in _plain(result.output).lower()


class TestFormatValidation:
    def test_unknown_format_rejected(self) -> None:
        result = runner.invoke(app, ["search", "--keyword", "x", "--format", "yaml"])
        assert result.exit_code != 0
        combined = _plain(result.output).lower()
        assert "unknown format" in combined
        assert "yaml" in combined


# -------------------------------------------------------------------------
# help output for the three subcommands
# -------------------------------------------------------------------------


class TestHelp:
    def test_search_help_documents_mutual_exclusion(self) -> None:
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "Mutually exclusive" in _plain(result.output)
        for flag in ("--keyword", "--page-url", "--page-slug"):
            assert flag in _plain(result.output)

    def test_search_help_shows_no_progress_flag(self) -> None:
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--no-progress" in _plain(result.output)

    def test_resume_help_shows_run_id_argument(self) -> None:
        result = runner.invoke(app, ["resume", "--help"])
        assert result.exit_code == 0
        output = _plain(result.output).lower()
        assert "run_id" in output or "run-id" in output

    def test_resume_help_shows_no_progress_flag(self) -> None:
        result = runner.invoke(app, ["resume", "--help"])
        assert result.exit_code == 0
        assert "--no-progress" in _plain(result.output)

    def test_runs_help_shows_limit_flag(self) -> None:
        result = runner.invoke(app, ["runs", "--help"])
        assert result.exit_code == 0
        assert "--limit" in _plain(result.output)

    def test_root_help_lists_all_three_commands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output = _plain(result.output)
        assert "search" in output
        assert "resume" in output
        assert "runs" in output


# -------------------------------------------------------------------------
# resume command
# -------------------------------------------------------------------------


class TestResumeCommand:
    def test_unknown_run_id_errors_cleanly(self, in_tmp_cwd: Path) -> None:
        result = runner.invoke(app, ["resume", "deadbeef-not-a-real-run"])
        assert result.exit_code != 0
        assert "deadbeef-not-a-real-run" in _plain(result.output)

    def test_missing_run_id_argument_errors(self) -> None:
        result = runner.invoke(app, ["resume"])
        assert result.exit_code != 0


# -------------------------------------------------------------------------
# runs command
# -------------------------------------------------------------------------


class TestRunsCommand:
    def test_empty_store_shows_no_runs_message(self, in_tmp_cwd: Path) -> None:
        result = runner.invoke(app, ["runs"])
        assert result.exit_code == 0
        assert "no runs recorded yet" in _plain(result.output).lower()

    def test_lists_seeded_runs(self, in_tmp_cwd: Path) -> None:
        _seed_run(in_tmp_cwd, query="shoes")
        result = runner.invoke(app, ["runs"])
        assert result.exit_code == 0
        output = _plain(result.output)
        assert "shoes" in output
        assert "keyword" in output

    def test_limit_flag_accepted(self, in_tmp_cwd: Path) -> None:
        for q in ("a", "b", "c"):
            _seed_run(in_tmp_cwd, query=q)
        result = runner.invoke(app, ["runs", "--limit", "2"])
        assert result.exit_code == 0


# -------------------------------------------------------------------------
# --no-progress
# -------------------------------------------------------------------------


class TestNoProgress:
    def test_search_accepts_no_progress(self) -> None:
        # --no-progress + bad input still errors at validation; we just
        # want to confirm the flag parses without "unknown option".
        result = runner.invoke(
            app,
            ["search", "--no-progress", "--keyword", "x", "--format", "yaml"],
        )
        # Errors on the bad --format, not on --no-progress.
        assert "no such option" not in _plain(result.output).lower()
        assert "unknown format" in _plain(result.output).lower()

    def test_resume_accepts_no_progress(self, in_tmp_cwd: Path) -> None:
        result = runner.invoke(
            app,
            ["resume", "--no-progress", "missing-run-id"],
        )
        assert "no such option" not in _plain(result.output).lower()


# -------------------------------------------------------------------------
# Typed exit codes
# -------------------------------------------------------------------------


class TestTypedExitCodes:
    """Each documented failure mode maps to the right exit code.

    Tested at the decorator boundary so the assertions stay independent
    of which command (search/resume/runs) raised. Per
    ``docs/architecture/08-cli-design.md``.
    """

    def test_scraper_blocked_maps_to_3(self) -> None:
        @_typed_exit_codes
        def fn() -> None:
            raise ScraperBlockedError("login wall")

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == EXIT_BLOCKED == 3

    def test_timeout_maps_to_4(self) -> None:
        @_typed_exit_codes
        def fn() -> None:
            raise TimeoutError("budget exceeded")

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == EXIT_TIMEOUT == 4

    def test_retry_error_maps_to_5(self) -> None:
        @_typed_exit_codes
        def fn() -> None:
            # tenacity.RetryError takes a "last_attempt" Future; we
            # don't need a real one for the type-mapping test.
            raise RetryError(last_attempt=None)  # type: ignore[arg-type]

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == EXIT_NETWORK == 5

    def test_keyboard_interrupt_maps_to_130(self) -> None:
        @_typed_exit_codes
        def fn() -> None:
            raise KeyboardInterrupt

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == EXIT_INTERRUPT == 130

    def test_unhandled_exception_propagates(self) -> None:
        @_typed_exit_codes
        def fn() -> None:
            raise ValueError("not in the map")

        # Falls through to typer/Click's default handler -> exit 1.
        with pytest.raises(ValueError, match="not in the map"):
            fn()

    def test_return_value_passes_through(self) -> None:
        @_typed_exit_codes
        def fn() -> int:
            return 42

        assert fn() == 42
