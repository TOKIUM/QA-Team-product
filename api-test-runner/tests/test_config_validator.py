"""Tests for api_test_runner.config_validator."""

from __future__ import annotations

import pytest

from api_test_runner.config_validator import validate_config


class TestValidateConfigValid:
    """正常系テスト."""

    def test_empty_config(self):
        assert validate_config({}) == []

    def test_full_valid_config(self):
        config = {
            "api": {"base_url": "https://example.com/api/v2"},
            "test": {
                "timeout": 30,
                "concurrency": 3,
                "methods": ["GET", "POST"],
                "patterns": ["auth", "pagination", "search"],
                "pagination": {"offset": 0, "limit": 5},
                "retry": {"max_retries": 2, "delay": 1.0},
            },
            "output": {"results_dir": "results"},
            "custom_tests": [
                {"name": "test-1", "url_path": "/test", "method": "GET",
                 "expected_status": 200},
            ],
        }
        assert validate_config(config) == []


class TestValidateApiSection:
    def test_invalid_base_url_scheme(self):
        config = {"api": {"base_url": "ftp://example.com"}}
        errors = validate_config(config)
        assert any("http://" in e for e in errors)

    def test_valid_http_url(self):
        config = {"api": {"base_url": "http://localhost:8080"}}
        assert validate_config(config) == []

    def test_valid_https_url(self):
        config = {"api": {"base_url": "https://example.com"}}
        assert validate_config(config) == []

    def test_non_string_base_url(self):
        config = {"api": {"base_url": 12345}}
        errors = validate_config(config)
        assert any("文字列" in e for e in errors)


class TestValidateTestTimeout:
    def test_valid(self):
        config = {"test": {"timeout": 30}}
        assert validate_config(config) == []

    def test_too_low(self):
        config = {"test": {"timeout": 0}}
        errors = validate_config(config)
        assert any("1〜300" in e for e in errors)

    def test_too_high(self):
        config = {"test": {"timeout": 301}}
        errors = validate_config(config)
        assert any("1〜300" in e for e in errors)

    def test_not_int(self):
        config = {"test": {"timeout": "thirty"}}
        errors = validate_config(config)
        assert any("整数" in e for e in errors)

    def test_bool_not_accepted(self):
        config = {"test": {"timeout": True}}
        errors = validate_config(config)
        assert any("整数" in e for e in errors)


class TestValidateTestConcurrency:
    def test_valid(self):
        config = {"test": {"concurrency": 5}}
        assert validate_config(config) == []

    def test_too_low(self):
        config = {"test": {"concurrency": 0}}
        errors = validate_config(config)
        assert any("1〜20" in e for e in errors)

    def test_too_high(self):
        config = {"test": {"concurrency": 21}}
        errors = validate_config(config)
        assert any("1〜20" in e for e in errors)


class TestValidateTestMethods:
    def test_valid(self):
        config = {"test": {"methods": ["GET", "POST", "PUT", "DELETE"]}}
        assert validate_config(config) == []

    def test_invalid_method(self):
        config = {"test": {"methods": ["GET", "PATCH"]}}
        errors = validate_config(config)
        assert any("PATCH" in e for e in errors)

    def test_not_list(self):
        config = {"test": {"methods": "GET"}}
        errors = validate_config(config)
        assert any("リスト" in e for e in errors)


class TestValidateTestPatterns:
    def test_valid(self):
        config = {"test": {"patterns": ["auth", "pagination", "search"]}}
        assert validate_config(config) == []

    def test_invalid_pattern(self):
        config = {"test": {"patterns": ["auth", "unknown"]}}
        errors = validate_config(config)
        assert any("unknown" in e for e in errors)

    def test_not_list(self):
        config = {"test": {"patterns": "auth"}}
        errors = validate_config(config)
        assert any("リスト" in e for e in errors)


class TestValidatePagination:
    def test_valid(self):
        config = {"test": {"pagination": {"offset": 0, "limit": 5}}}
        assert validate_config(config) == []

    def test_negative_offset(self):
        config = {"test": {"pagination": {"offset": -1}}}
        errors = validate_config(config)
        assert any("0 以上" in e for e in errors)

    def test_zero_limit(self):
        config = {"test": {"pagination": {"limit": 0}}}
        errors = validate_config(config)
        assert any("1 以上" in e for e in errors)


