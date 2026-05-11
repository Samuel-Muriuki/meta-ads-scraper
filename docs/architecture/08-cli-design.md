# 08 — CLI Design

## Tool: Typer

Modern, Pydantic-aligned, supports rich help output.

## Surface

```bash
# Primary command: search
meta-ads-scraper search [OPTIONS]

# Sub-command: resume
meta-ads-scraper resume <RUN_ID>

# Sub-command: version
meta-ads-scraper version
```

## search options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--keyword` | str | None | Search by free-text keyword |
| `--page-url` | str | None | Search by Facebook page URL |
| `--page-slug` | str | None | Search by Facebook page slug (e.g., "Nike") |
| `--country` | str | "ALL" | ISO 3166-1 alpha-2 or "ALL" |
| `--ad-type` | enum | "all" | all, political_and_issue_ads |
| `--active-status` | enum | "all" | all, active, inactive |
| `--max-results` | int | None | Cap on results (hard ceiling 1000) |
| `--timeout` | int | 300 | Total run time in seconds |
| `--format` | enum | "json" | csv, json |
| `--out` | path | stdout | Output file path |
| `--rate-limit` | float | 1.0 | Requests per second |
| `--concurrency` | int | 1 | Concurrent browser tabs (max 3) |
| `--dry-run` | flag | false | Don't write output |
| `--no-progress` | flag | false | Suppress progress bar |
| `--screenshot-on-error` | flag | false | Dump page state on failures |
| `-v / -vv` | flag | 0 | Verbose (INFO / DEBUG) |

## Mutual exclusion

Exactly one of `--keyword`, `--page-url`, `--page-slug` must be set. Enforce via Typer callback:

```python
@app.command()
def search(
    keyword: Optional[str] = typer.Option(None),
    page_url: Optional[str] = typer.Option(None),
    page_slug: Optional[str] = typer.Option(None),
    ...,
):
    inputs = [keyword, page_url, page_slug]
    set_count = sum(1 for x in inputs if x is not None)
    if set_count != 1:
        raise typer.BadParameter(
            "Exactly one of --keyword, --page-url, --page-slug must be set"
        )
```

## Output behaviour

- **No `--out`** → stdout (works with shell pipes: `python -m meta_ads_scraper ... | jq .`)
- **`--out file.csv`** → writes to file, prints summary line to stdout
- **`--format` mismatched with `--out` extension** → format wins; warn but proceed

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic error |
| 2 | Argument parsing error (Typer default) |
| 3 | ScraperBlockedError (CAPTCHA / login) |
| 4 | Timeout exceeded |
| 5 | Network unrecoverable |
| 130 | User interrupt (Ctrl+C) |

These let bash scripts handle outcomes:
```bash
python -m meta_ads_scraper search --keyword "shoes" --out shoes.csv
case $? in
  0) echo "scraped";;
  3) echo "blocked — try later or use auth";;
  *) echo "failed";;
esac
```

## Help output

Rich-formatted, with examples:

```
$ meta-ads-scraper search --help

Usage: meta-ads-scraper search [OPTIONS]

  Search Meta Ad Library by keyword, page URL, or page slug.

  Exactly one of --keyword, --page-url, --page-slug is required.

Examples:
  meta-ads-scraper search --keyword "dental practices" --max-results 50
  meta-ads-scraper search --page-slug Nike --format csv --out nike.csv
  meta-ads-scraper search --page-url https://www.facebook.com/Nike

Options:
  ...
```
