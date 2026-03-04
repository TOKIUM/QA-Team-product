"""Tests for csv_parser extensions: max_value extraction and nested param parsing."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from api_test_runner.csv_parser import _extract_max_value, parse_csv, parse_single


class TestExtractMaxValue:
    def test_max_1000(self):
        assert _extract_max_value("最大1000") == 1000

    def test_max_in_sentence(self):
        assert _extract_max_value("デフォルトは10です。最大1000。") == 1000

    def test_max_suffix(self):
        assert _extract_max_value("最大100件") == 100

    def test_no_max(self):
        assert _extract_max_value("デフォルトは10です。") is None

    def test_max_without_digits(self):
        """「最大取得件数」のように数字がない場合はマッチしない."""
        assert _extract_max_value("最大取得件数です") is None

    def test_empty(self):
        assert _extract_max_value("") is None


class TestParseCsvMaxValue:
    @staticmethod
    def _write_csv(rows, path):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def test_max_value_extracted(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        param_row = [""] * 28
        param_row[3] = "取得件数"
        param_row[10] = "limit"
        param_row[20] = "整数値"
        param_row[25] = ""
        param_row[27] = "最大1000"

        rows = [
            ["■ URL"],
            ["/api/v2/members.json"],
            ["■ HTTPメソッド"],
            ["GET"],
            ["■ GETパラメータ"],
            param_row,
        ]
        self._write_csv(rows, csv_file)

        result = parse_csv(csv_file)
        assert len(result["params"]) == 1
        assert result["params"][0]["max_value"] == 1000

    def test_no_max_value(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        param_row = [""] * 28
        param_row[3] = "部署名"
        param_row[10] = "name"
        param_row[20] = "文字列"
        param_row[25] = ""
        param_row[27] = ""

        rows = [
            ["■ GETパラメータ"],
            param_row,
        ]
        self._write_csv(rows, csv_file)

        result = parse_csv(csv_file)
        assert result["params"][0]["max_value"] is None


class TestParseCsvNesting:
    @staticmethod
    def _write_csv(rows, path):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def _make_param_row(self, item_name, param_name, data_type="文字列",
                        required="", remarks=""):
        row = [""] * 28
        row[3] = item_name
        row[10] = param_name
        row[20] = data_type
        row[25] = required
        row[27] = remarks
        return row

    def _make_subsection_header(self, item_name):
        """サブセクション境界行（item_name あり、param_name なし）."""
        row = [""] * 28
        row[3] = item_name
        return row

    def _make_column_header(self):
        row = [""] * 28
        row[3] = "項目名"
        row[10] = "パラメータ名"
        return row

    def test_nested_array_with_children(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        rows = [
            ["■ URL"],
            ["/api/v2/members/bulk_create_job.json"],
            ["■ HTTPメソッド"],
            ["POST"],
            ["■ POSTパラメータ"],
            self._make_param_row("従業員情報", "members", "配列", "〇", "下記参照"),
            [""],  # 空行
            self._make_subsection_header("従業員情報"),
            self._make_column_header(),
            self._make_param_row("従業員名", "name", "文字列", "〇"),
            self._make_param_row("メールアドレス", "email", "文字列", "〇"),
        ]
        self._write_csv(rows, csv_file)

        result = parse_csv(csv_file)
        assert len(result["params"]) == 1  # トップレベルは members のみ
        members = result["params"][0]
        assert members["param_name"] == "members"
        assert len(members["children"]) == 2
        assert members["children"][0]["param_name"] == "name"
        assert members["children"][1]["param_name"] == "email"

    def test_multi_level_nesting(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        rows = [
            ["■ URL"],
            ["/api/v2/members/bulk_create_job.json"],
            ["■ HTTPメソッド"],
            ["POST"],
            ["■ POSTパラメータ"],
            self._make_param_row("従業員情報", "members", "配列", "〇", "下記参照"),
            [""],
            self._make_subsection_header("従業員情報"),
            self._make_column_header(),
            self._make_param_row("従業員名", "name", "文字列", "〇"),
            self._make_param_row("権限情報", "authorities", "オブジェクト", "〇", "下記参照"),
            [""],
            self._make_subsection_header("権限情報"),
            self._make_column_header(),
            self._make_param_row("管理者権限", "is_admin", "真偽値"),
        ]
        self._write_csv(rows, csv_file)

        result = parse_csv(csv_file)
        members = result["params"][0]
        assert len(members["children"]) == 2  # name, authorities

        authorities = members["children"][1]
        assert authorities["param_name"] == "authorities"
        assert len(authorities["children"]) == 1
        assert authorities["children"][0]["param_name"] == "is_admin"

    def test_get_api_no_nesting(self, tmp_path):
        """GET API はネスト構造なし."""
        csv_file = tmp_path / "test.csv"
        rows = [
            ["■ URL"],
            ["/api/v2/groups.json"],
            ["■ HTTPメソッド"],
            ["GET"],
            ["■ GETパラメータ"],
            self._make_param_row("部署名", "name", "文字列"),
            self._make_param_row("取得件数", "limit", "整数値", "", "最大1000"),
        ]
        self._write_csv(rows, csv_file)

        result = parse_csv(csv_file)
        assert len(result["params"]) == 2
        assert result["params"][0]["children"] == []
        assert result["params"][1]["children"] == []
        assert result["params"][1]["max_value"] == 1000


class TestParseSingleWithNewFields:
    @staticmethod
    def _write_csv(rows, path):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def test_parameter_has_max_value(self, tmp_path):
        csv_file = tmp_path / "spec - 2従業員取得API.csv"
        param_row = [""] * 28
        param_row[3] = "リミット"
        param_row[10] = "limit"
        param_row[20] = "整数値"
        param_row[27] = "最大1000"

        rows = [
            ["■ URL"],
            ["/api/v2/members.json"],
            ["■ HTTPメソッド"],
            ["GET"],
            ["■ GETパラメータ"],
            param_row,
        ]
        self._write_csv(rows, csv_file)

        spec = parse_single(csv_file)
        assert spec is not None
        assert spec.params[0].max_value == 1000
        assert spec.params[0].children == []

    def test_parameter_has_children(self, tmp_path):
        csv_file = tmp_path / "spec - 9従業員登録API.csv"

        def make_row(item, param, dtype="文字列", req="", rem=""):
            r = [""] * 28
            r[3] = item
            r[10] = param
            r[20] = dtype
            r[25] = req
            r[27] = rem
            return r

        def make_sub(item):
            r = [""] * 28
            r[3] = item
            return r

        rows = [
            ["■ URL"],
            ["/api/v2/members/bulk_create_job.json"],
            ["■ HTTPメソッド"],
            ["POST"],
            ["■ POSTパラメータ"],
            make_row("従業員情報", "members", "配列", "〇", "下記参照"),
            [""],
            make_sub("従業員情報"),
            make_row("項目名", "パラメータ名"),  # header
            make_row("従業員名", "name", "文字列", "〇"),
        ]
        self._write_csv(rows, csv_file)

        spec = parse_single(csv_file)
        assert spec is not None
        assert len(spec.params) == 1
        assert spec.params[0].param_name == "members"
        assert len(spec.params[0].children) == 1
        assert spec.params[0].children[0].param_name == "name"
