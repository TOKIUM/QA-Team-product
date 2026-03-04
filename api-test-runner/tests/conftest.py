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
            Parameter("取得件数", "limit", "整数", "", "最大1000", max_value=1000),
        ],
    )


@pytest.fixture
def sample_spec_no_max():
    """max_value なしの ApiSpec（部署API等）."""
    return ApiSpec(
        number="4",
        name="役職取得API",
        url="/api/v2/positions.json",
        method="GET",
        resource="positions",
        params=[
            Parameter("役職名", "name", "文字列", "", ""),
            Parameter("オフセット", "offset", "整数", "", ""),
            Parameter("取得件数", "limit", "整数", "", ""),
        ],
    )


@pytest.fixture
def sample_post_spec():
    """POST API 用の ApiSpec（ネスト構造あり）."""
    return ApiSpec(
        number="9",
        name="従業員登録用バッチジョブ登録API",
        url="/api/v2/members/bulk_create_job.json",
        method="POST",
        resource="bulk_create_job",
        params=[
            Parameter(
                "従業員情報", "members", "配列", "〇", "下記参照",
                children=[
                    Parameter("従業員名", "name", "文字列", "〇", ""),
                    Parameter("メールアドレス", "email", "文字列", "〇", ""),
                    Parameter("従業員番号", "employee_id", "文字列", "", ""),
                    Parameter(
                        "権限情報", "authorities", "オブジェクト", "〇", "下記参照",
                        children=[
                            Parameter("管理者権限", "is_admin", "真偽値", "", ""),
                            Parameter("集計者権限", "is_accountant", "真偽値", "", ""),
                        ],
                    ),
                    Parameter("パスワード", "password", "文字列", "〇", "最低8文字"),
                ],
            ),
        ],
    )


@pytest.fixture
def sample_put_spec():
    """PUT API 用の ApiSpec."""
    return ApiSpec(
        number="10",
        name="従業員更新API",
        url="/api/v2/members/update.json",
        method="PUT",
        resource="member",
        params=[
            Parameter("従業員名", "name", "文字列", "〇", ""),
            Parameter("メールアドレス", "email", "文字列", "〇", ""),
        ],
    )


@pytest.fixture
def sample_delete_spec():
    """DELETE API 用の ApiSpec."""
    return ApiSpec(
        number="11",
        name="従業員削除API",
        url="/api/v2/members/delete.json",
        method="DELETE",
        resource="member",
        params=[],
    )


@pytest.fixture
def sample_patch_spec():
    """PATCH API 用の ApiSpec."""
    return ApiSpec(
        number="12",
        name="従業員部分更新API",
        url="/api/v2/members/patch.json",
        method="PATCH",
        resource="member",
        params=[
            Parameter("従業員名", "name", "文字列", "〇", ""),
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
