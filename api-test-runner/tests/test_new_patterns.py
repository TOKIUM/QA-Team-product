"""Tests for new test patterns: boundary, missing_required, post_normal."""

from __future__ import annotations

from pathlib import Path

import pytest

from api_test_runner.models import ApiSpec, Parameter, TestCase
from api_test_runner.test_runner import TestRunner


class TestBoundaryPattern:
    def _make_runner(self, patterns: list[str], **kwargs) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
                **kwargs,
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_boundary_with_max_value(self, sample_spec):
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([sample_spec])

        # limit 4ケース + offset 2ケース = 6
        assert len(cases) == 6
        names = [c.name for c in cases]
        assert "boundary-groups-limit-negative" in names
        assert "boundary-groups-limit-zero" in names
        assert "boundary-groups-limit-max" in names
        assert "boundary-groups-limit-overflow" in names
        assert "boundary-groups-offset-negative" in names
        assert "boundary-groups-offset-large" in names

        neg = next(c for c in cases if "negative" in c.name)
        assert neg.query_params == {"limit": -1}
        assert neg.expected_status == 400

        zero = next(c for c in cases if "zero" in c.name)
        assert zero.query_params == {"limit": 0}
        assert zero.expected_status == 200

        max_case = next(c for c in cases if c.name.endswith("-max"))
        assert max_case.query_params == {"limit": 1000}
        assert max_case.expected_status == 200

        overflow = next(c for c in cases if "overflow" in c.name)
        assert overflow.query_params == {"limit": 1001}
        assert overflow.expected_status == 400

    def test_boundary_without_max_value(self, sample_spec_no_max):
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([sample_spec_no_max])

        # max_value なし → limit 負数/ゼロ(2) + offset 負数/巨大値(2) = 4
        assert len(cases) == 4
        names = [c.name for c in cases]
        assert "boundary-positions-limit-negative" in names
        assert "boundary-positions-limit-zero" in names
        assert "boundary-positions-offset-negative" in names
        assert "boundary-positions-offset-large" in names

    def test_boundary_overflow_status_configurable(self, sample_spec):
        runner = self._make_runner(
            ["boundary"],
            boundary={"overflow_expected_status": 200},
        )
        cases = runner.generate_test_cases([sample_spec])
        overflow = next(c for c in cases if "overflow" in c.name)
        assert overflow.expected_status == 200

    def test_boundary_skips_post_apis(self, sample_post_spec):
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([sample_post_spec])
        assert len(cases) == 0

    def test_boundary_all_cases_use_auth(self, sample_spec):
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([sample_spec])
        assert all(c.use_auth for c in cases)
        assert all(c.pattern == "boundary" for c in cases)


class TestMissingRequiredPattern:
    def _make_runner(self, patterns: list[str]) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_get_api_with_required_params(self):
        spec = ApiSpec(
            "8", "ジョブ取得API",
            "/api/v2/members/bulk_create_job.json", "GET", "bulk_create_job",
            params=[
                Parameter("ジョブID", "job_id", "整数", "〇", ""),
                Parameter("ステータス", "status", "文字列", "", ""),
            ],
        )
        runner = self._make_runner(["missing_required"])
        cases = runner.generate_test_cases([spec])

        assert len(cases) == 1
        assert cases[0].pattern == "missing_required"
        assert cases[0].expected_status == 400
        assert "job_id" not in cases[0].query_params

    def test_get_api_no_required_params(self, sample_spec):
        """必須パラメータなし → missing_required ケースなし."""
        runner = self._make_runner(["missing_required"])
        cases = runner.generate_test_cases([sample_spec])
        assert len(cases) == 0

    def test_post_api_missing_required(self, sample_post_spec):
        runner = self._make_runner(["missing_required"])
        cases = runner.generate_test_cases([sample_post_spec])

        # members（親）, members[0].name, members[0].email, members[0].authorities（子親）, members[0].password
        assert len(cases) >= 4
        assert all(c.pattern == "missing_required" for c in cases)
        assert all(c.expected_status == 400 for c in cases)
        assert all(c.request_body is not None for c in cases)

        # members 自体を省略するケース（名前末尾で完全一致）
        members_case = next(
            (c for c in cases if c.name.endswith("-no-members")), None,
        )
        assert members_case is not None
        assert "members" not in members_case.request_body

    def test_post_api_missing_nested_required(self, sample_post_spec):
        runner = self._make_runner(["missing_required"])
        cases = runner.generate_test_cases([sample_post_spec])

        # name を省略するケース
        name_case = next(
            (c for c in cases if "no-members.name" in c.name
             or "no-members-name" in c.name), None,
        )
        assert name_case is not None
        # members 配列は存在するが name が欠損
        assert "members" in name_case.request_body


