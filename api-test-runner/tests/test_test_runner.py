"""Tests for test_runner module."""

from __future__ import annotations

from pathlib import Path

import pytest

from api_test_runner.models import ApiSpec, Parameter, TestCase, TestResult
from api_test_runner.test_runner import TestRunner


class TestResolvePaths:
    def test_strips_base_path(self):
        spec = ApiSpec("3", "test", "/api/v2/groups.json", "GET", "groups")
        path, name = TestRunner._resolve_paths(spec, "/api/v2")
        assert path == "groups.json"
        assert name == "groups"

    def test_nested_url(self):
        spec = ApiSpec("8", "test", "/api/v2/members/bulk_create_job.json", "GET", "bulk_create_job")
        path, name = TestRunner._resolve_paths(spec, "/api/v2")
        assert path == "members/bulk_create_job.json"
        assert name == "members-bulk_create_job"

    def test_no_base_path(self):
        spec = ApiSpec("3", "test", "/groups.json", "GET", "groups")
        path, name = TestRunner._resolve_paths(spec, "")
        assert path == "groups.json"
        assert name == "groups"


class TestSearchTestValue:
    def test_integer_type(self):
        assert TestRunner._search_test_value("整数") == 1

    def test_boolean_type(self):
        assert TestRunner._search_test_value("真偽値") == "true"

    def test_id_param_name(self):
        assert TestRunner._search_test_value("文字列", "department_id") == 1

    def test_quoted_remarks(self):
        val = TestRunner._search_test_value("文字列", "status", '"all" or "active"')
        assert val == "all"

    def test_colon_remarks(self):
        val = TestRunner._search_test_value("文字列", "type", "通常の役職: company")
        assert val == "company"

    def test_fallback(self):
        assert TestRunner._search_test_value("文字列") == "test"


class TestGenerateTestCases:
    def _make_runner(self, patterns: list[str]) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_auth_pattern(self, sample_spec):
        runner = self._make_runner(["auth"])
        cases = runner.generate_test_cases([sample_spec])

        assert len(cases) == 2
        assert cases[0].pattern == "auth"
        assert cases[0].use_auth is True
        assert cases[0].expected_status == 200
        assert cases[1].pattern == "no_auth"
        assert cases[1].use_auth is False
        assert cases[1].expected_status == 401

    def test_pagination_pattern(self, sample_spec):
        runner = self._make_runner(["pagination"])
        cases = runner.generate_test_cases([sample_spec])

        assert len(cases) == 1
        assert cases[0].pattern == "pagination"
        assert cases[0].query_params == {"offset": 0, "limit": 5}

    def test_search_pattern(self, sample_spec):
        runner = self._make_runner(["search"])
        cases = runner.generate_test_cases([sample_spec])

        # name パラメータのみ（offset/limit は除外）
        assert len(cases) == 1
        assert cases[0].pattern == "search"
        assert "name" in cases[0].query_params

    def test_post_api_generates_no_auth_only(self):
        spec = ApiSpec(
            "9", "従業員登録用バッチジョブ登録API",
            "/api/v2/members/bulk_create_job.json", "POST", "bulk_create_job",
            params=[Parameter("従業員名", "name", "文字列", "〇", "")],
        )
        runner = self._make_runner(["auth", "pagination", "search"])
        cases = runner.generate_test_cases([spec])

        assert len(cases) == 1
        assert cases[0].pattern == "no_auth"
        assert cases[0].method == "POST"
        assert cases[0].expected_status == 401

    def test_skips_api_with_required_params(self):
        spec = ApiSpec(
            "8", "test", "/api/v2/members/bulk_create_job.json", "GET", "bulk_create_job",
            params=[Parameter("ジョブID", "job_id", "整数", "〇", "")],
        )
        runner = self._make_runner(["auth", "pagination"])
        cases = runner.generate_test_cases([spec])
        assert len(cases) == 0

    def test_combined_patterns(self, sample_spec):
        runner = self._make_runner(["auth", "pagination", "search"])
        cases = runner.generate_test_cases([sample_spec])

        patterns = [c.pattern for c in cases]
        assert "auth" in patterns
        assert "no_auth" in patterns
        assert "pagination" in patterns
        assert "search" in patterns


class TestLoadCustomTests:
    def test_loads_from_config(self):
        config = {
            "custom_tests": [
                {
                    "name": "health-check",
                    "url_path": "reports",
                    "method": "GET",
                    "use_auth": True,
                    "expected_status": 200,
                },
            ],
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.load_custom_tests()

        assert len(cases) == 1
        assert cases[0].name == "health-check"
        assert cases[0].pattern == "custom"

    def test_empty_config(self):
        runner = TestRunner({}, None, Path("/tmp"))
        assert runner.load_custom_tests() == []


class TestValidateSchema:
    @staticmethod
    def _make_result(
        api: ApiSpec | None = None,
        body: dict | list | None = None,
        passed: bool = True,
        expected_status: int = 200,
    ) -> TestResult:
        tc = TestCase(
            name="test", pattern="auth", api=api, method="GET",
            url_path="groups.json", query_params={},
            use_auth=True, expected_status=expected_status,
        )
        return TestResult(
            test_case=tc, status_code=expected_status,
            response_body=body, elapsed_ms=100.0, passed=passed,
        )

    def test_valid_response(self, sample_spec):
        result = self._make_result(
            api=sample_spec,
            body={"groups": [{"id": 1}]},
        )
        TestRunner._validate_schema(result)
        assert result.schema_warnings == []

    def test_missing_resource_key(self, sample_spec):
        result = self._make_result(
            api=sample_spec,
            body={"data": [{"id": 1}]},
        )
        TestRunner._validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "groups" in result.schema_warnings[0]

    def test_resource_not_list(self, sample_spec):
        result = self._make_result(
            api=sample_spec,
            body={"groups": {"id": 1}},
        )
        TestRunner._validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "list" in result.schema_warnings[0]

    def test_body_is_none(self, sample_spec):
        result = self._make_result(api=sample_spec, body=None)
        TestRunner._validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "空" in result.schema_warnings[0]

    def test_body_is_list(self, sample_spec):
        result = self._make_result(api=sample_spec, body=[{"id": 1}])
        TestRunner._validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "dict" in result.schema_warnings[0]

    def test_skips_failed_tests(self, sample_spec):
        result = self._make_result(api=sample_spec, body=None, passed=False)
        TestRunner._validate_schema(result)
        assert result.schema_warnings == []

    def test_skips_no_auth_tests(self, sample_spec):
        result = self._make_result(
            api=sample_spec, body={"error": "Unauthorized"},
            expected_status=401, passed=True,
        )
        # expected_status != 200 なのでスキップ
        TestRunner._validate_schema(result)
        assert result.schema_warnings == []

    def test_skips_custom_tests(self):
        result = self._make_result(api=None, body={"data": []})
        TestRunner._validate_schema(result)
        assert result.schema_warnings == []
