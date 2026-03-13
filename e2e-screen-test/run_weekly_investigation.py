"""
週次画面調査オーケストレーター

毎週火曜9:00に実行。11本の画面調査スクリプトを順次実行し、
探索的テスト+差分検出を行い、レポートを生成する。

使い方:
  python run_weekly_investigation.py                          # 全スクリプト実行
  python run_weekly_investigation.py --scripts "WDL サイトマップ"  # 指定スクリプトのみ
  python run_weekly_investigation.py --skip-exploratory        # 探索的テストをスキップ
  python run_weekly_investigation.py --skip-diff               # 差分検出をスキップ
  python run_weekly_investigation.py --no-lock                 # ロック無効（デバッグ用）
"""

import argparse
import atexit
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent
INVESTIGATION_DIR = BASE_DIR / "screen_investigation"
PREVIOUS_DIR = INVESTIGATION_DIR / "_previous"
REPORTS_DIR = BASE_DIR / "reports"

# 11本の画面調査スクリプト定義
# (表示名, スクリプトパス, タイムアウト秒)
INVESTIGATION_SCRIPTS = [
    ("TH-01 全画面", BASE_DIR / "investigate_all_screens.py", 600),
    ("TH-02 テナント", BASE_DIR / "investigate_th02_screens.py", 600),
    ("TH-04 テナント", BASE_DIR / "investigate_th04_screens.py", 600),
    ("TITK テナント", BASE_DIR / "investigate_titk.py", 600),
    ("TKTI10 詳細", BASE_DIR / "investigate_tkti10_detail.py", 600),
    ("ユーザー画面", BASE_DIR / "investigate_user_screens.py", 600),
    ("WDL サイトマップ", BASE_DIR / "screen_investigation" / "investigate_wdl.py", 600),
    ("WDL 詳細", BASE_DIR / "screen_investigation" / "investigate_wdl_detail.py", 600),
    ("WDL 受信ポスト詳細", BASE_DIR / "screen_investigation" / "investigate_wdl_invoice_post_detail.py", 600),
    ("WDL プロフィール", BASE_DIR / "screen_investigation" / "investigate_wdl_profile.py", 600),
    ("WDL 設定", BASE_DIR / "screen_investigation" / "investigate_wdl_settings.py", 600),
]

# 表示名 → インデックスのエイリアス
SCRIPT_ALIASES = {s[0]: i for i, s in enumerate(INVESTIGATION_SCRIPTS)}


def backup_previous_results():
    """前回結果を _previous/ にバックアップ（上書き）"""
    if PREVIOUS_DIR.exists():
        shutil.rmtree(PREVIOUS_DIR)

    if not INVESTIGATION_DIR.exists():
        INVESTIGATION_DIR.mkdir(parents=True, exist_ok=True)
        return

    # JSON + screenshots をコピー
    PREVIOUS_DIR.mkdir(parents=True, exist_ok=True)
    for item in INVESTIGATION_DIR.iterdir():
        if item.name == "_previous":
            continue
        if item.is_file() and item.suffix == ".json":
            shutil.copy2(item, PREVIOUS_DIR / item.name)
        elif item.is_dir() and item.name == "screenshots":
            shutil.copytree(item, PREVIOUS_DIR / "screenshots", dirs_exist_ok=True)

    print(f"[BACKUP] 前回結果を {PREVIOUS_DIR} にバックアップ")


def run_script(name: str, script_path: Path, timeout: int) -> dict:
    """1スクリプトを実行"""
    result = {
        "name": name,
        "script": str(script_path.relative_to(BASE_DIR)),
        "start_time": datetime.now().isoformat(),
        "status": "unknown",
        "duration_sec": 0,
        "output": "",
        "error": "",
    }

    if not script_path.exists():
        result["status"] = "skip"
        result["error"] = f"スクリプト不在: {script_path}"
        print(f"  [SKIP] {name}: スクリプトが見つかりません")
        return result

    print(f"  [RUN] {name} ...")
    start = time.time()

    try:
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(BASE_DIR),
            encoding="utf-8",
            errors="replace",
        )
        result["duration_sec"] = round(time.time() - start, 1)
        result["output"] = proc.stdout[-2000:] if proc.stdout else ""
        result["error"] = proc.stderr[-1000:] if proc.stderr else ""
        result["return_code"] = proc.returncode
        result["status"] = "pass" if proc.returncode == 0 else "fail"
        status_icon = "OK" if proc.returncode == 0 else "FAIL"
        print(f"  [{status_icon}] {name} ({result['duration_sec']}s)")

    except subprocess.TimeoutExpired:
        result["duration_sec"] = round(time.time() - start, 1)
        result["status"] = "timeout"
        result["error"] = f"タイムアウト ({timeout}s)"
        print(f"  [TIMEOUT] {name} ({timeout}s超過)")

    except Exception as e:
        result["duration_sec"] = round(time.time() - start, 1)
        result["status"] = "error"
        result["error"] = str(e)[:500]
        print(f"  [ERROR] {name}: {e}")

    result["end_time"] = datetime.now().isoformat()
    return result


