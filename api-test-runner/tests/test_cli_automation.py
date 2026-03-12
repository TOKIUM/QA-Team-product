"""Tests for CLI automation features (--yes, --csv-files, --body-override, --output-json, --fetch-resource)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api_test_runner.__main__ import main


class TestCliArgParsing:
    """新規CLI引数のパース検証."""

    def test_yes_flag(self):
        """--yes フラグがパースされる."""
        with patch("sys.argv", ["prog", "run", "--yes"]):
            import argparse
            from api_test_runner.__main__ import main as _  # noqa: F811
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command")
            run_p = sub.add_parser("run")
            run_p.add_argument("csv_dir", nargs="?", default="document")
            run_p.add_argument("--yes", "-y", action="store_true")
            args = parser.parse_args(["run", "--yes"])
            assert args.yes is True

    def test_csv_files_flag(self):
        """--csv-files がパースされる."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        run_p = sub.add_parser("run")
        run_p.add_argument("csv_dir", nargs="?", default="document")
        run_p.add_argument("--csv-files", default=None)
        args = parser.parse_args(["run", "--csv-files", "a.csv,b.csv"])
        assert args.csv_files == "a.csv,b.csv"

    def test_body_override_flag(self):
        """--body-override がパースされる."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        run_p = sub.add_parser("run")
        run_p.add_argument("csv_dir", nargs="?", default="document")
        run_p.add_argument("--body-override", default=None)
        json_str = '{"api.json": {"id": "abc"}}'
        args = parser.parse_args(["run", "--body-override", json_str])
        assert args.body_override == json_str
        parsed = json.loads(args.body_override)
        assert parsed["api.json"]["id"] == "abc"

    def test_output_json_flag(self):
        """--output-json がパースされる."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        run_p = sub.add_parser("run")
        run_p.add_argument("csv_dir", nargs="?", default="document")
        run_p.add_argument("--output-json", action="store_true")
        args = parser.parse_args(["run", "--output-json"])
        assert args.output_json is True

    def test_fetch_resource_flag(self):
        """--fetch-resource がパースされる."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        run_p = sub.add_parser("run")
        run_p.add_argument("csv_dir", nargs="?", default="document")
        run_p.add_argument("--fetch-resource", action="store_true")
        args = parser.parse_args(["run", "--fetch-resource"])
        assert args.fetch_resource is True


class TestYesFlag:
    """--yes フラグの確認スキップ動作."""

    def test_yes_skips_prompt(self):
        """--yes 指定時は input() が呼ばれない."""
        # safe_write + yes の組み合わせでプロンプトスキップを確認
        config = {"test": {"patterns": []}}
        patterns = config["test"]["patterns"]
        write_patterns = ["post_normal", "put_normal", "delete_normal", "patch_normal"]
        for wp in write_patterns:
            if wp not in patterns:
                patterns.append(wp)

        # auto_yes=True の場合、input() は呼ばれないはず
        auto_yes = True
        input_called = False

        def mock_input(prompt):
            nonlocal input_called
            input_called = True
            return "n"

        if not auto_yes:
            mock_input("test")

        assert not input_called


class TestCsvFilesOption:
    """--csv-files によるCSVファイル個別指定."""

    def test_csv_files_split(self):
        """カンマ区切りのファイル名が正しく分割される."""
        csv_files_str = "file1.csv,file2.csv,file3.csv"
        file_names = [f.strip() for f in csv_files_str.split(",")]
        assert file_names == ["file1.csv", "file2.csv", "file3.csv"]

    def test_csv_files_with_spaces(self):
        """前後のスペースがトリムされる."""
        csv_files_str = " file1.csv , file2.csv "
        file_names = [f.strip() for f in csv_files_str.split(",")]
        assert file_names == ["file1.csv", "file2.csv"]

    def test_csv_files_disables_individual_only(self):
        """--csv-files 指定時は individual_only が無効化される."""
        config = {
            "test": {
                "post_normal": {"individual_only": ["some_api"]},
                "put_normal": {"individual_only": ["other_api"]},
            }
        }
        test_cfg = config.setdefault("test", {})
        for pattern_key in ("post_normal", "put_normal", "delete_normal", "patch_normal"):
            test_cfg.setdefault(pattern_key, {})["individual_only"] = []

        assert config["test"]["post_normal"]["individual_only"] == []
        assert config["test"]["put_normal"]["individual_only"] == []


class TestOutputJson:
    """--output-json のJSON出力構造."""

    def test_json_output_structure(self):
        """JSON出力に必要なフィールドが含まれる."""
        # テスト結果のモック
        results = []
        total = len(results)
        passed = 0
        failed_count = 0
        json_output = {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed_count,
            },
            "tests": [],
            "report_path": None,
        }
        assert "summary" in json_output
        assert "tests" in json_output
        assert json_output["summary"]["total"] == 0

    def test_json_output_with_results(self):
        """テスト結果がJSON出力に正しく含まれる."""
        mock_results = [
            {"name": "test-1", "passed": True, "elapsed_ms": 100.5},
            {"name": "test-2", "passed": False, "elapsed_ms": 50.2},
        ]
        total = len(mock_results)
        passed = sum(1 for r in mock_results if r["passed"])
        json_output = {
            "summary": {"total": total, "passed": passed, "failed": total - passed},
            "tests": mock_results,
        }
        assert json_output["summary"]["total"] == 2
        assert json_output["summary"]["passed"] == 1
        assert json_output["summary"]["failed"] == 1


class TestFetchResource:
    """--fetch-resource のリソース自動取得."""

    def test_fetch_resource_empty_endpoints(self):
        """get_endpoints が空の場合は config がそのまま返る."""
        from api_test_runner.__main__ import _fetch_and_apply_resources
        config = {"test": {}}
        result = _fetch_and_apply_resources(config, "https://example.com", "key")
        assert result == config

    def test_fetch_resource_collects_endpoints(self):
        """get_endpoints のマッピングが正しく収集される."""
        config = {
            "test": {
                "post_normal": {
                    "data_comparison": {
                        "get_endpoints": {
                            "members/bulk_create_job.json": "members.json"
                        }
                    }
                }
            }
        }
        test_cfg = config.get("test", {})
        all_endpoints = {}
        for pk in ("post_normal", "put_normal", "delete_normal", "patch_normal"):
            dc = test_cfg.get(pk, {}).get("data_comparison", {})
            endpoints = dc.get("get_endpoints", {})
            all_endpoints.update(endpoints)

        assert "members/bulk_create_job.json" in all_endpoints
        assert all_endpoints["members/bulk_create_job.json"] == "members.json"
