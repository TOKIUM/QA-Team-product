"""テストケース生成 + 実行制御."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .http_client import ApiClient
from .models import ApiSpec, TestCase, TestResult


class TestRunner:
    """CSV 仕様から生成したテストケースを実行する."""

    def __init__(self, config: dict, client: ApiClient, results_dir: Path):
        self.config = config
        self.client = client
        self.results_dir = results_dir
        self.json_indent = config.get("output", {}).get("json_indent", 4)

    def load_custom_tests(self) -> list[TestCase]:
        """config.yaml の custom_tests セクションから TestCase リストを生成."""
        custom = self.config.get("custom_tests", [])
        cases: list[TestCase] = []

        for entry in custom:
            cases.append(TestCase(
                name=entry["name"],
                pattern="custom",
                api=None,
                method=entry.get("method", "GET"),
                url_path=entry["url_path"],
                query_params=entry.get("query_params", {}),
                use_auth=entry.get("use_auth", True),
                expected_status=entry.get("expected_status", 200),
                request_body=entry.get("request_body"),
            ))

        return cases

    def generate_test_cases(self, specs: list[ApiSpec]) -> list[TestCase]:
        """ApiSpec × パターン → TestCase リスト生成."""
        test_config = self.config.get("test", {})
        patterns = test_config.get("patterns", ["auth", "pagination"])
        pagination = test_config.get("pagination", {"offset": 0, "limit": 5})

        # base_url のパス部分を取得（ネストURL対応）
        base_path = urlparse(
            self.config.get("api", {}).get("base_url", "")
        ).path.rstrip("/")

        cases: list[TestCase] = []

        get_specs = [s for s in specs if s.method == "GET"]
        post_specs = [s for s in specs if s.method == "POST"]

        # --- GET API テストケース ---
        for spec in get_specs:
            url_path, resource_name = self._resolve_paths(spec, base_path)

            # 必須パラメータ（offset/limit/fields以外）を持つAPIは
            # 一覧取得ではないため auth/pagination の対象外
            has_required = any(
                p.required in ("\u25cb", "\u3007")
                for p in spec.params
                if p.param_name not in ("offset", "limit", "fields")
            )

            if "auth" in patterns and not has_required:
                cases.append(TestCase(
                    name=f"get-{resource_name}",
                    pattern="auth",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=True,
                    expected_status=200,
                ))
                cases.append(TestCase(
                    name=f"get-{resource_name}-no-auth",
                    pattern="no_auth",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=False,
                    expected_status=401,
                ))

            if "pagination" in patterns and not has_required:
                cases.append(TestCase(
                    name=f"get-{resource_name}-pagination",
                    pattern="pagination",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={
                        "offset": pagination.get("offset", 0),
                        "limit": pagination.get("limit", 5),
                    },
                    use_auth=True,
                    expected_status=200,
                ))

        if "search" in patterns:
            search_overrides = test_config.get("search", {}).get("overrides", {})
            for spec in get_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                search_params = [
                    p for p in spec.params
                    if p.param_name not in ("offset", "limit", "fields")
                    and p.required not in ("\u25cb", "\u3007")
                ]
                for param in search_params:
                    if param.param_name in search_overrides:
                        test_value = search_overrides[param.param_name]
                    else:
                        test_value = self._search_test_value(
                            param.data_type, param.param_name, param.remarks,
                        )
                    cases.append(TestCase(
                        name=f"search-{resource_name}-by-{param.param_name}",
                        pattern="search",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={param.param_name: test_value},
                        use_auth=True,
                        expected_status=200,
                    ))

        # --- POST API テストケース ---
        if "auth" in patterns:
            for spec in post_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                # no_auth のみ自動生成（401 検証、安全）
                cases.append(TestCase(
                    name=f"post-{resource_name}-no-auth",
                    pattern="no_auth",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=False,
                    expected_status=401,
                ))

        return cases

    def run_all(self, test_cases: list[TestCase]) -> list[TestResult]:
        """全テスト実行、JSON 保存、コンソール出力."""
        # タイムスタンプディレクトリ作成
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        run_dir = self.results_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        print(f"Results: results/{timestamp}")
        print()

        concurrency = self.config.get("test", {}).get("concurrency", 1)

        # テスト実行
        if concurrency > 1:
            raw_results = self._run_concurrent(test_cases, concurrency)
        else:
            raw_results = self._run_sequential(test_cases)

        # スキーマ検証 + JSON 保存
        results: list[TestResult] = []
        for tc, result in zip(test_cases, raw_results):
            self._validate_schema(result)
            if result.response_body is not None:
                output_file = run_dir / f"{tc.name}.json"
                with open(output_file, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(result.response_body, f,
                              indent=self.json_indent, ensure_ascii=False)
                    f.write("\n")
                result.output_file = str(output_file)
            results.append(result)

        # 並行モードの場合はまとめて結果表示
        if concurrency > 1:
            for result in results:
                self._print_result(result)
            print()

        # latest.txt 更新
        latest_file = self.results_dir / "latest.txt"
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(timestamp + "\n")

        return results

    def _run_sequential(self, test_cases: list[TestCase]) -> list[TestResult]:
        """逐次実行（従来動作）."""
        raw_results: list[TestResult] = []
        for tc in test_cases:
            desc = self._test_description(tc)
            print(f"--- {desc} ---")
            result = self.client.execute(tc)
            self._print_result(result)
            print()
            raw_results.append(result)
        return raw_results

    def _run_concurrent(self, test_cases: list[TestCase], concurrency: int) -> list[TestResult]:
        """並行実行."""
        from concurrent.futures import ThreadPoolExecutor

        print(f"Concurrent execution (workers: {concurrency})")
        print()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            return list(executor.map(self.client.execute, test_cases))

    @staticmethod
    def _validate_schema(result: TestResult) -> None:
        """レスポンスのスキーマを検証し、警告を result.schema_warnings に追加."""
        tc = result.test_case
        # 検証対象: PASS かつ API 仕様あり かつ 200 期待
        if not result.passed or tc.api is None or tc.expected_status != 200:
            return
        body = result.response_body
        resource = tc.api.resource
        if not resource:
            return

        if body is None:
            result.schema_warnings.append("レスポンスボディが空です")
            return
        if not isinstance(body, dict):
            result.schema_warnings.append(
                f"レスポンスが dict ではなく {type(body).__name__} です"
            )
            return
        if resource not in body:
            result.schema_warnings.append(
                f"キー '{resource}' がレスポンスに存在しません (keys: {list(body.keys())})"
            )
            return
        if not isinstance(body[resource], list):
            result.schema_warnings.append(
                f"'{resource}' が list ではなく {type(body[resource]).__name__} です"
            )

    @staticmethod
    def _print_result(result: TestResult) -> None:
        """テスト結果を1行表示."""
        tc = result.test_case
        desc = TestRunner._test_description(tc)
        status_label = "PASS" if result.passed else "FAIL"
        if result.passed:
            warn = f" [WARN: {'; '.join(result.schema_warnings)}]" if result.schema_warnings else ""
            print(f"  [{status_label}] {desc}{warn}")
        else:
            print(f"  [{status_label}] {desc} - Expected {tc.expected_status}, got {result.status_code}")

    @staticmethod
    def _test_description(tc: TestCase) -> str:
        """テストの表示名を生成."""
        if tc.pattern == "auth":
            return f"{tc.method} /{tc.url_path} - 200 OK with valid token"
        elif tc.pattern == "no_auth":
            return f"{tc.method} /{tc.url_path} - 401 without token"
        elif tc.pattern == "pagination":
            return f"GET /{tc.url_path} with pagination (offset={tc.query_params.get('offset', 0)}, limit={tc.query_params.get('limit', 5)})"
        elif tc.pattern == "search":
            params_str = "&".join(f"{k}={v}" for k, v in tc.query_params.items())
            return f"GET /{tc.url_path} with search ({params_str})"
        elif tc.pattern == "custom":
            extras = []
            if tc.query_params:
                extras.append(f"params={tc.query_params}")
            if tc.request_body:
                extras.append("with body")
            suffix = f" ({', '.join(extras)})" if extras else ""
            return f"{tc.method} /{tc.url_path} - {tc.expected_status}{suffix}"
        return f"{tc.method} /{tc.url_path}"

    @staticmethod
    def _resolve_paths(spec: ApiSpec, base_path: str) -> tuple[str, str]:
        """spec.url から相対URLパスと一意なリソース名を導出する.

        Returns:
            url_path: HTTP クライアントに渡す相対パス (例: "members/bulk_create_job.json")
            resource_name: テスト名に使う一意な識別子 (例: "members-bulk_create_job")
        """
        if base_path and spec.url.startswith(base_path):
            url_path = spec.url[len(base_path):].lstrip("/")
        else:
            url_path = spec.url.split("/")[-1]
        resource_name = url_path.replace(".json", "").replace("/", "-")
        return url_path, resource_name

    @staticmethod
    def _search_test_value(
        data_type: str, param_name: str = "", remarks: str = "",
    ) -> str | int | bool:
        """データ型・パラメータ名・備考欄から適切なテスト値を返す."""
        # 1. 備考欄から列挙値を抽出
        if remarks:
            # ダブルクォート囲みの英字値（例: "all"）
            quoted = re.findall(r'"([a-zA-Z_]\w*)"', remarks)
            if quoted:
                return quoted[0]
            # コロン後の英字値（例: "通常の役職: company"）
            after_colon = re.findall(r':\s*([a-zA-Z_]\w*)', remarks)
            if after_colon:
                return after_colon[0]
        # 2. パラメータ名が _id で終わる場合は数値
        if param_name.endswith("_id"):
            return 1
        # 3. データ型による判定
        if "整数" in data_type:
            return 1
        if "真偽" in data_type:
            return "true"
        return "test"
