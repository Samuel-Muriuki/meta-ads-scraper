from __future__ import annotations

import re

from typer.testing import CliRunner

from meta_ads_scraper.cli import app

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_RE.sub("", text)


class TestMutualExclusion:
    def test_no_input_flags_rejected(self):
        result = runner.invoke(app, ["search"])
        assert result.exit_code != 0
        assert "exactly one" in _plain(result.output).lower()

    def test_keyword_and_page_url_rejected(self):
        result = runner.invoke(
            app,
            ["search", "--keyword", "shoes", "--page-url", "https://www.facebook.com/Nike"],
        )
        assert result.exit_code != 0
        combined = _plain(result.output).lower()
        assert "mutually exclusive" in combined
        assert "--keyword" in combined
        assert "--page-url" in combined

    def test_keyword_and_page_slug_rejected(self):
        result = runner.invoke(
            app,
            ["search", "--keyword", "shoes", "--page-slug", "Nike"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in _plain(result.output).lower()

    def test_all_three_rejected(self):
        result = runner.invoke(
            app,
            [
                "search",
                "--keyword",
                "shoes",
                "--page-url",
                "https://www.facebook.com/Nike",
                "--page-slug",
                "Nike",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in _plain(result.output).lower()


class TestFormatValidation:
    def test_unknown_format_rejected(self):
        result = runner.invoke(app, ["search", "--keyword", "x", "--format", "yaml"])
        assert result.exit_code != 0
        combined = _plain(result.output).lower()
        assert "unknown format" in combined
        assert "yaml" in combined


class TestHelp:
    def test_search_help_documents_mutual_exclusion(self):
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "Mutually exclusive" in _plain(result.output)
        for flag in ("--keyword", "--page-url", "--page-slug"):
            assert flag in _plain(result.output)

    def test_root_help_lists_search_command(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "search" in _plain(result.output)
