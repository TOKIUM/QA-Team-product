"""Tests for validator module (JSONスキーマ検証)."""

from __future__ import annotations

from pathlib import Path

import pytest

from api_test_runner.models import ApiSpec, Parameter, TestCase, TestResult
from api_test_runner.validator import ResponseValidator


class TestValidateJsonSchema:
    """validate_json_schema のテスト."""

    @staticmethod
    def _make_validator(json_schema_check=True):
        config = {
            "test": {
                "response_validation": {
                    "enabled": True,
                    "json_schema_check": json_schema_check,
                },
            },
        }
        return ResponseValidator(config)

    @staticmethod
    def _make_result(
        api=None, body=None, passed=True, expected_status=200, method="GET",
    ):
        tc = TestCase(
            name="test", pattern="auth", api=api, method=method,
            url_path="groups.json", query_params={},
            use_auth=True, expected_status=expected_status,
        )
        return TestResult(
            test_case=tc, status_code=expected_status,
            response_body=body, elapsed_ms=100.0, passed=passed,
        )

    def test_valid_types(self):
        """全フィールドの型が一致する場合、警告なし."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
            Parameter("名前", "name", "文字列", "", ""),
            Parameter("有効", "active", "真偽値", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"id": 1, "name": "test", "active": True}]},
        )
        validator.validate_json_schema(result)
        assert not any("型検証" in w for w in result.schema_warnings)

    def test_type_mismatch_integer(self):
        """整数フィールドに文字列がある場合、警告."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"id": "not_a_number"}]},
        )
        validator.validate_json_schema(result)
        assert any("型検証" in w and "id" in w for w in result.schema_warnings)

    def test_type_mismatch_string(self):
        """文字列フィールドに整数がある場合、警告."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("名前", "name", "文字列", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"name": 123}]},
        )
        validator.validate_json_schema(result)
        assert any("型検証" in w and "name" in w for w in result.schema_warnings)

    def test_type_mismatch_boolean(self):
        """真偽値フィールドに文字列がある場合、警告."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("有効", "active", "真偽値", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"active": "yes"}]},
        )
        validator.validate_json_schema(result)
        assert any("型検証" in w and "active" in w for w in result.schema_warnings)

    def test_type_mismatch_array(self):
        """配列フィールドに文字列がある場合、警告."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("タグ", "tags", "配列", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"tags": "not_array"}]},
        )
        validator.validate_json_schema(result)
        assert any("型検証" in w and "tags" in w for w in result.schema_warnings)

    def test_missing_field(self):
        """定義されたフィールドがレスポンスにない場合、警告."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
            Parameter("名前", "name", "文字列", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"id": 1}]},
        )
        validator.validate_json_schema(result)
        assert any("型検証" in w and "name" in w for w in result.schema_warnings)

    def test_null_value_allowed(self):
        """null 値は型チェックをスキップ."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("名前", "name", "文字列", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"name": None}]},
        )
        validator.validate_json_schema(result)
        assert not any("型検証" in w for w in result.schema_warnings)

    def test_disabled(self):
        """json_schema_check: false の場合、検証しない."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
        ])
        validator = self._make_validator(json_schema_check=False)
        result = self._make_result(
            api=spec,
            body={"groups": [{"id": "bad"}]},
        )
        validator.validate_json_schema(result)
        assert not any("型検証" in w for w in result.schema_warnings)

    def test_skips_non_get(self):
        """GET 以外のメソッドはスキップ."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "POST", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"id": "bad"}]},
            method="POST",
        )
        validator.validate_json_schema(result)
        assert not any("型検証" in w for w in result.schema_warnings)

    def test_skips_failed(self):
        """FAIL テストはスキップ."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(api=spec, body=None, passed=False)
        validator.validate_json_schema(result)
        assert not any("型検証" in w for w in result.schema_warnings)

    def test_skips_pagination_params(self):
        """offset/limit/fields はスキップする."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("オフセット", "offset", "整数", "", ""),
            Parameter("取得件数", "limit", "整数", "", ""),
            Parameter("フィールド", "fields", "文字列", "", ""),
            Parameter("名前", "name", "文字列", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"name": "test"}]},
        )
        validator.validate_json_schema(result)
        # offset/limit/fields の欠損警告は出ない
        warnings_text = " ".join(result.schema_warnings)
        assert "offset" not in warnings_text
        assert "limit" not in warnings_text
        assert "fields" not in warnings_text

    def test_empty_items(self):
        """リソース配列が空の場合、検証しない."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": []},
        )
        validator.validate_json_schema(result)
        assert not any("型検証" in w for w in result.schema_warnings)

    def test_bool_not_counted_as_int(self):
        """bool は整数として扱わない."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"id": True}]},
        )
        validator.validate_json_schema(result)
        assert any("型検証" in w and "id" in w for w in result.schema_warnings)


    def test_custom_skip_params(self):
        """json_schema_skip_params でカスタム除外パラメータを指定."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ソート", "sort", "文字列", "", ""),
            Parameter("名前", "name", "文字列", "", ""),
        ])
        config = {
            "test": {
                "response_validation": {
                    "enabled": True,
                    "json_schema_check": True,
                    "json_schema_skip_params": ["sort"],
                },
            },
        }
        validator = ResponseValidator(config)
        result = self._make_result(
            api=spec,
            body={"groups": [{"name": "test"}]},
        )
        validator.validate_json_schema(result)
        # sort は除外されるので欠損警告なし
        assert not any("sort" in w for w in result.schema_warnings)

    def test_nested_object_only_checks_top_level(self):
        """ネストされたオブジェクト型はトップレベルのフィールドのみ検証."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ID", "id", "整数", "", ""),
            Parameter("ユーザー", "user", "オブジェクト", "", "",
                      children=[
                          Parameter("名前", "name", "文字列", "〇", ""),
                      ]),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"id": 1, "user": {"name": "test"}}]},
        )
        validator.validate_json_schema(result)
        # user はオブジェクト型として検証（子フィールドは対象外）
        assert not any("型検証" in w for w in result.schema_warnings)

    def test_nested_object_type_mismatch(self):
        """ネストされたオブジェクト型に文字列が入っている場合、警告."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("ユーザー", "user", "オブジェクト", "", ""),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"user": "not_object"}]},
        )
        validator.validate_json_schema(result)
        assert any("型検証" in w and "user" in w for w in result.schema_warnings)

    def test_nested_array_type_check(self):
        """配列型フィールドがリストであれば警告なし."""
        spec = ApiSpec("1", "test", "/api/v2/groups.json", "GET", "groups", params=[
            Parameter("タグ", "tags", "配列", "", "",
                      children=[
                          Parameter("タグ名", "name", "文字列", "〇", ""),
                      ]),
        ])
        validator = self._make_validator()
        result = self._make_result(
            api=spec,
            body={"groups": [{"tags": [{"name": "a"}]}]},
        )
        validator.validate_json_schema(result)
        assert not any("型検証" in w for w in result.schema_warnings)


