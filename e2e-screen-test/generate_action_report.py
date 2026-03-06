"""
全画面E2Eテスト 操作ログ統合レポート生成

各画面のtest_results/から_actions.logを収集し、
統合レポート（Markdown + JSON）を生成する。

使い方:
    python generate_action_report.py
    python generate_action_report.py --output reports/action_report.md
"""

import os
import re
import json
import argparse
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 画面定義: (画面名, test_resultsディレクトリの相対パス, TH-IDプレフィックス)
SCREENS = [
    ("取引先", "取引先/test_results", "TH-PL"),
    ("請求書一覧", "請求書/請求書一覧/test_results", "TH-IL"),
    ("請求書詳細", "請求書/請求書一覧/test_results", "TH-ID"),
    ("PDF取り込み", "請求書/請求書一覧/請求書作成/PDFを取り込む/test_results", "TH-PO"),
]


def parse_action_log(filepath):
    """アクションログを解析して構造化データを返す"""
    result = {
        "file": filepath,
        "test_name": None,
        "th_id": None,
        "result": None,
        "duration": None,
        "steps": [],
        "step_count": 0,
        "actions": defaultdict(int),
    }

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip()
        if line.startswith("テスト: "):
            result["test_name"] = line[4:]
        elif line.startswith("TH-ID: "):
            result["th_id"] = line[6:]
        elif line.startswith("結果: "):
            result["result"] = line[4:]
        elif line.startswith("実行時間: "):
            try:
                result["duration"] = float(line[5:].replace("s", ""))
            except ValueError:
                pass
        elif re.match(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\]", line):
            result["steps"].append(line)
            # アクション種別をカウント
            if "クリック" in line:
                result["actions"]["クリック"] += 1
            elif "入力" in line:
                result["actions"]["入力"] += 1
            elif "選択" in line:
                result["actions"]["選択"] += 1
            elif "ページ遷移" in line:
                result["actions"]["ページ遷移"] += 1
            elif "イベント発火" in line:
                result["actions"]["イベント発火"] += 1
            elif "チェック" in line:
                result["actions"]["チェック"] += 1

    result["step_count"] = len(result["steps"])
    result["actions"] = dict(result["actions"])
    return result