def run_exploratory_phase() -> dict:
    """Phase 2: 探索的テスト実行"""
    print("\n[Phase 2] 探索的テスト実行...")
    try:
        from exploratory_tester import run_exploratory_tests
        return run_exploratory_tests()
    except Exception as e:
        print(f"  [ERROR] 探索的テスト失敗: {e}")
        return {"status": "error", "reason": str(e), "results": []}


def run_diff_phase() -> dict:
    """Phase 3: 差分検出"""
    print("\n[Phase 3] 差分検出...")
    try:
        from investigation_diff import run_diff
        return run_diff(INVESTIGATION_DIR, PREVIOUS_DIR)
    except Exception as e:
        print(f"  [ERROR] 差分検出失敗: {e}")
        return {"status": "error", "reason": str(e)}


def build_report(script_results: list, exploratory: dict | None, diff: dict | None,
                 total_duration: float) -> dict:
    """最終レポート生成"""
    passed = len([r for r in script_results if r["status"] == "pass"])
    failed = len([r for r in script_results if r["status"] == "fail"])
    errors = len([r for r in script_results if r["status"] in ("error", "timeout")])
    skipped = len([r for r in script_results if r["status"] == "skip"])

    report = {
        "report_type": "weekly_investigation",
        "generated_at": datetime.now().isoformat(),
        "total_duration_sec": round(total_duration, 1),
        "summary": {
            "scripts_total": len(script_results),
            "scripts_passed": passed,
            "scripts_failed": failed,
            "scripts_error": errors,
            "scripts_skipped": skipped,
            "overall_status": "ALL PASS" if failed == 0 and errors == 0 else "HAS ISSUES",
        },
        "phase1_scripts": script_results,
        "phase2_exploratory": exploratory,
        "phase3_diff": diff,
    }

    # 探索的テストサマリー追加
    if exploratory and exploratory.get("summary"):
        es = exploratory["summary"]
        report["summary"]["exploratory_pages"] = es.get("total_pages", 0)
        report["summary"]["exploratory_issues"] = (
            es.get("warnings", 0) + es.get("critical", 0) + es.get("errors", 0)
        )
        report["summary"]["exploratory_findings"] = es.get("total_findings", 0)
        report["summary"]["console_errors"] = es.get("total_console_errors", 0)
        report["summary"]["broken_links"] = es.get("total_broken_links", 0)
        report["summary"]["exploratory_by_category"] = es.get("by_category", {})

    # 差分サマリー追加
    if diff and diff.get("summary"):
        ds = diff["summary"]
        report["summary"]["json_changes"] = ds.get("changed_json", 0)
        report["summary"]["screenshot_changes"] = ds.get("changed_screenshots", 0)

    return report


