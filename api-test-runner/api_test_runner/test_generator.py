"""テストケース生成."""

from __future__ import annotations

import copy
import re
import time

from .models import ApiSpec, Parameter, TestCase


class TestGenerator:
    """CSV 仕様からテストケースを生成する."""

    __test__ = False  # pytest collection 除外

    def __init__(self, config: dict):
        self.config = config

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

        base_url = self.config.get("api", {}).get("base_url", "")
        base_path = ""
        if base_url:
            from urllib.parse import urlparse
            base_path = urlparse(base_url).path.rstrip("/")

        methods = test_config.get("methods", ["GET"])
        get_specs = [s for s in specs if s.method == "GET"]
        post_specs = [s for s in specs if s.method == "POST"]
        put_specs = [s for s in specs if s.method == "PUT"]
        delete_specs = [s for s in specs if s.method == "DELETE"]
        patch_specs = [s for s in specs if s.method == "PATCH"]

        cases: list[TestCase] = []

        # --- auth + no_auth パターン ---
        if "auth" in patterns:
            for spec in get_specs:
                # 必須パラメータがあるGETはスキップ（テスト値不明）
                required = [
                    p for p in spec.params
                    if p.required == "〇"
                    and p.param_name not in ("offset", "limit", "fields")
                ]
                if required:
                    continue

                url_path, resource_name = self._resolve_paths(spec, base_path)
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

        # --- pagination パターン ---
        if "pagination" in patterns:
            for spec in get_specs:
                required = [
                    p for p in spec.params
                    if p.required == "〇"
                    and p.param_name not in ("offset", "limit", "fields")
                ]
                if required:
                    continue

                url_path, resource_name = self._resolve_paths(spec, base_path)
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
                    and p.required != "〇"
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
                    if p.required == "〇"
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
            base_overrides = test_config.get("search", {}).get("overrides", {})
            post_normal_config = test_config.get("post_normal", {})
            success_status = post_normal_config.get("expected_status", 200)
            pn_api_overrides = post_normal_config.get("api_overrides", {})
            pn_body_overrides = post_normal_config.get("body_overrides", {})
            individual_only = set(post_normal_config.get("individual_only", []))
            for spec in post_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                # individual_only に含まれるAPIは全実行時スキップ
                if resource_name in individual_only:
                    continue
                pn_overrides = pn_api_overrides.get(resource_name, {})
                api_success_status = pn_overrides.get(
                    "expected_status", success_status)
                # API別body_overrides → 共通search.overrides の順でマージ
                api_body_ov = pn_body_overrides.get(resource_name, {})
                flat_ov = api_body_ov[0] if isinstance(api_body_ov, list) and api_body_ov else (api_body_ov if isinstance(api_body_ov, dict) else {})
                overrides = {**base_overrides, **flat_ov}
                body = self._build_minimal_body(spec.params, overrides)
                self._apply_body_overrides(body, api_body_ov)
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
            base_overrides = test_config.get("search", {}).get("overrides", {})
            put_normal_config = test_config.get("put_normal", {})
            success_status = put_normal_config.get("expected_status", 200)
            pn_api_overrides = put_normal_config.get("api_overrides", {})
            pn_body_overrides = put_normal_config.get("body_overrides", {})
            individual_only = set(put_normal_config.get("individual_only") or [])
            for spec in put_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                if resource_name in individual_only:
                    continue
                pn_overrides = pn_api_overrides.get(resource_name, {})
                api_success_status = pn_overrides.get(
                    "expected_status", success_status)
                api_body_ov = pn_body_overrides.get(resource_name, {})
                flat_ov = api_body_ov[0] if isinstance(api_body_ov, list) and api_body_ov else (api_body_ov if isinstance(api_body_ov, dict) else {})
                overrides = {**base_overrides, **flat_ov}
                body = self._build_minimal_body(spec.params, overrides)
                self._apply_body_overrides(body, api_body_ov)
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
            individual_only = set(delete_normal_config.get("individual_only") or [])
            for spec in delete_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                if resource_name in individual_only:
                    continue
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
            base_overrides = test_config.get("search", {}).get("overrides", {})
            patch_normal_config = test_config.get("patch_normal", {})
            success_status = patch_normal_config.get("expected_status", 200)
            pn_api_overrides = patch_normal_config.get("api_overrides", {})
            pn_body_overrides = patch_normal_config.get("body_overrides", {})
            individual_only = set(patch_normal_config.get("individual_only") or [])
            for spec in patch_specs:
                url_path, resource_name = self._resolve_paths(spec, base_path)
                if resource_name in individual_only:
                    continue
                pn_overrides = pn_api_overrides.get(resource_name, {})
                api_success_status = pn_overrides.get(
                    "expected_status", success_status)
                api_body_ov = pn_body_overrides.get(resource_name, {})
                flat_ov = api_body_ov[0] if isinstance(api_body_ov, list) and api_body_ov else (api_body_ov if isinstance(api_body_ov, dict) else {})
                overrides = {**base_overrides, **flat_ov}
                body = self._build_minimal_body(spec.params, overrides)
                self._apply_body_overrides(body, api_body_ov)
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
                        if p.required != "〇":
                            continue
                        invalid_val = self._invalid_value_for_type(p.data_type)
                        if invalid_val is None:
                            continue
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

    @staticmethod
    def _apply_body_overrides(body: dict, api_body_ov: dict | list) -> None:
        """body_overridesをリクエストボディの配列要素にマージする.

        api_body_ov が dict の場合: 配列の先頭要素に各フィールドをマージ（従来動作）
        api_body_ov が list の場合: 配列要素をリストの数だけ複製し各々にマージ
        """
        if not api_body_ov or not body:
            return

        # リスト形式を正規化
        ov_items = api_body_ov if isinstance(api_body_ov, list) else [api_body_ov]

        for top_key, top_val in body.items():
            if not (isinstance(top_val, list) and top_val
                    and isinstance(top_val[0], dict)):
                continue
            template = top_val[0]
            # 最初の要素にマージ
            for ov_key, ov_val in ov_items[0].items():
                if ov_val is not None and ov_key not in template:
                    template[ov_key] = ov_val
            # 2件目以降: テンプレートを複製してマージ
            for ov_item in ov_items[1:]:
                import copy
                elem = copy.deepcopy(template)
                for ov_key, ov_val in ov_item.items():
                    if ov_val is not None:
                        elem[ov_key] = ov_val
                top_val.append(elem)
            break  # 最初の配列キーのみ処理

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
            val = overrides[param.param_name]
            # {NOW} プレースホルダーを実行時タイムスタンプに展開
            if isinstance(val, str) and "{NOW}" in val:
                from datetime import datetime
                val = val.replace("{NOW}", datetime.now().strftime("%Y%m%d_%H%M%S"))
            return val

        data_type = param.data_type

        # 配列型: 子の必須フィールドを再帰的に生成し要素1個の配列
        if "配列" in data_type:
            if param.children:
                child_obj = TestGenerator._build_minimal_object(param.children, overrides)
                return [child_obj] if child_obj else [{}]
            return [{}]

        # オブジェクト型: 子の必須フィールドを再帰的に生成
        if "オブジェクト" in data_type:
            if param.children:
                return TestGenerator._build_minimal_object(param.children, overrides)
            return {}

        # 真偽値
        if "真偽" in data_type:
            return False

        # 整数値
        if "整数" in data_type:
            return 1

        # 文字列: email 系なら email 形式
        if "email" in param.param_name.lower():
            return f"test_{int(time.time())}@example.com"

        # パスワード
        if param.param_name == "password":
            return "Test1234!"

        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"[APIテスト]{param.param_name}_{ts}"

    @staticmethod
    def _build_minimal_object(
        params: list[Parameter], overrides: dict | None = None,
    ) -> dict:
        """パラメータリストから必須フィールドのみの最小オブジェクトを生成.

        overrides で None を指定したフィールドはオブジェクトから除外される。
        """
        obj: dict = {}
        for p in params:
            if p.required == "〇":
                val = TestGenerator._post_test_value(p, overrides)
                if val is not None:
                    obj[p.param_name] = val
        return obj

    @staticmethod
    def _build_minimal_body(
        params: list[Parameter], overrides: dict | None = None,
    ) -> dict:
        """API の全パラメータから必須フィールドのみの最小リクエストボディを生成.

        overrides で None を指定したフィールドはボディから除外される。
        """
        body: dict = {}
        for p in params:
            if p.required == "〇":
                val = TestGenerator._post_test_value(p, overrides)
                if val is not None:
                    body[p.param_name] = val
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
            if p.required != "〇":
                continue
            if prefix:
                dot_path = f"{prefix}.{p.param_name}"
            else:
                dot_path = p.param_name

            # 配列/オブジェクトで子がある場合は子のパスを再帰収集
            if p.children and "配列" in p.data_type:
                child_paths = TestGenerator._collect_required_paths(
                    p.children, f"{dot_path}[0]",
                )
                paths.extend(child_paths)
                # 親自体も省略テスト対象
                paths.append((dot_path, dot_path))
            elif p.children and "オブジェクト" in p.data_type:
                child_paths = TestGenerator._collect_required_paths(
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
