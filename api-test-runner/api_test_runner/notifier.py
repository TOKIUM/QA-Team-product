"""Slack webhook 通知."""

from __future__ import annotations

import json
import urllib.request
from collections import Counter

from .models import TestResult


class SlackNotifier:
    """Slack Incoming Webhook による結果通知."""

    def build_payload(self, results: list[TestResult]) -> dict:
        """通知用の Slack メッセージペイロードを構築."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        # パターン別集計
        by_pattern: Counter[str] = Counter()
        fail_by_pattern: Counter[str] = Counter()
        for r in results:
            pat = r.test_case.pattern
            by_pattern[pat] += 1
            if not r.passed:
                fail_by_pattern[pat] += 1

        # スキーマ警告集計
        warn_count = sum(len(r.schema_warnings) for r in results)

        icon = ":white_check_mark:" if failed == 0 else ":x:"
        title = f"{icon} API Test Results: {passed}/{total} passed"
        if failed > 0:
            title += f" ({failed} failed)"
        if warn_count > 0:
            title += f" :warning: {warn_count} warnings"

        lines = [title, ""]

        # パターン別
        lines.append("*Pattern Summary:*")
        for pat in sorted(by_pattern.keys()):
            t = by_pattern[pat]
            f = fail_by_pattern.get(pat, 0)
            status = "ALL PASS" if f == 0 else f"{f} FAIL"
            lines.append(f"  {pat}: {t - f}/{t} ({status})")

        # スキーマ警告一覧
        warn_tests = [r for r in results if r.schema_warnings]
        if warn_tests:
            lines.append("")
            lines.append("*Schema Warnings:*")
            for r in warn_tests:
                for w in r.schema_warnings:
                    lines.append(f"  - {r.test_case.name}: {w}")

        # FAIL テスト一覧
        fail_tests = [r for r in results if not r.passed]
        if fail_tests:
            lines.append("")
            lines.append("*Failed Tests:*")
            for r in fail_tests:
                tc = r.test_case
                lines.append(
                    f"  - {tc.name}: expected {tc.expected_status}, "
                    f"got {r.status_code}")

        return {"text": "\n".join(lines)}

    def notify(self, results: list[TestResult], webhook_url: str) -> bool:
        """Slack webhook に結果を送信."""
        if not webhook_url:
            return False

        payload = self.build_payload(results)
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False
