"""Tests for test_runner module."""

from __future__ import annotations

from pathlib import Path

import pytest

from api_test_runner.models import ApiSpec, Parameter, TestCase, TestResult
from api_test_runner.test_generator import TestGenerator
from api_test_runner.test_runner import TestRunner
from api_test_runner.validator import ResponseValidator


class TestResolvePaths:
    def test_strips_base_path(self):
        spec = ApiSpec("3", "test", "/api/v2/groups.json", "GET", "groups")
        path, name = TestGenerator({})._resolve_paths(spec,"/api/v2")
        assert path == "groups.json"
        assert name == "groups"

    def test_nested_url(self):
        spec = ApiSpec("8", "test", "/api/v2/members/bulk_create_job.json", "GET", "bulk_create_job")
        path, name = TestGenerator({})._resolve_paths(spec,"/api/v2")
        assert path == "members/bulk_create_job.json"
        assert name == "members-bulk_create_job"

    def test_no_base_path(self):
        spec = ApiSpec("3", "test", "/groups.json", "GET", "groups")
        path, name = TestGenerator({})._resolve_paths(spec,"")
        assert path == "groups.json"
        assert name == "groups"


class TestSearchTestValue:
    def test_integer_type(self):
        assert TestGenerator._search_test_value("整数") == 1

    def test_boolean_type(self):
        assert TestGenerator._search_test_value("真偽値") == "true"

    def test_id_param_name(self):
        assert TestGenerator._search_test_value("文字列", "department_id") == 1

    def test_quoted_remarks(self):
        val = TestGenerator._search_test_value("文字列", "status", '"all" or "active"')
        assert val == "all"

    def test_colon_remarks(self):
        val = TestGenerator._search_test_value("文字列", "type", "通常の役職: company")
        assert val == "company"

    def test_fallback(self):
        assert TestGenerator._search_test_value("文字列") == "test"


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
        ResponseValidator.validate_schema(result)
        assert result.schema_warnings == []

    def test_missing_resource_key(self, sample_spec):
        result = self._make_result(
            api=sample_spec,
            body={"data": [{"id": 1}]},
        )
        ResponseValidator.validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "groups" in result.schema_warnings[0]

    def test_resource_not_list(self, sample_spec):
        result = self._make_result(
            api=sample_spec,
            body={"groups": {"id": 1}},
        )
        ResponseValidator.validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "list" in result.schema_warnings[0]

    def test_body_is_none(self, sample_spec):
        result = self._make_result(api=sample_spec, body=None)
        ResponseValidator.validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "空" in result.schema_warnings[0]

    def test_body_is_list(self, sample_spec):
        result = self._make_result(api=sample_spec, body=[{"id": 1}])
        ResponseValidator.validate_schema(result)
        assert len(result.schema_warnings) == 1
        assert "dict" in result.schema_warnings[0]

    def test_skips_failed_tests(self, sample_spec):
        result = self._make_result(api=sample_spec, body=None, passed=False)
        ResponseValidator.validate_schema(result)
        assert result.schema_warnings == []

    def test_skips_no_auth_tests(self, sample_spec):
        result = self._make_result(
            api=sample_spec, body={"error": "Unauthorized"},
            expected_status=401, passed=True,
        )
        # expected_status != 200 なのでスキップ
        ResponseValidator.validate_schema(result)
        assert result.schema_warnings == []

    def test_skips_custom_tests(self):
        result = self._make_result(api=None, body={"data": []})
        ResponseValidator.validate_schema(result)
        assert result.schema_warnings == []


