"""レスポンス JSON の差分検知."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiffChange:
    """個別の変更."""

    kind: str       # "added", "removed", "type_changed"
    path: str       # "groups[0].new_field" etc.
    detail: str     # 説明


@dataclass
class DiffResult:
    """1つのレスポンスファイルの差分結果."""

    name: str
    changes: list[DiffChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0


def _get_type_name(value: object) -> str:
    """JSON の値の型名を返す."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _compare_schema(prev: object, curr: object, path: str = "") -> list[DiffChange]:
    """2つの JSON 値のスキーマ（キー構造・型）を再帰的に比較."""
    changes: list[DiffChange] = []

    prev_type = _get_type_name(prev)
    curr_type = _get_type_name(curr)

    # 型変更
    if prev_type != curr_type:
        changes.append(DiffChange(
            kind="type_changed",
            path=path or "(root)",
            detail=f"{prev_type} -> {curr_type}",
        ))
        return changes

    # dict: キーの追加・削除 + 再帰比較
    if isinstance(prev, dict) and isinstance(curr, dict):
        prev_keys = set(prev.keys())
        curr_keys = set(curr.keys())

        for key in sorted(curr_keys - prev_keys):
            child_path = f"{path}.{key}" if path else key
            changes.append(DiffChange(
                kind="added",
                path=child_path,
                detail=f"type={_get_type_name(curr[key])}",
            ))

        for key in sorted(prev_keys - curr_keys):
            child_path = f"{path}.{key}" if path else key
            changes.append(DiffChange(
                kind="removed",
                path=child_path,
                detail=f"was type={_get_type_name(prev[key])}",
            ))

        for key in sorted(prev_keys & curr_keys):
            child_path = f"{path}.{key}" if path else key
            changes.extend(_compare_schema(prev[key], curr[key], child_path))

    # list: 最初の要素同士で構造比較
    elif isinstance(prev, list) and isinstance(curr, list):
        if prev and curr:
            array_path = f"{path}[0]" if path else "[0]"
            changes.extend(_compare_schema(prev[0], curr[0], array_path))

    return changes


class ResponseDiffer:
    """2回のテスト実行のレスポンスを比較."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

    def get_timestamps(self) -> list[str]:
        """利用可能なタイムスタンプ一覧を返す（降順）."""
        if not self.results_dir.exists():
            return []
        return sorted(
            [d.name for d in self.results_dir.iterdir()
             if d.is_dir() and d.name.isdigit()],
            reverse=True,
        )

    def compare_responses(self, prev_dir: Path, curr_dir: Path) -> list[DiffResult]:
        """2つのタイムスタンプディレクトリのレスポンスを比較."""
        results: list[DiffResult] = []

        # JSON ファイル一覧（report.json, report.csv 除外）
        prev_files = {
            f.stem: f for f in prev_dir.glob("*.json")
            if f.name != "report.json"
        }
        curr_files = {
            f.stem: f for f in curr_dir.glob("*.json")
            if f.name != "report.json"
        }

        # no_auth テストは 401 レスポンスなので除外
        prev_files = {k: v for k, v in prev_files.items() if "no-auth" not in k}
        curr_files = {k: v for k, v in curr_files.items() if "no-auth" not in k}

        all_names = sorted(set(prev_files.keys()) | set(curr_files.keys()))

        for name in all_names:
            diff = DiffResult(name=name)

            if name not in prev_files:
                diff.changes.append(DiffChange(
                    kind="added",
                    path="(file)",
                    detail="new response file",
                ))
                results.append(diff)
                continue

            if name not in curr_files:
                diff.changes.append(DiffChange(
                    kind="removed",
                    path="(file)",
                    detail="response file removed",
                ))
                results.append(diff)
                continue

            # 両方存在する場合はスキーマ比較
            try:
                with open(prev_files[name], encoding="utf-8") as f:
                    prev_data = json.load(f)
                with open(curr_files[name], encoding="utf-8") as f:
                    curr_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            changes = _compare_schema(prev_data, curr_data)
            diff.changes = changes

            if diff.has_changes:
                results.append(diff)

        return results

    def compare_latest(self, n: int = 2) -> list[DiffResult] | None:
        """最新 n 回分のうち直近2回を比較."""
        timestamps = self.get_timestamps()
        if len(timestamps) < n:
            return None

        prev_dir = self.results_dir / timestamps[1]
        curr_dir = self.results_dir / timestamps[0]
        return self.compare_responses(prev_dir, curr_dir)
