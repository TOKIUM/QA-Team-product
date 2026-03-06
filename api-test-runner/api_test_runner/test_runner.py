"""テスト実行制御."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .http_client import ApiClient
from .models import ApiSpec, Parameter, TestCase, TestResult
from .test_generator import TestGenerator
from .validator import ResponseValidator


class TestRunner:
    """CSV 仕様から生成したテストケースを実行する.

    生成は TestGenerator、検証は ResponseValidator に委譲し、
    本クラスは実行制御を担当する。
    後方互換のため、旧 staticmethod は委譲メソッドとして残す。
    """

    def __init__(self, config: dict, client: ApiClient, results_dir: Path):
        self.config = config
        self.client = client
        self.results_dir = results_dir
        self.json_indent = config.get("output", {}).get("json_indent", 4)
        self._generator = TestGenerator(config)
        self._validator = ResponseValidator(config)

    # --- 生成: TestGenerator への委譲 ---

    def load_custom_tests(self) -> list[TestCase]:
        """config.yaml の custom_tests セクションから TestCase リストを生成."""
        return self._generator.load_custom_tests()

    def generate_test_cases(self, specs: list[ApiSpec]) -> list[TestCase]:
        """ApiSpec × パターン → TestCase リスト生成."""
        return self._generator.generate_test_cases(specs)

    # --- 実行 ---

    def run_all(self, test_cases: list[TestCase]) -> list[TestResult]:
        """全テスト実行、JSON 保存、コンソール出力."""
        # タイムスタンプディレクトリ作成
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        run_dir = self.results_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        print(f"Results: results/{timestamp}")
        print()

        # crud_chain を通常テストと分離
        normal_cases = [tc for tc in test_cases if tc.pattern != "crud_chain"]
        chain_cases = [tc for tc in test_cases if tc.pattern == "crud_chain"]

        concurrency = self.config.get("test", {}).get("concurrency", 1)

        # 通常テスト実行
        if concurrency > 1:
            raw_results = self._run_concurrent(normal_cases, concurrency)
        else:
            raw_results = self._run_sequential(normal_cases)

        # スキーマ検証 + エラーボディ検証 + JSON 保存
        error_body_enabled = self.config.get("test", {}).get(
            "error_body_validation", False)
        results: list[TestResult] = []
        for tc, result in zip(normal_cases, raw_results):
            self._validator.validate_schema(result)
            if error_body_enabled:
                self._validator.validate_error_body(result)
            self._validator.validate_response_body(result)
            self._validator.validate_json_schema(result)
            if result.response_body is not None:
                output_file = run_dir / f"{tc.name}.json"
                with open(output_file, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(result.response_body, f,
                              indent=self.json_indent, ensure_ascii=False)
                    f.write("\n")
                result.output_file = str(output_file)
            results.append(result)

        # CRUD chain テスト（逐次実行）
        cc_config = self.config.get("test", {}).get("crud_chain", {})
        for tc in chain_cases:
            chain_results = self._run_crud_chain(tc, cc_config, run_dir)
            results.extend(chain_results)

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

    def _run_crud_chain(
        self, tc: TestCase, cc_config: dict, run_dir: Path,
    ) -> list[TestResult]:
        """POST→GET→DELETE→GET のCRUDチェーンを実行.

        失敗時もDELETEを試みてクリーンアップする。
        """
        results: list[TestResult] = []
        resource_name = tc.name.replace("crud-chain-", "")
        id_field = cc_config.get("id_field", "id")
        delete_url_pattern = cc_config.get("delete_url_pattern", "{url_path}/{id}")
        post_status = cc_config.get("post_expected_status", 200)
        delete_status = cc_config.get("delete_expected_status", 200)
        verify_delete_status = cc_config.get("verify_delete_expected_status", 404)

        print(f"--- CRUD chain: {resource_name} ---")
        created_id = None

        try:
            # Step 1: POST（作成）
            post_tc = TestCase(
                name=f"crud-chain-{resource_name}-post",
                pattern="crud_chain",
                api=tc.api,
                method="POST",
                url_path=tc.url_path,
                query_params={},
                use_auth=True,
                expected_status=post_status,
                request_body=tc.request_body,
            )
            post_result = self.client.execute(post_tc)
            self._print_result(post_result)
            results.append(post_result)

            # ID 抽出
            if post_result.passed and post_result.response_body:
                body = post_result.response_body
                if isinstance(body, dict):
                    # 直接 id がある場合
                    if id_field in body:
                        created_id = body[id_field]
                    else:
                        # リソースキー配下の最初の要素から取得
                        for val in body.values():
                            if isinstance(val, list) and val:
                                if isinstance(val[0], dict) and id_field in val[0]:
                                    created_id = val[0][id_field]
                                    break
                            elif isinstance(val, dict) and id_field in val:
                                created_id = val[id_field]
                                break

            if created_id is None:
                print(f"  [SKIP] ID 抽出失敗 - 後続ステップをスキップ")
                return results

            # Step 2: GET（作成確認）
            get_url = delete_url_pattern.format(url_path=tc.url_path, id=created_id)
            get_tc = TestCase(
                name=f"crud-chain-{resource_name}-get-verify",
                pattern="crud_chain",
                api=tc.api,
                method="GET",
                url_path=get_url,
                query_params={},
                use_auth=True,
                expected_status=200,
            )
            get_result = self.client.execute(get_tc)
            self._print_result(get_result)
            results.append(get_result)

        finally:
            # Step 3: DELETE（削除）— try/finally で teardown 保証
            if created_id is not None:
                del_url = delete_url_pattern.format(url_path=tc.url_path, id=created_id)
                del_tc = TestCase(
                    name=f"crud-chain-{resource_name}-delete",
                    pattern="crud_chain",
                    api=tc.api,
                    method="DELETE",
                    url_path=del_url,
                    query_params={},
                    use_auth=True,
                    expected_status=delete_status,
                )
                del_result = self.client.execute(del_tc)
                self._print_result(del_result)
                results.append(del_result)

                # Step 4: GET（削除確認）
                verify_tc = TestCase(
                    name=f"crud-chain-{resource_name}-get-deleted",
                    pattern="crud_chain",
                    api=tc.api,
                    method="GET",
                    url_path=del_url,
                    query_params={},
                    use_auth=True,
                    expected_status=verify_delete_status,
                )
                verify_result = self.client.execute(verify_tc)
                self._print_result(verify_result)
                results.append(verify_result)

        # JSON 保存
        for r in results:
            if r.response_body is not None:
                output_file = run_dir / f"{r.test_case.name}.json"
                with open(output_file, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(r.response_body, f,
                              indent=self.json_indent, ensure_ascii=False)
                    f.write("\n")
                r.output_file = str(output_file)

        print()
        return results

    # --- 後方互換: 検証・表示の委譲メソッド ---

    @staticmethod
    def _validate_schema(result: TestResult) -> None:
        ResponseValidator.validate_schema(result)

    @staticmethod
    def _validate_error_body(result: TestResult) -> None:
        ResponseValidator.validate_error_body(result)

    # インスタンスメソッド: config に依存するため staticmethod にできない
    def _validate_response_body(self, result: TestResult) -> None:
        self._validator.validate_response_body(result)

    @staticmethod
    def _print_result(result: TestResult) -> None:
        ResponseValidator.print_result(result)

    @staticmethod
    def _test_description(tc: TestCase) -> str:
        return ResponseValidator.test_description(tc)

    # --- 後方互換: 生成ヘルパーの委譲メソッド ---

    @staticmethod
    def _resolve_paths(spec: ApiSpec, base_path: str) -> tuple[str, str]:
        return TestGenerator._resolve_paths(spec, base_path)

    @staticmethod
    def _search_test_value(
        data_type: str, param_name: str = "", remarks: str = "",
    ) -> str | int | bool:
        return TestGenerator._search_test_value(data_type, param_name, remarks)

    @staticmethod
    def _post_test_value(
        param: Parameter, overrides: dict | None = None,
    ) -> str | int | bool | list | dict:
        return TestGenerator._post_test_value(param, overrides)

    @staticmethod
    def _build_minimal_object(
        params: list[Parameter], overrides: dict | None = None,
    ) -> dict:
        return TestGenerator._build_minimal_object(params, overrides)

    @staticmethod
    def _build_minimal_body(
        params: list[Parameter], overrides: dict | None = None,
    ) -> dict:
        return TestGenerator._build_minimal_body(params, overrides)

    @staticmethod
    def _collect_required_paths(
        params: list[Parameter], prefix: str,
    ) -> list[tuple[str, str]]:
        return TestGenerator._collect_required_paths(params, prefix)

    @staticmethod
    def _omit_field(body: dict, dot_path: str) -> dict:
        return TestGenerator._omit_field(body, dot_path)

    @staticmethod
    def _invalid_value_for_type(data_type: str):
        return TestGenerator._invalid_value_for_type(data_type)
