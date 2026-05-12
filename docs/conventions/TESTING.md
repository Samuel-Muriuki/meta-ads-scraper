# Testing Discipline

## Three layers

1. **Unit** (`tests/unit/`) — fast, no I/O. Run on every push.
2. **Integration Replay** (`tests/integration/test_replay.py`) — HAR-based, deterministic. Run on every push.
3. **Live Smoke** (`tests/integration/test_live_smoke.py`) — real Meta. Gated by `META_LIVE_TESTS=1`. Manual only.

## Coverage gate

- `fail_under = 78` in `pyproject.toml` (CI-enforced in the
  Integration + Coverage Gate job, see `.github/workflows/ci.yml`)
- Current overall coverage: 78–79% — gate sits one point below the
  measured floor; followup to raise to 80% once additional
  `playwright_scraper.py` paths are unit-covered.
- Per-module aspirational targets in
  `.project/patterns/pytest-patterns/README.md`

## What every PR adds

- New code → new tests for that code
- Bug fix → regression test that fails before, passes after
- Refactor → existing tests still pass (no new tests needed)

## Speed

- Unit suite must complete in <5 seconds locally
- Integration replay in <30 seconds
- If a test is slow, mark it `@pytest.mark.slow` so the default suite stays fast
