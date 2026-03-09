"""バックグラウンドテスト実行管理."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..csv_parser import parse_directory
from ..http_client import ApiClient
from ..reporter import Reporter
from ..test_runner import TestRunner


@dataclass
class RunState:
    """テスト実行の状態."""

    status: str = "idle"  # idle, running, completed, error
    total: int = 0
    completed: int = 0
    passed: int = 0
    failed: int = 0
    results: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    error: str = ""
    timestamp: str = ""


class RunManager:
    """テスト実行を管理するシングルトン的クラス."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._state = RunState()
        self._lock = threading.Lock()

    def get_state(self) -> dict:
        """スレッドセーフに現在の状態を返す."""
        with self._lock:
            return {
                "status": self._state.status,
                "total": self._state.total,
                "completed": self._state.completed,
                "passed": self._state.passed,
                "failed": self._state.failed,
                "error": self._state.error,
                "timestamp": self._state.timestamp,
                "summary": self._state.summary,
                "results": self._state.results,
            }

    def start(self, config: dict, base_url: str, api_key: str,
              csv_dir: str, patterns: list[str] | None = None,
              csv_files: list[str] | None = None) -> dict:
        """テスト実行を開始する（バックグラウンドスレッド）."""
        with self._lock:
            if self._state.status == "running":
                return {"error": "テストが実行中です"}
            self._state = RunState(status="running")

        t = threading.Thread(
            target=self._run_thread,
            args=(config, base_url, api_key, csv_dir, patterns, csv_files),
            daemon=True,
        )
        t.start()
        return {"status": "started"}

    def _run_thread(self, config: dict, base_url: str, api_key: str,
                    csv_dir_name: str, patterns: list[str] | None,
                    csv_files: list[str] | None):
        """バックグラウンドでテストを実行."""
        try:
            csv_dir = self.project_root / csv_dir_name
            if not csv_dir.exists():
                self._set_error(f"CSV ディレクトリが見つかりません: {csv_dir}")
                return

            methods = config.get("test", {}).get("methods", ["GET", "POST"])

            # 特定ファイルが指定されている場合は個別パース
            if csv_files:
                from ..csv_parser import parse_single
                specs = []
                for fname in csv_files:
                    fpath = csv_dir / fname
                    if fpath.exists():
                        spec = parse_single(fpath)
                        if spec and (methods is None or spec.method in methods):
                            specs.append(spec)
            else:
                specs = parse_directory(csv_dir, methods=methods)

            if not specs:
                self._set_error(f"有効な API 仕様が見つかりません: {csv_dir}")
                return

            test_config = config.get("test", {})
            timeout = test_config.get("timeout", 30)
            retry_config = test_config.get("retry", {})
            max_retries = retry_config.get("max_retries", 0)
            retry_delay = retry_config.get("delay", 1.0)
            results_dir_name = config.get("output", {}).get("results_dir", "results")
            results_dir = self.project_root / results_dir_name

            # Web UIから選択されたパターンでconfig.patternsを上書き
            if patterns:
                config = {**config, "test": {**config.get("test", {}), "patterns": patterns}}

            # ファイル個別選択時は individual_only を無効化（CLIの --api と同等）
            if csv_files:
                test_cfg = config.get("test", {})
                pn_cfg = test_cfg.get("post_normal", {})
                if pn_cfg.get("individual_only"):
                    pn_cfg = {**pn_cfg, "individual_only": []}
                    test_cfg = {**test_cfg, "post_normal": pn_cfg}
                    config = {**config, "test": test_cfg}

            client = ApiClient(
                base_url, api_key, timeout=timeout,
                max_retries=max_retries, retry_delay=retry_delay,
            )
            runner = TestRunner(config, client, results_dir)
            test_cases = runner.generate_test_cases(specs)
            custom_tests = runner.load_custom_tests()
            test_cases.extend(custom_tests)

            # パターンフィルタリング
            if patterns:
                pattern_set = set(patterns)
                test_cases = [tc for tc in test_cases if tc.pattern in pattern_set]

            with self._lock:
                self._state.total = len(test_cases)

            if not test_cases:
                # 選択状況に応じた具体的メッセージ
                if patterns:
                    pattern_str = ", ".join(patterns)
                    methods_in_specs = set(s.method for s in specs)
                    if all(m == "GET" for m in methods_in_specs) and any(
                            p in patterns for p in [
                                "post_normal", "put_normal",
                                "delete_normal", "patch_normal"]):
                        msg = (f"選択したCSVファイルはGET APIのため、"
                               f"書き込み系パターン({pattern_str})では"
                               f"テストが生成されません")
                    else:
                        msg = (f"パターン [{pattern_str}] に一致する"
                               f"テストケースがありません")
                else:
                    msg = "フィルタ条件に一致するテストケースがありません"
                self._set_error(msg)
                client.close()
                return

            # テスト実行
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            run_dir = results_dir / timestamp
            run_dir.mkdir(parents=True, exist_ok=True)

            # データ比較設定
            dc_config = config.get("test", {}).get(
                "post_normal", {}).get("data_comparison", {})
            dc_enabled = dc_config.get("enabled", False)

            results = []
            for tc in test_cases:
                # テスト前スナップショット（post_normal + 認証あり + 成功期待のみ）
                before = None
                if (dc_enabled and tc.pattern == "post_normal"
                        and tc.use_auth and tc.expected_status < 400):
                    before = runner._get_snapshot(tc, dc_config)

                result = client.execute(tc)

                # テスト後スナップショット + 差分計算
                if before is not None and result.passed:
                    after = runner._get_after_snapshot(tc, result, dc_config)
                    if after is not None:
                        result.before_snapshot = before
                        result.after_snapshot = after
                        result.data_diff_summary = runner._compute_data_diff(
                            before, after)

                # スキーマ検証
                if result.passed and result.response_body is not None:
                    warnings = TestRunner._validate_schema(result)
                    result.schema_warnings = warnings
                runner._validate_response_body(result)

                # JSON 保存
                if result.response_body is not None:
                    output_file = run_dir / f"{tc.name}.json"
                    with open(output_file, "w", encoding="utf-8", newline="\n") as f:
                        json.dump(result.response_body, f,
                                  indent=runner.json_indent, ensure_ascii=False)
                        f.write("\n")
                    result.output_file = str(output_file)

                # before/after スナップショット保存
                if result.before_snapshot is not None:
                    bf = run_dir / f"{tc.name}_before.json"
                    with open(bf, "w", encoding="utf-8", newline="\n") as f:
                        json.dump(result.before_snapshot, f,
                                  indent=runner.json_indent, ensure_ascii=False)
                        f.write("\n")
                if result.after_snapshot is not None:
                    af = run_dir / f"{tc.name}_after.json"
                    with open(af, "w", encoding="utf-8", newline="\n") as f:
                        json.dump(result.after_snapshot, f,
                                  indent=runner.json_indent, ensure_ascii=False)
                        f.write("\n")

                results.append(result)

                with self._lock:
                    self._state.completed += 1
                    if result.passed:
                        self._state.passed += 1
                    else:
                        self._state.failed += 1

            # latest.txt 更新
            latest_file = results_dir / "latest.txt"
            with open(latest_file, "w", encoding="utf-8") as f:
                f.write(timestamp + "\n")

            # レポート保存
            reporter = Reporter()
            reporter.save_report(results, results_dir)
            reporter.save_html_report(results, results_dir)
            reporter.save_csv_report(results, results_dir)
            client.close()

            # Slack 通知
            notification = config.get("notification", {})
            slack_config = notification.get("slack", {})
            webhook_url = slack_config.get("webhook_url", "")
            if webhook_url:
                on_failure_only = slack_config.get("on_failure_only", True)
                has_failure = any(not r.passed for r in results)
                if not on_failure_only or has_failure:
                    from ..notifier import SlackNotifier
                    notifier = SlackNotifier()
                    notifier.notify(results, webhook_url)

            # 結果を state に格納
            result_list = []
            by_pattern: dict[str, dict[str, int]] = {}
            for r in results:
                tc = r.test_case
                pat = tc.pattern
                if pat not in by_pattern:
                    by_pattern[pat] = {"total": 0, "passed": 0}
                by_pattern[pat]["total"] += 1
                if r.passed:
                    by_pattern[pat]["passed"] += 1

                if not r.passed:
                    label = "FAIL"
                elif r.schema_warnings:
                    label = "WARN"
                else:
                    label = "PASS"

                # 操作種別を判定
                operation = ""
                if tc.pattern == "post_normal":
                    name_lower = tc.name.lower()
                    if "create" in name_lower or "登録" in tc.name:
                        operation = "create"
                    elif "update" in name_lower or "更新" in tc.name:
                        operation = "update"
                    elif "delete" in name_lower or "削除" in tc.name:
                        operation = "delete"
                    else:
                        operation = "post"

                # レスポンスボディ（先頭2000文字まで、ポーリングサイズ抑制）
                response_body_preview = None
                response_body_truncated = False
                if r.response_body is not None:
                    body_str = json.dumps(
                        r.response_body, indent=2, ensure_ascii=False)
                    if len(body_str) > 2000:
                        response_body_preview = body_str[:2000]
                        response_body_truncated = True
                    else:
                        response_body_preview = body_str

                entry = {
                    "name": tc.name,
                    "pattern": tc.pattern,
                    "description": TestRunner._test_description(tc),
                    "method": tc.method,
                    "url_path": tc.url_path,
                    "expected_status": tc.expected_status,
                    "actual_status": r.status_code,
                    "passed": r.passed,
                    "elapsed_ms": round(r.elapsed_ms, 1),
                    "label": label,
                    "request_url": r.request_url or "",
                    "request_headers": r.request_headers or {},
                    "query_params": tc.query_params or {},
                    "request_body": tc.request_body,
                    "schema_warnings": r.schema_warnings or [],
                    "output_file": tc.name + ".json" if r.response_body is not None else "",
                    "operation": operation,
                    "response_body": response_body_preview,
                    "response_body_truncated": response_body_truncated,
                }
                if r.data_diff_summary:
                    entry["data_comparison"] = r.data_diff_summary
                result_list.append(entry)

            total = len(results)
            passed = sum(1 for r in results if r.passed)
            failed = total - passed
            warn_count = sum(1 for r in results if r.passed and r.schema_warnings)

            with self._lock:
                self._state.status = "completed"
                self._state.timestamp = timestamp
                self._state.results = result_list
                self._state.summary = {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "warn": warn_count,
                    "by_pattern": by_pattern,
                }

        except Exception as e:
            self._set_error(str(e))

    def _set_error(self, msg: str):
        with self._lock:
            self._state.status = "error"
            self._state.error = msg