class TestPostNormalPattern:
    def _make_runner(self, patterns: list[str], **kwargs) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
                **kwargs,
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_post_normal_generates_two_cases(self, sample_post_spec):
        runner = self._make_runner(["post_normal"])
        cases = runner.generate_test_cases([sample_post_spec])

        assert len(cases) == 2
        normal = next(c for c in cases if c.use_auth)
        no_auth = next(c for c in cases if not c.use_auth)

        assert normal.pattern == "post_normal"
        assert normal.expected_status == 200
        assert normal.request_body is not None
        assert "members" in normal.request_body

        assert no_auth.pattern == "post_normal"
        assert no_auth.expected_status == 401

    def test_post_normal_custom_status(self, sample_post_spec):
        runner = self._make_runner(
            ["post_normal"],
            post_normal={"expected_status": 201},
        )
        cases = runner.generate_test_cases([sample_post_spec])
        normal = next(c for c in cases if c.use_auth)
        assert normal.expected_status == 201

    def test_post_normal_skips_get_apis(self, sample_spec):
        runner = self._make_runner(["post_normal"])
        cases = runner.generate_test_cases([sample_spec])
        assert len(cases) == 0


class TestPostTestValue:
    def test_string_type(self):
        p = Parameter("名前", "name", "文字列", "〇", "")
        val = TestRunner._post_test_value(p)
        assert val == "test_value"

    def test_email_type(self):
        p = Parameter("メール", "email", "文字列", "〇", "")
        val = TestRunner._post_test_value(p)
        assert "@example.com" in val

    def test_password_type(self):
        p = Parameter("パスワード", "password", "文字列", "〇", "")
        val = TestRunner._post_test_value(p)
        assert isinstance(val, str)
        assert len(val) >= 8

    def test_integer_type(self):
        p = Parameter("ID", "id", "整数", "〇", "")
        assert TestRunner._post_test_value(p) == 1

    def test_boolean_type(self):
        p = Parameter("権限", "is_admin", "真偽値", "", "")
        assert TestRunner._post_test_value(p) is False

    def test_array_with_children(self):
        child = Parameter("名前", "name", "文字列", "〇", "")
        p = Parameter("一覧", "items", "配列", "〇", "", children=[child])
        val = TestRunner._post_test_value(p)
        assert isinstance(val, list)
        assert len(val) == 1
        assert val[0] == {"name": "test_value"}

    def test_object_with_children(self):
        child = Parameter("権限", "is_admin", "真偽値", "〇", "")
        p = Parameter("権限情報", "authorities", "オブジェクト", "〇", "", children=[child])
        val = TestRunner._post_test_value(p)
        assert isinstance(val, dict)
        assert val == {"is_admin": False}

    def test_override(self):
        p = Parameter("部署ID", "department_id", "文字列", "〇", "")
        val = TestRunner._post_test_value(p, {"department_id": "abc-123"})
        assert val == "abc-123"


class TestBuildMinimalBody:
    def test_simple_required(self):
        params = [
            Parameter("名前", "name", "文字列", "〇", ""),
            Parameter("任意", "optional", "文字列", "", ""),
        ]
        body = TestRunner._build_minimal_body(params)
        assert "name" in body
        assert "optional" not in body

    def test_nested_required(self, sample_post_spec):
        body = TestRunner._build_minimal_body(sample_post_spec.params)
        assert "members" in body
        assert isinstance(body["members"], list)
        assert len(body["members"]) == 1
        member = body["members"][0]
        assert "name" in member
        assert "email" in member
        assert "password" in member
        assert "authorities" in member
        # employee_id は任意なので含まれない
        assert "employee_id" not in member


