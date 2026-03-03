"""python -m api_test_runner エントリポイント.

Usage:
    python -m api_test_runner run [csv_dir] [--config config.yaml]
    python -m api_test_runner run [csv_dir] --pattern auth,search
    python -m api_test_runner run [csv_dir] --api groups,members
    python -m api_test_runner run [csv_dir] --failed-only
    python -m api_test_runner parse [csv_dir]
    python -m api_test_runner gui
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .csv_parser import parse_directory
from .http_client import ApiClient
from .reporter import Reporter
from .test_runner import TestRunner


def load_env(env_path: Path) -> dict[str, str]:
    """自前 .env パース（python-dotenv 不使用）."""
    env: dict[str, str] = {}
    if not env_path.exists():
        return env

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()

    return env


def load_config(config_path: Path) -> dict:
    """config.yaml を読み込む."""
    if not config_path.exists():
        return {}

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_settings(config: dict, env: dict[str, str]) -> tuple[str, str]:
    """config.yaml + .env から base_url と api_key を解決."""
    # .env の値を優先（既存互換）
    base_url = env.get("BASE_URL", "")
    if not base_url:
        base_url = config.get("api", {}).get("base_url", "")

    # api_key: .env の API_KEY、または config で指定された環境変数名
    api_key = env.get("API_KEY", "")
    if not api_key:
        token_env = config.get("api", {}).get("auth", {}).get("token_env", "API_KEY")
        import os
        api_key = os.environ.get(token_env, "")

    return base_url, api_key


def cmd_parse(args: argparse.Namespace, project_root: Path) -> int:
    """parse サブコマンド: CSV 解析のみ（テストケース一覧表示）."""
    csv_dir = project_root / args.csv_dir

    if not csv_dir.exists():
        print(f"Error: CSV directory not found: {csv_dir}")
        return 1

    specs = parse_directory(csv_dir)
    if not specs:
        print(f"Error: No valid API specs found in {csv_dir}")
        return 1

    print(f"CSV directory: {csv_dir}")
    print(f"Found {len(specs)} API spec(s)")
    print()

    total_params = 0
    for spec in specs:
        print(f"  [{spec.number}] {spec.name}")
        print(f"      URL: {spec.url}")
        print(f"      Method: {spec.method}")
        print(f"      Resource: {spec.resource}")
        print(f"      Params: {len(spec.params)}")
        total_params += len(spec.params)

        for p in spec.params:
            req = " *" if p.required == "\u25cb" else ""
            print(f"        - {p.param_name} ({p.item_name}){req}")
        print()

    print(f"Total: {len(specs)} APIs, {total_params} parameters")
    return 0


def _filter_failed_only(test_cases: list, results_dir: Path) -> list:
    """前回 FAIL したテストのみに絞り込む."""
    latest_file = results_dir / "latest.txt"
    if not latest_file.exists():
        return test_cases

    latest_ts = latest_file.read_text(encoding="utf-8").strip()
    prev_report = results_dir / latest_ts / "report.json"
    if not prev_report.exists():
        return test_cases

    with open(prev_report, encoding="utf-8") as f:
        prev = json.load(f)

    failed_names = {t["name"] for t in prev["tests"] if not t["passed"]}
    if not failed_names:
        print("  (No failures in previous run)")
        return []

    return [tc for tc in test_cases if tc.name in failed_names]


def cmd_run(args: argparse.Namespace, project_root: Path) -> int:
    """run サブコマンド: CSV 解析 → テスト実行 → 結果保存 → レポート."""
    config_path = project_root / args.config
    config = load_config(config_path)
    env = load_env(project_root / ".env")
    base_url, api_key = resolve_settings(config, env)

    # 設定バリデーション
    from .config_validator import validate_config
    validation_errors = validate_config(config)
    if validation_errors:
        print("Config validation errors:")
        for err in validation_errors:
            print(f"  - {err}")
        print()
        # 警告のみの場合は続行
        has_error = any(not e.startswith("警告:") for e in validation_errors)
        if has_error:
            return 1

    if not base_url:
        print("Error: BASE_URL not set (.env or config.yaml)")
        return 1
    if not api_key:
        print("Error: API_KEY not set (.env or config.yaml)")
        return 1

    csv_dir = project_root / args.csv_dir

    if not csv_dir.exists():
        print(f"Error: CSV directory not found: {csv_dir}")
        return 1

    # CSV 解析（対象メソッド）
    methods = config.get("test", {}).get("methods", ["GET", "POST"])
    specs = parse_directory(csv_dir, methods=methods)
    if not specs:
        print(f"Error: No valid API specs found in {csv_dir}")
        return 1

    # 設定表示
    test_config = config.get("test", {})
    timeout = test_config.get("timeout", 30)
    retry_config = test_config.get("retry", {})
    max_retries = retry_config.get("max_retries", 0)
    retry_delay = retry_config.get("delay", 1.0)
    results_dir_name = config.get("output", {}).get("results_dir", "results")
    results_dir = project_root / results_dir_name

    print("========================================")
    print("  API Tests - Python Runner")
    print("========================================")
    print()
    print(f"Base URL: {base_url}")
    print(f"CSV specs: {len(specs)} APIs")
    print()

    # テストケース生成
    client = ApiClient(
        base_url, api_key, timeout=timeout,
        max_retries=max_retries, retry_delay=retry_delay,
    )
    runner = TestRunner(config, client, results_dir)
    test_cases = runner.generate_test_cases(specs)
    custom_tests = runner.load_custom_tests()
    test_cases.extend(custom_tests)

    # フィルタリング
    total_before = len(test_cases)
    if hasattr(args, "pattern") and args.pattern:
        patterns = set(args.pattern.split(","))
        test_cases = [tc for tc in test_cases if tc.pattern in patterns]
    if hasattr(args, "api") and args.api:
        apis = set(args.api.split(","))
        test_cases = [tc for tc in test_cases if any(a in tc.name for a in apis)]
    if hasattr(args, "failed_only") and args.failed_only:
        test_cases = _filter_failed_only(test_cases, results_dir)
    filtered = total_before != len(test_cases)

    # メソッド別カウント
    get_count = sum(1 for tc in test_cases if tc.method == "GET")
    post_count = sum(1 for tc in test_cases if tc.method == "POST")
    method_info = f"GET: {get_count}"
    if post_count:
        method_info += f", POST: {post_count}"

    info = f"Test cases: {len(test_cases)} ({method_info})"
    if filtered:
        info += f" (filtered from {total_before})"
    print(info)
    print()
    print("----------------------------------------")

    # ドライラン
    if hasattr(args, "dry_run") and args.dry_run:
        from .test_runner import TestRunner as TR
        for tc in test_cases:
            desc = TR._test_description(tc)
            print(f"  {desc}")
        print()
        print(f"Dry run: {len(test_cases)} test(s) would be executed")
        client.close()
        return 0

    # テスト実行
    results = runner.run_all(test_cases)

    # レポート
    reporter = Reporter()
    reporter.print_summary(results)

    report_path = reporter.save_report(results, results_dir)
    if report_path:
        print(f"Report: {report_path}")

    html_path = reporter.save_html_report(results, results_dir)
    if html_path:
        print(f"Report: {html_path}")

    csv_path = reporter.save_csv_report(results, results_dir)
    if csv_path:
        print(f"Report: {csv_path}")

    # Slack 通知
    notification = config.get("notification", {})
    slack_config = notification.get("slack", {})
    webhook_url = slack_config.get("webhook_url", "")
    if webhook_url:
        on_failure_only = slack_config.get("on_failure_only", True)
        has_failure = any(not r.passed for r in results)
        if not on_failure_only or has_failure:
            from .notifier import SlackNotifier
            notifier = SlackNotifier()
            if notifier.notify(results, webhook_url):
                print("Slack notification sent.")
            else:
                print("Warning: Slack notification failed.")

    client.close()

    # 終了コード
    failed = sum(1 for r in results if not r.passed)
    return 1 if failed > 0 else 0


def cmd_diff(args: argparse.Namespace, project_root: Path) -> int:
    """diff サブコマンド: 2回分のレスポンス差分を表示."""
    config = load_config(project_root / args.config)
    results_dir_name = config.get("output", {}).get("results_dir", "results")
    results_dir = project_root / results_dir_name

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return 1

    from .diff import ResponseDiffer

    differ = ResponseDiffer(results_dir)

    if args.ts1 and args.ts2:
        prev_dir = results_dir / args.ts1
        curr_dir = results_dir / args.ts2
        if not prev_dir.exists():
            print(f"Error: Directory not found: {prev_dir}")
            return 1
        if not curr_dir.exists():
            print(f"Error: Directory not found: {curr_dir}")
            return 1
        diffs = differ.compare_responses(prev_dir, curr_dir)
        label = f"{args.ts1} vs {args.ts2}"
    else:
        timestamps = differ.get_timestamps()
        if len(timestamps) < 2:
            print("Error: Need at least 2 test runs to compare.")
            return 1
        diffs = differ.compare_latest()
        if diffs is None:
            print("Error: Could not compare latest runs.")
            return 1
        label = f"{timestamps[1]} vs {timestamps[0]}"

    print(f"=== Response Diff: {label} ===")
    print()

    if not diffs:
        print("  No schema differences detected.")
        return 0

    for d in diffs:
        print(f"  [{d.name}]")
        for c in d.changes:
            print(f"    {c.kind}: {c.path} ({c.detail})")
        print()

    total_changes = sum(len(d.changes) for d in diffs)
    print(f"  Total: {len(diffs)} file(s), {total_changes} change(s)")
    return 0


def cmd_trend(args: argparse.Namespace, project_root: Path) -> int:
    """trend サブコマンド: パフォーマンストレンド分析."""
    config = load_config(project_root / args.config)
    results_dir_name = config.get("output", {}).get("results_dir", "results")
    results_dir = project_root / results_dir_name

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return 1

    from .trend import TrendAnalyzer
    analyzer = TrendAnalyzer(results_dir)
    analyzer.print_trend(last_n=args.last)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="api_test_runner",
        description="Python 統合 API テストランナー",
    )
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

    # run
    run_parser = subparsers.add_parser("run", help="CSV 解析 → テスト実行 → レポート")
    run_parser.add_argument("csv_dir", nargs="?", default="document",
                            help="CSV ディレクトリ (default: document)")
    run_parser.add_argument("--config", "-c", default="config.yaml",
                            help="設定ファイル (default: config.yaml)")
    run_parser.add_argument("--pattern", "-p", default=None,
                            help="パターンフィルタ (カンマ区切り, 例: auth,search)")
    run_parser.add_argument("--api", "-a", default=None,
                            help="API フィルタ (カンマ区切り, 例: groups,members)")
    run_parser.add_argument("--failed-only", "-f", action="store_true",
                            help="前回 FAIL のテストのみ再実行")
    run_parser.add_argument("--dry-run", action="store_true",
                            help="テスト一覧を表示するのみ（実行しない）")

    # parse
    parse_parser = subparsers.add_parser("parse", help="CSV 解析のみ（一覧表示）")
    parse_parser.add_argument("csv_dir", nargs="?", default="document",
                              help="CSV ディレクトリ (default: document)")

    # gui
    subparsers.add_parser("gui", help="GUI モードで起動")

    # diff
    diff_parser = subparsers.add_parser("diff", help="レスポンス差分検知")
    diff_parser.add_argument("--ts1", default=None,
                              help="比較元タイムスタンプ (省略時は latest - 1)")
    diff_parser.add_argument("--ts2", default=None,
                              help="比較先タイムスタンプ (省略時は latest)")
    diff_parser.add_argument("--config", "-c", default="config.yaml",
                              help="設定ファイル (default: config.yaml)")

    # trend
    trend_parser = subparsers.add_parser("trend", help="パフォーマンストレンド分析")
    trend_parser.add_argument("--last", "-n", type=int, default=10,
                              help="分析する過去の実行回数 (default: 10)")
    trend_parser.add_argument("--config", "-c", default="config.yaml",
                              help="設定ファイル (default: config.yaml)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # プロジェクトルート = このパッケージの親ディレクトリ
    project_root = Path(__file__).resolve().parent.parent

    if args.command == "run":
        return cmd_run(args, project_root)
    elif args.command == "parse":
        return cmd_parse(args, project_root)
    elif args.command == "gui":
        from .gui import launch
        return launch(project_root)
    elif args.command == "diff":
        return cmd_diff(args, project_root)
    elif args.command == "trend":
        return cmd_trend(args, project_root)

    return 1


if __name__ == "__main__":
    sys.exit(main())
