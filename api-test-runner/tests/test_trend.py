"""Tests for trend module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api_test_runner.trend import TrendAnalyzer, TrendEntry, Degradation


def _create_run(tmp_path: Path, timestamp: str, tests: list[dict]) -> None:
    """テスト用の report.json を作成."""
    run_dir = tmp_path / timestamp
    run_dir.mkdir()
    report = {
        "summary": {
            "total": len(tests),
            "passed": sum(1 for t in tests if t.get("passed", True)),
            "failed": sum(1 for t in tests if not t.get("passed", True)),
        },
        "tests": tests,
    }
    with open(run_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(report, f)


class TestLoadRuns:
    def test_loads_sorted_by_timestamp(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
        ])
        _create_run(tmp_path, "20260227120000", [
            {"name": "test-a", "elapsed_ms": 200, "passed": True},
        ])

        analyzer = TrendAnalyzer(tmp_path)
        runs = analyzer.load_runs()

        assert len(runs) == 2
        assert runs[0]["timestamp"] == "20260227100000"
        assert runs[1]["timestamp"] == "20260227120000"

    def test_last_n_limits_results(self, tmp_path):
        for i in range(5):
            _create_run(tmp_path, f"2026022710000{i}", [
                {"name": "test-a", "elapsed_ms": 100 + i * 10, "passed": True},
            ])

        analyzer = TrendAnalyzer(tmp_path)
        runs = analyzer.load_runs(last_n=2)
        assert len(runs) == 2
        assert runs[0]["timestamp"] == "20260227100003"

    def test_empty_directory(self, tmp_path):
        analyzer = TrendAnalyzer(tmp_path)
        assert analyzer.load_runs() == []

    def test_skips_non_numeric_dirs(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
        ])
        # non-numeric dir
        (tmp_path / "latest.txt").write_text("test")
        (tmp_path / "get-groups.json").write_text("{}")

        analyzer = TrendAnalyzer(tmp_path)
        runs = analyzer.load_runs()
        assert len(runs) == 1


class TestGetTimeline:
    def test_builds_timeline(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
            {"name": "test-b", "elapsed_ms": 200, "passed": True},
        ])
        _create_run(tmp_path, "20260227120000", [
            {"name": "test-a", "elapsed_ms": 150, "passed": True},
            {"name": "test-b", "elapsed_ms": 180, "passed": True},
        ])

        analyzer = TrendAnalyzer(tmp_path)
        runs = analyzer.load_runs()
        timeline = analyzer.get_timeline(runs)

        assert "test-a" in timeline
        assert len(timeline["test-a"]) == 2
        assert timeline["test-a"][0].elapsed_ms == 100
        assert timeline["test-a"][1].elapsed_ms == 150


class TestDetectDegradations:
    def test_detects_2x_slowdown(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
            {"name": "test-b", "elapsed_ms": 200, "passed": True},
        ])
        _create_run(tmp_path, "20260227120000", [
            {"name": "test-a", "elapsed_ms": 250, "passed": True},  # 2.5x
            {"name": "test-b", "elapsed_ms": 210, "passed": True},  # 1.05x
        ])

        analyzer = TrendAnalyzer(tmp_path)
        runs = analyzer.load_runs()
        degs = analyzer.detect_degradations(runs)

        assert len(degs) == 1
        assert degs[0].name == "test-a"
        assert degs[0].ratio == pytest.approx(2.5)

    def test_no_degradation(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
        ])
        _create_run(tmp_path, "20260227120000", [
            {"name": "test-a", "elapsed_ms": 90, "passed": True},
        ])

        analyzer = TrendAnalyzer(tmp_path)
        degs = analyzer.detect_degradations(analyzer.load_runs())
        assert degs == []

    def test_single_run(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
        ])

        analyzer = TrendAnalyzer(tmp_path)
        degs = analyzer.detect_degradations(analyzer.load_runs())
        assert degs == []

    def test_skips_fast_tests(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 10, "passed": True},  # < 50ms
        ])
        _create_run(tmp_path, "20260227120000", [
            {"name": "test-a", "elapsed_ms": 30, "passed": True},  # 3x but too fast
        ])

        analyzer = TrendAnalyzer(tmp_path)
        degs = analyzer.detect_degradations(analyzer.load_runs())
        assert degs == []

    def test_custom_threshold(self, tmp_path):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
        ])
        _create_run(tmp_path, "20260227120000", [
            {"name": "test-a", "elapsed_ms": 140, "passed": True},  # 1.4x
        ])

        analyzer = TrendAnalyzer(tmp_path)
        runs = analyzer.load_runs()
        # threshold=1.3 なら検出される
        degs = analyzer.detect_degradations(runs, threshold=1.3)
        assert len(degs) == 1

        # threshold=1.5 なら検出されない
        degs = analyzer.detect_degradations(runs, threshold=1.5)
        assert degs == []


class TestPrintTrend:
    def test_prints_output(self, tmp_path, capsys):
        _create_run(tmp_path, "20260227100000", [
            {"name": "test-a", "elapsed_ms": 100, "passed": True},
        ])
        _create_run(tmp_path, "20260227120000", [
            {"name": "test-a", "elapsed_ms": 150, "passed": True},
        ])

        analyzer = TrendAnalyzer(tmp_path)
        analyzer.print_trend()

        output = capsys.readouterr().out
        assert "Performance Trend" in output
        assert "2 runs" in output
        assert "test-a" in output

    def test_empty_runs(self, tmp_path, capsys):
        analyzer = TrendAnalyzer(tmp_path)
        analyzer.print_trend()

        output = capsys.readouterr().out
        assert "No test runs found" in output
