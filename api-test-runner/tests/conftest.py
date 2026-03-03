"""Shared fixtures for api_test_runner tests."""

from __future__ import annotations

import pytest

from api_test_runner.models import ApiSpec, Parameter, TestCase, TestResult


@pytest.fixture
def sample_spec():
    """テスト用の ApiSpec."""
    return ApiSpec(
        number="3",
        name="部署取得API",
        url="/api/v2/groups.json",
        method="GET",
        resource="groups",
        params=[
            Parameter("部署名", "name", "文字列", "", ""),
            Parameter("オフセット", "offset", "整数", "", ""),
            Parameter("取得件数", "limit", "整数", "", ""),
        ],
    )


@pytest.fixture
def sample_test_case():
    """テスト用の TestCase."""
    return TestCase(
        name="get-groups",
        pattern="auth",
        api=None,
        method="GET",
        url_path="groups.json",
        query_params={},
        use_auth=True,
        expected_status=200,
    )


@pytest.fixture
def sample_results(sample_test_case):
    """テスト用の TestResult リスト（複数パターン）."""
    tc_auth = sample_test_case

    tc_no_auth = TestCase(
        name="get-groups-no-auth",
        pattern="no_auth",
        api=None,
        method="GET",
        url_path="groups.json",
        query_params={},
        use_auth=False,
        expected_status=401,
    )

    tc_pagination = TestCase(
        name="get-groups-pagination",
        pattern="pagination",
        api=None,
        method="GET",
        url_path="groups.json",
        query_params={"offset": 0, "limit": 5},
        use_auth=True,
        expected_status=200,
    )

    return [
        TestResult(
            test_case=tc_auth,
            status_code=200,
            response_body={"groups": [{"id": 1}]},
            elapsed_ms=150.0,
            passed=True,
            output_file="/tmp/results/20260101/get-groups.json",
            request_url="https://example.com/api/v2/groups.json",
            request_headers={"Authorization": "Bearer test123456789"},
        ),
        TestResult(
            test_case=tc_no_auth,
            status_code=401,
            response_body={"error": "Unauthorized"},
            elapsed_ms=50.0,
            passed=True,
            output_file="/tmp/results/20260101/get-groups-no-auth.json",
            request_url="https://example.com/api/v2/groups.json",
            request_headers={},
        ),
        TestResult(
            test_case=tc_pagination,
            status_code=200,
            response_body={"groups": [{"id": 1}]},
            elapsed_ms=200.0,
            passed=True,
            output_file="/tmp/results/20260101/get-groups-pagination.json",
            request_url="https://example.com/api/v2/groups.json?offset=0&limit=5",
            request_headers={"Authorization": "Bearer test123456789"},
        ),
    ]
