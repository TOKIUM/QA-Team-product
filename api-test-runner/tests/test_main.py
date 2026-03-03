"""Tests for api_test_runner.__main__ logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from api_test_runner.__main__ import (
    _filter_failed_only,
    load_config,
    load_env,
    resolve_settings,
)
from api_test_runner.models import TestCase


class TestLoadEnv:
    def test_normal(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("BASE_URL=https://example.com\nAPI_KEY=secret123\n",
                            encoding="utf-8")
        result = load_env(env_file)
        assert result["BASE_URL"] == "https://example.com"
        assert result["API_KEY"] == "secret123"

    def test_comment_and_empty_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY=value\n", encoding="utf-8")
        result = load_env(env_file)
        assert result == {"KEY": "value"}

    def test_nonexistent_file(self, tmp_path):
        result = load_env(tmp_path / ".env.missing")
        assert result == {}

    def test_value_with_equals(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("URL=https://example.com?a=1&b=2\n", encoding="utf-8")
        result = load_env(env_file)
        assert result["URL"] == "https://example.com?a=1&b=2"

    def test_whitespace_trimming(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("  KEY  =  value  \n", encoding="utf-8")
        result = load_env(env_file)
        assert result["KEY"] == "value"


class TestLoadConfig:
    def test_normal(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("api:\n  base_url: https://example.com\n",
                               encoding="utf-8")
        result = load_config(config_file)
        assert result["api"]["base_url"] == "https://example.com"

    def test_empty_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("", encoding="utf-8")
        result = load_config(config_file)
        assert result == {}

    def test_nonexistent_file(self, tmp_path):
        result = load_config(tmp_path / "missing.yaml")
        assert result == {}


class TestResolveSettings:
    def test_env_priority(self):
        config = {"api": {"base_url": "https://config.com"}}
        env = {"BASE_URL": "https://env.com", "API_KEY": "env_key"}
        base_url, api_key = resolve_settings(config, env)
        assert base_url == "https://env.com"
        assert api_key == "env_key"

    def test_config_fallback(self):
        config = {"api": {"base_url": "https://config.com"}}
        env: dict[str, str] = {}
        base_url, api_key = resolve_settings(config, env)
        assert base_url == "https://config.com"

    def test_empty_both(self):
        base_url, api_key = resolve_settings({}, {})
        assert base_url == ""
        assert api_key == ""

    def test_token_env_from_config(self):
        config = {"api": {"auth": {"token_env": "CUSTOM_KEY"}}}
        env: dict[str, str] = {}
        with patch.dict("os.environ", {"CUSTOM_KEY": "custom_value"}):
            base_url, api_key = resolve_settings(config, env)
        assert api_key == "custom_value"


class TestFilterFailedOnly:
    def _make_test_case(self, name: str) -> TestCase:
        return TestCase(
            name=name, pattern="auth", api=None, method="GET",
            url_path="test.json", query_params={}, use_auth=True,
            expected_status=200,
        )

    def test_with_failures(self, tmp_path):
        results_dir = tmp_path / "results"
        ts_dir = results_dir / "20260101120000"
        ts_dir.mkdir(parents=True)
        report = {"tests": [
            {"name": "test-a", "passed": True},
            {"name": "test-b", "passed": False},
            {"name": "test-c", "passed": False},
        ]}
        (ts_dir / "report.json").write_text(
            json.dumps(report), encoding="utf-8")
        (results_dir / "latest.txt").write_text(
            "20260101120000", encoding="utf-8")

        test_cases = [
            self._make_test_case("test-a"),
            self._make_test_case("test-b"),
            self._make_test_case("test-c"),
        ]
        filtered = _filter_failed_only(test_cases, results_dir)
        names = [tc.name for tc in filtered]
        assert "test-b" in names
        assert "test-c" in names
        assert "test-a" not in names

    def test_no_failures(self, tmp_path):
        results_dir = tmp_path / "results"
        ts_dir = results_dir / "20260101120000"
        ts_dir.mkdir(parents=True)
        report = {"tests": [
            {"name": "test-a", "passed": True},
        ]}
        (ts_dir / "report.json").write_text(
            json.dumps(report), encoding="utf-8")
        (results_dir / "latest.txt").write_text(
            "20260101120000", encoding="utf-8")

        test_cases = [self._make_test_case("test-a")]
        filtered = _filter_failed_only(test_cases, results_dir)
        assert filtered == []

    def test_no_latest_file(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir(parents=True)
        test_cases = [self._make_test_case("test-a")]
        filtered = _filter_failed_only(test_cases, results_dir)
        assert filtered == test_cases

    def test_no_report_file(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir(parents=True)
        (results_dir / "latest.txt").write_text(
            "20260101120000", encoding="utf-8")
        test_cases = [self._make_test_case("test-a")]
        filtered = _filter_failed_only(test_cases, results_dir)
        assert filtered == test_cases
