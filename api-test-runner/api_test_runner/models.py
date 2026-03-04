"""Data models for API test runner."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Parameter:
    """API パラメータ定義."""

    item_name: str       # "部署名"
    param_name: str      # "name"
    data_type: str       # "文字列"
    required: str        # "〇" | ""
    remarks: str         # 備考
    max_value: int | None = None           # 備考欄「最大N」から抽出した上限値
    children: list[Parameter] = field(default_factory=list)  # ネスト構造の子パラメータ


@dataclass
class ApiSpec:
    """CSV から解析した API 仕様."""

    number: str          # "3"
    name: str            # "部署取得API"
    url: str             # "/api/v2/groups.json"
    method: str          # "GET"
    resource: str        # "groups"
    params: list[Parameter] = field(default_factory=list)


@dataclass
class TestCase:
    """テストケース定義."""

    name: str            # "get-groups"
    pattern: str         # "auth" | "no_auth" | "pagination"
    api: ApiSpec | None   # None for custom tests
    method: str          # "GET"
    url_path: str        # "groups.json"
    query_params: dict   # {} or {"offset": 0, "limit": 5}
    use_auth: bool       # True/False
    expected_status: int  # 200 or 401
    request_body: dict | None = None  # JSON request body


@dataclass
class TestResult:
    """テスト実行結果."""

    test_case: TestCase
    status_code: int
    response_body: dict | list | None
    elapsed_ms: float
    passed: bool
    output_file: str | None = None      # 保存先パス
    request_url: str | None = None      # 実際のリクエスト URL
    request_headers: dict | None = None  # 送信ヘッダー
    schema_warnings: list[str] = field(default_factory=list)  # スキーマ検証警告
