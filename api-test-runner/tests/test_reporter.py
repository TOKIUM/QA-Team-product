"""Tests for reporter module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api_test_runner.reporter import Reporter, _esc


class TestAggregateByPattern:
    def test_groups_by_pattern(self, sample_results):
        reporter = Reporter()
        agg = reporter._aggregate_by_pattern(sample_results)

        assert "auth" in agg
        assert "no_auth" in agg
        assert "pagination" in agg
        assert agg["auth"] == {"total": 1, "passed": 1}
        assert agg["no_auth"] == {"total": 1, "passed": 1}
        assert agg["pagination"] == {"total": 1, "passed": 1}

    def test_empty_results(self):
        reporter = Reporter()
        agg = reporter._aggregate_by_pattern([])
        assert agg == {}


class TestPrintSummary:
    def test_prints_pattern_breakdown(self, sample_results, capsys):
        reporter = Reporter()
        reporter.print_summary(sample_results)
        output = capsys.readouterr().out

        assert "3 passed, 0 failed / 3 total" in output
        assert "auth" in output
        assert "no_auth" in output
        assert "pagination" in output
        assert "FAIL details" not in output


class TestSaveReport:
    def test_creates_report_json(self, sample_results, tmp_path):
        run_dir = tmp_path / "20260101"
        run_dir.mkdir()
        for r in sample_results:
            r.output_file = str(run_dir / f"{r.test_case.name}.json")
            Path(r.output_file).write_text("{}")

        reporter = Reporter()
        path = reporter.save_report(sample_results, tmp_path)

        assert path is not None
        with open(path, encoding="utf-8") as f:
            report = json.load(f)

        assert report["summary"]["total"] == 3
        assert report["summary"]["passed"] == 3
        assert report["summary"]["failed"] == 0
        assert "by_pattern" in report["summary"]
        assert report["summary"]["by_pattern"]["auth"]["total"] == 1

    def test_returns_none_without_output_files(self, sample_results, tmp_path):
        for r in sample_results:
            r.output_file = None
        reporter = Reporter()
        assert reporter.save_report(sample_results, tmp_path) is None

    def test_masks_auth_header(self, sample_results, tmp_path):
        run_dir = tmp_path / "20260101"
        run_dir.mkdir()
        for r in sample_results:
            r.output_file = str(run_dir / f"{r.test_case.name}.json")
            Path(r.output_file).write_text("{}")

        reporter = Reporter()
        path = reporter.save_report(sample_results, tmp_path)

        with open(path, encoding="utf-8") as f:
            report = json.load(f)

        # auth テストのヘッダーはマスクされている
        auth_test = next(t for t in report["tests"] if t["name"] == "get-groups")
        auth_header = auth_test["request_headers"]["Authorization"]
        assert "***" in auth_header
        assert "test123456789" not in auth_header


class TestSaveHtmlReport:
    def test_creates_html_file(self, sample_results, tmp_path):
        run_dir = tmp_path / "20260101"
        run_dir.mkdir()
        for r in sample_results:
            r.output_file = str(run_dir / f"{r.test_case.name}.json")
            Path(r.output_file).write_text("{}")

        reporter = Reporter()
        path = reporter.save_html_report(sample_results, tmp_path)

        assert path is not None
        assert path.endswith("report.html")

        content = Path(path).read_text(encoding="utf-8")
        assert "API Test Report" in content
        assert "auth" in content
        assert "filterRows" in content

    def test_returns_none_without_output_files(self, sample_results, tmp_path):
        for r in sample_results:
            r.output_file = None
        reporter = Reporter()
        assert reporter.save_html_report(sample_results, tmp_path) is None


class TestEsc:
    def test_escapes_html_entities(self):
        assert _esc("<script>") == "&lt;script&gt;"
        assert _esc('a="b"') == 'a=&quot;b&quot;'
        assert _esc("a&b") == "a&amp;b"

    def test_plain_text_unchanged(self):
        assert _esc("hello world") == "hello world"
