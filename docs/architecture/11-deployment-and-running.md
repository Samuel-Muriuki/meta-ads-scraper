# 11 — Deployment & Running

## Local dev

```bash
git clone https://github.com/Samuel-Muriuki/meta-ads-scraper.git
cd meta-ads-scraper
bash bootstrap.sh
source .venv/bin/activate

python -m meta_ads_scraper search --keyword "dental" --max-results 20 --format csv --out dental.csv
```

## Running on a server

This scraper assumes a single-machine deployment. For cron-driven scheduled runs:

```cron
# crontab -e
0 3 * * * cd /opt/meta-ads-scraper && /opt/meta-ads-scraper/.venv/bin/python -m meta_ads_scraper search --keyword "dental" --out /var/lib/meta-ads/dental-$(date +\%Y\%m\%d).csv
```

Pre-reqs on the server:
- Python 3.11+
- Playwright system deps: `playwright install-deps chromium`
- Sufficient disk for `data/` (browser profile + checkpoint SQLite)

## Running in Docker (future)

Not in MVP. If added:
- Use `mcr.microsoft.com/playwright/python:v1.45.0-focal` as base
- Mount `data/` as a volume
- Set `PLAYWRIGHT_BROWSERS_PATH=0` to use the prebuilt browsers
- Run as non-root user

## Running on GHA (CI)

CI uses the workflow at `.github/workflows/ci.yml`. Smoke tests against real Meta are gated to `workflow_dispatch` to avoid rate-limit penalties on every push.

## What this scraper is NOT designed for

- Multi-machine coordination
- High-throughput scraping (>1000 ads/hour)
- Real-time feeds
- Production CRM integration (use webhooks to GoHighLevel separately)

For Hoski's use case (periodic competitive intel runs, ~50-500 ads per run, weekly cadence), the single-machine cron pattern is enough.
