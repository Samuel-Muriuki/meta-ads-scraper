# Examples

Real output from live scrape runs against Meta's Ad Library. Generated
during Phase 5 with `--rate-limit 0.5 --max-results 10 --no-progress`
so the runs were polite and bounded in size.

| File | Command | Rows | Format |
|---|---|---|---|
| `keyword_shoes.json` | `python -m meta_ads_scraper search --keyword shoes --max-results 10 --format json --out examples/keyword_shoes.json --rate-limit 0.5` | 10 | JSON |
| `page_slug_nike.csv` | `python -m meta_ads_scraper search --page-slug Nike --max-results 10 --format csv --out examples/page_slug_nike.csv --rate-limit 0.5` | 10 | CSV |

The Phase 7 demo runs against Hoski-relevant verticals (dental,
jewelry, automotive) will replace or augment this set; these two files
exist so anyone cloning the repo can see real output without burning
their own rate-limit budget.

## Known cosmetic issue

`ad_creative_text` contains Meta's layout artifacts (zero-width
spaces, `Active` / `Sponsored` labels, `Started running on...`
metadata, `Platforms` headers). Real ad copy starts after the
`Sponsored` marker. A post-processor in `parsers/ad_card.py` is
logged in `.project/journal/JOURNAL.md` as a deferred Phase 5/6 polish
item — the records are functional and contain the right data, just
verbose.
