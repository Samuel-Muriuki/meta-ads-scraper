"""Structured logging configuration.

Three verbosity levels via a single ``configure_logging`` entry point:

* ``verbosity=0`` — WARNING+ to stderr, JSON renderer (production default).
* ``verbosity=1`` (``-v``) — INFO+ to stderr, JSON renderer.
* ``verbosity=2+`` (``-vv``) — DEBUG+ to stderr, pretty console renderer.

Logs go to **stderr** so they do not contaminate CSV/JSON output written
to stdout.

A stdlib-bridge formatter is installed so logs from third-party libraries
(Playwright, httpx, tenacity, urllib3) flow through the same processor
chain and come out in the chosen shape. This is how
``tenacity.before_sleep_log`` events end up as JSON alongside our own
``scrape_start`` / ``pagination_stalled`` events.

Stable log event names — DO NOT rename without surfacing first
================================================================
The following event names are the project's stable log API surface and
must not be renamed silently:

* ``scrape_start``
* ``no_cookie_consent_dialog``
* ``cookie_consent_dismissed``
* ``no_ads_visible``
* ``max_results_reached``
* ``pagination_stalled``
* ``pagination_timeout``
* ``pagination_stall_tick``
* ``shutdown_requested``
* ``page_id_resolve_start``
* ``page_id_resolved``
* ``max_results_zero_treated_as_unlimited``
* ``max_results_above_ceiling``
* ``rate_limit_concurrency_clamped``

Any rename needs to be surfaced in a PR Completion Report under
Architectural Decisions, not folded into another change.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

__all__ = ["configure_logging"]


_VERBOSITY_TO_LEVEL = {
    0: logging.WARNING,
    1: logging.INFO,
}


def configure_logging(verbosity: int = 0) -> None:
    """Configure structlog + stdlib logging for the given verbosity.

    Idempotent: safe to call again from tests or to re-tune mid-run.
    Each call clears and re-installs handlers on the stdlib root logger.

    Args:
        verbosity: 0 -> WARNING (JSON). 1 -> INFO (JSON). 2+ -> DEBUG
            (pretty console). Values above 2 are treated as 2.
    """
    level = _VERBOSITY_TO_LEVEL.get(verbosity, logging.DEBUG)
    pretty = verbosity >= 2

    # Processors that run on every event regardless of origin
    # (structlog-native or routed in from stdlib logging).
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Structlog-side: end the chain by handing off to the stdlib
    # ProcessorFormatter, which will run the final renderer.
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=False,
    )

    final_renderer: Any
    if pretty:
        final_renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        final_renderer = structlog.processors.JSONRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            final_renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