class TestOmitField:
    def test_simple_key(self):
        body = {"name": "test", "email": "a@b.com"}
        result = TestRunner._omit_field(body, "name")
        assert "name" not in result
        assert "email" in result

    def test_nested_array_key(self):
        body = {"members": [{"name": "test", "email": "a@b.com"}]}
        result = TestRunner._omit_field(body, "members[0].name")
        assert "name" not in result["members"][0]
        assert "email" in result["members"][0]

    def test_top_level_key(self):
        body = {"members": [{"name": "test"}], "other": 1}
        result = TestRunner._omit_field(body, "members")
        assert "members" not in result
        assert "other" in result

    def test_invalid_path_returns_original(self):
        body = {"name": "test"}
        result = TestRunner._omit_field(body, "nonexistent.field")
        assert result == body

    def test_does_not_mutate_original(self):
        body = {"members": [{"name": "test", "email": "a@b.com"}]}
        TestRunner._omit_field(body, "members[0].name")
        assert "name" in body["members"][0]


class TestOffsetBoundary:
    """offset 境界値テスト."""

    def _make_runner(self, patterns: list[str], **kwargs) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
                **kwargs,
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_offset_boundary_generates_two_cases(self, sample_spec):
        """offset パラメータがある API で負数・巨大値の2ケース生成."""
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([sample_spec])
        offset_cases = [c for c in cases if "offset" in c.name]
        assert len(offset_cases) == 2
        names = [c.name for c in offset_cases]
        assert "boundary-groups-offset-negative" in names
        assert "boundary-groups-offset-large" in names

    def test_offset_negative_defaults_to_400(self, sample_spec):
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([sample_spec])
        neg = next(c for c in cases if "offset-negative" in c.name)
        assert neg.query_params == {"offset": -1}
        assert neg.expected_status == 400

    def test_offset_large_defaults(self, sample_spec):
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([sample_spec])
        large = next(c for c in cases if "offset-large" in c.name)
        assert large.query_params == {"offset": 999999}
        assert large.expected_status == 200

    def test_offset_large_value_configurable(self, sample_spec):
        runner = self._make_runner(
            ["boundary"],
            boundary={"offset_large_value": 500000},
        )
        cases = runner.generate_test_cases([sample_spec])
        large = next(c for c in cases if "offset-large" in c.name)
        assert large.query_params == {"offset": 500000}

    def test_offset_api_overrides(self, sample_spec):
        """api_overrides で offset 設定を上書き."""
        runner = self._make_runner(
            ["boundary"],
            boundary={
                "offset_negative_expected_status": 400,
                "api_overrides": {
                    "groups": {
                        "offset_negative_expected_status": 200,
                        "offset_large_value": 100000,
                        "offset_large_expected_status": 400,
                    },
                },
            },
        )
        cases = runner.generate_test_cases([sample_spec])
        neg = next(c for c in cases if "offset-negative" in c.name)
        assert neg.expected_status == 200
        large = next(c for c in cases if "offset-large" in c.name)
        assert large.query_params == {"offset": 100000}
        assert large.expected_status == 400

    def test_no_offset_param_no_cases(self):
        """offset パラメータがない API では offset 境界値テストなし."""
        spec = ApiSpec(
            "10", "テストAPI", "/api/v2/test.json", "GET", "test",
            params=[
                Parameter("名前", "name", "文字列", "", ""),
                Parameter("取得件数", "limit", "整数", "", "最大100", max_value=100),
            ],
        )
        runner = self._make_runner(["boundary"])
        cases = runner.generate_test_cases([spec])
        offset_cases = [c for c in cases if "offset" in c.name]
        assert len(offset_cases) == 0


