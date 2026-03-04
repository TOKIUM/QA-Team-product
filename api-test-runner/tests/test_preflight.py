"""Tests for preflight module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api_test_runner.preflight import (
    CheckItem,
    CheckSection,
    PreflightChecker,
    PreflightResult,
    print_preflight_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_config():
    """search overrides + custom_tests 付きの標準設定."""
    return {
        "test": {
            "search": {
                "overrides": {
                    "department_id": "90980a77-cdab-4db8-b845-0ea3d27e1954",
                },
            },
        },
        "custom_tests": [
            {
                "name": "health-check",
                "url_path": "payment_requests/reports",
                "method": "GET",
                "use_auth": True,
                "expected_status": 200,
            },
        ],
    }


@pytest.fixture
def mock_specs():
    """parse_directory が返すダミー spec リスト."""
    from api_test_runner.models import ApiSpec, Parameter

    return [
        ApiSpec(
            number="1",
            name="部署取得API",
            url="/api/v2/groups.json",
            method="GET",
            resource="groups",
            params=[],
        ),
        ApiSpec(
            number="2",
            name="メンバー取得API",
            url="/api/v2/members.json",
            method="GET",
            resource="members",
            params=[
                Parameter(
                    item_name="部署ID",
                    param_name="department_id",
                    data_type="文字列",
                    required="",
                    remarks="",
                ),
            ],
        ),
        ApiSpec(
            number="3",
            name="プロジェクト作成API",
            url="/api/v2/projects.json",
            method="POST",
            resource="projects",
            params=[],
        ),
    ]


def _mock_response(status_code: int = 200):
    """requests.get の戻り値を模倣する Mock."""
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# 1. Connectivity
# ---------------------------------------------------------------------------

class TestCheckConnectivity:

    @patch("api_test_runner.preflight.parse_directory", return_value=[])
    @patch("api_test_runner.preflight.requests.get")
    def test_pass(self, mock_get, mock_parse, base_config):
        mock_get.return_value = _mock_response(200)
        checker = PreflightChecker(
            "https://example.com/api/v2", "valid-key",
            base_config, Path("document"),
        )
        section = checker.check_connectivity()
        assert section.title == "Connectivity"
        assert len(section.items) == 2
        assert section.items[0].status == "PASS"  # base URL
        assert section.items[1].status == "PASS"  # auth

    @patch("api_test_runner.preflight.parse_directory", return_value=[])
    @patch("api_test_runner.preflight.requests.get")
    def test_connection_error(self, mock_get, mock_parse, base_config):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("refused")
        checker = PreflightChecker(
            "https://example.com/api/v2", "key",
            base_config, Path("document"),
        )
        section = checker.check_connectivity()
        assert section.items[0].status == "FAIL"
        assert "refused" in section.items[0].detail

    @patch("api_test_runner.preflight.parse_directory", return_value=[])
    @patch("api_test_runner.preflight.requests.get")
    def test_500_base_url(self, mock_get, mock_parse, base_config):
        mock_get.return_value = _mock_response(500)
        checker = PreflightChecker(
            "https://example.com/api/v2", "key",
            base_config, Path("document"),
        )
        section = checker.check_connectivity()
        # base URL: 500 でも到達はできている → PASS
        assert section.items[0].status == "PASS"
        assert "500" in section.items[0].detail

    @patch("api_test_runner.preflight.parse_directory", return_value=[])
    @patch("api_test_runner.preflight.requests.get")
    def test_401_auth(self, mock_get, mock_parse, base_config):
        # base URL → 200, auth → 401
        mock_get.side_effect = [_mock_response(200), _mock_response(401)]
        checker = PreflightChecker(
            "https://example.com/api/v2", "bad-key",
            base_config, Path("document"),
        )
        section = checker.check_connectivity()
        assert section.items[0].status == "PASS"
        assert section.items[1].status == "FAIL"
        assert "401" in section.items[1].detail


# ---------------------------------------------------------------------------
# 2. CSV Specs
# ---------------------------------------------------------------------------

class TestCheckCsvSpecs:

    @patch("api_test_runner.preflight.parse_directory")
    def test_pass(self, mock_parse, mock_specs, base_config):
        mock_parse.return_value = mock_specs
        checker = PreflightChecker(
            "https://example.com", "key",
            base_config, Path("document"),
        )
        section = checker.check_csv_specs()
        assert section.items[0].status == "PASS"
        assert "3 specs" in section.items[0].detail
        assert "GET: 2" in section.items[0].detail
        assert "POST: 1" in section.items[0].detail

    @patch("api_test_runner.preflight.parse_directory", return_value=[])
    def test_no_specs_dir_exists(self, mock_parse, base_config, tmp_path):
        csv_dir = tmp_path / "document"
        csv_dir.mkdir()
        checker = PreflightChecker(
            "https://example.com", "key",
            base_config, csv_dir,
        )
        section = checker.check_csv_specs()
        assert section.items[0].status == "FAIL"

    @patch("api_test_runner.preflight.parse_directory", return_value=[])
    def test_no_specs_dir_missing(self, mock_parse, base_config):
        checker = PreflightChecker(
            "https://example.com", "key",
            base_config, Path("/nonexistent"),
        )
        section = checker.check_csv_specs()
        assert section.items[0].status == "WARN"


# ---------------------------------------------------------------------------
# 3. Search Overrides
# ---------------------------------------------------------------------------

class TestCheckSearchOverrides:

    @patch("api_test_runner.preflight.requests.get")
    @patch("api_test_runner.preflight.parse_directory")
    def test_pass_200(self, mock_parse, mock_get, mock_specs, base_config):
        mock_parse.return_value = mock_specs
        mock_get.return_value = _mock_response(200)
        checker = PreflightChecker(
            "https://example.com/api/v2", "key",
            base_config, Path("document"),
        )
        section = checker.check_search_overrides()
        assert len(section.items) == 1
        assert section.items[0].status == "PASS"
        assert "department_id" in section.items[0].label

    @patch("api_test_runner.preflight.requests.get")
    @patch("api_test_runner.preflight.parse_directory")
    def test_fail_400(self, mock_parse, mock_get, mock_specs, base_config):
        mock_parse.return_value = mock_specs
        mock_get.return_value = _mock_response(400)
        checker = PreflightChecker(
            "https://example.com/api/v2", "key",
            base_config, Path("document"),
        )
        section = checker.check_search_overrides()
        assert section.items[0].status == "FAIL"
        assert "400" in section.items[0].detail

    @patch("api_test_runner.preflight.parse_directory")
    def test_param_not_found_warns(self, mock_parse, mock_specs):
        mock_parse.return_value = mock_specs
        config = {
            "test": {
                "search": {
                    "overrides": {"unknown_param": "value"},
                },
            },
        }
        checker = PreflightChecker(
            "https://example.com/api/v2", "key",
            config, Path("document"),
        )
        section = checker.check_search_overrides()
        assert section.items[0].status == "WARN"

    def test_no_overrides(self):
        checker = PreflightChecker(
            "https://example.com", "key",
            {}, Path("document"),
        )
        section = checker.check_search_overrides()
        assert len(section.items) == 1
        assert section.items[0].status == "PASS"


# ---------------------------------------------------------------------------
# 4. Custom Tests
# ---------------------------------------------------------------------------

class TestCheckCustomTests:

    @patch("api_test_runner.preflight.requests.get")
    def test_pass_200(self, mock_get, base_config):
        mock_get.return_value = _mock_response(200)
        checker = PreflightChecker(
            "https://example.com/api/v2", "key",
            base_config, Path("document"),
        )
        # _specs を空リストに初期化（CSV パースを回避）
        checker._specs = []
        section = checker.check_custom_tests()
        assert len(section.items) == 1
        assert section.items[0].status == "PASS"

    @patch("api_test_runner.preflight.requests.get")
    def test_fail_404(self, mock_get, base_config):
        mock_get.return_value = _mock_response(404)
        checker = PreflightChecker(
            "https://example.com/api/v2", "key",
            base_config, Path("document"),
        )
        checker._specs = []
        section = checker.check_custom_tests()
        assert section.items[0].status == "FAIL"
        assert "404" in section.items[0].detail

    def test_no_custom_tests(self):
        checker = PreflightChecker(
            "https://example.com", "key",
            {}, Path("document"),
        )
        checker._specs = []
        section = checker.check_custom_tests()
        assert len(section.items) == 1
        assert section.items[0].status == "PASS"

    @patch("api_test_runner.preflight.requests.get")
    def test_dedup_same_url(self, mock_get):
        mock_get.return_value = _mock_response(200)
        config = {
            "custom_tests": [
                {"name": "a", "url_path": "reports", "method": "GET",
                 "use_auth": True, "expected_status": 200},
                {"name": "b", "url_path": "reports", "method": "GET",
                 "use_auth": False, "expected_status": 401},
            ],
        }
        checker = PreflightChecker(
            "https://example.com", "key",
            config, Path("document"),
        )
        checker._specs = []
        section = checker.check_custom_tests()
        # 同一 url_path は 1 回のみチェック
        assert len(section.items) == 1


# ---------------------------------------------------------------------------
# PreflightResult properties
# ---------------------------------------------------------------------------

class TestPreflightResult:

    def test_ok_all_pass(self):
        result = PreflightResult(sections=[
            CheckSection("S1", [CheckItem("a", "PASS")]),
            CheckSection("S2", [CheckItem("b", "PASS")]),
        ])
        assert result.ok is True
        assert result.total == 2
        assert result.passed == 2
        assert result.failed == 0

    def test_not_ok_with_fail(self):
        result = PreflightResult(sections=[
            CheckSection("S1", [
                CheckItem("a", "PASS"),
                CheckItem("b", "FAIL", "bad"),
            ]),
        ])
        assert result.ok is False
        assert result.passed == 1
        assert result.failed == 1

    def test_ok_with_warn_only(self):
        result = PreflightResult(sections=[
            CheckSection("S1", [
                CheckItem("a", "PASS"),
                CheckItem("b", "WARN", "hmm"),
            ]),
        ])
        assert result.ok is True
        assert result.warned == 1

    def test_to_dict(self):
        result = PreflightResult(sections=[
            CheckSection("S1", [CheckItem("a", "PASS", "detail")]),
        ])
        d = result.to_dict()
        assert d["ok"] is True
        assert d["total"] == 1
        assert d["sections"][0]["title"] == "S1"
        assert d["sections"][0]["items"][0]["label"] == "a"
        assert d["sections"][0]["items"][0]["status"] == "PASS"
        assert d["sections"][0]["items"][0]["detail"] == "detail"


# ---------------------------------------------------------------------------
# print_preflight_result (smoke test)
# ---------------------------------------------------------------------------

class TestPrintPreflightResult:

    def test_output(self, capsys):
        result = PreflightResult(sections=[
            CheckSection("Connectivity", [
                CheckItem("Base URL reachable", "PASS", "-> 200"),
            ]),
            CheckSection("CSV Specs", [
                CheckItem("API specs found", "FAIL", "No specs"),
            ]),
        ])
        print_preflight_result(result)
        captured = capsys.readouterr().out
        assert "Preflight Check" in captured
        assert "[PASS]" in captured
        assert "[FAIL]" in captured
        assert "1 passed" in captured
        assert "1 failed" in captured