class TestCheckType:
    """_check_type のエッジケース."""

    def test_object_type(self):
        assert ResponseValidator._check_type("string", "オブジェクト") == "str"
        assert ResponseValidator._check_type({}, "オブジェクト") is None

    def test_unknown_type_passes(self):
        assert ResponseValidator._check_type("anything", "不明な型") is None

    def test_integer_with_bool(self):
        """bool は int のサブクラスだが整数として扱わない."""
        assert ResponseValidator._check_type(True, "整数") == "bool"
        assert ResponseValidator._check_type(False, "整数") == "bool"
        assert ResponseValidator._check_type(42, "整数") is None

    def test_string_type(self):
        assert ResponseValidator._check_type(123, "文字列") == "int"
        assert ResponseValidator._check_type("hello", "文字列") is None

    def test_boolean_type(self):
        assert ResponseValidator._check_type("yes", "真偽値") == "str"
        assert ResponseValidator._check_type(True, "真偽値") is None

    def test_array_type(self):
        assert ResponseValidator._check_type("not_list", "配列") == "str"
        assert ResponseValidator._check_type([1, 2], "配列") is None

    def test_null_always_passes(self):
        assert ResponseValidator._check_type(None, "整数") is None
        assert ResponseValidator._check_type(None, "文字列") is None


class TestBuildFieldTypeMap:
    """_build_field_type_map のテスト."""

    def test_skips_pagination_params(self):
        params = [
            Parameter("オフセット", "offset", "整数", "", ""),
            Parameter("取得件数", "limit", "整数", "", ""),
            Parameter("名前", "name", "文字列", "", ""),
        ]
        result = ResponseValidator._build_field_type_map(params)
        assert "offset" not in result
        assert "limit" not in result
        assert result == {"name": "文字列"}

    def test_custom_skip_params(self):
        """カスタム除外パラメータを指定."""
        params = [
            Parameter("ソート", "sort", "文字列", "", ""),
            Parameter("名前", "name", "文字列", "", ""),
        ]
        result = ResponseValidator._build_field_type_map(
            params, skip_params={"sort", "offset", "limit", "fields"})
        assert "sort" not in result
        assert result == {"name": "文字列"}

    def test_nested_params_included_as_top_level(self):
        """ネストされたパラメータの親はトップレベルとして含まれる."""
        params = [
            Parameter("ユーザー", "user", "オブジェクト", "", "",
                      children=[
                          Parameter("名前", "name", "文字列", "〇", ""),
                      ]),
            Parameter("ID", "id", "整数", "", ""),
        ]
        result = ResponseValidator._build_field_type_map(params)
        assert result == {"user": "オブジェクト", "id": "整数"}
