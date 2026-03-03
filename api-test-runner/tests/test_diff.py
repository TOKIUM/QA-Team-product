"""Tests for api_test_runner.diff."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api_test_runner.diff import (
    DiffChange,
    DiffResult,
    ResponseDiffer,
    _compare_schema,
    _get_type_name,
)


class TestGetTypeName:
    def test_null(self):
        assert _get_type_name(None) == "null"

    def test_bool(self):
        assert _get_type_name(True) == "bool"

    def test_int(self):
        assert _get_type_name(42) == "int"

    def test_float(self):
        assert _get_type_name(3.14) == "float"

    def test_str(self):
        assert _get_type_name("hello") == "str"

    def test_list(self):
        assert _get_type_name([1, 2]) == "array"

    def test_dict(self):
        assert _get_type_name({"a": 1}) == "object"


class TestCompareSchema:
    def test_no_diff(self):
        prev = {"id": 1, "name": "test"}
        curr = {"id": 2, "name": "other"}
        changes = _compare_schema(prev, curr)
        assert changes == []

    def test_key_added(self):
        prev = {"id": 1}
        curr = {"id": 1, "email": "a@b.com"}
        changes = _compare_schema(prev, curr)
        assert len(changes) == 1
        assert changes[0].kind == "added"
        assert changes[0].path == "email"

    def test_key_removed(self):
        prev = {"id": 1, "name": "test"}
        curr = {"id": 1}
        changes = _compare_schema(prev, curr)
        assert len(changes) == 1
        assert changes[0].kind == "removed"
        assert changes[0].path == "name"

    def test_type_changed(self):
        prev = {"id": 1, "count": 10}
        curr = {"id": 1, "count": "ten"}
        changes = _compare_schema(prev, curr)
        assert len(changes) == 1
        assert changes[0].kind == "type_changed"
        assert changes[0].path == "count"
        assert "int -> str" in changes[0].detail

    def test_nested_key_added(self):
        prev = {"data": {"id": 1}}
        curr = {"data": {"id": 1, "new_field": True}}
        changes = _compare_schema(prev, curr)
        assert len(changes) == 1
        assert changes[0].path == "data.new_field"

    def test_array_element_schema_change(self):
        prev = {"items": [{"id": 1, "name": "a"}]}
        curr = {"items": [{"id": 1, "name": "a", "status": "active"}]}
        changes = _compare_schema(prev, curr)
        assert len(changes) == 1
        assert changes[0].kind == "added"
        assert "items[0].status" in changes[0].path

    def test_root_type_changed(self):
        changes = _compare_schema({"a": 1}, [1, 2])
        assert len(changes) == 1
        assert changes[0].kind == "type_changed"
        assert changes[0].path == "(root)"

    def test_empty_arrays(self):
        changes = _compare_schema({"items": []}, {"items": []})
        assert changes == []

    def test_multiple_changes(self):
        prev = {"a": 1, "b": "hello", "c": True}
        curr = {"a": 1, "d": "new"}
        changes = _compare_schema(prev, curr)
        kinds = {c.kind for c in changes}
        assert "added" in kinds
        assert "removed" in kinds


class TestResponseDiffer:
    def test_compare_responses_key_added(self, tmp_path):
        prev_dir = tmp_path / "20260101120000"
        curr_dir = tmp_path / "20260101130000"
        prev_dir.mkdir()
        curr_dir.mkdir()

        prev_data = {"groups": [{"id": 1, "name": "A"}]}
        curr_data = {"groups": [{"id": 1, "name": "A", "code": "001"}]}

        (prev_dir / "get-groups-auth.json").write_text(
            json.dumps(prev_data), encoding="utf-8")
        (curr_dir / "get-groups-auth.json").write_text(
            json.dumps(curr_data), encoding="utf-8")

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_responses(prev_dir, curr_dir)
        assert len(results) == 1
        assert results[0].name == "get-groups-auth"
        assert any(c.kind == "added" for c in results[0].changes)

    def test_compare_responses_no_diff(self, tmp_path):
        prev_dir = tmp_path / "20260101120000"
        curr_dir = tmp_path / "20260101130000"
        prev_dir.mkdir()
        curr_dir.mkdir()

        data = {"groups": [{"id": 1}]}
        (prev_dir / "get-groups-auth.json").write_text(
            json.dumps(data), encoding="utf-8")
        (curr_dir / "get-groups-auth.json").write_text(
            json.dumps(data), encoding="utf-8")

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_responses(prev_dir, curr_dir)
        assert results == []

    def test_compare_responses_new_file(self, tmp_path):
        prev_dir = tmp_path / "20260101120000"
        curr_dir = tmp_path / "20260101130000"
        prev_dir.mkdir()
        curr_dir.mkdir()

        (curr_dir / "new-test.json").write_text(
            json.dumps({"data": 1}), encoding="utf-8")

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_responses(prev_dir, curr_dir)
        assert len(results) == 1
        assert results[0].changes[0].kind == "added"

    def test_compare_responses_removed_file(self, tmp_path):
        prev_dir = tmp_path / "20260101120000"
        curr_dir = tmp_path / "20260101130000"
        prev_dir.mkdir()
        curr_dir.mkdir()

        (prev_dir / "old-test.json").write_text(
            json.dumps({"data": 1}), encoding="utf-8")

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_responses(prev_dir, curr_dir)
        assert len(results) == 1
        assert results[0].changes[0].kind == "removed"

    def test_no_auth_excluded(self, tmp_path):
        prev_dir = tmp_path / "20260101120000"
        curr_dir = tmp_path / "20260101130000"
        prev_dir.mkdir()
        curr_dir.mkdir()

        (prev_dir / "get-groups-no-auth.json").write_text(
            json.dumps({"error": "Unauthorized"}), encoding="utf-8")
        (curr_dir / "get-groups-no-auth.json").write_text(
            json.dumps({"error": "Forbidden"}), encoding="utf-8")

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_responses(prev_dir, curr_dir)
        assert results == []

    def test_report_json_excluded(self, tmp_path):
        prev_dir = tmp_path / "20260101120000"
        curr_dir = tmp_path / "20260101130000"
        prev_dir.mkdir()
        curr_dir.mkdir()

        (prev_dir / "report.json").write_text(
            json.dumps({"summary": {}}), encoding="utf-8")
        (curr_dir / "report.json").write_text(
            json.dumps({"summary": {"new": 1}}), encoding="utf-8")

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_responses(prev_dir, curr_dir)
        assert results == []

    def test_compare_latest(self, tmp_path):
        dir1 = tmp_path / "20260101120000"
        dir2 = tmp_path / "20260101130000"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "test.json").write_text(
            json.dumps({"a": 1}), encoding="utf-8")
        (dir2 / "test.json").write_text(
            json.dumps({"a": 1, "b": 2}), encoding="utf-8")

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_latest()
        assert results is not None
        assert len(results) == 1

    def test_compare_latest_not_enough_runs(self, tmp_path):
        dir1 = tmp_path / "20260101120000"
        dir1.mkdir()

        differ = ResponseDiffer(tmp_path)
        results = differ.compare_latest()
        assert results is None

    def test_get_timestamps(self, tmp_path):
        (tmp_path / "20260101120000").mkdir()
        (tmp_path / "20260101130000").mkdir()
        (tmp_path / "latest.txt").write_text("test")

        differ = ResponseDiffer(tmp_path)
        stamps = differ.get_timestamps()
        assert stamps == ["20260101130000", "20260101120000"]
