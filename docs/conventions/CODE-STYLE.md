# Code Style

## Python

- **Version:** 3.11+
- **Formatter:** ruff format (replaces black)
- **Linter:** ruff check
- **Type checker:** mypy strict
- **Line length:** 100

## Always

- `from __future__ import annotations` at the top of every module
- Type hints on every public function and class method
- Pydantic v2 for any data crossing a module boundary
- `async`/`await` for all I/O
- Custom exceptions in `exceptions.py`, never raise bare `Exception`
- structlog for logging, never `print()`

## Never

- `from x import *`
- bare `except:` — always except specific types
- `Any` unless commented why
- Mutable defaults: `def foo(items=[])` is forbidden
- `time.sleep()` in async code — use `asyncio.sleep()`

## Imports

ruff handles ordering. Manual rule:
1. `from __future__ import annotations`
2. stdlib
3. third-party
4. first-party (`meta_ads_scraper.*`)

## Docstrings

Public functions get docstrings. Internal helpers don't need them.

```python
async def search(self, spec: SearchSpec) -> AsyncIterator[Ad]:
    """Yield ads matching the given search spec.

    Args:
        spec: The search criteria.

    Yields:
        Ad objects as they are scraped.

    Raises:
        ScraperBlockedError: If Meta blocks the request (CAPTCHA/login).
    """
```

## File length

If a module exceeds ~300 lines, split it. The parser, scraper, and CLI are the only modules that approach this.