def save_report(report: dict) -> Path:
    """レポートをJSONファイルに保存"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d")
    report_path = REPORTS_DIR / f"weekly_investigation_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[REPORT] {report_path}")
    return report_path


def send_slack_notification(report: dict, webhook_url: str):
    """Slack通知送信"""
    s = report["summary"]
    status_emoji = ":white_check_mark:" if s["overall_status"] == "ALL PASS" else ":warning:"
    duration = f"{report['total_duration_sec']:.0f}s"

    blocks = [
        f"{status_emoji} *週次画面調査完了*",
        f"スクリプト: {s['scripts_passed']}/{s['scripts_total']} PASS | 所要: {duration}",
    ]

    if s.get("exploratory_findings", 0) > 0:
        blocks.append(f":mag: 探索的テスト: {s['exploratory_findings']}件の検出 ({s.get('exploratory_pages', 0)}ページ)")
        # カテゴリ別の内訳
        by_cat = s.get("exploratory_by_category", {})
        top_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_cats:
            cat_str = " / ".join(f"{c}:{n}" for c, n in top_cats if n > 0)
            if cat_str:
                blocks.append(f"  内訳: {cat_str}")
    if s.get("console_errors", 0) > 0:
        blocks.append(f":warning: コンソールエラー: {s['console_errors']}件")
    if s.get("broken_links", 0) > 0:
        blocks.append(f":link: リンク切れ: {s['broken_links']}件")
    if s.get("json_changes", 0) > 0 or s.get("screenshot_changes", 0) > 0:
        blocks.append(f":arrows_counterclockwise: 変更検出: JSON {s.get('json_changes', 0)}件 / SS {s.get('screenshot_changes', 0)}件")

    if s["scripts_failed"] > 0 or s.get("scripts_error", 0) > 0:
        failed_names = [r["name"] for r in report["phase1_scripts"]
                        if r["status"] in ("fail", "error", "timeout")]
        blocks.append(f":x: 失敗: {', '.join(failed_names)}")

    payload = {"text": "\n".join(blocks)}

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        print("[SLACK] 通知送信完了")
    except Exception as e:
        print(f"[SLACK] 通知送信失敗: {e}")


def print_summary(report: dict):
    """サマリー表示"""
    s = report["summary"]
    print("\n" + "=" * 60)
    print(f"週次画面調査レポート  {report['generated_at'][:10]}")
    print("=" * 60)
    print(f"Phase 1 スクリプト: {s['scripts_passed']}/{s['scripts_total']} PASS"
          f" ({s['scripts_failed']} fail, {s['scripts_error']} error, {s['scripts_skipped']} skip)")

    if s.get("exploratory_pages"):
        print(f"Phase 2 探索テスト: {s['exploratory_pages']} ページ / "
              f"{s.get('exploratory_findings', 0)} 検出")
        by_cat = s.get("exploratory_by_category", {})
        if by_cat:
            cat_str = " / ".join(f"{c}:{n}" for c, n in sorted(by_cat.items()) if n > 0)
            if cat_str:
                print(f"  カテゴリ別: {cat_str}")

    if s.get("json_changes") is not None:
        print(f"Phase 3 差分検出: JSON {s.get('json_changes', 0)}件変更"
              f" / スクリーンショット {s.get('screenshot_changes', 0)}件変更")

    print(f"所要時間: {report['total_duration_sec']:.0f}s")
    print(f"ステータス: {s['overall_status']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="週次画面調査オーケストレーター")
    parser.add_argument(
        "--scripts", nargs="*",
        help='実行するスクリプト名（部分一致）。例: --scripts "WDL サイトマップ" "TH-01"',
    )
    parser.add_argument("--skip-exploratory", action="store_true", help="探索的テストをスキップ")
    parser.add_argument("--skip-diff", action="store_true", help="差分検出をスキップ")
    parser.add_argument("--no-lock", action="store_true", help="ロック機構を無効化")
    parser.add_argument(
        "--slack-url",
        default=os.environ.get("E2E_SLACK_WEBHOOK_URL"),
        help="Slack Webhook URL",
    )
    args = parser.parse_args()

    # ロック取得
    _lock_mgr = None
    _queue_id = None
    if not args.no_lock:
        from e2e_lock import LockManager, QueueManager
        _lock_mgr = LockManager()
        _qm = QueueManager()

        if not _lock_mgr.acquire(screens=["investigation"], source="weekly_investigation"):
            info = _lock_mgr.get_info()
            print(f"[WAIT] 他のE2Eテストが実行中 (PID:{info.get('pid') if info else '?'})")
            _queue_id = _qm.enqueue(screens=["investigation"])
            print(f"[QUEUE] キューに追加: {_queue_id}")

            deadline = time.time() + 30 * 60
            while time.time() < deadline:
                if _qm.is_my_turn(_queue_id) and _lock_mgr.acquire(
                        screens=["investigation"], source="weekly_investigation"):
                    print("[START] ロック取得")
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

    # 実行対象スクリプトの決定
    scripts = list(INVESTIGATION_SCRIPTS)
    if args.scripts:
        filtered = []
        for name_filter in args.scripts:
            for s in INVESTIGATION_SCRIPTS:
                if name_filter in s[0] and s not in filtered:
                    filtered.append(s)
        if not filtered:
            print(f"[ERROR] 該当スクリプトなし: {args.scripts}")
            print(f"利用可能: {[s[0] for s in INVESTIGATION_SCRIPTS]}")
            sys.exit(1)
        scripts = filtered

    print(f"週次画面調査開始: {len(scripts)} スクリプト")
    print(f"対象: {', '.join(s[0] for s in scripts)}")
    total_start = time.time()

    # Phase 0: バックアップ
    backup_previous_results()

    # Phase 1: スクリプト順次実行
    print(f"\n[Phase 1] 画面調査スクリプト実行 ({len(scripts)}本)...")
    script_results = []
    for name, path, timeout in scripts:
        result = run_script(name, path, timeout)
        script_results.append(result)

    # Phase 2: 探索的テスト
    exploratory = None
    if not args.skip_exploratory:
        exploratory = run_exploratory_phase()
    else:
        print("\n[Phase 2] スキップ (--skip-exploratory)")

    # Phase 3: 差分検出
    diff = None
    if not args.skip_diff:
        diff = run_diff_phase()
    else:
        print("\n[Phase 3] スキップ (--skip-diff)")

    total_duration = time.time() - total_start

    # レポート生成
    report = build_report(script_results, exploratory, diff, total_duration)
    print_summary(report)
    save_report(report)

    # Slack通知
    if args.slack_url:
        send_slack_notification(report, args.slack_url)

    # 失敗があれば exit code 1
    if report["summary"]["overall_status"] != "ALL PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
