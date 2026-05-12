"""Smoke test for `configure_logging`'s JSON output shape.

Per the Phase 4 prompt: one assertion. We are not verifying internal
structlog renderer details — only that the JSON envelope is well-formed
and that the event name passes through unchanged.
"""

from __future__ import annotations

import json

import pytest
import structlog

from meta_ads_scraper.logging_config import configure_logging


def test_configure_logging_emits_parseable_json(
    capfd: pytest.CaptureFixture[str],
) -> None:
    configure_logging(verbosity=1)
    structlog.get_logger().info("test_event", key="value")
    line = capfd.readouterr().err.strip().splitlines()[-1]
    parsed = json.loads(line)
    assert parsed["event"] == "test_event"
