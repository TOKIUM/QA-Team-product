"""Tests for error response body validation."""

from __future__ import annotations

import pytest

from api_test_runner.models import TestCase, TestResult
from api_test_runner.test_runner import TestRunner
from api_test_runner.validator import ResponseValidator


def _make_result(
    expected_status: int,
    status_code: int,
    response_body: dict | list | None,
    pattern: str = "boundary",
    passed: bool | None = None,
) -> TestResult:
    tc = TestCase(
        name="test-case",
        pattern=pattern,
        api=None,
        method="GET",
        url_path="groups.json",
        query_params={},
        use_auth=True,
        expected_status=expected_status,
    )
    if passed is None:
        passed = (status_code == expected_status)
    return TestResult(
        test_case=tc,
        status_code=status_code,
        response_body=response_body,
        elapsed_ms=100.0,
        passed=passed,
    )


class TestValidateErrorBody400:
    def test_400_with_message_key(self):
        result = _make_result(400, 400, {"message": "Bad Request"})
        ResponseValidator.validate_error_body(result)
        assert len(result.schema_warnings) == 0

    def test_400_missing_message_key(self):
        result = _make_result(400, 400, {"error": "something"})
        ResponseValidator.validate_error_body(result)
        assert any("message" in w for w in result.schema_warnings)

    def test_400_none_body(self):
        result = _make_result(400, 400, None)
        ResponseValidator.validate_error_body(result)
        assert any("空" in w for w in result.schema_warnings)

    def test_400_non_dict_body(self):
        result = _make_result(400, 400, [1, 2, 3])
        ResponseValidator.validate_error_body(result)
        assert any("dict" in w for w in result.schema_warnings)

    def test_400_missing_required_with_param_key(self):
        result = _make_result(
            400, 400,
            {"message": "missing param", "param": "job_id"},
            pattern="missing_required",
        )
        ResponseValidator.validate_error_body(result)
        # message あり + param あり → 警告なし
        assert len(result.schema_warnings) == 0

    def test_400_missing_required_with_missing_values_key(self):
        result = _make_result(
            400, 400,
            {"message": "missing", "missing_values": ["name"]},
            pattern="missing_required",
        )
        ResponseValidator.validate_error_body(result)
        assert len(result.schema_warnings) == 0

    def test_400_missing_required_with_errors_key(self):
        result = _make_result(
            400, 400,
            {"message": "error", "errors": [{"field": "name"}]},
            pattern="missing_required",
        )
        ResponseValidator.validate_error_body(result)
        assert len(result.schema_warnings) == 0

    def test_400_missing_required_no_detail_keys(self):
        result = _make_result(
            400, 400,
            {"message": "error"},
            pattern="missing_required",
        )
        ResponseValidator.validate_error_body(result)
        assert any("param" in w or "missing_values" in w or "errors" in w
                    for w in result.schema_warnings)


class TestValidateErrorBody401:
    def test_401_non_empty_body(self):
        result = _make_result(401, 401, {"error": "Unauthorized"})
        ResponseValidator.validate_error_body(result)
        assert len(result.schema_warnings) == 0

    def test_401_empty_body(self):
        result = _make_result(401, 401, {})
        ResponseValidator.validate_error_body(result)
        assert any("401" in w and "空" in w for w in result.schema_warnings)

    def test_401_none_body(self):
        result = _make_result(401, 401, None)
        ResponseValidator.validate_error_body(result)
        assert any("401" in w and "空" in w for w in result.schema_warnings)


class TestValidateErrorBodySkips:
    def test_skips_failed_test(self):
        """FAIL テストはスキップ."""
        result = _make_result(400, 200, {"no_message": True}, passed=False)
        ResponseValidator.validate_error_body(result)
        assert len(result.schema_warnings) == 0

    def test_skips_200_response(self):
        """200 レスポンスはスキップ."""
        result = _make_result(200, 200, {"groups": []})
        ResponseValidator.validate_error_body(result)
        assert len(result.schema_warnings) == 0


class TestRunAllErrorBodyIntegration:
    """run_all 内での error_body_validation 連携テスト."""

    def test_error_body_validation_enabled(self, tmp_path):
        """error_body_validation: true で _validate_error_body が呼ばれる."""
        from unittest.mock import MagicMock, patch

        config = {
            "test": {"error_body_validation": True, "concurrency": 1},
            "output": {"json_indent": 2},
        }
        tc = TestCase(
            name="test-400",
            pattern="boundary",
            api=None,
            method="GET",
            url_path="groups.json",
            query_params={"limit": -1},
            use_auth=True,
            expected_status=400,
        )
        mock_result = TestResult(
            test_case=tc,
            status_code=400,
            response_body={"error": "no message key"},
            elapsed_ms=50.0,
            passed=True,
        )

        mock_client = MagicMock()
        mock_client.execute.return_value = mock_result

        runner = TestRunner(config, mock_client, tmp_path)
        results = runner.run_all([tc])

        assert len(results) == 1
        assert any("message" in w for w in results[0].schema_warnings)

    def test_error_body_validation_disabled(self, tmp_path):
        """error_body_validation: false ではスキップ."""
        from unittest.mock import MagicMock

        config = {
            "test": {"error_body_validation": False, "concurrency": 1},
            "output": {"json_indent": 2},
        }
        tc = TestCase(
            name="test-400",
            pattern="boundary",
            api=None,
            method="GET",
            url_path="groups.json",
            query_params={"limit": -1},
            use_auth=True,
            expected_status=400,
        )
        mock_result = TestResult(
            test_case=tc,
            status_code=400,
            response_body={"error": "no message key"},
            elapsed_ms=50.0,
            passed=True,
        )

        mock_client = MagicMock()
        mock_client.execute.return_value = mock_result

        runner = TestRunner(config, mock_client, tmp_path)
        results = runner.run_all([tc])

        assert len(results) == 1
        assert len(results[0].schema_warnings) == 0
