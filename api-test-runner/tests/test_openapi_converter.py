"""Tests for OpenAPI → CSV converter."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from api_test_runner.openapi_converter import OpenApiConverter


@pytest.fixture
def simple_spec():
    return {
        "openapi": "3.0.0",
        "paths": {
            "/api/v2/groups.json": {
                "get": {
                    "summary": "部署取得API",
                    "parameters": [
                        {
                            "name": "name",
                            "in": "query",
                            "description": "部署名",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "取得件数",
                            "required": True,
                            "schema": {"type": "integer", "maximum": 1000},
                        },
                    ],
                },
            },
        },
    }


@pytest.fixture
def post_spec():
    return {
        "openapi": "3.0.0",
        "paths": {
            "/api/v2/members/bulk_create_job.json": {
                "post": {
                    "summary": "従業員登録API",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["members"],
                                    "properties": {
                                        "members": {
                                            "type": "array",
                                            "description": "従業員情報",
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }


class TestConvert:
    def test_get_endpoint(self, simple_spec):
        converter = OpenApiConverter(simple_spec)
        rows = converter.convert()
        assert len(rows) == 2
        assert rows[0]["API名"] == "部署取得API"
        assert rows[0]["メソッド"] == "GET"
        assert rows[0]["パラメータ名"] == "name"
        assert rows[0]["データ型"] == "文字列"
        assert rows[0]["必須"] == ""

    def test_required_and_max_value(self, simple_spec):
        converter = OpenApiConverter(simple_spec)
        rows = converter.convert()
        limit_row = rows[1]
        assert limit_row["パラメータ名"] == "limit"
        assert limit_row["必須"] == "〇"
        assert "最大1000" in limit_row["備考"]

    def test_post_with_request_body(self, post_spec):
        converter = OpenApiConverter(post_spec)
        rows = converter.convert()
        assert len(rows) == 1
        assert rows[0]["メソッド"] == "POST"
        assert rows[0]["パラメータ名"] == "members"
        assert rows[0]["データ型"] == "配列"
        assert rows[0]["必須"] == "〇"

    def test_resource_extraction(self):
        assert OpenApiConverter._extract_resource("/api/v2/groups.json") == "groups"
        assert OpenApiConverter._extract_resource("/api/v2/members/bulk_create_job.json") == "bulk_create_job"

    def test_type_mapping(self):
        assert OpenApiConverter._map_type({"type": "integer"}) == "整数"
        assert OpenApiConverter._map_type({"type": "string"}) == "文字列"
        assert OpenApiConverter._map_type({"type": "boolean"}) == "真偽値"
        assert OpenApiConverter._map_type({"type": "array"}) == "配列"
        assert OpenApiConverter._map_type({"type": "object"}) == "オブジェクト"

    def test_empty_spec(self):
        converter = OpenApiConverter({"openapi": "3.0.0", "paths": {}})
        rows = converter.convert()
        assert rows == []


class TestToCsv:
    def test_csv_output(self, simple_spec):
        converter = OpenApiConverter(simple_spec)
        csv_text = converter.to_csv()
        assert "番号" in csv_text
        assert "部署取得API" in csv_text
        assert "name" in csv_text
        assert "limit" in csv_text

    def test_roundtrip_file(self, simple_spec, tmp_path):
        """ファイル書き込み→読み込みのラウンドトリップ."""
        converter = OpenApiConverter(simple_spec)
        output = tmp_path / "test.csv"
        converter.to_csv(output)
        assert output.exists()
        content = output.read_text(encoding="utf-8-sig")
        assert "部署取得API" in content


class TestFromFile:
    def test_json_file(self, simple_spec, tmp_path):
        json_file = tmp_path / "spec.json"
        json_file.write_text(json.dumps(simple_spec), encoding="utf-8")
        converter = OpenApiConverter.from_file(json_file)
        rows = converter.convert()
        assert len(rows) == 2

    def test_yaml_file(self, simple_spec, tmp_path):
        import yaml
        yaml_file = tmp_path / "spec.yaml"
        yaml_file.write_text(yaml.dump(simple_spec), encoding="utf-8")
        converter = OpenApiConverter.from_file(yaml_file)
        rows = converter.convert()
        assert len(rows) == 2
