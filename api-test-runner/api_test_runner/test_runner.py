"""テストケース生成 + 実行制御."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .http_client import ApiClient
from .models import ApiSpec, Parameter, TestCase, TestResult


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
        put_specs = [s for s in specs if s.method == "PUT"]
        delete_specs = [s for s in specs if s.method == "DELETE"]
        patch_specs = [s for s in specs if s.method == "PATCH"]

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

        # --- boundary パターン（limit の境界値テスト）---
        if "boundary" in patterns:
            boundary_config = test_config.get("boundary", {})
            overflow_status = boundary_config.get("overflow_expected_status", 400)
            api_overrides_map = boundary_config.get("api_overrides", {})
            for spec in get_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                overrides_b = api_overrides_map.get(resource_name, {})
                limit_params = [
                    p for p in spec.params if p.param_name == "limit"
                ]
                for param in limit_params:
                    # 負数: デフォルト400、api_overrides で上書き可
                    cases.append(TestCase(
                        name=f"boundary-{resource_name}-limit-negative",
                        pattern="boundary",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={"limit": -1},
                        use_auth=True,
                        expected_status=overrides_b.get(
                            "negative_expected_status", 400),
                    ))
                    # ゼロ: デフォルト200、api_overrides で上書き可
                    cases.append(TestCase(
                        name=f"boundary-{resource_name}-limit-zero",
                        pattern="boundary",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={"limit": 0},
                        use_auth=True,
                        expected_status=overrides_b.get(
                            "zero_expected_status", 200),
                    ))
                    # max_value がある場合のみ上限系テスト
                    if param.max_value is not None:
                        # 上限値: 200 を期待
                        cases.append(TestCase(
                            name=f"boundary-{resource_name}-limit-max",
                            pattern="boundary",
                            api=spec,
                            method=spec.method,
                            url_path=url_path,
                            query_params={"limit": param.max_value},
                            use_auth=True,
                            expected_status=200,
                        ))
                        # 上限超過: グローバル or api_overrides で設定可
                        cases.append(TestCase(
                            name=f"boundary-{resource_name}-limit-overflow",
                            pattern="boundary",
                            api=spec,
                            method=spec.method,
                            url_path=url_path,
                            query_params={"limit": param.max_value + 1},
                            use_auth=True,
                            expected_status=overrides_b.get(
                                "overflow_expected_status", overflow_status),
                        ))

                # offset 境界値テスト
                offset_params = [
                    p for p in spec.params if p.param_name == "offset"
                ]
                if offset_params:
                    offset_neg_status = overrides_b.get(
                        "offset_negative_expected_status",
                        boundary_config.get("offset_negative_expected_status", 400),
                    )
                    offset_large_val = overrides_b.get(
                        "offset_large_value",
                        boundary_config.get("offset_large_value", 999999),
                    )
                    offset_large_status = overrides_b.get(
                        "offset_large_expected_status",
                        boundary_config.get("offset_large_expected_status", 200),
                    )
                    # offset 負数
                    cases.append(TestCase(
                        name=f"boundary-{resource_name}-offset-negative",
                        pattern="boundary",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={"offset": -1},
                        use_auth=True,
                        expected_status=offset_neg_status,
                    ))
                    # offset 巨大値（空配列を期待）
                    cases.append(TestCase(
                        name=f"boundary-{resource_name}-offset-large",
                        pattern="boundary",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={"offset": offset_large_val},
                        use_auth=True,
                        expected_status=offset_large_status,
                    ))

        # --- missing_required パターン（必須パラメータ欠損テスト）---
        if "missing_required" in patterns:
            overrides = test_config.get("search", {}).get("overrides", {})
            mr_config = test_config.get("missing_required", {})
            mr_default_status = mr_config.get("expected_status", 400)
            mr_api_overrides = mr_config.get("api_overrides", {})
            # GET API: 必須パラメータを1つずつ省略
            for spec in get_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                mr_status = mr_api_overrides.get(
                    resource_name, {}).get(
                    "expected_status", mr_default_status)
                required_params = [
                    p for p in spec.params
                    if p.required in ("\u25cb", "\u3007")
                    and p.param_name not in ("offset", "limit", "fields")
                ]
                if not required_params:
                    continue
                # 全必須パラメータ入りのベースクエリ
                base_query = {}
                for p in required_params:
                    if p.param_name in overrides:
                        base_query[p.param_name] = overrides[p.param_name]
                    else:
                        base_query[p.param_name] = self._search_test_value(
                            p.data_type, p.param_name, p.remarks,
                        )
                for omit in required_params:
                    query = {k: v for k, v in base_query.items() if k != omit.param_name}
                    cases.append(TestCase(
                        name=f"missing-required-{resource_name}-no-{omit.param_name}",
                        pattern="missing_required",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params=query,
                        use_auth=True,
                        expected_status=mr_status,
                    ))
            # POST/PUT/PATCH API: 必須フィールドを1つずつ省略
            for body_specs in [post_specs, put_specs, patch_specs]:
                for spec in body_specs:
                    url_path, resource_name = self._resolve_paths(spec, base_path)
                    mr_res_overrides = mr_api_overrides.get(resource_name, {})
                    mr_status = mr_res_overrides.get(
                        "expected_status", mr_default_status)
                    skip_fields = set(mr_res_overrides.get("skip_fields", []))
                    base_body = self._build_minimal_body(spec.params, overrides)
                    if not base_body:
                        continue
                    required_paths = self._collect_required_paths(spec.params, "")
                    for path_key, display_name in required_paths:
                        if path_key in skip_fields:
                            continue
                        body = self._omit_field(base_body, path_key)
                        if body == base_body:
                            continue
                        safe_name = display_name.replace(".", "-").replace("[0]", "")
                        cases.append(TestCase(
                            name=f"missing-required-{resource_name}-no-{safe_name}",
                            pattern="missing_required",
                            api=spec,
                            method=spec.method,
                            url_path=url_path,
                            query_params={},
                            use_auth=True,
                            expected_status=mr_status,
                            request_body=body,
                        ))

        # --- POST/PUT/DELETE/PATCH API no-auth テストケース ---
        if "auth" in patterns:
            for method_prefix, method_specs in [
                ("post", post_specs),
                ("put", put_specs),
                ("delete", delete_specs),
                ("patch", patch_specs),
            ]:
                for spec in method_specs:
                    url_path, resource_name = self._resolve_paths(spec, base_path)
                    # no_auth のみ自動生成（401 検証、安全）
                    cases.append(TestCase(
                        name=f"{method_prefix}-{resource_name}-no-auth",
                        pattern="no_auth",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={},
                        use_auth=False,
                        expected_status=401,
                    ))

        # --- post_normal パターン（POST 正常系テスト）---
        if "post_normal" in patterns:
            overrides = test_config.get("search", {}).get("overrides", {})
            post_normal_config = test_config.get("post_normal", {})
            success_status = post_normal_config.get("expected_status", 200)
            pn_api_overrides = post_normal_config.get("api_overrides", {})
            for spec in post_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                pn_overrides = pn_api_overrides.get(resource_name, {})
                api_success_status = pn_overrides.get(
                    "expected_status", success_status)
                body = self._build_minimal_body(spec.params, overrides)
                if not body:
                    continue
                # 最小ボディ正常系
                cases.append(TestCase(
                    name=f"post-{resource_name}-normal",
                    pattern="post_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=True,
                    expected_status=api_success_status,
                    request_body=body,
                ))
                # 認証なし
                cases.append(TestCase(
                    name=f"post-{resource_name}-normal-no-auth",
                    pattern="post_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=False,
                    expected_status=401,
                    request_body=body,
                ))

        # --- put_normal パターン（PUT 正常系テスト）---
        if "put_normal" in patterns:
            overrides = test_config.get("search", {}).get("overrides", {})
            put_normal_config = test_config.get("put_normal", {})
            success_status = put_normal_config.get("expected_status", 200)
            pn_api_overrides = put_normal_config.get("api_overrides", {})
            for spec in put_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                pn_overrides = pn_api_overrides.get(resource_name, {})
                api_success_status = pn_overrides.get(
                    "expected_status", success_status)
                body = self._build_minimal_body(spec.params, overrides)
                if not body:
                    continue
                cases.append(TestCase(
                    name=f"put-{resource_name}-normal",
                    pattern="put_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=True,
                    expected_status=api_success_status,
                    request_body=body,
                ))
                cases.append(TestCase(
                    name=f"put-{resource_name}-normal-no-auth",
                    pattern="put_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=False,
                    expected_status=401,
                    request_body=body,
                ))

        # --- delete_normal パターン（DELETE 正常系テスト）---
        if "delete_normal" in patterns:
            delete_normal_config = test_config.get("delete_normal", {})
            success_status = delete_normal_config.get("expected_status", 200)
            dn_api_overrides = delete_normal_config.get("api_overrides", {})
            for spec in delete_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                dn_overrides = dn_api_overrides.get(resource_name, {})
                api_success_status = dn_overrides.get(
                    "expected_status", success_status)
                cases.append(TestCase(
                    name=f"delete-{resource_name}-normal",
                    pattern="delete_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=True,
                    expected_status=api_success_status,
                ))
                cases.append(TestCase(
                    name=f"delete-{resource_name}-normal-no-auth",
                    pattern="delete_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=False,
                    expected_status=401,
                ))

        # --- patch_normal パターン（PATCH 正常系テスト）---
        if "patch_normal" in patterns:
            overrides = test_config.get("search", {}).get("overrides", {})
            patch_normal_config = test_config.get("patch_normal", {})
            success_status = patch_normal_config.get("expected_status", 200)
            pn_api_overrides = patch_normal_config.get("api_overrides", {})
            for spec in patch_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                pn_overrides = pn_api_overrides.get(resource_name, {})
                api_success_status = pn_overrides.get(
                    "expected_status", success_status)
                body = self._build_minimal_body(spec.params, overrides)
                if not body:
                    continue
                cases.append(TestCase(
                    name=f"patch-{resource_name}-normal",
                    pattern="patch_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=True,
                    expected_status=api_success_status,
                    request_body=body,
                ))
                cases.append(TestCase(
                    name=f"patch-{resource_name}-normal-no-auth",
                    pattern="patch_normal",
                    api=spec,
                    method=spec.method,
                    url_path=url_path,
                    query_params={},
                    use_auth=False,
                    expected_status=401,
                    request_body=body,
                ))

        # --- crud_chain パターン（POST→GET→DELETE→GET チェーン）---
        if "crud_chain" in patterns:
            cc_config = test_config.get("crud_chain", {})
            if cc_config.get("enabled", False):
                overrides = test_config.get("search", {}).get("overrides", {})
                for spec in post_specs:
                    url_path, resource_name = self._resolve_paths(spec, base_path)
                    body = self._build_minimal_body(spec.params, overrides)
                    cases.append(TestCase(
                        name=f"crud-chain-{resource_name}",
                        pattern="crud_chain",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={},
                        use_auth=True,
                        expected_status=cc_config.get("post_expected_status", 200),
                        request_body=body if body else {},
                    ))

        # --- invalid_body パターン（型不正値テスト）---
        if "invalid_body" in patterns:
            ib_config = test_config.get("invalid_body", {})
            ib_default_status = ib_config.get("expected_status", 400)
            ib_api_overrides = ib_config.get("api_overrides", {})
            overrides = test_config.get("search", {}).get("overrides", {})
            for body_specs, method_prefix in [
                (post_specs, "post"),
                (put_specs, "put"),
                (patch_specs, "patch"),
            ]:
                for spec in body_specs:
                    url_path, resource_name = self._resolve_paths(spec, base_path)
                    ib_res_overrides = ib_api_overrides.get(resource_name, {})
                    ib_status = ib_res_overrides.get("expected_status", ib_default_status)
                    # 空ボディ {} → 400 期待
                    cases.append(TestCase(
                        name=f"invalid-body-{resource_name}-empty",
                        pattern="invalid_body",
                        api=spec,
                        method=spec.method,
                        url_path=url_path,
                        query_params={},
                        use_auth=True,
                        expected_status=ib_status,
                        request_body={},
                    ))
                    # 各必須フィールドに型不正値を設定
                    base_body = self._build_minimal_body(spec.params, overrides)
                    if not base_body:
                        continue
                    for p in spec.params:
                        if p.required not in ("〇", "〇"):
                            continue
                        invalid_val = self._invalid_value_for_type(p.data_type)
                        if invalid_val is None:
                            continue
                        import copy
                        bad_body = copy.deepcopy(base_body)
                        bad_body[p.param_name] = invalid_val
                        safe_name = p.param_name.replace(".", "-")
                        cases.append(TestCase(
                            name=f"invalid-body-{resource_name}-{safe_name}-wrong-type",
                            pattern="invalid_body",
                            api=spec,
                            method=spec.method,
                            url_path=url_path,
                            query_params={},
                            use_auth=True,
                            expected_status=ib_status,
                            request_body=bad_body,
                        ))

        return cases

    @staticmethod
    def _invalid_value_for_type(data_type: str):
        """データ型に対して不正な値を返す（型不一致テスト用）."""
        if "文字列" in data_type:
            return 999  # string に整数
        if "整数" in data_type:
            return "abc"  # int に文字列
        if "真偽" in data_type:
            return "invalid"  # bool に文字列
        if "配列" in data_type:
            return "not_an_array"  # array に文字列
        if "オブジェクト" in data_type:
            return "not_an_object"  # object に文字列
        return None

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
            self._validate_schema(result)
            if error_body_enabled:
                self._validate_error_body(result)
            self._validate_response_body(result)
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
    def _validate_error_body(result: TestResult) -> None:
        """エラーレスポンス（400/401）のボディ構造を検証し、警告を追加."""
        if not result.passed:
            return
        tc = result.test_case
        body = result.response_body

        if tc.expected_status == 401:
            if body is None or body == {}:
                result.schema_warnings.append(
                    "401 レスポンスボディが空です")
            return

        if tc.expected_status == 400:
            if body is None:
                result.schema_warnings.append(
                    "400 レスポンスボディが空です")
                return
            if not isinstance(body, dict):
                result.schema_warnings.append(
                    f"400 レスポンスが dict ではなく {type(body).__name__} です")
                return
            if "message" not in body:
                result.schema_warnings.append(
                    "400 レスポンスに 'message' キーがありません "
                    f"(keys: {list(body.keys())})")
            if tc.pattern == "missing_required":
                has_detail = any(
                    k in body for k in ("param", "missing_values", "errors")
                )
                if not has_detail:
                    result.schema_warnings.append(
                        "missing_required 400 レスポンスに 'param', "
                        "'missing_values', 'errors' のいずれもありません "
                        f"(keys: {list(body.keys())})")

    def _validate_response_body(self, result: TestResult) -> None:
        """レスポンスボディの内容を検証し、警告を result.schema_warnings に追加.

        - 空ボディ検知: 200 で body が null/空/{} → WARN
        - pagination 件数チェック: limit=N なら結果が N件以下か
        - レスポンス要素キー一貫性: リソース配列の各要素で同じキーが存在するか
        """
        rv_config = self.config.get("test", {}).get("response_validation", {})
        if not rv_config.get("enabled", False):
            return

        tc = result.test_case
        # PASS + api あり + 200 期待のみ対象
        if not result.passed or tc.api is None or tc.expected_status != 200:
            return

        body = result.response_body
        resource = tc.api.resource if tc.api else None

        # 空ボディ検知
        if body is None or body == {} or body == []:
            result.schema_warnings.append(
                "response_validation: 200 レスポンスボディが空です")
            return

        if not isinstance(body, dict) or not resource:
            return

        items = body.get(resource)
        if not isinstance(items, list):
            return

        # pagination 件数チェック
        if rv_config.get("pagination_count_check", True):
            limit = tc.query_params.get("limit")
            if limit is not None and isinstance(limit, int) and limit > 0:
                if len(items) > limit:
                    result.schema_warnings.append(
                        f"response_validation: limit={limit} だが {len(items)} 件返却")

        # キー一貫性チェック
        if rv_config.get("required_fields_check", True) and len(items) >= 2:
            all_keys = set()
            for item in items:
                if isinstance(item, dict):
                    all_keys |= set(item.keys())
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    missing = all_keys - set(item.keys())
                    if missing:
                        result.schema_warnings.append(
                            f"response_validation: {resource}[{i}] にキー欠損: "
                            f"{sorted(missing)}")
                        break  # 1件目の不一致で終了

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
        elif tc.pattern == "boundary":
            params_str = "&".join(f"{k}={v}" for k, v in tc.query_params.items())
            return f"GET /{tc.url_path} boundary ({params_str}) - expect {tc.expected_status}"
        elif tc.pattern == "missing_required":
            suffix = ""
            if tc.request_body is not None:
                suffix = " with body"
            return f"{tc.method} /{tc.url_path} missing required{suffix} - expect {tc.expected_status}"
        elif tc.pattern == "post_normal":
            return f"POST /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "put_normal":
            return f"PUT /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "delete_normal":
            return f"DELETE /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "patch_normal":
            return f"PATCH /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "crud_chain":
            return f"CRUD chain /{tc.url_path} (POST→GET→DELETE→GET)"
        elif tc.pattern == "invalid_body":
            return f"{tc.method} /{tc.url_path} invalid body - expect {tc.expected_status}"
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

    @staticmethod
    def _post_test_value(
        param: Parameter, overrides: dict | None = None,
    ) -> str | int | bool | list | dict:
        """POST 用テスト値を自動推定する."""
        if overrides and param.param_name in overrides:
            return overrides[param.param_name]

        data_type = param.data_type

        # 配列型: 子の必須フィールドを再帰的に生成し要素1個の配列
        if "\u914d\u5217" in data_type:
            if param.children:
                child_obj = TestRunner._build_minimal_object(param.children, overrides)
                return [child_obj] if child_obj else [{}]
            return [{}]

        # オブジェクト型: 子の必須フィールドを再帰的に生成
        if "\u30aa\u30d6\u30b8\u30a7\u30af\u30c8" in data_type:
            if param.children:
                return TestRunner._build_minimal_object(param.children, overrides)
            return {}

        # 真偽値
        if "\u771f\u507d" in data_type:
            return False

        # 整数値
        if "\u6574\u6570" in data_type:
            return 1

        # 文字列: email 系なら email 形式
        if "email" in param.param_name.lower():
            import time
            return f"test_{int(time.time())}@example.com"

        # パスワード
        if param.param_name == "password":
            return "Test1234!"

        return "test_value"

    @staticmethod
    def _build_minimal_object(
        params: list[Parameter], overrides: dict | None = None,
    ) -> dict:
        """パラメータリストから必須フィールドのみの最小オブジェクトを生成."""
        obj: dict = {}
        for p in params:
            if p.required in ("\u25cb", "\u3007"):
                obj[p.param_name] = TestRunner._post_test_value(p, overrides)
        return obj

    @staticmethod
    def _build_minimal_body(
        params: list[Parameter], overrides: dict | None = None,
    ) -> dict:
        """API の全パラメータから必須フィールドのみの最小リクエストボディを生成."""
        body: dict = {}
        for p in params:
            if p.required in ("\u25cb", "\u3007"):
                body[p.param_name] = TestRunner._post_test_value(p, overrides)
        return body

    @staticmethod
    def _collect_required_paths(
        params: list[Parameter], prefix: str,
    ) -> list[tuple[str, str]]:
        """必須パラメータのパスを再帰的に収集する.

        Returns:
            list of (dot_path, display_name) tuples.
            例: [("members[0].name", "members.name"), ("members[0].authorities.is_admin", "members.authorities.is_admin")]
        """
        paths: list[tuple[str, str]] = []
        for p in params:
            if p.required not in ("\u25cb", "\u3007"):
                continue
            if prefix:
                dot_path = f"{prefix}.{p.param_name}"
            else:
                dot_path = p.param_name

            # 配列/オブジェクトで子がある場合は子のパスを再帰収集
            if p.children and "\u914d\u5217" in p.data_type:
                child_paths = TestRunner._collect_required_paths(
                    p.children, f"{dot_path}[0]",
                )
                paths.extend(child_paths)
                # 親自体も省略テスト対象
                paths.append((dot_path, dot_path))
            elif p.children and "\u30aa\u30d6\u30b8\u30a7\u30af\u30c8" in p.data_type:
                child_paths = TestRunner._collect_required_paths(
                    p.children, dot_path,
                )
                paths.extend(child_paths)
                paths.append((dot_path, dot_path))
            else:
                paths.append((dot_path, dot_path))
        return paths

    @staticmethod
    def _omit_field(body: dict, dot_path: str) -> dict:
        """ドットパスで指定されたフィールドを省略したコピーを返す.

        例: _omit_field({"members": [{"name": "a", "email": "b"}]}, "members[0].name")
            → {"members": [{"email": "b"}]}
        """
        import copy
        result = copy.deepcopy(body)

        parts = []
        for part in dot_path.split("."):
            # "members[0]" → ("members", 0)
            m = re.match(r"^(.+)\[(\d+)\]$", part)
            if m:
                parts.append(m.group(1))
                parts.append(int(m.group(2)))
            else:
                parts.append(part)

        # Navigate to parent and delete the target key
        obj = result
        for i, part in enumerate(parts[:-1]):
            if isinstance(part, int):
                if not isinstance(obj, list) or part >= len(obj):
                    return body  # パスが不正 → 元のまま返す
                obj = obj[part]
            else:
                if not isinstance(obj, dict) or part not in obj:
                    return body
                obj = obj[part]

        last = parts[-1]
        if isinstance(last, int):
            if isinstance(obj, list) and last < len(obj):
                del obj[last]
        elif isinstance(obj, dict) and last in obj:
            del obj[last]
        else:
            return body

        return result
