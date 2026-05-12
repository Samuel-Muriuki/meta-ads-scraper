"""Slim and scrub a captured HAR fixture before committing.

Capturing against live Meta produces a ~15 MB HAR dominated by JPEG /
MP4 / WebP responses that are irrelevant for offline DOM-replay tests.
This script:

1. Filters entries to keep only the hosts and MIME types the scraper
   actually exercises (page HTML, JS bundles, GraphQL/XHR responses).
2. Scrubs ``Cookie`` and ``Authorization`` headers in both request and
   response (replaced with ``<SCRUBBED>``).
3. Writes the result back to the same path, compactly formatted to
   keep the diff small.

Usage::

    .venv\\Scripts\\Activate.ps1 ; python scripts/slim_har.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HAR_PATH = Path("tests/fixtures/har/keyword_shoes_paginated.har")

KEEP_HOSTS = frozenset(
    [
        "www.facebook.com",
        "web.facebook.com",
        "static.xx.fbcdn.net",
    ]
)
KEEP_MIMES = frozenset(
    [
        "text/html",
        "text/plain",
        "application/json",
        "application/javascript",
        "application/x-javascript",
        "x-unknown",
    ]
)
SCRUB_HEADER_NAMES = frozenset(
    [
        "cookie",
        "set-cookie",
        "authorization",
        "x-fb-debug",
        "x-fb-rlafr",
        "x-fb-connection-quality",
    ]
)


def _scrub_headers(headers: list[dict[str, Any]]) -> int:
    scrubbed = 0
    for h in headers:
        if h.get("name", "").lower() in SCRUB_HEADER_NAMES:
            h["value"] = "<SCRUBBED>"
            scrubbed += 1
    return scrubbed


def _host_of(url: str) -> str:
    if "://" not in url:
        return ""
    return url.split("/", 3)[2]


def main() -> None:
    har = json.loads(HAR_PATH.read_text("utf-8"))
    entries = har["log"]["entries"]
    before_n = len(entries)
    before_size = HAR_PATH.stat().st_size

    kept: list[dict[str, Any]] = []
    total_scrubbed = 0
    for entry in entries:
        url = entry.get("request", {}).get("url", "")
        host = _host_of(url)
        mime = (
            entry.get("response", {})
            .get("content", {})
            .get("mimeType", "")
            .split(";", 1)[0]
            .strip()
        )
        if host not in KEEP_HOSTS and mime not in KEEP_MIMES:
            continue
        total_scrubbed += _scrub_headers(entry.get("request", {}).get("headers", []))
        total_scrubbed += _scrub_headers(entry.get("response", {}).get("headers", []))
        kept.append(entry)

    har["log"]["entries"] = kept

    # Compact write so the file diff stays small.
    HAR_PATH.write_text(json.dumps(har, separators=(",", ":")), encoding="utf-8")

    after_n = len(kept)
    after_size = HAR_PATH.stat().st_size
    print(f"entries: {before_n} -> {after_n}", file=sys.stderr)
    print(f"size:    {before_size:,} -> {after_size:,} bytes", file=sys.stderr)
    print(f"scrubbed: {total_scrubbed} sensitive header values", file=sys.stderr)


if __name__ == "__main__":
    main()