def collect_logs(screen_name, test_results_dir, prefix):
    """指定画面のアクションログを収集"""
    logs = []
    if not os.path.exists(test_results_dir):
        return logs

    for entry in sorted(os.listdir(test_results_dir)):
        if not entry.startswith(prefix):
            continue
        entry_path = os.path.join(test_results_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        log_file = os.path.join(entry_path, f"{entry}_actions.log")
        if os.path.exists(log_file):
            parsed = parse_action_log(log_file)
            parsed["screen"] = screen_name
            logs.append(parsed)

    return logs


def generate_report(all_logs, output_path):
    """統合レポート（Markdown）を生成"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 画面別集計
    screen_stats = defaultdict(lambda: {
        "total": 0, "pass": 0, "fail": 0,
        "total_duration": 0, "total_steps": 0,
        "actions": defaultdict(int),
    })

    for log in all_logs:
        s = screen_stats[log["screen"]]
        s["total"] += 1
        if log["result"] == "PASS":
            s["pass"] += 1
        else:
            s["fail"] += 1
        s["total_duration"] += log["duration"] or 0
        s["total_steps"] += log["step_count"]
        for action, count in log["actions"].items():
            s["actions"][action] += count

    # 全体集計
    total_tests = sum(s["total"] for s in screen_stats.values())
    total_pass = sum(s["pass"] for s in screen_stats.values())
    total_fail = sum(s["fail"] for s in screen_stats.values())
    total_duration = sum(s["total_duration"] for s in screen_stats.values())
    total_steps = sum(s["total_steps"] for s in screen_stats.values())

    # 全体アクション集計
    all_actions = defaultdict(int)
    for s in screen_stats.values():
        for action, count in s["actions"].items():
            all_actions[action] += count

    lines = []
    lines.append(f"# E2Eテスト 操作ログ統合レポート")
    lines.append(f"")
    lines.append(f"生成日時: {now}")
    lines.append(f"")

    # サマリー
    lines.append(f"## サマリー")
    lines.append(f"")
    lines.append(f"| 項目 | 値 |")
    lines.append(f"|------|-----|")
    lines.append(f"| テスト総数 | {total_tests} |")
    lines.append(f"| PASS | {total_pass} |")
    lines.append(f"| FAIL | {total_fail} |")
    lines.append(f"| 合計実行時間 | {total_duration:.1f}s ({total_duration/60:.1f}分) |")
    lines.append(f"| 記録された操作数 | {total_steps} |")
    lines.append(f"")

    # アクション種別サマリー
    lines.append(f"### 操作種別の内訳")
    lines.append(f"")
    lines.append(f"| 操作 | 回数 |")
    lines.append(f"|------|------|")
    for action in ["ページ遷移", "クリック", "入力", "選択", "イベント発火", "チェック"]:
        if action in all_actions:
            lines.append(f"| {action} | {all_actions[action]} |")
    lines.append(f"")

    # 画面別サマリー
    lines.append(f"## 画面別サマリー")
    lines.append(f"")
    lines.append(f"| 画面 | テスト数 | PASS | FAIL | 実行時間 | 操作数 |")
    lines.append(f"|------|---------|------|------|---------|--------|")
    for screen_name in ["取引先", "請求書一覧", "請求書詳細", "PDF取り込み"]:
        s = screen_stats.get(screen_name)
        if s:
            lines.append(
                f"| {screen_name} | {s['total']} | {s['pass']} | {s['fail']} "
                f"| {s['total_duration']:.1f}s | {s['total_steps']} |"
            )
    lines.append(f"")

    # 画面別テスト一覧
    lines.append(f"## テスト一覧")
    lines.append(f"")

    current_screen = None
    for log in all_logs:
        if log["screen"] != current_screen:
            current_screen = log["screen"]
            lines.append(f"### {current_screen}")
            lines.append(f"")
            lines.append(f"| TH-ID | テスト名 | 結果 | 時間 | 操作数 |")
            lines.append(f"|-------|---------|------|------|--------|")

        test_name = log["test_name"] or "N/A"
        # [chromium] を除去して短縮
        test_name = re.sub(r"\[chromium\]$", "", test_name)
        th_id = log["th_id"] or "N/A"
        result = log["result"] or "N/A"
        duration = f"{log['duration']:.1f}s" if log["duration"] else "N/A"
        lines.append(
            f"| {th_id} | {test_name} | {result} | {duration} | {log['step_count']} |"
        )

    lines.append(f"")

    report_text = "\n".join(lines)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    # JSON版も出力
    json_path = output_path.replace(".md", ".json")
    json_data = {
        "generated_at": now,
        "summary": {
            "total_tests": total_tests,
            "passed": total_pass,
            "failed": total_fail,
            "total_duration_seconds": round(total_duration, 1),
            "total_steps": total_steps,
            "actions": dict(all_actions),
        },
        "screens": {
            name: {
                "total": s["total"],
                "passed": s["pass"],
                "failed": s["fail"],
                "duration_seconds": round(s["total_duration"], 1),
                "total_steps": s["total_steps"],
                "actions": dict(s["actions"]),
            }
            for name, s in screen_stats.items()
        },
        "tests": [
            {
                "screen": log["screen"],
                "th_id": log["th_id"],
                "test_name": log["test_name"],
                "result": log["result"],
                "duration": log["duration"],
                "step_count": log["step_count"],
                "actions": log["actions"],
            }
            for log in all_logs
        ],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    return report_text, json_path


def find_previous_report(reports_dir, current_json_path):
    """前回のJSONレポートを検索して返す"""
    if not os.path.exists(reports_dir):
        return None
    json_files = sorted(
        [f for f in os.listdir(reports_dir)
         if f.startswith("action_report_") and f.endswith(".json")],
        reverse=True,
    )
    current_name = os.path.basename(current_json_path)
    for f in json_files:
        if f != current_name:
            return os.path.join(reports_dir, f)
    return None


def compare_reports(current_json_path, previous_json_path):
    """前回と今回のレポートを比較し、差分サマリーを返す"""
    with open(current_json_path, "r", encoding="utf-8") as f:
        current = json.load(f)
    with open(previous_json_path, "r", encoding="utf-8") as f:
        previous = json.load(f)

    lines = []
    lines.append("## 前回との比較")
    lines.append("")
    lines.append(f"前回レポート: {os.path.basename(previous_json_path)}")
    lines.append("")

    # サマリー比較
    cs = current["summary"]
    ps = previous["summary"]
    lines.append("| 項目 | 前回 | 今回 | 差分 |")
    lines.append("|------|------|------|------|")

    for key, label in [
        ("total_tests", "テスト数"),
        ("passed", "PASS"),
        ("failed", "FAIL"),
        ("total_duration_seconds", "実行時間(s)"),
        ("total_steps", "操作数"),
    ]:
        prev_val = ps.get(key, 0)
        curr_val = cs.get(key, 0)
        diff = curr_val - prev_val
        if isinstance(diff, float):
            diff = round(diff, 1)
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        lines.append(f"| {label} | {prev_val} | {curr_val} | {diff_str} |")
    lines.append("")

    # 実行時間の劣化検知（基準10: 前回比150%超で警告）
    prev_tests = {t["th_id"]: t for t in previous.get("tests", []) if t.get("th_id")}
    warnings = []
    for test in current.get("tests", []):
        th_id = test.get("th_id")
        if not th_id or th_id not in prev_tests:
            continue
        curr_dur = test.get("duration") or 0
        prev_dur = prev_tests[th_id].get("duration") or 0
        if prev_dur > 0 and curr_dur > prev_dur * 1.5:
            ratio = curr_dur / prev_dur
            warnings.append(
                f"| {th_id} | {test.get('test_name', 'N/A')} | "
                f"{prev_dur:.1f}s | {curr_dur:.1f}s | {ratio:.1f}x |"
            )

    if warnings:
        lines.append("### 実行時間劣化警告（前回比150%超）")
        lines.append("")
        lines.append("| TH-ID | テスト名 | 前回 | 今回 | 倍率 |")
        lines.append("|-------|---------|------|------|------|")
        lines.extend(warnings)
    else:
        lines.append("### 実行時間劣化警告")
        lines.append("")
        lines.append("劣化なし（全テストが前回比150%以内）")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="E2Eテスト操作ログ統合レポート生成")
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(SCRIPT_DIR, "reports", f"action_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"),
        help="出力ファイルパス（デフォルト: reports/action_report_YYYYMMDD_HHMMSS.md）",
    )
    args = parser.parse_args()

    all_logs = []
    for screen_name, rel_path, prefix in SCREENS:
        test_results_dir = os.path.join(SCRIPT_DIR, rel_path)
        logs = collect_logs(screen_name, test_results_dir, prefix)
        all_logs.extend(logs)
        print(f"  {screen_name}: {len(logs)} テストのログ収集完了")

    if not all_logs:
        print("アクションログが見つかりません。テストを実行してください。")
        return

    report_text, json_path = generate_report(all_logs, args.output)

    # 前回レポートとの比較（基準10: 実行時間監視）
    reports_dir = os.path.dirname(args.output)
    prev_report = find_previous_report(reports_dir, json_path)
    if prev_report:
        comparison = compare_reports(json_path, prev_report)
        # Markdownレポートに追記
        with open(args.output, "a", encoding="utf-8") as f:
            f.write("\n" + comparison)
        print(f"\n前回比較: {os.path.basename(prev_report)} と比較完了")
    else:
        print("\n前回レポートなし（初回実行）")

    print(f"\n統合レポート生成完了:")
    print(f"  Markdown: {args.output}")
    print(f"  JSON: {json_path}")
    print(f"  テスト総数: {len(all_logs)}")


if __name__ == "__main__":
    main()
