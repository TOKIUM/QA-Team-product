"""Preflight check — テスト実行前の接続・認証・設定値ライブ検証."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .csv_parser import parse_directory


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

@dataclass
class CheckItem:
    """個別チェック結果."""

    label: str          # "Base URL reachable"
    status: str         # "PASS" | "FAIL" | "WARN"
    detail: str = ""    # "https://dev.keihi.com/api/v2 -> 200"


@dataclass
class CheckSection:
    """セクション（Connectivity, CSV Specs, ...）."""

    title: str
    items: list[CheckItem] = field(default_factory=list)


@dataclass
class PreflightResult:
    """全チェック結果."""

    sections: list[CheckSection] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(len(s.items) for s in self.sections)

    @property
    def passed(self) -> int:
        return sum(
            1 for s in self.sections for i in s.items if i.status == "PASS"
        )

    @property
    def failed(self) -> int:
        return sum(
            1 for s in self.sections for i in s.items if i.status == "FAIL"
        )

    @property
    def warned(self) -> int:
        return sum(
            1 for s in self.sections for i in s.items if i.status == "WARN"
        )

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        """JSON シリアライズ用."""
        return {
            "ok": self.ok,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "warned": self.warned,
            "sections": [
                {
                    "title": s.title,
                    "items": [
                        {
                            "label": i.label,
                            "status": i.status,
                            "detail": i.detail,
                        }
                        for i in s.items
                    ],
                }
                for s in self.sections
            ],
        }


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

class PreflightChecker:
    """4 セクションのプリフライトチェックを実行する."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config: dict,
        csv_dir: Path,
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.config = config
        self.csv_dir = csv_dir
        self.timeout = timeout
        self._specs = None  # lazy cache

    # -- public ------------------------------------------------------------

    def run_all(self) -> PreflightResult:
        result = PreflightResult()
        result.sections.append(self.check_connectivity())
        result.sections.append(self.check_csv_specs())
        result.sections.append(self.check_search_overrides())
        result.sections.append(self.check_custom_tests())
        return result

    # -- 1. Connectivity ---------------------------------------------------

    def check_connectivity(self) -> CheckSection:
        section = CheckSection(title="Connectivity")

        # Base URL reachable
        try:
            resp = requests.get(self.base_url, timeout=self.timeout)
            section.items.append(CheckItem(
                label="Base URL reachable",
                status="PASS",
                detail=f"{self.base_url} -> {resp.status_code}",
            ))
        except requests.RequestException as e:
            section.items.append(CheckItem(
                label="Base URL reachable",
                status="FAIL",
                detail=str(e),
            ))

        # Auth token valid — GET first spec URL with ?limit=1
        specs = self._load_specs()
        if specs:
            test_url_path = specs[0].url.lstrip("/")
        else:
            test_url_path = "members.json"

        url = f"{self.base_url}/{test_url_path}"
        try:
            resp = requests.get(
                url,
                params={"limit": 1},
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                section.items.append(CheckItem(
                    label="Auth token valid",
                    status="PASS",
                    detail=f"GET {test_url_path}?limit=1 -> {resp.status_code}",
                ))
            elif resp.status_code == 401:
                section.items.append(CheckItem(
                    label="Auth token valid",
                    status="FAIL",
                    detail=f"GET {test_url_path}?limit=1 -> 401 Unauthorized",
                ))
            else:
                section.items.append(CheckItem(
                    label="Auth token valid",
                    status="WARN",
                    detail=f"GET {test_url_path}?limit=1 -> {resp.status_code}",
                ))
        except requests.RequestException as e:
            section.items.append(CheckItem(
                label="Auth token valid",
                status="FAIL",
                detail=str(e),
            ))

        return section

    # -- 2. CSV Specs ------------------------------------------------------

    def check_csv_specs(self) -> CheckSection:
        section = CheckSection(title="CSV Specs")
        specs = self._load_specs()

        if not specs:
            section.items.append(CheckItem(
                label="API specs found",
                status="FAIL" if self.csv_dir.exists() else "WARN",
                detail=f"No specs in {self.csv_dir}",
            ))
            return section

        methods = Counter(s.method for s in specs)
        method_str = ", ".join(f"{m}: {c}" for m, c in sorted(methods.items()))
        section.items.append(CheckItem(
            label="API specs found",
            status="PASS",
            detail=f"{len(specs)} specs ({method_str})",
        ))

        # URL / method 欠損チェック
        missing = [s for s in specs if not s.url or not s.method]
        if missing:
            names = ", ".join(s.name for s in missing)
            section.items.append(CheckItem(
                label="Specs completeness",
                status="FAIL",
                detail=f"Missing URL/method: {names}",
            ))

        return section

    # -- 3. Search Overrides -----------------------------------------------

    def check_search_overrides(self) -> CheckSection:
        section = CheckSection(title="Search Overrides")
        overrides = (
            self.config.get("test", {}).get("search", {}).get("overrides", {})
        )

        if not overrides:
            section.items.append(CheckItem(
                label="(no overrides configured)",
                status="PASS",
                detail="Nothing to check",
            ))
            return section

        specs = self._load_specs()
        # param_name → spec のマッピングを構築
        param_spec_map: dict[str, str] = {}
        for spec in specs:
            if spec.method != "GET":
                continue
            for p in spec.params:
                param_spec_map[p.param_name] = spec.url.lstrip("/")

        for param_name, value in overrides.items():
            url_path = param_spec_map.get(param_name)
            if not url_path:
                # パラメータに対応する GET spec が見つからない → WARN
                section.items.append(CheckItem(
                    label=f"{param_name} = \"{value}\"",
                    status="WARN",
                    detail=f"No GET spec with param '{param_name}'",
                ))
                continue

            url = f"{self.base_url}/{url_path}"
            try:
                resp = requests.get(
                    url,
                    params={param_name: value, "limit": 1},
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    section.items.append(CheckItem(
                        label=f"{param_name} = \"{value}\"",
                        status="PASS",
                        detail=(
                            f"GET {url_path}?{param_name}={value}&limit=1"
                            f" -> {resp.status_code}"
                        ),
                    ))
                else:
                    section.items.append(CheckItem(
                        label=f"{param_name} = \"{value}\"",
                        status="FAIL",
                        detail=(
                            f"GET {url_path}?{param_name}={value}&limit=1"
                            f" -> {resp.status_code}"
                        ),
                    ))
            except requests.RequestException as e:
                section.items.append(CheckItem(
                    label=f"{param_name} = \"{value}\"",
                    status="FAIL",
                    detail=str(e),
                ))

        return section

    # -- 4. Custom Tests Endpoints -----------------------------------------

    def check_custom_tests(self) -> CheckSection:
        section = CheckSection(title="Custom Tests Endpoints")
        custom_tests = self.config.get("custom_tests", [])

        if not custom_tests:
            section.items.append(CheckItem(
                label="(no custom tests configured)",
                status="PASS",
                detail="Nothing to check",
            ))
            return section

        # 同じ url_path は一度だけチェック
        checked: set[str] = set()
        for ct in custom_tests:
            url_path = ct.get("url_path", "")
            if not url_path or url_path in checked:
                continue
            checked.add(url_path)

            method = ct.get("method", "GET")
            use_auth = ct.get("use_auth", True)
            expected = ct.get("expected_status", 200)

            url = f"{self.base_url}/{url_path}"
            headers = {"Accept": "application/json"}
            if use_auth:
                headers["Authorization"] = f"Bearer {self.api_key}"

            try:
                # 安全のため常に GET（POST/PUT/DELETE でもデータ変更しない）
                resp = requests.get(url, headers=headers, timeout=self.timeout)
                label = f"{method} {url_path}"
                if resp.status_code == expected:
                    section.items.append(CheckItem(
                        label=label,
                        status="PASS",
                        detail=f"-> {resp.status_code} (expected {expected})",
                    ))
                else:
                    section.items.append(CheckItem(
                        label=label,
                        status="FAIL",
                        detail=(
                            f"-> {resp.status_code}"
                            f" (expected {expected})"
                        ),
                    ))
            except requests.RequestException as e:
                section.items.append(CheckItem(
                    label=f"{method} {url_path}",
                    status="FAIL",
                    detail=str(e),
                ))

        return section

    # -- internal ----------------------------------------------------------

    def _load_specs(self):
        if self._specs is None:
            if self.csv_dir.exists():
                self._specs = parse_directory(self.csv_dir)
            else:
                self._specs = []
        return self._specs


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_preflight_result(result: PreflightResult) -> None:
    """プリフライト結果をコンソール出力する."""
    print()
    print("========================================")
    print("  Preflight Check")
    print("========================================")
    print()

    for idx, section in enumerate(result.sections, 1):
        print(f"[{idx}/{len(result.sections)}] {section.title}")
        for item in section.items:
            tag = f"[{item.status}]"
            print(f"  {tag:6s} {item.label}")
            if item.detail:
                print(f"         {item.detail}")
        print()

    status = "OK" if result.ok else "FAILED"
    parts = []
    if result.passed:
        parts.append(f"{result.passed} passed")
    if result.failed:
        parts.append(f"{result.failed} failed")
    if result.warned:
        parts.append(f"{result.warned} warned")
    summary = ", ".join(parts)

    print("========================================")
    print(f"  Result: {summary} / {result.total} checks")
    print("========================================")
