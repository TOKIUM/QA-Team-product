"""
E2Eテスト全画面一括実行スクリプト

全画面のE2Eテストを順次実行し、結果サマリーを生成する。
Slack Webhook URLが設定されていれば通知も送信する。

使い方:
  python run_all_e2e.py                    # 全画面実行
  python run_all_e2e.py --screens login    # 特定画面のみ
  python run_all_e2e.py --slack-url https://hooks.slack.com/...  # Slack通知付き
"""

import argparse
import atexit
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent

# テスト対象の画面定義（名前, ディレクトリ, テストファイルパターン）
SCREEN_CONFIGS = [
    {
        "name": "ログイン",
        "dir": BASE_DIR / "ログイン",
        "tests": "generated_tests/test_tokium_login.py",
        "smoke_test": "ログインページの表示確認",
        "category": "login",
    },
    {
        "name": "取引先",
        "dir": BASE_DIR / "取引先",
        "tests": "test_partner_list.py",
        "smoke_test": "一覧ページの表示確認",
        "category": "invoicing",
    },
    {
        "name": "帳票レイアウト",
        "dir": BASE_DIR / "帳票レイアウト",
        "tests": "test_design_list.py",
        "smoke_test": "帳票レイアウト画面に遷移できる",
        "category": "invoicing",
    },
    {
        "name": "請求書一覧",
        "dir": BASE_DIR / "請求書" / "請求書一覧",
        "tests": "generated_tests/test_invoice_list.py",
        "smoke_test": "一覧ページの表示確認",
        "category": "invoicing",
    },
    {
        "name": "請求書詳細",
        "dir": BASE_DIR / "請求書" / "請求書一覧",
        "tests": "generated_tests/test_invoice_detail.py",
        "smoke_test": "請求書詳細画面",
        "category": "invoicing",
    },
    {
        "name": "一括添付",
        "dir": BASE_DIR / "請求書" / "請求書一覧" / "その他の操作" / "共通添付ファイルの一括添付",
        "tests": ".",
        "category": "invoicing",
    },
    {
        "name": "CSV請求書作成",
        "dir": BASE_DIR / "請求書" / "請求書一覧" / "請求書作成" / "CSVから新規作成",
        "tests": "test_invoice_creation.py",
        "category": "invoicing",
    },
    {
        "name": "PDF取り込み",
        "dir": BASE_DIR / "請求書" / "請求書一覧" / "請求書作成" / "PDFを取り込む",
        "tests": "test_pdf_organizer.py",
        "smoke_test": "ファイル分割モードにURL直接アクセスできる",
        "category": "invoicing",
    },
    {
        "name": "インボイス取引先",
        "dir": BASE_DIR / "TOKIUMインボイス",
        "tests": "test_invoice_suppliers.py",
        "smoke_test": "取引先一覧ページの表示確認",
        "category": "invoice",
    },
    {
        "name": "インボイス請求書",
        "dir": BASE_DIR / "TOKIUMインボイス",
        "tests": "test_invoice_reports.py",
        "smoke_test": "請求書一覧ページの表示確認",
        "category": "invoice",
    },
    {
        "name": "インボイス自動入力",
        "dir": BASE_DIR / "TOKIUMインボイス",
        "tests": "test_auto_input.py",
        "smoke_test": "自動入力中書類一覧の表示確認",
        "category": "invoice",
    },
    {
        "name": "インボイス国税関係書類",
        "dir": BASE_DIR / "TOKIUMインボイス",
        "tests": "test_national_tax.py",
        "smoke_test": "国税関係書類一覧の表示確認",
        "category": "invoice",
    },
    {
        "name": "インボイス集計",
        "dir": BASE_DIR / "TOKIUMインボイス",
        "tests": "test_aggregation.py",
        "smoke_test": "集計画面の表示確認",
        "category": "invoice",
    },
    {
        "name": "経費申請",
        "dir": BASE_DIR / "経費精算",
        "tests": "test_requests.py",
        "smoke_test": "申請画面の表示確認",
        "category": "expense",
    },
    {
        "name": "経費一覧",
        "dir": BASE_DIR / "経費精算",
        "tests": "test_transactions.py",
        "smoke_test": "経費画面の表示確認",
        "category": "expense",
    },
    {
        "name": "カード明細",
        "dir": BASE_DIR / "経費精算",
        "tests": "test_card_statements.py",
        "smoke_test": "カード明細画面の表示確認",
        "category": "expense",
    },
    {
        "name": "経費集計",
        "dir": BASE_DIR / "経費精算",
        "tests": "test_expense_analyses.py",
        "smoke_test": "集計画面の表示確認",
        "category": "expense",
    },
    {
        "name": "WDL帳票",
        "dir": BASE_DIR / "WDL",
        "tests": "test_wdl_invoices.py",
        "smoke_test": "帳票一覧ページの表示確認",
        "category": "wdl",
    },
    {
        "name": "WDL受信ポスト",
        "dir": BASE_DIR / "WDL",
        "tests": "test_wdl_invoice_posts.py",
        "smoke_test": "受信ポスト画面の表示確認",
        "category": "wdl",
    },
]

