# Examples

Real output from live scrape runs against Meta's Ad Library. Each file
was produced by an actual command, polite-paced, and committed so
anyone cloning the repo can see real output without burning their own
rate-limit budget.

| File | Mode | Query | Ads | Notes |
|---|---|---|---|---|
| `keyword_shoes.json` | keyword | shoes | 10 | Phase 5 smoke |
| `page_slug_nike.csv` | page_slug | Nike | 10 | Phase 5 smoke |
| `jewelry_demo.json` | keyword | diamond jewelry | 25 | Phase 7 vertical demo |
| `dental_demo.json` | keyword | dental implants | 24 | Phase 7 vertical demo (pagination_stalled at 24 — natural end) |
| `automotive_demo.json` | keyword | luxury cars | 25 | Phase 7 vertical demo |

The Phase 7 vertical demos were captured during the submission pass at
`--rate-limit 0.5 --max-results 25 --no-progress`. Run-ids and per-run
durations live in `demo_runs.log` alongside this README.

## Reproducing

```bash
# Phase 5 smokes
python -m meta_ads_scraper search --keyword shoes --max-results 10 \
    --format json --out examples/keyword_shoes.json --rate-limit 0.5
python -m meta_ads_scraper search --page-slug Nike --max-results 10 \
    --format csv --out examples/page_slug_nike.csv --rate-limit 0.5

# Phase 7 vertical demos
python -m meta_ads_scraper search --keyword "diamond jewelry" \
    --max-results 25 --rate-limit 0.5 --format json \
    --out examples/jewelry_demo.json --no-progress
python -m meta_ads_scraper search --keyword "dental implants" \
    --max-results 25 --rate-limit 0.5 --format json \
    --out examples/dental_demo.json --no-progress
python -m meta_ads_scraper search --keyword "luxury cars" \
    --max-results 25 --rate-limit 0.5 --format json \
    --out examples/automotive_demo.json --no-progress
```

## Sustained-load demonstration

`stress_test_500ads.json` + `stress_test.log` (Phase 7 Task 3) exercise
the rate limiter and retry layer over a longer scrape. See those files
for the full run record.

## Known cosmetic issue

`ad_creative_text` contains Meta's layout artifacts (zero-width
spaces, `Active` / `Sponsored` labels, `Started running on...`
metadata, `Platforms` headers). Real ad copy starts after the
`Sponsored` marker. A post-processor in `parsers/ad_card.py` is
logged in `.project/journal/JOURNAL.md` as a deferred polish item —
the records are functional and contain the right data, just verbose.
