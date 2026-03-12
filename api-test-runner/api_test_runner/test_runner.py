"""テスト実行制御."""

from __future__ import annotations

import json
import time
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
    """

    __test__ = False  # pytest collection 除外

    # data_comparison 対象の書き込み系パターン
    _WRITE_PATTERNS = frozenset(("post_normal", "put_normal", "delete_normal", "patch_normal"))

    def __init__(self, config: dict, client: ApiClient, results_dir: Path):
        self.config = config
        self.client = client
        self.results_dir = results_dir
        self.json_indent = config.get("output", {}).get("json_indent", 4)
        self._generator = TestGenerator(config)
        self._validator = ResponseValidator(config)

    def _get_dc_config(self, pattern: str) -> tuple[bool, dict]:
        """パターン別の data_comparison 設定を取得する.

        各パターンの設定を優先し、なければ post_normal の設定をフォールバック。
        Returns: (enabled, dc_config_dict)
        """
        test_cfg = self.config.get("test", {})
        # パターン固有の設定を最優先
        pattern_dc = test_cfg.get(pattern, {}).get("data_comparison", {})
        if pattern_dc:
            return pattern_dc.get("enabled", False), pattern_dc
        # フォールバック: post_normal の data_comparison
        post_dc = test_cfg.get("post_normal", {}).get("data_comparison", {})
        return post_dc.get("enabled", False), post_dc

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
        # いずれかの書き込み系パターンで data_comparison が有効か
        dc_enabled = any(
            self._get_dc_config(p)[0] for p in self._WRITE_PATTERNS
        )

        # crud_sequence（POST版CRUDチェーン）を通常テストから分離
        cs_config = self.config.get("test", {}).get(
            "post_normal", {}).get("crud_sequence", {})
        cs_enabled = cs_config.get("enabled", False)
        sequence_api_names: set[str] = set()
        if cs_enabled:
            for seq in cs_config.get("sequences", {}).values():
                for key in ("create", "update", "delete"):
                    if seq.get(key):
                        sequence_api_names.add(seq[key])

        # crud_sequence対象のpost_normalケースを分離
        seq_cases = []
        non_seq_normal = []
        for tc in normal_cases:
            if (cs_enabled and tc.pattern == "post_normal" and tc.use_auth
                    and tc.expected_status < 400
                    and self._get_resource_name(tc.name) in sequence_api_names):
                seq_cases.append(tc)
            else:
                non_seq_normal.append(tc)

        # 通常テスト実行
        # data_comparison有効時は書き込み系を逐次実行に分離（前後比較に順序が必要）
        if concurrency > 1 and dc_enabled:
            dc_cases = [tc for tc in non_seq_normal
                        if tc.pattern in self._WRITE_PATTERNS and tc.use_auth
                        and tc.expected_status < 400]
            other_cases = [tc for tc in non_seq_normal if tc not in dc_cases]
            raw_results_other = self._run_concurrent(
                other_cases, concurrency) if other_cases else []
            raw_results_dc = self._run_sequential(
                dc_cases) if dc_cases else []
            # 元の順序を復元
            dc_set = set(id(tc) for tc in dc_cases)
            raw_results = []
            dc_iter = iter(raw_results_dc)
            other_iter = iter(raw_results_other)
            for tc in non_seq_normal:
                if id(tc) in dc_set:
                    raw_results.append(next(dc_iter))
                else:
                    raw_results.append(next(other_iter))
        elif concurrency > 1:
            raw_results = self._run_concurrent(non_seq_normal, concurrency)
        else:
            raw_results = self._run_sequential(non_seq_normal)

        # スキーマ検証 + エラーボディ検証 + JSON 保存
        error_body_enabled = self.config.get("test", {}).get(
            "error_body_validation", False)
        results: list[TestResult] = []
        for tc, result in zip(non_seq_normal, raw_results):
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
            # before/after スナップショット保存
            if result.before_snapshot is not None:
                bf = run_dir / f"{tc.name}_before.json"
                with open(bf, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(result.before_snapshot, f,
                              indent=self.json_indent, ensure_ascii=False)
                    f.write("\n")
            if result.after_snapshot is not None:
                af = run_dir / f"{tc.name}_after.json"
                with open(af, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(result.after_snapshot, f,
                              indent=self.json_indent, ensure_ascii=False)
                    f.write("\n")
            results.append(result)

        # POST版CRUDシーケンス（作成→更新→削除）
        if cs_enabled and seq_cases:
            seq_results = self._run_post_crud_sequence(
                seq_cases, cs_config, run_dir)
            results.extend(seq_results)

        # CRUD chain テスト（逐次実行）
        cc_config = self.config.get("test", {}).get("crud_chain", {})
        for tc in chain_cases:
            chain_results = self._run_crud_chain(tc, cc_config, run_dir)
            results.extend(chain_results)

        # 並行モードの場合はまとめて結果表示
        if concurrency > 1:
            for result in results:
                ResponseValidator.print_result(result)
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
            desc = ResponseValidator.test_description(tc)
            print(f"--- {desc} ---")

            # テスト前スナップショット（書き込み系 + 認証あり のみ）
            before = None
            if (tc.pattern in self._WRITE_PATTERNS
                    and tc.use_auth and tc.expected_status < 400):
                dc_enabled, dc_config = self._get_dc_config(tc.pattern)
                if dc_enabled:
                    before = self._get_snapshot(tc, dc_config)

            result = self.client.execute(tc)

            # テスト後スナップショット + 差分計算
            if before is not None and result.passed:
                after = self._get_after_snapshot(tc, result, dc_config)
                if after is not None:
                    result.before_snapshot = before
                    result.after_snapshot = after
                    result.data_diff_summary = self._compute_data_diff(
                        before, after)

            ResponseValidator.print_result(result)
            if result.data_diff_summary:
                self._print_data_diff(result.data_diff_summary)
                # 作成テスト時: テストデータ名でIDを検索して表示
                if (tc.request_body and "create" in tc.url_path
                        and result.data_diff_summary.get("_total", {}).get("diff", 0) > 0):
                    self._find_and_print_created_id(tc, dc_config)
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
            ResponseValidator.print_result(post_result)
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
            ResponseValidator.print_result(get_result)
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
                ResponseValidator.print_result(del_result)
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
                ResponseValidator.print_result(verify_result)
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

    # --- POST版CRUDシーケンス ---

    @staticmethod
    def _get_resource_name(test_name: str) -> str:
        """テスト名からリソース名を抽出. 'post-projects-bulk_create_job-normal' → 'projects-bulk_create_job'."""
        parts = test_name.split("-")
        if len(parts) >= 3 and parts[0] == "post":
            # post-{resource}-normal / post-{resource}-normal-no-auth
            return "-".join(parts[1:-1])
        return test_name

    def _run_post_crud_sequence(
        self, seq_cases: list[TestCase], cs_config: dict, run_dir: Path,
    ) -> list[TestResult]:
        """POST版CRUDシーケンス: 作成→更新→削除を自動チェーン実行.

        作成で得たIDを更新・削除に自動注入する。
        """
        dc_config = self.config.get("test", {}).get("post_normal", {}).get(
            "data_comparison", {})
        job_config = dc_config.get("job_polling", {})
        results: list[TestResult] = []

        # テストケースをリソース名でマップ
        case_map = {}
        for tc in seq_cases:
            rname = self._get_resource_name(tc.name)
            case_map[rname] = tc

        for seq_name, seq in cs_config.get("sequences", {}).items():
            create_name = seq.get("create", "")
            update_name = seq.get("update", "")
            delete_name = seq.get("delete", "")
            list_endpoint = seq.get("list_endpoint", "")
            resource_key = seq.get("resource_key", seq_name)
            id_field = seq.get("id_field", "id")

            create_tc = case_map.get(create_name)
            update_tc = case_map.get(update_name)
            delete_tc = case_map.get(delete_name)

            if not create_tc:
                print(f"  [SKIP] {seq_name} CRUDシーケンス: 作成テストケースなし")
                continue

            print(f"========== CRUDシーケンス: {seq_name} ==========")
            created_id = None

            try:
                # --- Step 1: 作成 ---
                print(f"\n--- Step 1: 作成 ({create_name}) ---")
                before = self._get_snapshot(create_tc, dc_config)
                create_result = self.client.execute(create_tc)
                ResponseValidator.print_result(create_result)

                if create_result.passed and create_result.response_body:
                    job_id = create_result.response_body.get("job_id")
                    if job_id and job_config.get("enabled", False):
                        self._poll_job_completion(create_tc, job_id, job_config)

                    after = self._get_snapshot(create_tc, dc_config)
                    if before and after:
                        create_result.before_snapshot = before
                        create_result.after_snapshot = after
                        diff = self._compute_data_diff(before, after)
                        create_result.data_diff_summary = diff
                        self._print_data_diff(diff)

                        # 追加されたIDを取得
                        res_diff = diff.get(resource_key, {})
                        added_ids = res_diff.get("added_ids", [])
                        if added_ids:
                            created_id = added_ids[0]
                            print(f"  [CRUD] 作成されたID: {created_id}")

                self._save_result(create_result, run_dir)
                results.append(create_result)

                if created_id is None:
                    print(f"  [SKIP] 作成IDを特定できませんでした。後続ステップをスキップします。")
                    continue

                # --- Step 2: 更新 ---
                if update_tc:
                    print(f"\n--- Step 2: 更新 ({update_name}) ---")
                    upd_tc = self._inject_id(update_tc, created_id,
                                             resource_key, id_field)
                    before = self._get_snapshot(upd_tc, dc_config)
                    upd_result = self.client.execute(upd_tc)
                    ResponseValidator.print_result(upd_result)

                    if upd_result.passed and upd_result.response_body:
                        job_id = upd_result.response_body.get("job_id")
                        if job_id and job_config.get("enabled", False):
                            self._poll_job_completion(upd_tc, job_id, job_config)

                        after = self._get_snapshot(upd_tc, dc_config)
                        if before and after:
                            upd_result.before_snapshot = before
                            upd_result.after_snapshot = after
                            diff = self._compute_data_diff(before, after)
                            upd_result.data_diff_summary = diff
                            self._print_data_diff(diff)

                    self._save_result(upd_result, run_dir)
                    results.append(upd_result)

            finally:
                # --- Step 3: 削除（確実に実行してクリーンアップ）---
                if delete_tc and created_id is not None:
                    print(f"\n--- Step 3: 削除 ({delete_name}) ---")
                    del_tc = self._inject_id(delete_tc, created_id,
                                             resource_key, id_field)
                    before = self._get_snapshot(del_tc, dc_config)
                    del_result = self.client.execute(del_tc)
                    ResponseValidator.print_result(del_result)

                    if del_result.passed and del_result.response_body:
                        job_id = del_result.response_body.get("job_id")
                        if job_id and job_config.get("enabled", False):
                            self._poll_job_completion(del_tc, job_id, job_config)

                        after = self._get_snapshot(del_tc, dc_config)
                        if before and after:
                            del_result.before_snapshot = before
                            del_result.after_snapshot = after
                            diff = self._compute_data_diff(before, after)
                            del_result.data_diff_summary = diff
                            self._print_data_diff(diff)

                    self._save_result(del_result, run_dir)
                    results.append(del_result)

            print(f"========== CRUDシーケンス完了: {seq_name} ==========\n")

        return results

    def _inject_id(
        self, tc: TestCase, target_id: str, resource_key: str, id_field: str,
    ) -> TestCase:
        """テストケースのリクエストボディにIDを注入した新しいTestCaseを返す."""
        import copy
        new_body = copy.deepcopy(tc.request_body) if tc.request_body else {}
        if resource_key in new_body and isinstance(new_body[resource_key], list):
            for item in new_body[resource_key]:
                if isinstance(item, dict):
                    item[id_field] = target_id
        return TestCase(
            name=tc.name,
            pattern=tc.pattern,
            api=tc.api,
            method=tc.method,
            url_path=tc.url_path,
            query_params=tc.query_params,
            use_auth=tc.use_auth,
            expected_status=tc.expected_status,
            request_body=new_body,
        )

    def _save_result(self, result: TestResult, run_dir: Path) -> None:
        """テスト結果のJSONを保存."""
        tc = result.test_case
        if result.response_body is not None:
            output_file = run_dir / f"{tc.name}.json"
            with open(output_file, "w", encoding="utf-8", newline="\n") as f:
                json.dump(result.response_body, f,
                          indent=self.json_indent, ensure_ascii=False)
                f.write("\n")
            result.output_file = str(output_file)
        if result.before_snapshot is not None:
            bf = run_dir / f"{tc.name}_before.json"
            with open(bf, "w", encoding="utf-8", newline="\n") as f:
                json.dump(result.before_snapshot, f,
                          indent=self.json_indent, ensure_ascii=False)
                f.write("\n")
        if result.after_snapshot is not None:
            af = run_dir / f"{tc.name}_after.json"
            with open(af, "w", encoding="utf-8", newline="\n") as f:
                json.dump(result.after_snapshot, f,
                          indent=self.json_indent, ensure_ascii=False)
                f.write("\n")

    # --- データ比較（post_normal 用）---

    def _get_snapshot(self, tc: TestCase, dc_config: dict) -> dict | None:
        """POST対象リソースのGETスナップショットを取得.

        件数(count)と先頭ページのデータを取得する軽量スナップショット。
        """
        get_endpoints = dc_config.get("get_endpoints", {})
        get_url = get_endpoints.get(tc.url_path)
        if not get_url:
            return None
        get_params = dict(dc_config.get("get_params", {"limit": 100}))
        snapshot_tc = TestCase(
            name=f"snapshot-{tc.name}",
            pattern="internal",
            api=tc.api,
            method="GET",
            url_path=get_url,
            query_params=get_params,
            use_auth=True,
            expected_status=200,
        )
        result = self.client.execute(snapshot_tc)
        if result.passed and result.response_body:
            return result.response_body
        return None

    def _get_after_snapshot(
        self, tc: TestCase, post_result: TestResult, dc_config: dict,
    ) -> dict | None:
        """POST後にジョブ完了を待ってからGETスナップショットを取得."""
        # バッチジョブのポーリング
        job_config = dc_config.get("job_polling", {})
        if job_config.get("enabled", False) and post_result.response_body:
            job_id = None
            body = post_result.response_body
            if isinstance(body, dict):
                job_id = body.get("job_id")
            if job_id:
                self._poll_job_completion(tc, job_id, job_config)

        # 固定待機（ポーリングなしの場合のフォールバック）
        wait = dc_config.get("wait_after_post_seconds", 3)
        if not job_config.get("enabled", False):
            time.sleep(wait)

        return self._get_snapshot(tc, dc_config)

    def _poll_job_completion(
        self, tc: TestCase, job_id: str, job_config: dict,
    ) -> bool:
        """バッチジョブの完了をポーリングで待機."""
        max_wait = job_config.get("max_wait_seconds", 30)
        interval = job_config.get("poll_interval_seconds", 3)
        status_pattern = job_config.get(
            "status_url_pattern", "{url_path}?job_id={job_id}")
        poll_url = status_pattern.format(url_path=tc.url_path, job_id=job_id)

        print(f"  [POLL] ジョブ完了待機中... (job_id: {job_id[:8]}...)")
        elapsed = 0
        while elapsed < max_wait:
            poll_tc = TestCase(
                name="job-poll",
                pattern="internal",
                api=tc.api,
                method="GET",
                url_path=poll_url,
                query_params={},
                use_auth=True,
                expected_status=200,
            )
            result = self.client.execute(poll_tc)
            if result.response_body and isinstance(result.response_body, dict):
                status = result.response_body.get("status", "")
                if status in ("completed", "done", "finished", "complete"):
                    print(f"  [POLL] ジョブ完了 ({elapsed}秒)")
                    return True
                if status in ("failed", "error"):
                    print(f"  [POLL] ジョブ失敗: {status}")
                    return False
            time.sleep(interval)
            elapsed += interval
        print(f"  [POLL] タイムアウト ({max_wait}秒)")
        return False

    @staticmethod
    def _compute_data_diff(before: dict, after: dict) -> dict:
        """before/afterのリソース配列の差分を計算.

        APIレスポンスの 'count' フィールド（総件数）と
        取得済みリソース配列の両方を比較する。
        """
        diff: dict = {}

        # 総件数の変化（countフィールド）
        before_total = before.get("count")
        after_total = after.get("count")
        if before_total is not None or after_total is not None:
            diff["_total"] = {
                "before_total": before_total,
                "after_total": after_total,
                "diff": (after_total or 0) - (before_total or 0),
            }

        for key in after:
            if not isinstance(after.get(key), list):
                continue
            before_items = before.get(key, [])
            after_items = after[key]
            if not isinstance(before_items, list):
                continue

            before_ids = {item.get("id") for item in before_items
                          if isinstance(item, dict) and "id" in item}
            after_ids = {item.get("id") for item in after_items
                         if isinstance(item, dict) and "id" in item}

            added_ids = after_ids - before_ids
            removed_ids = before_ids - after_ids

            # 更新検出（同一IDで値が変わったもの）
            before_map = {item["id"]: item for item in before_items
                          if isinstance(item, dict) and "id" in item}
            after_map = {item["id"]: item for item in after_items
                         if isinstance(item, dict) and "id" in item}
            changed = {}
            for item_id in before_ids & after_ids:
                if before_map[item_id] != after_map[item_id]:
                    changes = {}
                    for field_key in set(before_map[item_id]) | set(after_map[item_id]):
                        old_val = before_map[item_id].get(field_key)
                        new_val = after_map[item_id].get(field_key)
                        if old_val != new_val:
                            changes[field_key] = {
                                "before": old_val, "after": new_val}
                    if changes:
                        changed[item_id] = changes

            diff[key] = {
                "before_count": len(before_items),
                "after_count": len(after_items),
                "added_count": len(added_ids),
                "added_ids": sorted(added_ids),
                "removed_count": len(removed_ids),
                "removed_ids": sorted(removed_ids),
                "changed_count": len(changed),
                "changed": changed,
            }
        return diff

    @staticmethod
    def _print_data_diff(diff: dict) -> None:
        """データ比較結果をコンソールに表示."""
        # 総件数の変化
        total = diff.get("_total")
        if total:
            bt = total.get("before_total", "?")
            at = total.get("after_total", "?")
            d = total.get("diff", 0)
            sign = "+" if d > 0 else ""
            print(f"  [DATA] 総件数: {bt} → {at} ({sign}{d})")

        for resource, d in diff.items():
            if resource == "_total":
                continue
            print(f"  [DATA] {resource}(取得分): "
                  f"{d['before_count']}件 → {d['after_count']}件 "
                  f"(追加: {d['added_count']}, 削除: {d['removed_count']}, "
                  f"変更: {d['changed_count']})")
            if d.get("added_ids"):
                for aid in d["added_ids"][:5]:
                    print(f"    追加ID: {aid}")
                if len(d["added_ids"]) > 5:
                    print(f"    ... 他{len(d['added_ids'])-5}件")
            if d.get("removed_ids"):
                for rid in d["removed_ids"][:5]:
                    print(f"    削除ID: {rid}")
                if len(d["removed_ids"]) > 5:
                    print(f"    ... 他{len(d['removed_ids'])-5}件")
            for item_id, changes in d.get("changed", {}).items():
                for field_name, vals in changes.items():
                    print(f"    {field_name}: {vals['before']} → {vals['after']}")

    def _find_and_print_created_id(
        self, tc: TestCase, dc_config: dict,
    ) -> str | None:
        """作成テスト後、末尾ページからテストデータを検索して作成IDを表示."""
        # リクエストボディからテストデータ名を取得
        test_name = None
        if tc.request_body:
            for val in tc.request_body.values():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    test_name = val[0].get("name") or val[0].get("display_id")
                    break
        if not test_name:
            return None

        # GETエンドポイントで末尾ページを取得
        get_endpoints = dc_config.get("get_endpoints", {})
        get_url = get_endpoints.get(tc.url_path)
        if not get_url:
            return None

        # まず総件数を取得
        count_tc = TestCase(
            name=f"count-{tc.name}", pattern="internal", api=tc.api,
            method="GET", url_path=get_url,
            query_params={"limit": 1}, use_auth=True, expected_status=200,
        )
        count_result = self.client.execute(count_tc)
        if not (count_result.passed and count_result.response_body):
            return None
        total = count_result.response_body.get("count", 0)

        # 末尾100件を取得して検索
        offset = max(0, total - 100)
        search_tc = TestCase(
            name=f"search-created-{tc.name}", pattern="internal", api=tc.api,
            method="GET", url_path=get_url,
            query_params={"limit": 100, "offset": offset},
            use_auth=True, expected_status=200,
        )
        result = self.client.execute(search_tc)
        if not (result.passed and result.response_body
                and isinstance(result.response_body, dict)):
            return None

        # テストデータ名でマッチするIDを探す
        for key, val in result.response_body.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and "id" in item:
                        item_name = item.get("name", "")
                        if test_name in item_name or "APIテスト" in item_name:
                            created_id = item["id"]
                            print(f"  [CRUD] 作成ID: {created_id}")
                            print(f"         名前: {item_name}")
                            print(f"  [HINT] 更新/削除時は config.yaml の"
                                  f" body_overrides に上記IDを設定してください")
                            return created_id
        return None