class TestApiOverrides:
    """api_overrides によるステータスコード上書きテスト."""

    def _make_runner(self, patterns: list[str], **kwargs) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
                **kwargs,
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_boundary_api_overrides_negative(self, sample_spec):
        """boundary の negative_expected_status を API 単位で上書き."""
        runner = self._make_runner(
            ["boundary"],
            boundary={
                "overflow_expected_status": 400,
                "api_overrides": {
                    "groups": {"negative_expected_status": 200},
                },
            },
        )
        cases = runner.generate_test_cases([sample_spec])
        neg = next(c for c in cases if "negative" in c.name)
        assert neg.expected_status == 200

    def test_boundary_api_overrides_zero(self, sample_spec):
        """boundary の zero_expected_status を API 単位で上書き."""
        runner = self._make_runner(
            ["boundary"],
            boundary={
                "api_overrides": {
                    "groups": {"zero_expected_status": 400},
                },
            },
        )
        cases = runner.generate_test_cases([sample_spec])
        zero = next(c for c in cases if "zero" in c.name)
        assert zero.expected_status == 400

    def test_boundary_api_overrides_overflow(self, sample_spec):
        """boundary の overflow_expected_status を API 単位で上書き."""
        runner = self._make_runner(
            ["boundary"],
            boundary={
                "overflow_expected_status": 400,
                "api_overrides": {
                    "groups": {"overflow_expected_status": 200},
                },
            },
        )
        cases = runner.generate_test_cases([sample_spec])
        overflow = next(c for c in cases if "overflow" in c.name)
        assert overflow.expected_status == 200

    def test_boundary_no_override_uses_global(self, sample_spec):
        """api_overrides に該当 API がなければグローバル設定を使用."""
        runner = self._make_runner(
            ["boundary"],
            boundary={
                "overflow_expected_status": 400,
                "api_overrides": {
                    "other_api": {"overflow_expected_status": 200},
                },
            },
        )
        cases = runner.generate_test_cases([sample_spec])
        overflow = next(c for c in cases if "overflow" in c.name)
        assert overflow.expected_status == 400

    def test_missing_required_api_overrides(self):
        """missing_required の expected_status を API 単位で上書き."""
        spec = ApiSpec(
            "8", "ジョブ取得API",
            "/api/v2/members/bulk_create_job.json", "GET", "bulk_create_job",
            params=[
                Parameter("ジョブID", "job_id", "整数", "〇", ""),
            ],
        )
        runner = self._make_runner(
            ["missing_required"],
            missing_required={
                "expected_status": 400,
                "api_overrides": {
                    "members-bulk_create_job": {"expected_status": 422},
                },
            },
        )
        cases = runner.generate_test_cases([spec])
        assert len(cases) == 1
        assert cases[0].expected_status == 422

    def test_missing_required_global_default(self):
        """missing_required のグローバル expected_status を変更."""
        spec = ApiSpec(
            "8", "ジョブ取得API",
            "/api/v2/members/bulk_create_job.json", "GET", "bulk_create_job",
            params=[
                Parameter("ジョブID", "job_id", "整数", "〇", ""),
            ],
        )
        runner = self._make_runner(
            ["missing_required"],
            missing_required={"expected_status": 422},
        )
        cases = runner.generate_test_cases([spec])
        assert cases[0].expected_status == 422

    def test_missing_required_post_api_overrides(self, sample_post_spec):
        """POST missing_required の expected_status を API 単位で上書き."""
        runner = self._make_runner(
            ["missing_required"],
            missing_required={
                "expected_status": 400,
                "api_overrides": {
                    "members-bulk_create_job": {"expected_status": 422},
                },
            },
        )
        cases = runner.generate_test_cases([sample_post_spec])
        assert all(c.expected_status == 422 for c in cases)

    def test_missing_required_skip_fields(self, sample_post_spec):
        """skip_fields で指定したフィールドのテストケースをスキップ."""
        runner = self._make_runner(
            ["missing_required"],
            missing_required={
                "api_overrides": {
                    "members-bulk_create_job": {
                        "skip_fields": ["members[0].password"],
                    },
                },
            },
        )
        cases = runner.generate_test_cases([sample_post_spec])
        names = [c.name for c in cases]
        assert not any("no-members-password" in n for n in names)
        # password 以外のケースは残る
        assert any("no-members-name" in n for n in names)

    def test_post_normal_api_overrides(self, sample_post_spec):
        """post_normal の expected_status を API 単位で上書き."""
        runner = self._make_runner(
            ["post_normal"],
            post_normal={
                "expected_status": 200,
                "api_overrides": {
                    "members-bulk_create_job": {"expected_status": 201},
                },
            },
        )
        cases = runner.generate_test_cases([sample_post_spec])
        normal = next(c for c in cases if c.use_auth)
        assert normal.expected_status == 201

    def test_post_normal_api_overrides_no_match(self, sample_post_spec):
        """api_overrides に該当なし → グローバル設定を使用."""
        runner = self._make_runner(
            ["post_normal"],
            post_normal={
                "expected_status": 200,
                "api_overrides": {
                    "other_api": {"expected_status": 201},
                },
            },
        )
        cases = runner.generate_test_cases([sample_post_spec])
        normal = next(c for c in cases if c.use_auth)
        assert normal.expected_status == 200


