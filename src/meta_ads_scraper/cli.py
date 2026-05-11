from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Annotated, TextIO

import typer

from .exporters import write_ads_csv, write_ads_json
from .models import Ad, SearchSpec
from .scraper.playwright_scraper import PlaywrightScraper

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
        int,
        typer.Option("--max-results", help="Maximum ads returned."),
    ] = 10,
) -> None:
    _validate_inputs(keyword=keyword, page_url=page_url, page_slug=page_slug)
    exporter = _select_exporter(format_)

    spec = _build_spec(keyword=keyword, page_url=page_url, page_slug=page_slug)
    ads = asyncio.run(_run_search(spec, max_results=max_results))

    if out is not None:
        count = exporter(ads, out)
        typer.echo(f"wrote {count} ad(s) to {out}", err=True)
    else:
        exporter(ads, sys.stdout)
        sys.stdout.write("\n")


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


def _build_spec(*, keyword: str | None, page_url: str | None, page_slug: str | None) -> SearchSpec:
    if keyword is not None:
        return SearchSpec(mode="keyword", query=keyword)
    if page_url is not None:
        return SearchSpec(mode="page_url", query=page_url)
    assert page_slug is not None
    return SearchSpec(mode="page_slug", query=page_slug)


async def _run_search(spec: SearchSpec, max_results: int) -> list[Ad]:
    ads: list[Ad] = []
    async with PlaywrightScraper() as scraper:
        async for ad in scraper.search(spec):
            ads.append(ad)
            if len(ads) >= max_results:
                break
    return ads
