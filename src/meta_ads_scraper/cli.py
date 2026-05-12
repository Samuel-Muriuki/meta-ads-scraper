from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Annotated, TextIO

import structlog
import typer
from rich.console import Console
from rich.table import Table

from .checkpoint import CheckpointStore, RunSummary
from .exporters import write_ads_csv, write_ads_json
from .logging_config import configure_logging
from .models import Ad, SearchSpec
from .rate_limit import MAX_CONCURRENCY_CEILING
from .scraper.playwright_scraper import PlaywrightScraper

logger = structlog.get_logger()

_MIN_RATE_LIMIT = 0.1
_MAX_RATE_LIMIT = 10.0

_Exporter = Callable[[Iterable[Ad], "Path | TextIO"], int]
_EXPORTERS: dict[str, _Exporter] = {
    "json": write_ads_json,
    "csv": write_ads_csv,
}

app = typer.Typer(
    name="meta-ads-scraper",
    help="Scrape structured ad data from Meta's Ad Library.",
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    pass


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
def search(
    keyword: Annotated[
        str | None,
        typer.Option(
            "--keyword",
            "-k",
            help="Keyword search. Mutually exclusive with --page-url and --page-slug.",
        ),
    ] = None,
    page_url: Annotated[
        str | None,
        typer.Option(
            "--page-url",
            help="Facebook page URL. Mutually exclusive with --keyword and --page-slug.",
        ),
    ] = None,
    page_slug: Annotated[
        str | None,
        typer.Option(
            "--page-slug",
            help="Facebook page slug. Mutually exclusive with --keyword and --page-url.",
        ),
    ] = None,
    format_: Annotated[
        str,
        typer.Option("--format", help="Output format: json or csv."),
    ] = "json",
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Output file path. Defaults to stdout."),
    ] = None,
    max_results: Annotated[
        int | None,
        typer.Option(
            "--max-results",
            help="Cap on ads returned. Unset or 0 = unlimited (clamped to 1000 ceiling).",
        ),
    ] = None,
    timeout_seconds: Annotated[
        int,
        typer.Option(
            "--timeout",
            help="Wall-clock budget for the scrape, in seconds.",
        ),
    ] = 300,
    rate_limit: Annotated[
        float,
        typer.Option(
            "--rate-limit",
            help=(
                "Requests per second to upstream. Clamped to "
                f"[{_MIN_RATE_LIMIT}, {_MAX_RATE_LIMIT}]."
            ),
        ),
    ] = 1.0,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            help=(
                "Max in-flight scroll iterations. Hard-clamped to "
                f"{MAX_CONCURRENCY_CEILING}; higher values log a warning."
            ),
        ),
    ] = 1,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Increase log verbosity. -v = INFO, -vv = DEBUG (pretty console).",
        ),
    ] = 0,
) -> None:
    """Start a fresh scrape and persist a checkpoint."""
    configure_logging(verbosity=verbose)
    _validate_inputs(keyword=keyword, page_url=page_url, page_slug=page_slug)
    rate_limit = _clamp_rate_limit(rate_limit)
    exporter = _select_exporter(format_)

    spec = _build_spec(keyword=keyword, page_url=page_url, page_slug=page_slug)
    checkpoint = CheckpointStore()
    run_id = checkpoint.start_run(spec)
    typer.echo(f"run-id: {run_id}", err=True)

    ads = _execute_scrape(
        spec=spec,
        checkpoint=checkpoint,
        run_id=run_id,
        yielded_ids=None,
        max_results=max_results,
        timeout_seconds=timeout_seconds,
        rate_limit=rate_limit,
        concurrency=concurrency,
    )

    _write_output(ads, exporter=exporter, out=out)


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


@app.command()
def resume(
    run_id: Annotated[str, typer.Argument(help="The run_id printed by `search`.")],
    format_: Annotated[
        str,
        typer.Option("--format", help="Output format for newly-scraped ads."),
    ] = "json",
    out: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help=(
                "Output file path for NEW ads only. The resumed run does not "
                "rewrite the original output; merge yourself if you need a combined file."
            ),
        ),
    ] = None,
    max_results: Annotated[
        int | None,
        typer.Option(
            "--max-results",
            help="Additional cap on this resume leg (counts only NEW ads).",
        ),
    ] = None,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", help="Wall-clock budget for this resume leg, in seconds."),
    ] = 300,
    rate_limit: Annotated[
        float,
        typer.Option(
            "--rate-limit",
            help=(
                "Requests per second to upstream. Clamped to "
                f"[{_MIN_RATE_LIMIT}, {_MAX_RATE_LIMIT}]."
            ),
        ),
    ] = 1.0,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            help=(
                "Max in-flight scroll iterations. Hard-clamped to "
                f"{MAX_CONCURRENCY_CEILING}; higher values log a warning."
            ),
        ),
    ] = 1,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Increase log verbosity. -v = INFO, -vv = DEBUG (pretty console).",
        ),
    ] = 0,
) -> None:
    """Continue an interrupted scrape using a previously-started run_id."""
    configure_logging(verbosity=verbose)
    rate_limit = _clamp_rate_limit(rate_limit)
    exporter = _select_exporter(format_)
    checkpoint = CheckpointStore()

    try:
        spec, yielded_ids = checkpoint.resume_run(run_id)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        f"resuming run-id: {run_id} ({len(yielded_ids)} ads already scraped)",
        err=True,
    )

    ads = _execute_scrape(
        spec=spec,
        checkpoint=checkpoint,
        run_id=run_id,
        yielded_ids=yielded_ids,
        max_results=max_results,
        timeout_seconds=timeout_seconds,
        rate_limit=rate_limit,
        concurrency=concurrency,
    )

    _write_output(ads, exporter=exporter, out=out)


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------


