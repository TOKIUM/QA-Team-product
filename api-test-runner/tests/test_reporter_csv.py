"""Tests for Reporter.save_csv_report."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from api_test_runner.models import TestCase, TestResult
from api_test_runner.reporter import Reporter


@pytest.fixture
def csv_results(tmp_path):
    """CSV テスト用の TestResult リスト."""
    run_dir = tmp_path / "20260101120000"
    run_dir.mkdir(parents=True)

    tc1 = TestCase(
        name="get-groups-auth", pattern="auth", api=None,
        method="GET", url_path="groups.json", query_params={},
        use_auth=True, expected_status=200,
    )
    tc2 = TestCase(
        name="get-groups-no-auth", pattern="no_auth", api=None,
        method="GET", url_path="groups.json", query_params={},
        use_auth=False, expected_status=401,
    )
    tc3 = TestCase(
        name="get-groups-pagination", pattern="pagination", api=None,
        method="GET", url_path="groups.json",
        query_params={"offset": 0, "limit": 5},
        use_auth=True, expected_status=200,
    )

    return [
        TestResult(
            test_case=tc1, status_code=200,
            response_body={"groups": []}, elapsed_ms=150.0,
            passed=True, output_file=str(run_dir / "get-groups-auth.json"),
        ),
        TestResult(
            test_case=tc2, status_code=401,
            response_body={"error": "Unauthorized"}, elapsed_ms=50.0,
            passed=True, output_file=str(run_dir / "get-groups-no-auth.json"),
        ),
        TestResult(
            test_case=tc3, status_code=200,
            response_body={"groups": []}, elapsed_ms=200.0,
            passed=True, output_file=str(run_dir / "get-groups-pagination.json"),
            schema_warnings=["Missing key: groups"],
        ),
    ], tmp_path


class TestSaveCsvReport:
    def test_csv_created(self, csv_results):
        results, results_dir = csv_results
        reporter = Reporter()
        path = reporter.save_csv_report(results, results_dir)
        assert path is not None
        assert Path(path).exists()
        assert Path(path).name == "report.csv"

    def test_csv_header(self, csv_results):
        results, results_dir = csv_results
        reporter = Reporter()
        path = reporter.save_csv_report(results, results_dir)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == [
            "name", "pattern", "method", "url_path",
            "expected_status", "actual_status", "elapsed_ms",
            "passed", "schema_warnings",
        ]

    def test_csv_row_count(self, csv_results):
        results, results_dir = csv_results
        reporter = Reporter()
        path = reporter.save_csv_report(results, results_dir)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 4  # header + 3 results

    def test_csv_content(self, csv_results):
        results, results_dir = csv_results
        reporter = Reporter()
        path = reporter.save_csv_report(results, results_dir)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        first = rows[0]
        assert first["name"] == "get-groups-auth"
        assert first["pattern"] == "auth"
        assert first["method"] == "GET"
        assert first["passed"] == "PASS"

        third = rows[2]
        assert third["schema_warnings"] == "Missing key: groups"

    def test_csv_no_results(self, tmp_path):
        reporter = Reporter()
        path = reporter.save_csv_report([], tmp_path)
        assert path is None

    def test_csv_fail_status(self, tmp_path):
        run_dir = tmp_path / "20260101120000"
        run_dir.mkdir(parents=True)

        tc = TestCase(
            name="fail-test", pattern="auth", api=None,
            method="GET", url_path="test.json", query_params={},
            use_auth=True, expected_status=200,
        )
        results = [TestResult(
            test_case=tc, status_code=500,
            response_body=None, elapsed_ms=100.0,
            passed=False, output_file=str(run_dir / "fail-test.json"),
        )]

        reporter = Reporter()
        path = reporter.save_csv_report(results, tmp_path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["passed"] == "FAIL"
        assert row["actual_status"] == "500"
