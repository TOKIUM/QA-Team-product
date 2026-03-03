"""Tests for csv_parser module."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from api_test_runner.csv_parser import (
    extract_api_number_and_name,
    parse_csv,
    parse_directory,
    parse_single,
)


class TestExtractApiNumberAndName:
    def test_standard_filename(self):
        num, name = extract_api_number_and_name(
            "【TOKIUM】標準API仕様書（20260630） - 3部署取得API.csv"
        )
        assert num == "3"
        assert name == "部署取得API"

    def test_double_digit(self):
        num, name = extract_api_number_and_name(
            "【TOKIUM】標準API仕様書（20260630） - 12プロジェクト登録用バッチジョブ取得API.csv"
        )
        assert num == "12"
        assert name == "プロジェクト登録用バッチジョブ取得API"

    def test_no_match(self):
        num, name = extract_api_number_and_name("random_file.csv")
        assert num is None
        assert name is None

    def test_trailing_space_in_name(self):
        num, name = extract_api_number_and_name(
            "spec - 15プロジェクト更新用バッチジョブ登録API .csv"
        )
        assert num == "15"
        assert name == "プロジェクト更新用バッチジョブ登録API "


class TestParseCsv:
    @staticmethod
    def _write_csv(rows: list[list[str]], path: Path) -> None:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def test_extracts_url_and_method(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        rows = [
            ["■ URL"],
            ["/api/v2/groups.json"],
            ["■ HTTPメソッド"],
            ["GET"],
        ]
        self._write_csv(rows, csv_file)

        result = parse_csv(csv_file)
        assert result["url"] == "/api/v2/groups.json"
        assert result["method"] == "GET"
        assert result["resource"] == "groups"

    def test_extracts_params(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        # 28列以上のデータ行を作成
        header_row = [""] * 28
        header_row[3] = "項目名"
        header_row[10] = "パラメータ名"

        param_row = [""] * 28
        param_row[3] = "部署名"
        param_row[10] = "name"
        param_row[20] = "文字列"
        param_row[25] = ""
        param_row[27] = ""

        rows = [
            ["■ GETパラメータ"],
            header_row,
            param_row,
        ]
        self._write_csv(rows, csv_file)

        result = parse_csv(csv_file)
        assert len(result["params"]) == 1
        assert result["params"][0]["param_name"] == "name"
        assert result["params"][0]["item_name"] == "部署名"
        assert result["params"][0]["data_type"] == "文字列"

    def test_empty_file(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        self._write_csv([], csv_file)

        result = parse_csv(csv_file)
        assert result["url"] is None
        assert result["method"] is None
        assert result["params"] == []


class TestParseSingle:
    def test_returns_none_for_bad_filename(self, tmp_path):
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("", encoding="utf-8")
        assert parse_single(csv_file) is None

    def test_returns_none_for_missing_url(self, tmp_path):
        csv_file = tmp_path / "spec - 1テストAPI.csv"
        csv_file.write_text("", encoding="utf-8-sig")
        assert parse_single(csv_file) is None


class TestParseCsvPost:
    @staticmethod
    def _write_csv(rows, path):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def test_post_params_detected(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        param_row = [""] * 28
        param_row[3] = "従業員名"
        param_row[10] = "name"
        param_row[20] = "文字列"
        param_row[25] = "〇"
        rows = [
            ["■ URL"],
            ["/api/v2/members/bulk_create_job.json"],
            ["■ HTTPメソッド"],
            ["POST"],
            ["■ POSTパラメータ"],
            param_row,
        ]
        self._write_csv(rows, csv_file)
        result = parse_csv(csv_file)
        assert result["method"] == "POST"
        assert len(result["params"]) == 1
        assert result["params"][0]["param_name"] == "name"


class TestParseDirectoryMethods:
    @staticmethod
    def _write_api(path, url, method):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["■ URL"])
            writer.writerow([url])
            writer.writerow(["■ HTTPメソッド"])
            writer.writerow([method])

    def test_filter_by_methods(self, tmp_path):
        self._write_api(tmp_path / "spec - 1GetAPI.csv", "/api/v2/a.json", "GET")
        self._write_api(tmp_path / "spec - 2PostAPI.csv", "/api/v2/b.json", "POST")

        all_specs = parse_directory(tmp_path)
        assert len(all_specs) == 2

        get_only = parse_directory(tmp_path, methods=["GET"])
        assert len(get_only) == 1
        assert get_only[0].method == "GET"

        post_only = parse_directory(tmp_path, methods=["POST"])
        assert len(post_only) == 1
        assert post_only[0].method == "POST"
