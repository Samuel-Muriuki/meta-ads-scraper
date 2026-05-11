from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("META_LIVE_TESTS") == "1":
        return
    skip_live = pytest.mark.skip(reason="META_LIVE_TESTS=1 not set")
    for item in items:
        if "live_test" in item.keywords:
            item.add_marker(skip_live)