# 画面名の短縮マッピング（CLIで指定しやすくする）
SCREEN_ALIASES = {
    "login": "ログイン",
    "partner": "取引先",
    "design": "帳票レイアウト",
    "invoice_list": "請求書一覧",
    "invoice_detail": "請求書詳細",
    "bulk": "一括添付",
    "csv": "CSV請求書作成",
    "pdf": "PDF取り込み",
    "invoice_supplier": "インボイス取引先",
    "invoice_report": "インボイス請求書",
    "invoice_auto_input": "インボイス自動入力",
    "invoice_national_tax": "インボイス国税関係書類",
    "invoice_aggregation": "インボイス集計",
    "expense_requests": "経費申請",
    "expense_transactions": "経費一覧",
    "expense_card": "カード明細",
    "expense_analyses": "経費集計",
    "wdl_invoices": "WDL帳票",
    "wdl_posts": "WDL受信ポスト",
}


def load_env(env_path: Path) -> dict:
    """ログイン/.env から環境変数を読み込む"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


def run_screen_tests(config: dict, env: dict, quick: bool = False, marker: str = None) -> dict:
    """1画面分のテストを実行し、結果を返す"""
    name = config["name"]
    test_dir = config["dir"]
    tests = config["tests"]

    if not test_dir.exists():
        return {
            "name": name,
            "status": "skip",
            "passed": 0,
            "failed": 0,
            "total": 0,
            "duration": 0,
            "error": f"ディレクトリが存在しません: {test_dir}",
        }

    test_path = test_dir / tests
    if tests != "." and not test_path.exists():
        return {
            "name": name,
            "status": "skip",
            "passed": 0,
            "failed": 0,
            "total": 0,
            "duration": 0,
            "error": f"テストファイルが存在しません: {test_path}",
        }

    print(f"\n{'='*60}")
    print(f"  {name} テスト実行中...")
    print(f"{'='*60}")

    cmd = [
        sys.executable, "-m", "pytest",
        tests,
        "-v",
        "--tb=short",
        "--json-report",
        "--json-report-file=.last_result.json",
    ]

    # quickモード: 最初のテスト1件だけ実行（-k で最初のテスト名を指定）
    if quick:
        first_test = config.get("smoke_test")
        if first_test:
            cmd.extend(["-k", first_test])
        else:
            cmd.extend(["--maxfail=1", "-x"])

    # マーカーフィルタ
    if marker:
        cmd.extend(["-m", marker])

    # 環境変数をマージ
    run_env = {**os.environ, **env}

    start = datetime.now()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(test_dir),
            env=run_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,  # 10分タイムアウト
        )
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "status": "timeout",
            "passed": 0,
            "failed": 0,
            "total": 0,
            "duration": 600,
            "error": "タイムアウト（10分）",
        }
    duration = (datetime.now() - start).total_seconds()

    # pytest-json-report の結果を読む
    json_report_path = test_dir / ".last_result.json"
    if json_report_path.exists():
        try:
            with open(json_report_path, encoding="utf-8") as f:
                report = json.load(f)
            summary = report.get("summary", {})
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            error_count = summary.get("error", 0)
            total = summary.get("total", passed + failed + error_count)
            json_report_path.unlink()  # 一時ファイル削除
        except Exception:
            passed, failed, total = _parse_pytest_output(result.stdout or "")
    else:
        # フォールバック: pytest出力からパース
        passed, failed, total = _parse_pytest_output(result.stdout or "")

    status = "pass" if failed == 0 and total > 0 else "fail" if failed > 0 else "error"

    # 失敗テストの詳細を抽出
    failure_details = []
    if failed > 0:
        for line in (result.stdout or "").splitlines():
            if "FAILED" in line:
                failure_details.append(line.strip())

    return {
        "name": name,
        "status": status,
        "passed": passed,
        "failed": failed,
        "total": total,
        "duration": round(duration, 1),
        "error": "\n".join(failure_details) if failure_details else None,
    }


def _parse_pytest_output(output: str) -> tuple:
    """pytest出力からpass/fail/totalをパースする（フォールバック）"""
    import re
    passed = failed = total = 0
    for line in output.splitlines():
        m = re.search(r"(\d+) passed", line)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", line)
        if m:
            failed = int(m.group(1))
    total = passed + failed
    return passed, failed, total


def build_summary(results: list, total_duration: float) -> dict:
    """全画面の結果からサマリーを構築"""
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_tests = sum(r["total"] for r in results)
    all_pass = all(r["status"] == "pass" for r in results if r["status"] != "skip")

    return {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "ALL PASS" if all_pass else "FAILURE",
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_tests": total_tests,
        "total_duration": round(total_duration, 1),
        "screens": results,
    }


def print_summary(summary: dict):
    """サマリーをコンソールに出力"""
    status = summary["overall_status"]
    icon = "[PASS]" if status == "ALL PASS" else "[FAIL]"

    print(f"\n{'='*60}")
    print(f"  {icon} E2Eテスト結果サマリー")
    print(f"{'='*60}")
    print(f"  実行日時: {summary['timestamp'][:19]}")
    print(f"  合計: {summary['total_passed']}/{summary['total_tests']} PASS"
          f"  ({summary['total_duration']}秒)")
    print(f"{'─'*60}")

    for s in summary["screens"]:
        if s["status"] == "skip":
            mark = "[SKIP]"
        elif s["status"] == "pass":
            mark = "[PASS]"
        else:
            mark = "[FAIL]"
        print(f"  {mark} {s['name']}: {s['passed']}/{s['total']} "
              f"({s['duration']}秒)")
        if s.get("error"):
            for line in s["error"].splitlines()[:3]:
                print(f"        {line}")

    print(f"{'='*60}\n")


def get_trend_alerts() -> list:
    """analyze_trends.pyのロジックを利用してトレンドアラートを取得"""
    try:
        from analyze_trends import load_reports, analyze_screen_stability
        reports = load_reports(7)
        if len(reports) < 2:
            return []
        screen_results = analyze_screen_stability(reports)
        alerts = []
        for name, data in screen_results.items():
            if data["is_flaky"]:
                alerts.append(f":warning: FLAKY: {name} (成功率{data['pass_rate']}%)")
            if data["is_degrading"]:
                alerts.append(f":chart_with_downwards_trend: 劣化: {name}")
            if data["is_slow"]:
                alerts.append(f":turtle: 低速: {name} ({data['latest_duration']}秒, 平均{data['avg_duration']}秒)")
        return alerts
    except Exception:
        return []


def send_slack_notification(summary: dict, webhook_url: str):
    """Slack Incoming Webhookで結果を送信"""
    status = summary["overall_status"]
    icon = ":white_check_mark:" if status == "ALL PASS" else ":x:"

    lines = [
        f"{icon} *E2Eテスト結果: {status}*",
        f"合計: {summary['total_passed']}/{summary['total_tests']} PASS "
        f"({summary['total_duration']}秒)",
        "",
    ]

    for s in summary["screens"]:
        if s["status"] == "skip":
            mark = ":arrow_right:"
        elif s["status"] == "pass":
            mark = ":white_check_mark:"
        else:
            mark = ":x:"
        lines.append(f"{mark} {s['name']}: {s['passed']}/{s['total']}")
        if s.get("error"):
            for err_line in s["error"].splitlines()[:2]:
                lines.append(f"    `{err_line}`")

    # トレンドアラート追加
    trend_alerts = get_trend_alerts()
    if trend_alerts:
        lines.append("")
        lines.append("*トレンドアラート:*")
        lines.extend(trend_alerts)

    payload = json.dumps({"text": "\n".join(lines)}).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req)
        print("Slack通知を送信しました")
    except urllib.error.URLError as e:
        print(f"Slack通知の送信に失敗: {e}")


def save_report(summary: dict, output_dir: Path):
    """JSON結果レポートを保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"e2e_report_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"レポート保存: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="E2Eテスト全画面一括実行")
    parser.add_argument(
        "--screens", nargs="*",
        help="実行する画面（省略時は全画面）。例: login partner design",
    )
    parser.add_argument(
        "--slack-url",
        default=os.environ.get("E2E_SLACK_WEBHOOK_URL"),
        help="Slack Incoming Webhook URL（環境変数 E2E_SLACK_WEBHOOK_URL でも可）",
    )
    parser.add_argument(
        "--report-dir",
        default=str(BASE_DIR / "reports"),
        help="レポート保存ディレクトリ（デフォルト: reports/）",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="スモークテスト: 各画面の最初のテスト1件だけ実行（約1-2分）",
    )
    parser.add_argument(
        "--category",
        choices=["login", "invoicing", "invoice", "wdl", "expense"],
        help="カテゴリで絞り込み: login=ログイン, invoicing=請求書発行, invoice=TOKIUMインボイス, wdl=WDL, expense=経費精算",
    )
    parser.add_argument(
        "--marker", "-m",
        help="pytestマーカーで絞り込み（例: smoke, regression）。各画面の-m引数に渡す",
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help="ロック機構を無効化（デバッグ用）",
    )
    args = parser.parse_args()

    # ロック取得
    _lock_mgr = None
    _queue_id = None
    if not args.no_lock:
        from e2e_lock import LockManager, QueueManager
        _lock_mgr = LockManager()
        _qm = QueueManager()
        screen_names = args.screens or []

        if not _lock_mgr.acquire(screens=screen_names, source="run_all_e2e"):
            info = _lock_mgr.get_info()
            print(f"[WAIT] 他のE2Eテストが実行中 (PID:{info.get('pid') if info else '?'})")
            _queue_id = _qm.enqueue(screens=screen_names)
            print(f"[QUEUE] キューに追加: {_queue_id}")

            # ポーリング待機（5秒間隔、30分タイムアウト）
            deadline = time.time() + 30 * 60
            while time.time() < deadline:
                if _qm.is_my_turn(_queue_id) and _lock_mgr.acquire(screens=screen_names, source="run_all_e2e"):
                    print("[START] ロック取得 — テスト開始")
                    break
                time.sleep(5)
            else:
                _qm.dequeue(_queue_id)
                print("[TIMEOUT] 30分待機しましたが実行できませんでした")
                sys.exit(2)

        def _cleanup():
            if _lock_mgr:
                _lock_mgr.release()
            if _queue_id and _qm:
                _qm.dequeue(_queue_id)

        atexit.register(_cleanup)
        signal.signal(signal.SIGINT, lambda s, f: (_cleanup(), sys.exit(130)))
        signal.signal(signal.SIGTERM, lambda s, f: (_cleanup(), sys.exit(143)))

    # .env 読み込み
    env_path = BASE_DIR / "ログイン" / ".env"
    env = load_env(env_path)
    if not env:
        print(f"[WARNING] .env が見つかりません: {env_path}")
        print("環境変数 TEST_EMAIL, TEST_PASSWORD が設定されていることを確認してください")

    # 実行対象の画面を決定
    configs = SCREEN_CONFIGS
    if args.screens:
        target_names = set()
        for s in args.screens:
            resolved = SCREEN_ALIASES.get(s, s)
            target_names.add(resolved)
        configs = [c for c in configs if c["name"] in target_names]
        if not configs:
            print(f"[ERROR] 指定された画面が見つかりません: {args.screens}")
            print(f"利用可能: {list(SCREEN_ALIASES.keys())}")
            sys.exit(1)
    if args.category:
        configs = [c for c in configs if c.get("category") == args.category]
        if not configs:
            print(f"[ERROR] カテゴリ '{args.category}' に該当する画面がありません")
            sys.exit(1)

    mode = "スモークテスト" if args.quick else "全テスト"
    print(f"E2Eテスト一括実行開始: {len(configs)} 画面（{mode}）")
    print(f"対象: {', '.join(c['name'] for c in configs)}")

    # テスト実行
    results = []
    total_start = datetime.now()
    for config in configs:
        result = run_screen_tests(config, env, quick=args.quick, marker=args.marker)
        results.append(result)
    total_duration = (datetime.now() - total_start).total_seconds()

    # サマリー
    summary = build_summary(results, total_duration)
    print_summary(summary)

    # レポート保存
    save_report(summary, Path(args.report_dir))

    # Slack通知
    if args.slack_url:
        send_slack_notification(summary, args.slack_url)

    # 失敗があれば exit code 1
    if summary["overall_status"] != "ALL PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
