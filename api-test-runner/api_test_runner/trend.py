"""パフォーマンストレンド分析."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrendEntry:
    """1回の実行における1テストの計測値."""

    timestamp: str       # "20260227140934"
    name: str            # "get-members"
    elapsed_ms: float    # 150.0
    passed: bool


@dataclass
class Degradation:
    """劣化検知結果."""

    name: str
    prev_ms: float
    curr_ms: float
    ratio: float         # curr / prev


class TrendAnalyzer:
    """過去の report.json を横断集計."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

    def load_runs(self, last_n: int = 10) -> list[dict]:
        """過去N回分の report.json を時系列順で読み込む.

        Returns:
            [{"timestamp": "20260227...", "summary": {...}, "tests": [...]}, ...]
        """
        run_dirs = sorted(
            [d for d in self.results_dir.iterdir()
             if d.is_dir() and d.name.isdigit()],
            key=lambda d: d.name,
        )

        # 最新N件
        run_dirs = run_dirs[-last_n:]

        runs: list[dict] = []
        for d in run_dirs:
            report_path = d / "report.json"
            if not report_path.exists():
                continue
            with open(report_path, encoding="utf-8") as f:
                data = json.load(f)
            data["timestamp"] = d.name
            runs.append(data)

        return runs

    def get_timeline(self, runs: list[dict]) -> dict[str, list[TrendEntry]]:
        """テスト名ごとの時系列データを構築.

        Returns:
            {"get-members": [TrendEntry(...), ...], ...}
        """
        timeline: dict[str, list[TrendEntry]] = {}

        for run in runs:
            ts = run["timestamp"]
            for test in run.get("tests", []):
                name = test["name"]
                if name not in timeline:
                    timeline[name] = []
                timeline[name].append(TrendEntry(
                    timestamp=ts,
                    name=name,
                    elapsed_ms=test.get("elapsed_ms", 0),
                    passed=test.get("passed", False),
                ))

        return timeline

    def detect_degradations(
        self, runs: list[dict], threshold: float = 2.0,
    ) -> list[Degradation]:
        """直近2回を比較し、応答時間が threshold 倍以上のテストを検出."""
        if len(runs) < 2:
            return []

        prev_run = runs[-2]
        curr_run = runs[-1]

        prev_times = {t["name"]: t["elapsed_ms"] for t in prev_run.get("tests", [])}
        degradations: list[Degradation] = []

        for test in curr_run.get("tests", []):
            name = test["name"]
            curr_ms = test.get("elapsed_ms", 0)
            prev_ms = prev_times.get(name)
            if prev_ms is None or prev_ms < 50:
                # 前回データなし or 50ms未満は誤差が大きいのでスキップ
                continue
            ratio = curr_ms / prev_ms
            if ratio >= threshold:
                degradations.append(Degradation(
                    name=name, prev_ms=prev_ms, curr_ms=curr_ms, ratio=ratio,
                ))

        return sorted(degradations, key=lambda d: -d.ratio)

    def print_trend(self, last_n: int = 10) -> None:
        """コンソールにトレンドサマリーを表示."""
        runs = self.load_runs(last_n)

        if not runs:
            print("No test runs found.")
            return

        print("========================================")
        print(f"  Performance Trend ({len(runs)} runs)")
        print("========================================")
        print()

        # タイムスタンプ一覧
        for run in runs:
            ts = run["timestamp"]
            s = run.get("summary", {})
            total = s.get("total", 0)
            passed = s.get("passed", 0)
            failed = s.get("failed", 0)
            display_ts = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:]}"
            status = "ALL PASS" if failed == 0 else f"{failed} FAIL"
            print(f"  {display_ts}  {passed}/{total} ({status})")

        print()

        # 劣化検知
        degradations = self.detect_degradations(runs)
        if degradations:
            print("  Degradations (>= 2x slower):")
            for d in degradations:
                print(f"    {d.name}: {d.prev_ms:.0f}ms -> {d.curr_ms:.0f}ms ({d.ratio:.1f}x)")
            print()
        else:
            print("  No performance degradations detected.")
            print()

        # API ごとの最新応答時間
        timeline = self.get_timeline(runs)
        print("  Latest response times:")
        pad = max((len(name) for name in timeline), default=0)
        for name in sorted(timeline.keys()):
            entries = timeline[name]
            latest = entries[-1]
            if len(entries) >= 2:
                prev = entries[-2]
                diff = latest.elapsed_ms - prev.elapsed_ms
                arrow = "+" if diff > 0 else ""
                print(f"    {name:<{pad}}  {latest.elapsed_ms:>7.0f}ms  ({arrow}{diff:.0f}ms)")
            else:
                print(f"    {name:<{pad}}  {latest.elapsed_ms:>7.0f}ms")

        print()
