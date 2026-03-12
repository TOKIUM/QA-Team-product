"""JSON レポート + コンソール出力 + HTML レポート + CSV エクスポート."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path

from .models import TestResult


class Reporter:
    """テスト結果のレポート生成."""

    def _aggregate_by_pattern(self, results: list[TestResult]) -> dict[str, dict[str, int]]:
        """パターン別に集計."""
        by_pattern: dict[str, dict[str, int]] = {}
        for r in results:
            pat = r.test_case.pattern
            if pat not in by_pattern:
                by_pattern[pat] = {"total": 0, "passed": 0}
            by_pattern[pat]["total"] += 1
            if r.passed:
                by_pattern[pat]["passed"] += 1
        return by_pattern

    def print_summary(self, results: list[TestResult]) -> None:
        """コンソールにサマリー表示（run-all.cmd と同じ見た目）."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        by_pattern = self._aggregate_by_pattern(results)

        print("========================================")
        print(f"  Results: {passed} passed, {failed} failed / {total} total")
        print("----------------------------------------")
        for pat, counts in by_pattern.items():
            pad = max(len(p) for p in by_pattern)
            print(f"  {pat:<{pad}} : {counts['passed']}/{counts['total']}")

        if failed > 0:
            print("----------------------------------------")
            print("  FAIL details:")
            for r in results:
                if not r.passed:
                    print(f"    {r.status_code}: {r.test_case.name} (expected {r.test_case.expected_status})")

        warn_results = [r for r in results if r.schema_warnings]
        if warn_results:
            print("----------------------------------------")
            print(f"  Schema warnings: {len(warn_results)}")
            for r in warn_results:
                for w in r.schema_warnings:
                    print(f"    {r.test_case.name}: {w}")

        print("========================================")
        print()

        # 保存されたファイル一覧
        saved = [r for r in results if r.output_file]
        if saved:
            # results/YYYYMMDDHHMMSS/ のパスから表示用パスを取得
            first_dir = Path(saved[0].output_file).parent
            rel_dir = first_dir.name
            print(f"Saved responses (results/{rel_dir}):")
            for r in saved:
                print(f"  {Path(r.output_file).name}")
            print()
            print(f"Results directory: results/{rel_dir}")
        print()

    def save_report(self, results: list[TestResult], results_dir: Path) -> str | None:
        """report.json を results/YYYYMMDDHHMMSS/ に保存."""
        # タイムスタンプディレクトリを特定
        saved = [r for r in results if r.output_file]
        if not saved:
            return None

        report_dir = Path(saved[0].output_file).parent

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        by_pattern = self._aggregate_by_pattern(results)

        report = {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "by_pattern": by_pattern,
            },
            "tests": [],
        }

        for r in results:
            # ヘッダーからトークンをマスク
            masked_headers = None
            if r.request_headers:
                masked_headers = {}
                for k, v in r.request_headers.items():
                    if k.lower() == "authorization":
                        masked_headers[k] = v[:12] + "***" if len(v) > 12 else "***"
                    else:
                        masked_headers[k] = v

            api = r.test_case.api
            test_entry = {
                "name": r.test_case.name,
                "pattern": r.test_case.pattern,
                "api": api.name if api else None,
                "method": r.test_case.method,
                "url_path": r.test_case.url_path,
                "request_url": r.request_url,
                "request_headers": masked_headers,
                "query_params": r.test_case.query_params,
                "request_body": r.test_case.request_body,
                "use_auth": r.test_case.use_auth,
                "expected_status": r.test_case.expected_status,
                "actual_status": r.status_code,
                "elapsed_ms": r.elapsed_ms,
                "passed": r.passed,
                "output_file": Path(r.output_file).name if r.output_file else None,
            }

            # レスポンス件数（リソース配列のカウント）
            if r.response_body and isinstance(r.response_body, dict) and api:
                resource = api.resource
                if resource in r.response_body and isinstance(r.response_body[resource], list):
                    test_entry["response_count"] = len(r.response_body[resource])

            if r.schema_warnings:
                test_entry["schema_warnings"] = r.schema_warnings

            if r.data_diff_summary:
                test_entry["data_comparison"] = r.data_diff_summary

            report["tests"].append(test_entry)

        report_path = report_dir / "report.json"
        with open(report_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
            f.write("\n")

        return str(report_path)

    def save_csv_report(self, results: list[TestResult], results_dir: Path) -> str | None:
        """report.csv を results/YYYYMMDDHHMMSS/ に保存."""
        saved = [r for r in results if r.output_file]
        if not saved:
            return None

        report_dir = Path(saved[0].output_file).parent

        csv_path = report_dir / "report.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "name", "pattern", "method", "url_path",
                "expected_status", "actual_status", "elapsed_ms",
                "passed", "schema_warnings",
            ])
            for r in results:
                tc = r.test_case
                warnings = "; ".join(r.schema_warnings) if r.schema_warnings else ""
                writer.writerow([
                    tc.name, tc.pattern, tc.method, tc.url_path,
                    tc.expected_status, r.status_code,
                    f"{r.elapsed_ms:.0f}",
                    "PASS" if r.passed else "FAIL",
                    warnings,
                ])

        return str(csv_path)

    def save_html_report(self, results: list[TestResult], results_dir: Path) -> str | None:
        """report.html を results/YYYYMMDDHHMMSS/ に保存."""
        saved = [r for r in results if r.output_file]
        if not saved:
            return None

        report_dir = Path(saved[0].output_file).parent

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        by_pattern = self._aggregate_by_pattern(results)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # パターン別サマリー行
        pattern_rows = ""
        for pat, counts in by_pattern.items():
            f = counts["total"] - counts["passed"]
            status = "PASS" if f == 0 else "FAIL"
            cls = "pass" if f == 0 else "fail"
            pattern_rows += (
                f"<tr><td>{_esc(pat)}</td>"
                f"<td>{counts['total']}</td>"
                f"<td>{counts['passed']}</td>"
                f"<td>{f}</td>"
                f'<td class="{cls}">{status}</td></tr>\n'
            )

        # テスト一覧行
        test_rows = ""
        for r in results:
            if not r.passed:
                cls = "fail"
                status = "FAIL"
            elif r.schema_warnings:
                cls = "warn"
                status = "WARN"
            else:
                cls = "pass"
                status = "PASS"
            warn_text = _esc("; ".join(r.schema_warnings)) if r.schema_warnings else ""

            # リクエストボディ（展開可能）
            body_html = ""
            if r.test_case.request_body:
                import json as _json
                body_json = _esc(_json.dumps(r.test_case.request_body, indent=2, ensure_ascii=False))
                body_html = (f'<details><summary>リクエストボディ</summary>'
                             f'<pre style="margin:4px 0;font-size:12px">{body_json}</pre></details>')

            # データ比較
            dc_html = ""
            if r.data_diff_summary:
                dc_parts = []
                total_info = r.data_diff_summary.get("_total")
                if total_info:
                    d = total_info.get("diff", 0)
                    sign = "+" if d > 0 else ""
                    dc_parts.append(f"総件数: {total_info.get('before_total')} → "
                                    f"{total_info.get('after_total')} ({sign}{d})")
                for key, val in r.data_diff_summary.items():
                    if key == "_total":
                        continue
                    dc_parts.append(
                        f"{_esc(key)}: {val['before_count']}件→{val['after_count']}件 "
                        f"(追加:{val['added_count']}, 変更:{val['changed_count']})")
                    for item_id, changes in val.get("changed", {}).items():
                        for fname, vals in changes.items():
                            dc_parts.append(
                                f"  {_esc(fname)}: {_esc(str(vals['before']))} → "
                                f"{_esc(str(vals['after']))}")
                dc_html = (f'<details><summary>データ比較</summary>'
                           f'<pre style="margin:4px 0;font-size:12px">{"<br>".join(dc_parts)}</pre></details>')

            extra = body_html + dc_html

            test_rows += (
                f'<tr class="row-{cls}">'
                f"<td>{_esc(r.test_case.name)}</td>"
                f"<td>{_esc(r.test_case.pattern)}</td>"
                f"<td>{r.test_case.method}</td>"
                f"<td>{_esc(r.test_case.url_path)}</td>"
                f"<td>{r.test_case.expected_status}</td>"
                f"<td>{r.status_code}</td>"
                f"<td>{r.elapsed_ms:.0f} ms</td>"
                f'<td class="{cls}">{status}</td>'
                f"<td>{warn_text}{extra}</td>"
                f"</tr>\n"
            )

        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>API Test Report - {_esc(now)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 2rem; background: #f8f9fa; }}
h1 {{ color: #333; }}
.summary {{ font-size: 1.2rem; margin-bottom: 1rem; }}
.summary .pass {{ color: #28a745; font-weight: bold; }}
.summary .fail {{ color: #dc3545; font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; background: #fff; }}
th, td {{ border: 1px solid #dee2e6; padding: 0.5rem 0.75rem; text-align: left; }}
th {{ background: #343a40; color: #fff; }}
td.pass {{ color: #28a745; font-weight: bold; }}
td.fail {{ color: #dc3545; font-weight: bold; }}
td.warn {{ color: #e67e22; font-weight: bold; }}
tr.row-fail {{ background: #fff5f5; }}
tr.row-warn {{ background: #fff8e1; }}
.filter-bar {{ margin-bottom: 1rem; }}
.filter-bar button {{ padding: 0.4rem 1rem; margin-right: 0.5rem; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; background: #fff; }}
.filter-bar button.active {{ background: #343a40; color: #fff; border-color: #343a40; }}
.bar-chart {{ background: #fff; padding: 1rem; border: 1px solid #dee2e6; margin-bottom: 2rem; }}
.bar-row {{ display: flex; align-items: center; margin: 0.25rem 0; font-size: 0.85rem; }}
.bar-label {{ width: 280px; text-align: right; padding-right: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.bar-bg {{ flex: 1; height: 20px; background: #e9ecef; position: relative; }}
.bar-fill {{ height: 100%; background: #007bff; }}
.bar-value {{ position: absolute; right: 4px; top: 1px; font-size: 0.75rem; color: #333; }}
</style>
</head>
<body>
<h1>API Test Report</h1>
<p class="summary">
  Date: {_esc(now)} &nbsp;|&nbsp;
  Total: {total} &nbsp;|&nbsp;
  <span class="pass">Passed: {passed}</span> &nbsp;|&nbsp;
  <span class="fail">Failed: {failed}</span>
</p>

<h2>Pattern Summary</h2>
<table>
<tr><th>Pattern</th><th>Total</th><th>Passed</th><th>Failed</th><th>Status</th></tr>
{pattern_rows}</table>

<h2>Test Results</h2>
<div class="filter-bar">
  <button class="active" onclick="filterRows('all')">All</button>
  <button onclick="filterRows('fail')">FAIL only</button>
  <button onclick="filterRows('warn')">WARN only</button>
</div>
<table id="results-table">
<tr><th>Name</th><th>Pattern</th><th>Method</th><th>URL Path</th><th>Expected</th><th>Actual</th><th>Time</th><th>Status</th><th>Warnings</th></tr>
{test_rows}</table>

<h2>Response Times</h2>
<div class="bar-chart">
{self._generate_bar_chart(results)}
</div>

<script>
function filterRows(mode) {{
  var rows = document.querySelectorAll('#results-table tr');
  var btns = document.querySelectorAll('.filter-bar button');
  btns.forEach(function(b) {{ b.classList.remove('active'); }});
  event.target.classList.add('active');
  for (var i = 1; i < rows.length; i++) {{
    if (mode === 'all') {{
      rows[i].style.display = '';
    }} else {{
      rows[i].style.display = rows[i].classList.contains('row-' + mode) ? '' : 'none';
    }}
  }}
}}
</script>
</body>
</html>
"""

        html_path = report_dir / "report.html"
        with open(html_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)

        return str(html_path)

    @staticmethod
    def _generate_bar_chart(results: list[TestResult]) -> str:
        """応答時間の水平バーチャート HTML を生成."""
        # 200 OK 期待のテストのみ（no_auth 除外）
        chart_results = [
            r for r in results
            if r.test_case.expected_status == 200 and r.elapsed_ms > 0
        ]
        if not chart_results:
            return '<p style="color:#999">No response time data</p>'

        max_ms = max(r.elapsed_ms for r in chart_results)
        if max_ms == 0:
            max_ms = 1

        rows = ""
        for r in sorted(chart_results, key=lambda x: -x.elapsed_ms):
            pct = (r.elapsed_ms / max_ms) * 100
            color = "#dc3545" if r.elapsed_ms > 1000 else "#e67e22" if r.elapsed_ms > 500 else "#007bff"
            rows += (
                f'<div class="bar-row">'
                f'<div class="bar-label">{_esc(r.test_case.name)}</div>'
                f'<div class="bar-bg">'
                f'<div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div>'
                f'<span class="bar-value">{r.elapsed_ms:.0f}ms</span>'
                f'</div></div>\n'
            )

        return rows


def _esc(text: str) -> str:
    """HTML エスケープ."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
