"""Tests for api_test_runner.notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api_test_runner.models import TestCase, TestResult
from api_test_runner.notifier import SlackNotifier


@pytest.fixture
def notifier():
    return SlackNotifier()


@pytest.fixture
def mixed_results():
    """PASS と FAIL を含む結果."""
    tc_pass = TestCase(
        name="get-groups-auth", pattern="auth", api=None,
        method="GET", url_path="groups.json", query_params={},
        use_auth=True, expected_status=200,
    )
    tc_fail = TestCase(
        name="get-members-auth", pattern="auth", api=None,
        method="GET", url_path="members.json", query_params={},
        use_auth=True, expected_status=200,
    )
    tc_pagination = TestCase(
        name="get-groups-pagination", pattern="pagination", api=None,
        method="GET", url_path="groups.json",
        query_params={"offset": 0, "limit": 5},
        use_auth=True, expected_status=200,
    )
    return [
        TestResult(test_case=tc_pass, status_code=200,
                   response_body={}, elapsed_ms=100, passed=True),
        TestResult(test_case=tc_fail, status_code=500,
                   response_body={}, elapsed_ms=200, passed=False),
        TestResult(test_case=tc_pagination, status_code=200,
                   response_body={}, elapsed_ms=150, passed=True),
    ]


@pytest.fixture
def all_pass_results():
    """全 PASS の結果."""
    tc = TestCase(
        name="get-groups-auth", pattern="auth", api=None,
        method="GET", url_path="groups.json", query_params={},
        use_auth=True, expected_status=200,
    )
    return [
        TestResult(test_case=tc, status_code=200,
                   response_body={}, elapsed_ms=100, passed=True),
    ]


class TestBuildPayload:
    def test_all_pass(self, notifier, all_pass_results):
        payload = notifier.build_payload(all_pass_results)
        assert "text" in payload
        assert ":white_check_mark:" in payload["text"]
        assert "1/1 passed" in payload["text"]

    def test_with_failures(self, notifier, mixed_results):
        payload = notifier.build_payload(mixed_results)
        text = payload["text"]
        assert ":x:" in text
        assert "2/3 passed" in text
        assert "1 failed" in text

    def test_pattern_summary(self, notifier, mixed_results):
        payload = notifier.build_payload(mixed_results)
        text = payload["text"]
        assert "auth:" in text
        assert "pagination:" in text

    def test_failed_tests_listed(self, notifier, mixed_results):
        payload = notifier.build_payload(mixed_results)
        text = payload["text"]
        assert "get-members-auth" in text
        assert "expected 200" in text
        assert "got 500" in text

    def test_no_failed_section_when_all_pass(self, notifier, all_pass_results):
        payload = notifier.build_payload(all_pass_results)
        text = payload["text"]
        assert "Failed Tests" not in text

    def test_schema_warnings_included(self, notifier):
        """スキーマ警告がペイロードに含まれる."""
        tc = TestCase(
            name="boundary-groups-limit-negative", pattern="boundary",
            api=None, method="GET", url_path="groups.json",
            query_params={"limit": -1}, use_auth=True,
            expected_status=400,
        )
        result = TestResult(
            test_case=tc, status_code=400,
            response_body={"error": "bad"}, elapsed_ms=100, passed=True,
            schema_warnings=["エラー検証: 400レスポンスに 'message' キーがありません。実際のキー: ['error']。エラー原因の特定にmessageフィールドが推奨されます"],
        )
        payload = notifier.build_payload([result])
        text = payload["text"]
        assert ":warning:" in text
        assert "1 warnings" in text
        assert "Schema Warnings" in text
        assert "message" in text

    def test_no_warnings_section_when_clean(self, notifier, all_pass_results):
        """警告なし時は Schema Warnings セクションなし."""
        payload = notifier.build_payload(all_pass_results)
        text = payload["text"]
        assert "Schema Warnings" not in text
        assert ":warning:" not in text


class TestNotify:
    def test_empty_url_returns_false(self, notifier, all_pass_results):
        assert notifier.notify(all_pass_results, "") is False

    @patch("api_test_runner.notifier.urllib.request.urlopen")
    def test_successful_send(self, mock_urlopen, notifier, all_pass_results):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = notifier.notify(all_pass_results, "https://hooks.slack.com/test")
        assert result is True
        mock_urlopen.assert_called_once()

    @patch("api_test_runner.notifier.urllib.request.urlopen")
    def test_failed_send(self, mock_urlopen, notifier, all_pass_results):
        mock_urlopen.side_effect = Exception("Connection error")
        result = notifier.notify(all_pass_results, "https://hooks.slack.com/test")
        assert result is False
