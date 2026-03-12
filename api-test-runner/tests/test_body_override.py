"""Tests for body_override module."""

from __future__ import annotations

from api_test_runner.body_override import merge_body_overrides


class TestMergeBodyOverrides:
    """merge_body_overrides のテスト."""

    def test_dict_merge(self):
        """dict同士のマージ（既存値 + 新規値）."""
        config = {
            "test": {
                "post_normal": {
                    "body_overrides": {
                        "api.json": {"name": "existing"}
                    }
                }
            }
        }
        overrides = {"api.json": {"id": "abc123"}}
        result = merge_body_overrides(config, overrides)
        bo = result["test"]["post_normal"]["body_overrides"]
        assert bo["api.json"] == {"name": "existing", "id": "abc123"}

    def test_list_inherits_from_existing_dict(self):
        """list形式: 既存dictのフィールドを各要素に継承."""
        config = {
            "test": {
                "post_normal": {
                    "body_overrides": {
                        "api.json": {"base_field": "value"}
                    }
                }
            }
        }
        overrides = {"api.json": [{"name": "a"}, {"name": "b"}]}
        result = merge_body_overrides(config, overrides)
        bo = result["test"]["post_normal"]["body_overrides"]
        assert bo["api.json"] == [
            {"base_field": "value", "name": "a"},
            {"base_field": "value", "name": "b"},
        ]

    def test_new_key_added(self):
        """存在しないキーの新規追加."""
        config = {"test": {"post_normal": {"body_overrides": {}}}}
        overrides = {"new_api.json": {"id": "123"}}
        result = merge_body_overrides(config, overrides)
        bo = result["test"]["post_normal"]["body_overrides"]
        assert bo["new_api.json"] == {"id": "123"}

    def test_applies_to_all_write_patterns(self):
        """4パターン全てにマージが適用される."""
        config = {"test": {}}
        overrides = {"api.json": {"id": "123"}}
        result = merge_body_overrides(config, overrides)
        for pattern in ("post_normal", "put_normal", "delete_normal", "patch_normal"):
            assert result["test"][pattern]["body_overrides"]["api.json"] == {"id": "123"}

    def test_scalar_override(self):
        """スカラー値による上書き."""
        config = {
            "test": {
                "post_normal": {
                    "body_overrides": {"api.json": "old_val"}
                }
            }
        }
        overrides = {"api.json": "new_val"}
        result = merge_body_overrides(config, overrides)
        assert result["test"]["post_normal"]["body_overrides"]["api.json"] == "new_val"

    def test_empty_config(self):
        """空のconfigでも動作する."""
        config = {}
        overrides = {"api.json": {"id": "abc"}}
        result = merge_body_overrides(config, overrides)
        assert result["test"]["post_normal"]["body_overrides"]["api.json"] == {"id": "abc"}

    def test_original_config_not_mutated(self):
        """元のconfigが変更されないこと."""
        config = {"test": {"post_normal": {"body_overrides": {"a": {"x": 1}}}}}
        overrides = {"a": {"y": 2}}
        merge_body_overrides(config, overrides)
        # 元のconfigは変更されていない
        assert config["test"]["post_normal"]["body_overrides"]["a"] == {"x": 1}
