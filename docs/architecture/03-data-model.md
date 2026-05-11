# 03 — Data Model

See `docs/contracts/ad-data-schema.md` for the full contract. This file is a thin orientation; the contract is the source of truth.

## Two models, both Pydantic v2

1. `Ad` — the output. One per scraped ad. Frozen, validated, type-safe.
2. `SearchSpec` — the input. Built from CLI args. Frozen.

## Why frozen?

- Hashable (works in dedup sets)
- Catches accidental mutation
- Documents intent: this is a snapshot

## Why `extra="forbid"`?

When Meta adds a new field to their DOM, the parser will try to set an unknown attribute on `Ad`, raising `ValidationError`. This forces us to update the schema rather than silently dropping data.

## Why `HttpUrl` for URLs?

Pydantic validates that the URL parses. A garbage URL in our pipeline becomes a `ValidationError` at construction time, not a confusing CSV row at export time.

## Why `datetime` not string?

Same reason. Type discipline at the boundary.
