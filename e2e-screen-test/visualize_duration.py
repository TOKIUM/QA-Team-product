"""
E2Eテスト実行時間の可視化スクリプト

action_report_*.json および e2e_report_*.json を読み込み、
テスト実行時間を複数の形式で可視化する。

使い方:
  python visualize_duration.py                # 最新レポートの実行時間を表示
  python visualize_duration.py --top 10       # 上位10件の遅いテストを表示
  python visualize_duration.py --html         # HTMLレポートを生成
  python visualize_duration.py --trend        # 画面別の実行時間推移を表示
  python visualize_duration.py --days 14      # 直近14日分を対象
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

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"


def load_action_reports() -> list:
    """action_report_*.json を新しい順に読み込む"""
    reports = []
    if not REPORTS_DIR.exists():
        return reports
    for f in sorted(REPORTS_DIR.glob("action_report_*.json"), reverse=True):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            data["_file"] = f.name
            reports.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return reports


def load_e2e_reports(days: int) -> list:
    """e2e_report_*.json を新しい順に読み込む"""
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


def print_duration_summary(report: dict, top_n: int = 0):
    """最新のaction_reportから実行時間サマリーを表示"""
    print(f"\n{'='*70}")
    print(f"  E2Eテスト 実行時間レポート")
    print(f"  生成日時: {report.get('generated_at', 'N/A')}")
    print(f"  ファイル: {report.get('_file', 'N/A')}")
    print(f"{'='*70}")

    summary = report.get("summary", {})
    total_duration = summary.get("total_duration_seconds", 0)
    total_tests = summary.get("total_tests", 0)
    print(f"\n  全体: {total_tests}テスト / {total_duration:.1f}秒"
          f" (平均 {total_duration/total_tests:.2f}秒/テスト)" if total_tests else "")

    # 画面別サマリー（棒グラフ風）
    screens = report.get("screens", {})
    if screens:
        print(f"\n--- 画面別実行時間 ---")
        max_dur = max(s.get("duration_seconds", 0) for s in screens.values())
        bar_max = 40

        for name, data in sorted(screens.items(),
                                  key=lambda x: x[1].get("duration_seconds", 0),
                                  reverse=True):
            dur = data.get("duration_seconds", 0)
            total = data.get("total", 0)
            avg = dur / total if total else 0
            bar_len = int(dur / max_dur * bar_max) if max_dur else 0
            bar = "█" * bar_len
            print(f"  {name:<12} {bar} {dur:>7.1f}秒"
                  f" ({total}件, 平均{avg:.2f}秒)")

    # テスト別ランキング
    tests = report.get("tests", [])
    if tests:
        sorted_tests = sorted(tests, key=lambda t: t.get("duration", 0), reverse=True)
        show = sorted_tests[:top_n] if top_n > 0 else sorted_tests[:15]

        print(f"\n--- 遅いテスト TOP{len(show)} ---")
        print(f"  {'#':<4} {'時間':>7} {'画面':<12} {'テスト名'}")
        print(f"  {'─'*4} {'─'*7} {'─'*12} {'─'*40}")

        for i, t in enumerate(show, 1):
            dur = t.get("duration", 0)
            screen = t.get("screen", "?")
            name = t.get("test_name", "?").strip().replace("[chromium]", "")
            # 遅いテストにマーク
            mark = " ⚠" if dur > 10 else ""
            print(f"  {i:<4} {dur:>6.2f}s {screen:<12} {name}{mark}")

        # 統計情報
        durations = [t.get("duration", 0) for t in tests]
        durations.sort()
        median = durations[len(durations) // 2]
        p95 = durations[int(len(durations) * 0.95)]
        print(f"\n  統計: 中央値={median:.2f}s / P95={p95:.2f}s"
              f" / 最大={durations[-1]:.2f}s / 最小={durations[0]:.2f}s")

    # 時間帯分布
    if tests:
        buckets = {"<1s": 0, "1-3s": 0, "3-5s": 0, "5-10s": 0, ">10s": 0}
        for t in tests:
            d = t.get("duration", 0)
            if d < 1:
                buckets["<1s"] += 1
            elif d < 3:
                buckets["1-3s"] += 1
            elif d < 5:
                buckets["3-5s"] += 1
            elif d < 10:
                buckets["5-10s"] += 1
            else:
                buckets[">10s"] += 1

        print(f"\n--- 実行時間分布 ---")
        for label, count in buckets.items():
            bar = "▓" * count
            print(f"  {label:>5} | {bar} {count}")

    print(f"\n{'='*70}\n")


def print_trend(e2e_reports: list, days: int):
    """画面別の実行時間推移を表示"""
    if not e2e_reports:
        print(f"\n  直近{days}日間のレポートがありません。")
        return

    print(f"\n{'='*70}")
    print(f"  E2Eテスト 実行時間推移（直近{days}日間、{len(e2e_reports)}件）")
    print(f"{'='*70}")

    # 全体の実行時間推移
    print(f"\n--- 全体実行時間推移 ---")
    for r in reversed(e2e_reports):
        ts = r["_ts"].strftime("%m/%d %H:%M")
        dur = r.get("total_duration", 0)
        total = r.get("total_tests", 0)
        passed = r.get("total_passed", 0)
        status = "PASS" if r.get("overall_status") == "ALL PASS" else "FAIL"
        bar_len = int(dur / 10)
        bar = "█" * min(bar_len, 50)
        print(f"  {ts} [{status}] {bar} {dur:>6.1f}秒 ({passed}/{total})")

    # 画面別の推移
    from collections import defaultdict
    screen_data = defaultdict(list)
    for r in e2e_reports:
        ts = r["_ts"].strftime("%m/%d %H:%M")
        for s in r.get("screens", []):
            screen_data[s["name"]].append({
                "date": ts,
                "duration": s["duration"],
                "status": s["status"],
            })

    if screen_data:
        print(f"\n--- 画面別実行時間推移 ---")
        for name, entries in sorted(screen_data.items()):
            durations = [e["duration"] for e in entries if e["duration"] > 0]
            if not durations:
                continue
            avg = sum(durations) / len(durations)
            latest = durations[0]
            change = ((latest - avg) / avg * 100) if avg > 0 else 0
            trend_icon = "↑" if change > 20 else "↓" if change < -20 else "→"
            print(f"  {name:<16} 最新:{latest:>6.1f}秒  "
                  f"平均:{avg:>6.1f}秒  {trend_icon} {change:>+.0f}%")

    print(f"\n{'='*70}\n")


def generate_html(action_report: dict, e2e_reports: list, output_path: Path):
    """HTMLレポートを生成"""
    tests = action_report.get("tests", [])
    screens = action_report.get("screens", {})
    summary = action_report.get("summary", {})

    # 画面別データ
    screen_labels = json.dumps(list(screens.keys()), ensure_ascii=False)
    screen_durations = json.dumps([s.get("duration_seconds", 0) for s in screens.values()])
    screen_counts = json.dumps([s.get("total", 0) for s in screens.values()])

    # テスト別データ（上位20件）
    sorted_tests = sorted(tests, key=lambda t: t.get("duration", 0), reverse=True)[:20]
    test_labels = json.dumps(
        [t.get("test_name", "?").strip().replace("[chromium]", "")[:30]
         for t in sorted_tests], ensure_ascii=False)
    test_durations = json.dumps([t.get("duration", 0) for t in sorted_tests])
    test_screens = json.dumps(
        [t.get("screen", "?") for t in sorted_tests], ensure_ascii=False)

    # 分布データ
    buckets = [0, 0, 0, 0, 0]
    for t in tests:
        d = t.get("duration", 0)
        if d < 1:
            buckets[0] += 1
        elif d < 3:
            buckets[1] += 1
        elif d < 5:
            buckets[2] += 1
        elif d < 10:
            buckets[3] += 1
        else:
            buckets[4] += 1

    # 時系列データ
    trend_dates = json.dumps(
        [r["_ts"].strftime("%m/%d %H:%M") for r in reversed(e2e_reports)],
        ensure_ascii=False)
    trend_durations = json.dumps(
        [r.get("total_duration", 0) for r in reversed(e2e_reports)])

    total_dur = summary.get("total_duration_seconds", 0)
    total_tests = summary.get("total_tests", 0)
    generated = action_report.get("generated_at", "N/A")

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>E2Eテスト実行時間レポート</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
  .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
  .card {{ background: white; padding: 20px; border-radius: 8px;
           box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; text-align: center; }}
  .card .value {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
  .card .label {{ color: #666; margin-top: 5px; }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
  .chart-box {{ background: white; padding: 20px; border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .chart-box.full {{ grid-column: 1 / -1; }}
  .chart-box h3 {{ margin-top: 0; color: #555; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f9f9f9; font-weight: 600; }}
  .slow {{ color: #f44336; font-weight: bold; }}
  .fast {{ color: #4CAF50; }}
  .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 0.9em; }}
</style>
</head>
<body>
<div class="container">
  <h1>E2Eテスト実行時間レポート</h1>
  <p>生成日時: {generated}</p>

  <div class="summary">
    <div class="card">
      <div class="value">{total_tests}</div>
      <div class="label">テスト数</div>
    </div>
    <div class="card">
      <div class="value">{total_dur:.1f}s</div>
      <div class="label">合計実行時間</div>
    </div>
    <div class="card">
      <div class="value">{total_dur/total_tests:.2f}s</div>
      <div class="label">平均実行時間</div>
    </div>
    <div class="card">
      <div class="value">{len(e2e_reports)}</div>
      <div class="label">レポート数</div>
    </div>
  </div>

  <div class="chart-row">
    <div class="chart-box">
      <h3>画面別実行時間</h3>
      <canvas id="screenChart"></canvas>
    </div>
    <div class="chart-box">
      <h3>実行時間分布</h3>
      <canvas id="distChart"></canvas>
    </div>
  </div>

  <div class="chart-row">
    <div class="chart-box full">
      <h3>遅いテスト TOP20</h3>
      <canvas id="testChart" height="100"></canvas>
    </div>
  </div>

  <div class="chart-row">
    <div class="chart-box full">
      <h3>全体実行時間の推移</h3>
      <canvas id="trendChart" height="60"></canvas>
    </div>
  </div>

  <div class="chart-box">
    <h3>テスト一覧（実行時間順）</h3>
    <table>
      <tr><th>#</th><th>画面</th><th>テスト名</th><th>時間</th><th>ステップ数</th></tr>
"""

    for i, t in enumerate(sorted(tests, key=lambda x: x.get("duration", 0), reverse=True), 1):
        dur = t.get("duration", 0)
        cls = "slow" if dur > 10 else "fast" if dur < 1 else ""
        name = t.get("test_name", "?").strip().replace("[chromium]", "")
        html += (f'      <tr><td>{i}</td><td>{t.get("screen","?")}</td>'
                 f'<td>{name}</td>'
                 f'<td class="{cls}">{dur:.2f}s</td>'
                 f'<td>{t.get("step_count",0)}</td></tr>\n')

    html += f"""    </table>
  </div>

  <div class="footer">Generated by visualize_duration.py</div>
</div>

<script>
const screenColors = ['#4CAF50','#2196F3','#FF9800','#9C27B0','#F44336','#00BCD4','#795548'];

// 画面別実行時間
new Chart(document.getElementById('screenChart'), {{
  type: 'bar',
  data: {{
    labels: {screen_labels},
    datasets: [{{
      label: '実行時間(秒)',
      data: {screen_durations},
      backgroundColor: screenColors
    }}, {{
      label: 'テスト数',
      data: {screen_counts},
      backgroundColor: 'rgba(0,0,0,0.1)',
      yAxisID: 'y1'
    }}]
  }},
  options: {{
    scales: {{
      y: {{ beginAtZero: true, title: {{ display: true, text: '秒' }} }},
      y1: {{ position: 'right', beginAtZero: true, title: {{ display: true, text: '件数' }},
             grid: {{ drawOnChartArea: false }} }}
    }}
  }}
}});

// 実行時間分布
new Chart(document.getElementById('distChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['<1秒', '1-3秒', '3-5秒', '5-10秒', '>10秒'],
    datasets: [{{
      data: {json.dumps(buckets)},
      backgroundColor: ['#4CAF50','#8BC34A','#FFC107','#FF9800','#F44336']
    }}]
  }}
}});

// 遅いテストTOP20
new Chart(document.getElementById('testChart'), {{
  type: 'bar',
  data: {{
    labels: {test_labels},
    datasets: [{{
      label: '実行時間(秒)',
      data: {test_durations},
      backgroundColor: {test_durations}.map(d => d > 10 ? '#F44336' : d > 5 ? '#FF9800' : '#4CAF50')
    }}]
  }},
  options: {{
    indexAxis: 'y',
    scales: {{ x: {{ beginAtZero: true, title: {{ display: true, text: '秒' }} }} }}
  }}
}});

// 全体実行時間推移
new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{
    labels: {trend_dates},
    datasets: [{{
      label: '合計実行時間(秒)',
      data: {trend_durations},
      borderColor: '#2196F3',
      fill: false,
      tension: 0.3
    }}]
  }},
  options: {{
    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: '秒' }} }} }}
  }}
}});
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTMLレポート生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="E2Eテスト実行時間の可視化")
    parser.add_argument("--top", type=int, default=0,
                        help="表示する遅いテストの件数（デフォルト: 15）")
    parser.add_argument("--html", action="store_true",
                        help="HTMLレポートを生成")
    parser.add_argument("--trend", action="store_true",
                        help="実行時間推移を表示")
    parser.add_argument("--days", type=int, default=7,
                        help="推移分析の対象日数（デフォルト: 7）")
    args = parser.parse_args()

    action_reports = load_action_reports()
    e2e_reports = load_e2e_reports(args.days)

    if not action_reports:
        print("action_report_*.json が見つかりません。")
        print("まず python generate_action_report.py を実行してください。")
        return

    latest = action_reports[0]

    if args.html:
        output = REPORTS_DIR / f"duration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        generate_html(latest, e2e_reports, output)
    elif args.trend:
        print_trend(e2e_reports, args.days)
    else:
        print_duration_summary(latest, args.top)


if __name__ == "__main__":
    main()
