"""Tests for http_client module (retry logic)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api_test_runner.http_client import ApiClient
from api_test_runner.models import TestCase, TestResult


@pytest.fixture
def test_case():
    return TestCase(
        name="test",
        pattern="auth",
        api=None,
        method="GET",
        url_path="groups.json",
        query_params={},
        use_auth=True,
        expected_status=200,
    )


class TestShouldRetry:
    def test_no_retry_on_pass(self, test_case):
        client = ApiClient("https://example.com", "key")
        result = TestResult(test_case, 200, None, 100.0, True)
        assert client._should_retry(result) is False

    def test_retry_on_500(self, test_case):
        client = ApiClient("https://example.com", "key")
        result = TestResult(test_case, 500, None, 100.0, False)
        assert client._should_retry(result) is True

    def test_retry_on_connection_error(self, test_case):
        client = ApiClient("https://example.com", "key")
        result = TestResult(test_case, 0, None, 100.0, False)
        assert client._should_retry(result) is True

    def test_no_retry_on_400(self, test_case):
        client = ApiClient("https://example.com", "key")
        result = TestResult(test_case, 400, None, 100.0, False)
        assert client._should_retry(result) is False

    def test_no_retry_on_401(self, test_case):
        client = ApiClient("https://example.com", "key")
        result = TestResult(test_case, 401, None, 100.0, False)
        assert client._should_retry(result) is False


class TestRetryBehavior:
    @patch.object(ApiClient, "_execute_once")
    @patch("api_test_runner.http_client.time.sleep")
    def test_retries_on_500(self, mock_sleep, mock_exec, test_case):
        fail_result = TestResult(test_case, 500, None, 100.0, False)
        pass_result = TestResult(test_case, 200, None, 100.0, True)
        mock_exec.side_effect = [fail_result, pass_result]

        client = ApiClient("https://example.com", "key", max_retries=2, retry_delay=0.1)
        result = client.execute(test_case)

        assert result.passed is True
        assert mock_exec.call_count == 2
        mock_sleep.assert_called_once()

    @patch.object(ApiClient, "_execute_once")
    @patch("api_test_runner.http_client.time.sleep")
    def test_no_retry_without_config(self, mock_sleep, mock_exec, test_case):
        fail_result = TestResult(test_case, 500, None, 100.0, False)
        mock_exec.return_value = fail_result

        client = ApiClient("https://example.com", "key", max_retries=0)
        result = client.execute(test_case)

        assert result.status_code == 500
        assert mock_exec.call_count == 1
        mock_sleep.assert_not_called()

    @patch.object(ApiClient, "_execute_once")
    @patch("api_test_runner.http_client.time.sleep")
    def test_exhausts_retries(self, mock_sleep, mock_exec, test_case):
        fail_result = TestResult(test_case, 503, None, 100.0, False)
        mock_exec.return_value = fail_result

        client = ApiClient("https://example.com", "key", max_retries=2, retry_delay=1.0)
        result = client.execute(test_case)

        assert result.status_code == 503
        assert mock_exec.call_count == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2