@app.command()
def runs(
    limit: Annotated[
        int,
        typer.Option("--limit", help="Number of recent runs to show (default 20)."),
    ] = 20,
) -> None:
    """List recent scrape runs (most recent first)."""
    checkpoint = CheckpointStore()
    summaries = checkpoint.list_runs(limit=limit)
    _render_runs_table(summaries)


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _validate_inputs(*, keyword: str | None, page_url: str | None, page_slug: str | None) -> None:
    provided = [
        flag
        for flag, value in (
            ("--keyword", keyword),
            ("--page-url", page_url),
            ("--page-slug", page_slug),
        )
        if value is not None
    ]
    if not provided:
        raise typer.BadParameter(
            "exactly one of --keyword, --page-url, --page-slug must be provided"
        )
    if len(provided) > 1:
        raise typer.BadParameter(
            f"--keyword, --page-url, --page-slug are mutually exclusive; got {', '.join(provided)}"
        )


def _select_exporter(format_: str) -> _Exporter:
    exporter = _EXPORTERS.get(format_)
    if exporter is None:
        raise typer.BadParameter(f"unknown format: {format_!r}; choose one of {sorted(_EXPORTERS)}")
    return exporter


def _clamp_rate_limit(rate_limit: float) -> float:
    if rate_limit < _MIN_RATE_LIMIT:
        raise typer.BadParameter(f"--rate-limit must be >= {_MIN_RATE_LIMIT}, got {rate_limit}")
    if rate_limit > _MAX_RATE_LIMIT:
        raise typer.BadParameter(f"--rate-limit must be <= {_MAX_RATE_LIMIT}, got {rate_limit}")
    return rate_limit


def _build_spec(*, keyword: str | None, page_url: str | None, page_slug: str | None) -> SearchSpec:
    if keyword is not None:
        return SearchSpec(mode="keyword", query=keyword)
    if page_url is not None:
        return SearchSpec(mode="page_url", query=page_url)
    assert page_slug is not None
    return SearchSpec(mode="page_slug", query=page_slug)


def _execute_scrape(
    *,
    spec: SearchSpec,
    checkpoint: CheckpointStore,
    run_id: str,
    yielded_ids: set[str] | None,
    max_results: int | None,
    timeout_seconds: int,
    rate_limit: float,
    concurrency: int,
) -> list[Ad]:
    """Run the scrape under a checkpoint lifecycle and return collected ads.

    Marks the run as completed on a clean async exit, aborted on any
    exception. The exception is then re-raised so the CLI exits non-zero.
    """
    try:
        ads = asyncio.run(
            _drive_scraper(
                spec=spec,
                checkpoint=checkpoint,
                run_id=run_id,
                yielded_ids=yielded_ids,
                max_results=max_results,
                timeout_seconds=timeout_seconds,
                rate_limit=rate_limit,
                concurrency=concurrency,
            )
        )
    except BaseException:
        checkpoint.abort_run(run_id)
        raise
    checkpoint.complete_run(run_id)
    return ads


async def _drive_scraper(
    *,
    spec: SearchSpec,
    checkpoint: CheckpointStore,
    run_id: str,
    yielded_ids: set[str] | None,
    max_results: int | None,
    timeout_seconds: int,
    rate_limit: float,
    concurrency: int,
) -> list[Ad]:
    ads: list[Ad] = []
    async with PlaywrightScraper(
        max_results=max_results,
        timeout_seconds=timeout_seconds,
        rate_limit=rate_limit,
        concurrency=concurrency,
        checkpoint=checkpoint,
        run_id=run_id,
        yielded_ids=yielded_ids,
    ) as scraper:
        async for ad in scraper.search(spec):
            ads.append(ad)
    return ads


def _write_output(
    ads: list[Ad],
    *,
    exporter: _Exporter,
    out: Path | None,
) -> None:
    if out is not None:
        count = exporter(ads, out)
        typer.echo(f"wrote {count} ad(s) to {out}", err=True)
    else:
        exporter(ads, sys.stdout)
        sys.stdout.write("\n")


def _render_runs_table(summaries: list[RunSummary]) -> None:
    # Table renders to stderr so it does not contaminate stdout pipes.
    console = Console(stderr=True)
    table = Table(title="Recent scrape runs")
    table.add_column("Run ID")
    table.add_column("Mode")
    table.add_column("Query")
    table.add_column("Started", justify="right")
    table.add_column("Status")
    table.add_column("Ads", justify="right")

    if not summaries:
        console.print("[dim]no runs recorded yet[/dim]")
        return

    for s in summaries:
        table.add_row(
            s.run_id,
            s.spec.mode,
            s.spec.query,
            s.started_at.strftime("%Y-%m-%d %H:%M"),
            s.status,
            str(s.ad_count),
        )
    console.print(table)