class TestInvalidBodyPattern:
    def _make_runner(self, patterns: list[str], **kwargs) -> TestRunner:
        config = {
            "test": {
                "patterns": patterns,
                "pagination": {"offset": 0, "limit": 5},
                **kwargs,
            },
            "api": {"base_url": "https://example.com/api/v2"},
        }
        return TestRunner(config, None, Path("/tmp"))

    def test_generates_empty_body_case(self, sample_post_spec):
        runner = self._make_runner(["invalid_body"])
        cases = runner.generate_test_cases([sample_post_spec])
        empty = [c for c in cases if c.name.endswith("-empty")]
        assert len(empty) == 1
        assert empty[0].request_body == {}
        assert empty[0].expected_status == 400

    def test_generates_wrong_type_cases(self, sample_post_spec):
        runner = self._make_runner(["invalid_body"])
        cases = runner.generate_test_cases([sample_post_spec])
        wrong_type = [c for c in cases if "wrong-type" in c.name]
        assert len(wrong_type) >= 1
        assert all(c.pattern == "invalid_body" for c in wrong_type)

    def test_skips_get_apis(self, sample_spec):
        runner = self._make_runner(["invalid_body"])
        cases = runner.generate_test_cases([sample_spec])
        assert len(cases) == 0

    def test_custom_expected_status(self, sample_post_spec):
        runner = self._make_runner(
            ["invalid_body"],
            invalid_body={"expected_status": 422},
        )
        cases = runner.generate_test_cases([sample_post_spec])
        assert all(c.expected_status == 422 for c in cases)

    def test_api_overrides(self, sample_post_spec):
        runner = self._make_runner(
            ["invalid_body"],
            invalid_body={
                "expected_status": 400,
                "api_overrides": {
                    "members-bulk_create_job": {"expected_status": 422},
                },
            },
        )
        cases = runner.generate_test_cases([sample_post_spec])
        assert all(c.expected_status == 422 for c in cases)

    def test_put_patch_also_generate(self, sample_put_spec, sample_patch_spec):
        runner = self._make_runner(["invalid_body"])
        cases = runner.generate_test_cases([sample_put_spec, sample_patch_spec])
        methods = {c.method for c in cases}
        assert "PUT" in methods
        assert "PATCH" in methods


class TestInvalidValueForType:
    def test_string_returns_int(self):
        assert TestRunner._invalid_value_for_type("文字列") == 999

    def test_int_returns_string(self):
        assert TestRunner._invalid_value_for_type("整数") == "abc"

    def test_bool_returns_string(self):
        assert TestRunner._invalid_value_for_type("真偽値") == "invalid"

    def test_array_returns_string(self):
        assert TestRunner._invalid_value_for_type("配列") == "not_an_array"

    def test_unknown_returns_none(self):
        assert TestRunner._invalid_value_for_type("不明な型") is None


class TestTestDescription:
    def test_boundary_description(self):
        tc = TestCase(
            name="boundary-groups-limit-negative",
            pattern="boundary",
            api=None,
            method="GET",
            url_path="groups.json",
            query_params={"limit": -1},
            use_auth=True,
            expected_status=400,
        )
        desc = TestRunner._test_description(tc)
        assert "boundary" in desc
        assert "limit=-1" in desc
        assert "400" in desc

    def test_missing_required_description(self):
        tc = TestCase(
            name="missing-required-test",
            pattern="missing_required",
            api=None,
            method="POST",
            url_path="members.json",
            query_params={},
            use_auth=True,
            expected_status=400,
            request_body={"name": "test"},
        )
        desc = TestRunner._test_description(tc)
        assert "missing required" in desc
        assert "400" in desc

    def test_invalid_body_description(self):
        tc = TestCase(
            name="invalid-body-members-empty",
            pattern="invalid_body",
            api=None,
            method="POST",
            url_path="members.json",
            query_params={},
            use_auth=True,
            expected_status=400,
            request_body={},
        )
        desc = TestRunner._test_description(tc)
        assert "invalid body" in desc
        assert "400" in desc

    def test_post_normal_description(self):
        tc = TestCase(
            name="post-members-normal",
            pattern="post_normal",
            api=None,
            method="POST",
            url_path="members.json",
            query_params={},
            use_auth=True,
            expected_status=200,
            request_body={"name": "test"},
        )
        desc = TestRunner._test_description(tc)
        assert "normal" in desc
        assert "200" in desc
