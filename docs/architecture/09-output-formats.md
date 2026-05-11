# 09 — Output Formats

## CSV

- UTF-8 with BOM (Excel-compatible)
- All Pydantic fields become columns
- List fields joined with `;` (semicolon, not comma — comma is the delimiter)
- Datetimes as ISO 8601 with timezone
- Dates as ISO 8601 (`2026-03-15`)
- None becomes empty cell

Header row uses snake_case field names.

```csv
ad_library_id,page_id,collected_at,source_url,page_name,page_url,...
"123","456","2026-05-11T12:00:00+00:00","https://...","Nike","https://...",...
```

## JSON

- Indented (2 spaces) for readability
- Native list/dict for nested fields
- ISO 8601 strings for datetimes/dates
- `null` for None
- Wrapped in a top-level array

```json
[
  {
    "ad_library_id": "123",
    "page_id": "456",
    "collected_at": "2026-05-11T12:00:00+00:00",
    "source_url": "https://www.facebook.com/ads/library/?id=123",
    "page_name": "Nike",
    "platforms": ["FACEBOOK", "INSTAGRAM"],
    ...
  }
]
```

## Streaming vs buffered

For MVP: buffer everything in memory, write at the end.

Justification:
- Max results capped at 1000
- ~1KB per ad → ~1MB max
- Streaming JSON arrays is non-trivial (commas, brackets)
- CSV streaming via `csv.DictWriter` is fine but complicates resume

Future enhancement: streaming via JSON Lines (`.jsonl`) format.
