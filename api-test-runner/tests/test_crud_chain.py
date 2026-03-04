"""Tests for crud_chain pattern generation and execution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from api_test_runner.models import ApiSpec, Parameter, TestCase, TestResult
from api_test_runner.test_runner import TestRunner


class TestCrudChainGeneration:
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

    def test_enabled_generates_cases(self, sample_post_spec):
        runner = self._make_runner(
            ["crud_chain"],
            crud_chain={"enabled": True},
        )
        cases = runner.generate_test_cases([sample_post_spec])
        assert len(cases) == 1
        assert cases[0].pattern == "crud_chain"
        assert cases[0].request_body is not None

    def test_disabled_generates_nothing(self, sample_post_spec):
        runner = self._make_runner(
            ["crud_chain"],
            crud_chain={"enabled": False},
        )
        cases = runner.generate_test_cases([sample_post_spec])
        assert len(cases) == 0

    def test_skips_get_apis(self, sample_spec):
        runner = self._make_runner(
            ["crud_chain"],
            crud_chain={"enabled": True},
        )
        cases = runner.generate_test_cases([sample_spec])
        assert len(cases) == 0


class TestCrudChainExecution:
    @staticmethod
    def _make_mock_client():
        return MagicMock()

    @staticmethod
    def _make_runner_with_mock(mock_client):
        config = {
            "test": {
                "crud_chain": {
                    "enabled": True,
                    "id_field": "id",
                    "delete_url_pattern": "{url_path}/{id}",
                    "post_expected_status": 200,
                    "delete_expected_status": 200,
                    "verify_delete_expected_status": 404,
                },
            },
            "api": {"base_url": "https://example.com/api/v2"},
            "output": {"json_indent": 4},
        }
        return TestRunner(config, mock_client, Path("/tmp"))

    @staticmethod
    def _mock_execute_side_effect(results_queue):
        """client.execute のモック: 呼ばれた tc を result.test_case に設定."""
        idx = [0]
        def side_effect(tc):
            result = results_queue[idx[0]]
            result.test_case = tc
            idx[0] += 1
            return result
        return side_effect

    def test_full_chain_success(self, sample_post_spec, tmp_path):
        mock_client = self._make_mock_client()
        runner = self._make_runner_with_mock(mock_client)
        runner.results_dir = tmp_path

        results_queue = [
            TestResult(test_case=None, status_code=200,
                       response_body={"id": 42}, elapsed_ms=100.0, passed=True),
            TestResult(test_case=None, status_code=200,
                       response_body={"id": 42, "name": "test"}, elapsed_ms=50.0, passed=True),
            TestResult(test_case=None, status_code=200,
                       response_body={}, elapsed_ms=80.0, passed=True),
            TestResult(test_case=None, status_code=404,
                       response_body=None, elapsed_ms=30.0, passed=True),
        ]
        mock_client.execute.side_effect = self._mock_execute_side_effect(results_queue)

        tc = TestCase(
            name="crud-chain-members-bulk_create_job",
            pattern="crud_chain",
            api=sample_post_spec,
            method="POST",
            url_path="members/bulk_create_job.json",
            query_params={},
            use_auth=True,
            expected_status=200,
            request_body={"members": [{"name": "test"}]},
        )

        run_dir = tmp_path / "20260101"
        run_dir.mkdir()
        cc_config = runner.config["test"]["crud_chain"]
        results = runner._run_crud_chain(tc, cc_config, run_dir)

        assert len(results) == 4
        assert mock_client.execute.call_count == 4

    def test_id_extraction_failure_skips_remaining(self, sample_post_spec, tmp_path):
        mock_client = self._make_mock_client()
        runner = self._make_runner_with_mock(mock_client)
        runner.results_dir = tmp_path

        results_queue = [
            TestResult(test_case=None, status_code=200,
                       response_body={"status": "ok"}, elapsed_ms=100.0, passed=True),
        ]
        mock_client.execute.side_effect = self._mock_execute_side_effect(results_queue)

        tc = TestCase(
            name="crud-chain-members-bulk_create_job",
            pattern="crud_chain",
            api=sample_post_spec,
            method="POST",
            url_path="members/bulk_create_job.json",
            query_params={},
            use_auth=True,
            expected_status=200,
            request_body={},
        )

        run_dir = tmp_path / "20260101"
        run_dir.mkdir()
        cc_config = runner.config["test"]["crud_chain"]
        results = runner._run_crud_chain(tc, cc_config, run_dir)

        assert len(results) == 1  # POST のみ
        assert mock_client.execute.call_count == 1

    def test_cleanup_on_error(self, sample_post_spec, tmp_path):
        mock_client = self._make_mock_client()
        runner = self._make_runner_with_mock(mock_client)
        runner.results_dir = tmp_path

        results_queue = [
            TestResult(test_case=None, status_code=200,
                       response_body={"id": 99}, elapsed_ms=100.0, passed=True),
            TestResult(test_case=None, status_code=500,
                       response_body=None, elapsed_ms=50.0, passed=False),
            TestResult(test_case=None, status_code=200,
                       response_body={}, elapsed_ms=80.0, passed=True),
            TestResult(test_case=None, status_code=404,
                       response_body=None, elapsed_ms=30.0, passed=True),
        ]
        mock_client.execute.side_effect = self._mock_execute_side_effect(results_queue)

        tc = TestCase(
            name="crud-chain-members-bulk_create_job",
            pattern="crud_chain",
            api=sample_post_spec,
            method="POST",
            url_path="members/bulk_create_job.json",
            query_params={},
            use_auth=True,
            expected_status=200,
            request_body={},
        )

        run_dir = tmp_path / "20260101"
        run_dir.mkdir()
        cc_config = runner.config["test"]["crud_chain"]
        results = runner._run_crud_chain(tc, cc_config, run_dir)

        # All 4 steps should execute (cleanup via finally)
        assert len(results) == 4
        assert mock_client.execute.call_count == 4