class TestValidateResponseBody:
    """レスポンスボディ検証テスト."""

    @staticmethod
    def _make_runner(enabled=True, pagination_check=True, fields_check=True):
        config = {
            "test": {
                "response_validation": {
                    "enabled": enabled,
                    "pagination_count_check": pagination_check,
                    "required_fields_check": fields_check,
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    @staticmethod
    def _make_result(api, body, passed=True, expected_status=200, query_params=None):
        tc = TestCase(
            name="test", pattern="auth", api=api, method="GET",
            url_path="groups.json", query_params=query_params or {},
            use_auth=True, expected_status=expected_status,
        )
        return TestResult(
            test_case=tc, status_code=expected_status,
            response_body=body, elapsed_ms=100.0, passed=passed,
        )

    def test_empty_body_warns(self, sample_spec):
        runner = self._make_runner()
        result = self._make_result(sample_spec, {})
        runner._validator.validate_response_body(result)
        assert any("空" in w for w in result.schema_warnings)

    def test_null_body_warns(self, sample_spec):
        runner = self._make_runner()
        result = self._make_result(sample_spec, None)
        runner._validator.validate_response_body(result)
        assert any("空" in w for w in result.schema_warnings)

    def test_pagination_count_exceeds_limit(self, sample_spec):
        runner = self._make_runner()
        body = {"groups": [{"id": 1}, {"id": 2}, {"id": 3}]}
        result = self._make_result(sample_spec, body, query_params={"limit": 2})
        runner._validator.validate_response_body(result)
        assert any("limit=2" in w for w in result.schema_warnings)

    def test_pagination_count_within_limit(self, sample_spec):
        runner = self._make_runner()
        body = {"groups": [{"id": 1}, {"id": 2}]}
        result = self._make_result(sample_spec, body, query_params={"limit": 5})
        runner._validator.validate_response_body(result)
        assert not any("limit" in w for w in result.schema_warnings)

    def test_disabled_skips_all(self, sample_spec):
        runner = self._make_runner(enabled=False)
        result = self._make_result(sample_spec, {})
        runner._validator.validate_response_body(result)
        assert not any("レスポンス検証" in w for w in result.schema_warnings)

    def test_fail_result_skipped(self, sample_spec):
        runner = self._make_runner()
        result = self._make_result(sample_spec, {}, passed=False)
        runner._validator.validate_response_body(result)
        assert result.schema_warnings == []

    def test_key_consistency_warns(self, sample_spec):
        runner = self._make_runner()
        body = {"groups": [{"id": 1, "name": "a"}, {"id": 2}]}
        result = self._make_result(sample_spec, body)
        runner._validator.validate_response_body(result)
        assert any("欠損" in w for w in result.schema_warnings)

    def test_key_consistency_ok(self, sample_spec):
        runner = self._make_runner()
        body = {"groups": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}
        result = self._make_result(sample_spec, body)
        runner._validator.validate_response_body(result)
        assert not any("キー欠損" in w for w in result.schema_warnings)


class TestPutDeletePatchPatterns:
    """PUT/DELETE/PATCH パターンのテストケース生成テスト."""

    def _make_runner(self, patterns: list[str]) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_put_normal_generates_normal_and_no_auth(self, sample_put_spec):
        runner = self._make_runner(["put_normal"])
        cases = runner.generate_test_cases([sample_put_spec])

        assert len(cases) == 2
        assert cases[0].name == "put-members-update-normal"
        assert cases[0].pattern == "put_normal"
        assert cases[0].method == "PUT"
        assert cases[0].use_auth is True
        assert cases[0].request_body is not None
        assert cases[0].expected_status == 200
        assert cases[1].name == "put-members-update-normal-no-auth"
        assert cases[1].use_auth is False
        assert cases[1].expected_status == 401

    def test_delete_normal_generates_normal_and_no_auth(self, sample_delete_spec):
        runner = self._make_runner(["delete_normal"])
        cases = runner.generate_test_cases([sample_delete_spec])

        assert len(cases) == 2
        assert cases[0].name == "delete-members-delete-normal"
        assert cases[0].pattern == "delete_normal"
        assert cases[0].method == "DELETE"
        assert cases[0].use_auth is True
        assert cases[0].request_body is None
        assert cases[0].expected_status == 200
        assert cases[1].name == "delete-members-delete-normal-no-auth"
        assert cases[1].use_auth is False
        assert cases[1].expected_status == 401

    def test_patch_normal_generates_normal_and_no_auth(self, sample_patch_spec):
        runner = self._make_runner(["patch_normal"])
        cases = runner.generate_test_cases([sample_patch_spec])

        assert len(cases) == 2
        assert cases[0].name == "patch-members-patch-normal"
        assert cases[0].pattern == "patch_normal"
        assert cases[0].method == "PATCH"
        assert cases[0].use_auth is True
        assert cases[0].request_body is not None
        assert cases[0].expected_status == 200
        assert cases[1].name == "patch-members-patch-normal-no-auth"
        assert cases[1].use_auth is False
        assert cases[1].expected_status == 401

    def test_auth_generates_no_auth_for_put_delete_patch(
        self, sample_put_spec, sample_delete_spec, sample_patch_spec,
    ):
        runner = self._make_runner(["auth"])
        cases = runner.generate_test_cases([
            sample_put_spec, sample_delete_spec, sample_patch_spec,
        ])

        assert len(cases) == 3
        methods = [c.method for c in cases]
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "PATCH" in methods
        assert all(c.pattern == "no_auth" for c in cases)
        assert all(c.expected_status == 401 for c in cases)

    def test_missing_required_for_put_spec(self, sample_put_spec):
        runner = self._make_runner(["missing_required"])
        cases = runner.generate_test_cases([sample_put_spec])

        assert len(cases) == 2  # name, email の2フィールド
        assert all(c.pattern == "missing_required" for c in cases)
        assert all(c.method == "PUT" for c in cases)
        assert all(c.request_body is not None for c in cases)

    def test_missing_required_for_patch_spec(self, sample_patch_spec):
        runner = self._make_runner(["missing_required"])
        cases = runner.generate_test_cases([sample_patch_spec])

        assert len(cases) == 1  # name の1フィールド
        assert cases[0].pattern == "missing_required"
        assert cases[0].method == "PATCH"

    def test_delete_not_in_missing_required(self, sample_delete_spec):
        """DELETE は body なしなので missing_required のbody省略テスト対象外."""
        runner = self._make_runner(["missing_required"])
        cases = runner.generate_test_cases([sample_delete_spec])
        assert len(cases) == 0

    def test_put_normal_with_api_overrides(self, sample_put_spec):
        config = {
            "test": {
                "patterns": ["put_normal"],
                "put_normal": {
                    "expected_status": 200,
                    "api_overrides": {
                        "members-update": {"expected_status": 204},
                    },
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.generate_test_cases([sample_put_spec])

        assert cases[0].expected_status == 204

    def test_put_normal_with_body_overrides(self, sample_put_spec):
        """PUT の body_overrides でフィールドが上書きされる."""
        config = {
            "test": {
                "patterns": ["put_normal"],
                "put_normal": {
                    "expected_status": 200,
                    "body_overrides": {
                        "members-update": {"name": "固定名前", "id": "abc-123"},
                    },
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.generate_test_cases([sample_put_spec])
        normal = next(c for c in cases if c.use_auth)
        assert normal.request_body["name"] == "固定名前"

    def test_put_normal_with_individual_only(self, sample_put_spec):
        """PUT の individual_only で全実行時にスキップされる."""
        config = {
            "test": {
                "patterns": ["put_normal"],
                "put_normal": {
                    "individual_only": ["members-update"],
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.generate_test_cases([sample_put_spec])
        assert len(cases) == 0

    def test_patch_normal_with_body_overrides(self, sample_patch_spec):
        """PATCH の body_overrides でフィールドが上書きされる."""
        config = {
            "test": {
                "patterns": ["patch_normal"],
                "patch_normal": {
                    "expected_status": 200,
                    "body_overrides": {
                        "members-patch": {"name": "パッチ名前"},
                    },
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.generate_test_cases([sample_patch_spec])
        normal = next(c for c in cases if c.use_auth)
        assert normal.request_body["name"] == "パッチ名前"

    def test_patch_normal_with_individual_only(self, sample_patch_spec):
        """PATCH の individual_only で全実行時にスキップされる."""
        config = {
            "test": {
                "patterns": ["patch_normal"],
                "patch_normal": {
                    "individual_only": ["members-patch"],
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.generate_test_cases([sample_patch_spec])
        assert len(cases) == 0

    def test_delete_normal_with_individual_only(self, sample_delete_spec):
        """DELETE の individual_only で全実行時にスキップされる."""
        config = {
            "test": {
                "patterns": ["delete_normal"],
                "delete_normal": {
                    "individual_only": ["members-delete"],
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.generate_test_cases([sample_delete_spec])
        assert len(cases) == 0

    def test_delete_normal_with_api_overrides(self, sample_delete_spec):
        config = {
            "test": {
                "patterns": ["delete_normal"],
                "delete_normal": {
                    "expected_status": 200,
                    "api_overrides": {
                        "members-delete": {"expected_status": 204},
                    },
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        cases = runner.generate_test_cases([sample_delete_spec])

        assert cases[0].expected_status == 204


class TestGetDcConfig:
    """_get_dc_config() のフォールバック動作テスト."""

    def test_pattern_specific_config(self):
        """パターン固有の data_comparison が優先される."""
        config = {
            "test": {
                "post_normal": {"data_comparison": {"enabled": True, "wait_after_post_seconds": 5}},
                "put_normal": {"data_comparison": {"enabled": False, "wait_after_post_seconds": 10}},
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        enabled, dc_cfg = runner._get_dc_config("put_normal")
        assert enabled is False
        assert dc_cfg.get("wait_after_post_seconds") == 10

    def test_fallback_to_post_normal(self):
        """パターン固有設定がない場合は post_normal にフォールバック."""
        config = {
            "test": {
                "post_normal": {"data_comparison": {"enabled": True, "wait_after_post_seconds": 5}},
                "delete_normal": {"expected_status": 200},
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        enabled, dc_cfg = runner._get_dc_config("delete_normal")
        assert enabled is True
        assert dc_cfg.get("wait_after_post_seconds") == 5

    def test_no_config_at_all(self):
        """どちらも未設定の場合は無効."""
        config = {
            "test": {},
            "api": {"base_url": "https://example.com/api/v2"},
        }
        runner = TestRunner(config, None, Path("/tmp"))
        enabled, dc_cfg = runner._get_dc_config("patch_normal")
        assert enabled is False
        assert dc_cfg == {}
