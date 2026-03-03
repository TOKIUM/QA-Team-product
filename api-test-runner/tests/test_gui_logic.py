"""Tests for GUI business logic (Tk-independent parts)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestBuildRequestInfo:
    """_build_request_info ロジックのテスト（App インスタンスなしで再現）."""

    @staticmethod
    def _build_request_info(report_data: dict | None, filename: str) -> str:
        """App._build_request_info と同等のロジック."""
        if not report_data:
            return "(report.json がないため、リクエスト情報を表示できません)"

        entry = None
        for t in report_data.get("tests", []):
            if t.get("output_file") == filename:
                entry = t
                break
        if not entry:
            return f"(report.json に {filename} の情報がありません)"

        lines = []
        url = entry.get("request_url") or entry.get("url_path", "")
        lines.append(f"{entry.get('method', 'GET')} {url}")
        lines.append("")

        headers = entry.get("request_headers")
        if headers:
            lines.append("Headers:")
            for k, v in headers.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append("Headers:")
            lines.append("  Accept: application/json")
            if entry.get("use_auth"):
                lines.append("  Authorization: Bearer ***")
            else:
                lines.append("  (認証なし)")

        params = entry.get("query_params", {})
        if params:
            lines.append("")
            lines.append("Query Parameters:")
            for k, v in params.items():
                lines.append(f"  {k} = {v}")

        lines.append("")
        passed = entry.get("passed", False)
        label = "PASS" if passed else "FAIL"
        lines.append(f"Status: {entry.get('actual_status')} "
                      f"(expected {entry.get('expected_status')}) "
                      f"[{label}] - {entry.get('elapsed_ms', 0):.0f}ms")

        return "\n".join(lines)

    def test_with_report_data(self):
        report_data = {
            "tests": [{
                "name": "get-groups-auth",
                "output_file": "get-groups-auth.json",
                "method": "GET",
                "request_url": "https://example.com/api/v2/groups.json",
                "url_path": "groups.json",
                "request_headers": {"Authorization": "Bearer test***"},
                "query_params": {},
                "use_auth": True,
                "expected_status": 200,
                "actual_status": 200,
                "elapsed_ms": 150.0,
                "passed": True,
            }],
        }
        result = self._build_request_info(report_data, "get-groups-auth.json")
        assert "GET https://example.com/api/v2/groups.json" in result
        assert "PASS" in result
        assert "150ms" in result

    def test_no_report_data(self):
        result = self._build_request_info(None, "test.json")
        assert "report.json がない" in result

    def test_file_not_found_in_report(self):
        report_data = {"tests": [{"output_file": "other.json"}]}
        result = self._build_request_info(report_data, "missing.json")
        assert "missing.json の情報がありません" in result

    def test_no_auth(self):
        report_data = {
            "tests": [{
                "output_file": "test.json",
                "method": "GET",
                "url_path": "test.json",
                "use_auth": False,
                "expected_status": 401,
                "actual_status": 401,
                "elapsed_ms": 50.0,
                "passed": True,
            }],
        }
        result = self._build_request_info(report_data, "test.json")
        assert "認証なし" in result

    def test_with_query_params(self):
        report_data = {
            "tests": [{
                "output_file": "test.json",
                "method": "GET",
                "url_path": "groups.json",
                "query_params": {"offset": 0, "limit": 5},
                "use_auth": True,
                "expected_status": 200,
                "actual_status": 200,
                "elapsed_ms": 100.0,
                "passed": True,
            }],
        }
        result = self._build_request_info(report_data, "test.json")
        assert "offset = 0" in result
        assert "limit = 5" in result

    def test_fail_result(self):
        report_data = {
            "tests": [{
                "output_file": "test.json",
                "method": "GET",
                "url_path": "test.json",
                "expected_status": 200,
                "actual_status": 500,
                "elapsed_ms": 200.0,
                "passed": False,
            }],
        }
        result = self._build_request_info(report_data, "test.json")
        assert "FAIL" in result
        assert "500" in result


class TestGetResultTimestamps:
    """_get_result_timestamps ロジックのテスト."""

    @staticmethod
    def _get_result_timestamps(results_dir: Path) -> list[str]:
        """App._get_result_timestamps と同等のロジック."""
        if not results_dir.exists():
            return []
        stamps = sorted(
            [d.name for d in results_dir.iterdir()
             if d.is_dir() and d.name.isdigit()],
            reverse=True,
        )
        return stamps

    def test_with_timestamps(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "20260101120000").mkdir()
        (results_dir / "20260101130000").mkdir()
        (results_dir / "20260102100000").mkdir()

        stamps = self._get_result_timestamps(results_dir)
        assert stamps == ["20260102100000", "20260101130000", "20260101120000"]

    def test_empty_dir(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        stamps = self._get_result_timestamps(results_dir)
        assert stamps == []

    def test_nonexistent_dir(self, tmp_path):
        stamps = self._get_result_timestamps(tmp_path / "nonexistent")
        assert stamps == []

    def test_non_digit_dirs_excluded(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "20260101120000").mkdir()
        (results_dir / "latest.txt").write_text("test")
        (results_dir / "backup").mkdir()

        stamps = self._get_result_timestamps(results_dir)
        assert stamps == ["20260101120000"]