class TestValidateRetry:
    def test_valid(self):
        config = {"test": {"retry": {"max_retries": 3, "delay": 2.0}}}
        assert validate_config(config) == []

    def test_max_retries_too_high(self):
        config = {"test": {"retry": {"max_retries": 11}}}
        errors = validate_config(config)
        assert any("0〜10" in e for e in errors)

    def test_delay_too_low(self):
        config = {"test": {"retry": {"delay": 0.01}}}
        errors = validate_config(config)
        assert any("0.1〜60" in e for e in errors)

    def test_delay_too_high(self):
        config = {"test": {"retry": {"delay": 61}}}
        errors = validate_config(config)
        assert any("0.1〜60" in e for e in errors)

    def test_delay_not_number(self):
        config = {"test": {"retry": {"delay": "fast"}}}
        errors = validate_config(config)
        assert any("数値" in e for e in errors)


class TestValidateOutput:
    def test_valid(self):
        config = {"output": {"results_dir": "results"}}
        assert validate_config(config) == []

    def test_non_string_results_dir(self):
        config = {"output": {"results_dir": 123}}
        errors = validate_config(config)
        assert any("文字列" in e for e in errors)


class TestValidateCustomTests:
    def test_valid(self):
        config = {"custom_tests": [
            {"name": "t1", "url_path": "/x", "method": "GET", "expected_status": 200},
        ]}
        assert validate_config(config) == []

    def test_missing_required_keys(self):
        config = {"custom_tests": [
            {"name": "t1"},
        ]}
        errors = validate_config(config)
        assert any("必須キー" in e for e in errors)

    def test_not_list(self):
        config = {"custom_tests": "not a list"}
        errors = validate_config(config)
        assert any("リスト" in e for e in errors)

    def test_entry_not_dict(self):
        config = {"custom_tests": ["string_entry"]}
        errors = validate_config(config)
        assert any("辞書型" in e for e in errors)


class TestUnknownTopLevelKeys:
    def test_unknown_key(self):
        config = {"unknown_section": {"key": "value"}}
        errors = validate_config(config)
        assert any("未知のトップレベルキー" in e for e in errors)

    def test_notification_key_accepted(self):
        config = {"notification": {"slack": {"webhook_url": ""}}}
        errors = validate_config(config)
        assert not any("未知" in e for e in errors)


class TestValidateOffsetBoundary:
    def test_valid_offset_large_value(self):
        config = {"test": {"boundary": {"offset_large_value": 999999}}}
        errors = validate_config(config)
        assert not any("offset_large_value" in e for e in errors)

    def test_offset_large_value_not_int(self):
        config = {"test": {"boundary": {"offset_large_value": "big"}}}
        errors = validate_config(config)
        assert any("offset_large_value" in e and "整数" in e for e in errors)

    def test_offset_large_value_zero(self):
        config = {"test": {"boundary": {"offset_large_value": 0}}}
        errors = validate_config(config)
        assert any("offset_large_value" in e and "1 以上" in e for e in errors)


class TestValidateApiOverrides:
    """api_overrides のバリデーションテスト."""

    def test_boundary_api_overrides_valid(self):
        config = {"test": {"boundary": {"api_overrides": {
            "groups": {"negative_expected_status": 200},
        }}}}
        errors = validate_config(config)
        assert not any("api_overrides" in e for e in errors)

    def test_boundary_api_overrides_not_dict(self):
        config = {"test": {"boundary": {"api_overrides": "invalid"}}}
        errors = validate_config(config)
        assert any("boundary.api_overrides" in e and "辞書型" in e for e in errors)

    def test_boundary_api_overrides_entry_not_dict(self):
        config = {"test": {"boundary": {"api_overrides": {"groups": 123}}}}
        errors = validate_config(config)
        assert any("groups" in e and "辞書型" in e for e in errors)

    def test_missing_required_api_overrides_valid(self):
        config = {"test": {"missing_required": {"api_overrides": {
            "members": {"expected_status": 422},
        }}}}
        errors = validate_config(config)
        assert not any("api_overrides" in e for e in errors)

    def test_missing_required_api_overrides_not_dict(self):
        config = {"test": {"missing_required": {"api_overrides": [1, 2]}}}
        errors = validate_config(config)
        assert any("missing_required.api_overrides" in e and "辞書型" in e for e in errors)

    def test_post_normal_api_overrides_valid(self):
        config = {"test": {"post_normal": {"api_overrides": {
            "members": {"expected_status": 201},
        }}}}
        errors = validate_config(config)
        assert not any("api_overrides" in e for e in errors)

    def test_post_normal_api_overrides_not_dict(self):
        config = {"test": {"post_normal": {"api_overrides": True}}}
        errors = validate_config(config)
        assert any("post_normal.api_overrides" in e and "辞書型" in e for e in errors)


class TestNonDictRoot:
    def test_non_dict(self):
        errors = validate_config("not a dict")  # type: ignore
        assert len(errors) == 1
        assert "ルートが辞書型" in errors[0]
