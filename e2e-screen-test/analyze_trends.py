"""
E2Eテスト結果トレンド分析スクリプト

過去のレポート（reports/e2e_report_*.json）を読み込み、以下を検出する:
- フレーキーテスト: 直近N日で成功率50-90%のテスト
- 劣化トレンド: 直近で失敗が増えている画面
- 実行時間の異常: 通常の2倍以上かかった画面
- 全体のパス率推移

使い方:
  python analyze_trends.py              # 直近7日分を分析
  python analyze_trends.py --days 14    # 直近14日分を分析
  python analyze_trends.py --json       # JSON形式で出力
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp932 文字化け対策
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from collections import defaultdict


BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"


def load_reports(days: int) -> list:
    """指定日数分のレポートを新しい順に読み込む"""
    cutoff = datetime.now() - timedelta(days=days)
    reports = []

    if not REPORTS_DIR.exists():
        return reports

    for f in sorted(REPORTS_DIR.glob("e2e_report_*.json"), reverse=True):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            ts = datetime.fromisoformat(data["timestamp"])
            if ts >= cutoff:
                data["_file"] = f.name
                data["_ts"] = ts
                reports.append(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue

    return reports


def analyze_screen_stability(reports: list) -> dict:
    """画面ごとの安定性を分析"""
    screen_history = defaultdict(list)

    for report in reports:
        date = report["_ts"].strftime("%Y-%m-%d")
        for screen in report.get("screens", []):
            name = screen["name"]
            screen_history[name].append({
                "date": date,
                "status": screen["status"],
                "passed": screen["passed"],
                "failed": screen["failed"],
                "total": screen["total"],
                "duration": screen["duration"],
                "error": screen.get("error"),
            })

    results = {}
    for name, history in screen_history.items():
        total_runs = len(history)
        pass_runs = sum(1 for h in history if h["status"] == "pass")
        fail_runs = sum(1 for h in history if h["status"] == "fail")
        skip_runs = sum(1 for h in history if h["status"] == "skip")
        pass_rate = pass_runs / total_runs * 100 if total_runs > 0 else 0

        durations = [h["duration"] for h in history if h["duration"] > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        # フレーキー判定: 成功率50-90%
        is_flaky = 50 <= pass_rate <= 90 and total_runs >= 3

        # 劣化トレンド: 直近3回中2回以上失敗かつ、それ以前は全パス
        recent = history[:3]
        older = history[3:]
        recent_fails = sum(1 for h in recent if h["status"] == "fail")
        older_fails = sum(1 for h in older if h["status"] == "fail")
        is_degrading = (
            recent_fails >= 2
            and len(recent) >= 2
            and (older_fails == 0 or len(older) == 0)
        )

        # 実行時間異常: 最新が平均の2倍以上
        latest_duration = history[0]["duration"] if history else 0
        is_slow = (
            avg_duration > 0
            and latest_duration > avg_duration * 2
            and total_runs >= 3
        )

        # 最新の失敗エラー
        latest_errors = []
        for h in history[:3]:
            if h.get("error"):
                latest_errors.append({"date": h["date"], "error": h["error"]})

        results[name] = {
            "total_runs": total_runs,
            "pass_rate": round(pass_rate, 1),
            "pass_runs": pass_runs,
            "fail_runs": fail_runs,
            "skip_runs": skip_runs,
            "avg_duration": round(avg_duration, 1),
            "max_duration": round(max_duration, 1),
            "latest_duration": round(latest_duration, 1),
            "is_flaky": is_flaky,
            "is_degrading": is_degrading,
            "is_slow": is_slow,
            "latest_errors": latest_errors,
        }

    return results


def analyze_overall_trend(reports: list) -> list:
    """全体のパス率推移"""
    trend = []
    for report in reports:
        total = report.get("total_tests", 0)
        passed = report.get("total_passed", 0)
        rate = round(passed / total * 100, 1) if total > 0 else 0
        trend.append({
            "date": report["_ts"].strftime("%Y-%m-%d %H:%M"),
            "status": report.get("overall_status", "UNKNOWN"),
            "passed": passed,
            "total": total,
            "pass_rate": rate,
            "duration": report.get("total_duration", 0),
        })
    return trend


def print_report(screen_results: dict, overall_trend: list, days: int):
    """分析結果をコンソールに出力"""
    print(f"\n{'='*60}")
    print(f"  E2Eテスト トレンド分析（直近{days}日間）")
    print(f"{'='*60}")

    # 全体トレンド
    print(f"\n--- 全体パス率推移 ---")
    for t in overall_trend:
        icon = "[PASS]" if t["status"] == "ALL PASS" else "[FAIL]"
        print(f"  {t['date']}  {icon}  {t['passed']}/{t['total']}"
              f" ({t['pass_rate']}%)  {t['duration']}秒")

    # アラート（問題があるものだけ）
    alerts = []
    for name, data in screen_results.items():
        if data["is_flaky"]:
            alerts.append(f"  [FLAKY] {name}: 成功率{data['pass_rate']}%"
                          f"（{data['total_runs']}回中{data['fail_runs']}回失敗）")
        if data["is_degrading"]:
            alerts.append(f"  [DEGRADE] {name}: 直近で失敗が増加中")
        if data["is_slow"]:
            alerts.append(f"  [SLOW] {name}: 最新{data['latest_duration']}秒"
                          f"（平均{data['avg_duration']}秒の"
                          f"{data['latest_duration']/data['avg_duration']:.1f}倍）")

    if alerts:
        print(f"\n--- アラート ---")
        for a in alerts:
            print(a)
    else:
        print(f"\n--- アラート ---")
        print("  問題なし")

    # 画面別サマリー
    print(f"\n--- 画面別安定性 ---")
    for name, data in sorted(screen_results.items(),
                             key=lambda x: x[1]["pass_rate"]):
        status = "OK" if data["pass_rate"] == 100 else f"{data['pass_rate']}%"
        flags = []
        if data["is_flaky"]:
            flags.append("FLAKY")
        if data["is_degrading"]:
            flags.append("DEGRADE")
        if data["is_slow"]:
            flags.append("SLOW")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        print(f"  {name}: {status} "
              f"({data['pass_runs']}/{data['total_runs']}回PASS, "
              f"平均{data['avg_duration']}秒){flag_str}")

        # エラー詳細
        for err in data["latest_errors"][:1]:
            for line in err["error"].splitlines()[:2]:
                print(f"    {err['date']}: {line.strip()}")

    # レポート数
    print(f"\n{'─'*60}")
    print(f"  分析対象: {len(overall_trend)}件のレポート")
    if not overall_trend:
        print("  [WARNING] レポートが見つかりません。"
              "まず python run_all_e2e.py を実行してください。")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="E2Eテスト結果トレンド分析")
    parser.add_argument(
        "--days", type=int, default=7,
        help="分析対象の日数（デフォルト: 7日）",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="JSON形式で出力",
    )
    args = parser.parse_args()

    reports = load_reports(args.days)
    screen_results = analyze_screen_stability(reports)
    overall_trend = analyze_overall_trend(reports)

    if args.json:
        output = {
            "analysis_date": datetime.now().isoformat(),
            "period_days": args.days,
            "report_count": len(reports),
            "overall_trend": overall_trend,
            "screens": screen_results,
            "alerts": {
                "flaky": [n for n, d in screen_results.items() if d["is_flaky"]],
                "degrading": [n for n, d in screen_results.items() if d["is_degrading"]],
                "slow": [n for n, d in screen_results.items() if d["is_slow"]],
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(screen_results, overall_trend, args.days)


if __name__ == "__main__":
    main()
