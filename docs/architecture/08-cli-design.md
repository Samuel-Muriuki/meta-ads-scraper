# 08 — CLI Design

## Tool: Typer

Modern, Pydantic-aligned, supports rich help output. Three subcommands:
`search`, `resume`, `runs`.

## Surface

```bash
# Start a fresh scrape and persist a checkpoint
meta-ads-scraper search [options]

# Continue a previously-started scrape using its run_id
meta-ads-scraper resume <run_id> [options]

# List recent runs (newest first)
meta-ads-scraper runs [--limit N]
```

## `search` options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--keyword`, `-k` | str | — | Free-text keyword search |
| `--page-url` | str | — | Facebook page URL (`https://www.facebook.com/Nike`) |
| `--page-slug` | str | — | Facebook page slug (`Nike`) |
| `--format` | `json` \| `csv` | `json` | Output format |
| `--out` | path | stdout | Output file path |
| `--max-results` | int | unlimited (1000 ceiling) | Cap on ads returned |
| `--timeout` | int | 300 | Wall-clock budget in seconds |
| `--rate-limit` | float | 1.0 | Requests per second (clamped to `[0.1, 10.0]`) |
| `--concurrency` | int | 1 | Max in-flight scroll iterations (hard ceiling 3) |
| `--no-progress` | flag | off | Suppress the progress bar |
| `-v`, `-vv` | count | 0 | `-v` = INFO, `-vv` = DEBUG with pretty console |

## `resume <run_id>` options

`resume` rehydrates the original `SearchSpec` from the checkpoint and
continues scraping. Accepts the same I/O and pacing flags as `search`
(`--format`, `--out`, `--max-results`, `--timeout`, `--rate-limit`,
`--concurrency`, `--no-progress`, `-v`). Output contains **new ads
only** (ads already recorded in the checkpoint are skipped); merge with
the original output yourself if you need a combined file.

## `runs` options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--limit` | int | 20 | Number of recent runs to show |

Renders a Rich table to **stderr** with Run ID, Mode, Query, Started,
Status, and Ad count. Empty stores print `no runs recorded yet`.

## Mutual exclusion

Exactly one of `--keyword`, `--page-url`, `--page-slug` must be set
on `search`. Enforced via a `_validate_inputs` helper inside `cli.py`:

```python
def _validate_inputs(*, keyword, page_url, page_slug):
    provided = [flag for flag, value in (
        ("--keyword", keyword),
        ("--page-url", page_url),
        ("--page-slug", page_slug),
    ) if value is not None]
    if not provided:
        raise typer.BadParameter(
            "exactly one of --keyword, --page-url, --page-slug must be provided"
        )
    if len(provided) > 1:
        raise typer.BadParameter(
            f"--keyword, --page-url, --page-slug are mutually exclusive; got {', '.join(provided)}"
        )
```

## Output discipline

- **stdout** is reserved for the JSON / CSV payload (when `--out` is
  omitted). Works with shell pipes: `meta-ads-scraper search ... | jq .`
- **stderr** carries everything else: the `run-id` banner at scrape
  start, structlog JSON logs, the rich progress bar (when enabled),
  the `runs` table, and any error messages from the exit-code
  decorator.

## Exit codes (wired in `_typed_exit_codes` decorator)

| Code | Trigger | Source |
|---|---|---|
| 0 | Success | normal command exit |
| 1 | Unhandled exception | typer/Click default for uncaught errors |
| 2 | Bad arguments | typer/Click default for `typer.BadParameter` |
| 3 | `ScraperBlockedError` | CAPTCHA / login wall hit; re-run from a different IP |
| 4 | `TimeoutError` | wall-clock budget exceeded |
| 5 | `tenacity.RetryError` | all retries on a network/transport call exhausted |
| 130 | `KeyboardInterrupt` | Ctrl+C / SIGINT |

The `_typed_exit_codes` decorator in `cli.py` wraps each `@app.command`
function. It catches the four listed exception types at the outermost
layer, emits a one-line stderr message naming the failure mode, and
raises `typer.Exit(<code>)`. Anything else falls through to Click's
default handling (uncaught exceptions become exit 1; `typer.BadParameter`
becomes exit 2).

These let bash scripts handle outcomes:

```bash
meta-ads-scraper search --keyword "shoes" --out shoes.csv
case $? in
  0)   echo "scraped";;
  3)   echo "blocked — try later or from a different IP";;
  4)   echo "ran out of time — bump --timeout or --max-results";;
  5)   echo "network failure — try again later";;
  130) echo "user interrupted";;
  *)   echo "failed";;
esac
```

## Help output

Rich-formatted, with three subcommands. Per-subcommand help shows the
full flag list, defaults, and (for `search`) the mutual-exclusion note.

```
$ meta-ads-scraper --help

Usage: meta-ads-scraper [OPTIONS] COMMAND [ARGS]...

  Scrape structured ad data from Meta's Ad Library.

Commands:
  search    Start a fresh scrape and persist a checkpoint.
  resume    Continue an interrupted scrape using a previously-started run_id.
  runs      List recent scrape runs (most recent first).
```

## Notes on flags not (yet) implemented

The original PLANNING-BRIEF (§9) listed `--country`, `--ad-type`,
`--active-status`, `--dry-run`, and `--screenshot-on-error` as
potential search flags. They are intentionally not on the surface
today:

- **`--country`, `--ad-type`, `--active-status`** — the `SearchSpec`
  model carries these fields with sensible defaults (`country="ALL"`,
  `ad_type="all"`, `active_status="all"`), but the URL resolver does
  not yet thread them through. Worth wiring when a real Hoski use
  case asks for them.
- **`--dry-run`** — adds little value over running with `--out
  /dev/null` (or `NUL` on Windows). Defer.
- **`--screenshot-on-error`** — useful for live-debug sessions; logged
  as a follow-up in `JOURNAL.md` for Phase 7+ if Loom recording shows
  flaky failures worth capturing.
