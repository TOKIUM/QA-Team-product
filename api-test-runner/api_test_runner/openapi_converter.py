"""OpenAPI JSON/YAML → CSV 変換."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import yaml


class OpenApiConverter:
    """OpenAPI 仕様からテスト用 CSV を生成する."""

    def __init__(self, spec: dict):
        self.spec = spec

    @classmethod
    def from_file(cls, path: Path) -> OpenApiConverter:
        """JSON/YAML ファイルからインスタンス生成."""
        text = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            spec = yaml.safe_load(text)
        else:
            spec = json.loads(text)
        return cls(spec)

    def convert(self) -> list[dict]:
        """OpenAPI spec → CSV 行のリストに変換.

        Returns:
            各行は {番号, API名, URL, メソッド, リソース名,
                    項目名, パラメータ名, データ型, 必須, 備考} のdict。
        """
        rows: list[dict] = []
        paths = self.spec.get("paths", {})
        number = 1

        for path, path_item in paths.items():
            for method in ("get", "post", "put", "delete", "patch"):
                if method not in path_item:
                    continue
                operation = path_item[method]
                api_name = operation.get("summary", "") or operation.get(
                    "operationId", f"{method.upper()} {path}")
                resource = self._extract_resource(path)

                params = self._extract_parameters(operation, path_item)
                body_params = self._extract_request_body(operation)
                all_params = params + body_params

                if not all_params:
                    rows.append(self._make_row(
                        number, api_name, path, method.upper(), resource,
                        "", "", "", "", "",
                    ))
                else:
                    for p in all_params:
                        rows.append(self._make_row(
                            number, api_name, path, method.upper(), resource,
                            p["item_name"], p["param_name"], p["data_type"],
                            p["required"], p["remarks"],
                        ))
                number += 1

        return rows

    def to_csv(self, output: Path | io.StringIO | None = None) -> str:
        """CSV 文字列を生成（ファイルパス指定時は書き込みも行う）."""
        rows = self.convert()
        fieldnames = [
            "番号", "API名", "URL", "メソッド", "リソース名",
            "項目名", "パラメータ名", "データ型", "必須", "備考",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        csv_text = buf.getvalue()

        if isinstance(output, Path):
            output.write_text(csv_text, encoding="utf-8-sig")
        elif isinstance(output, io.StringIO):
            output.write(csv_text)

        return csv_text

    @staticmethod
    def _extract_resource(path: str) -> str:
        """パスからリソース名を推定."""
        parts = [p for p in path.strip("/").split("/")
                 if not p.startswith("{")]
        if parts:
            last = parts[-1]
            return last.replace(".json", "")
        return ""

    @staticmethod
    def _extract_parameters(operation: dict, path_item: dict) -> list[dict]:
        """parameters セクションからパラメータ情報を抽出."""
        params = []
        raw = operation.get("parameters", []) + path_item.get("parameters", [])
        seen: set[str] = set()

        for p in raw:
            name = p.get("name", "")
            if name in seen:
                continue
            seen.add(name)

            schema = p.get("schema", {})
            params.append({
                "item_name": p.get("description", name),
                "param_name": name,
                "data_type": OpenApiConverter._map_type(schema),
                "required": "〇" if p.get("required", False) else "",
                "remarks": OpenApiConverter._extract_remarks(schema),
            })
        return params

    @staticmethod
    def _extract_request_body(operation: dict) -> list[dict]:
        """requestBody から params を抽出."""
        body = operation.get("requestBody", {})
        content = body.get("content", {})
        json_schema = content.get("application/json", {}).get("schema", {})
        if not json_schema:
            return []

        required_fields = set(json_schema.get("required", []))
        properties = json_schema.get("properties", {})
        params = []

        for name, prop in properties.items():
            params.append({
                "item_name": prop.get("description", name),
                "param_name": name,
                "data_type": OpenApiConverter._map_type(prop),
                "required": "〇" if name in required_fields else "",
                "remarks": OpenApiConverter._extract_remarks(prop),
            })
        return params

    @staticmethod
    def _map_type(schema: dict) -> str:
        """OpenAPI type → CSV のデータ型."""
        t = schema.get("type", "")
        fmt = schema.get("format", "")
        mapping = {
            "integer": "整数",
            "number": "数値",
            "string": "文字列",
            "boolean": "真偽値",
            "array": "配列",
            "object": "オブジェクト",
        }
        base = mapping.get(t, t)
        if fmt == "date-time":
            base = "文字列"
        return base

    @staticmethod
    def _extract_remarks(schema: dict) -> str:
        """スキーマから備考を生成."""
        parts = []
        if "maximum" in schema:
            parts.append(f"最大{schema['maximum']}")
        if "minimum" in schema:
            parts.append(f"最小{schema['minimum']}")
        if "maxLength" in schema:
            parts.append(f"最大{schema['maxLength']}文字")
        if "enum" in schema:
            parts.append(f"選択肢: {', '.join(str(v) for v in schema['enum'])}")
        if "description" in schema:
            desc = schema["description"]
            if desc and not parts:
                parts.append(desc)
        return "; ".join(parts)

    @staticmethod
    def _make_row(
        number: int, api_name: str, url: str, method: str, resource: str,
        item_name: str, param_name: str, data_type: str,
        required: str, remarks: str,
    ) -> dict:
        return {
            "番号": str(number),
            "API名": api_name,
            "URL": url,
            "メソッド": method,
            "リソース名": resource,
            "項目名": item_name,
            "パラメータ名": param_name,
            "データ型": data_type,
            "必須": required,
            "備考": remarks,
        }
