"""body_overrides マージ共通関数（CLI用）."""

from __future__ import annotations


_WRITE_PATTERNS = ("post_normal", "put_normal", "delete_normal", "patch_normal")


def merge_body_overrides(config: dict, body_overrides: dict) -> dict:
    """body_overrides を config の各 write pattern にマージする.

    4パターン (post/put/delete/patch) に同一のマージを適用:
    - list 形式: 既存 dict フィールドを各要素に継承
    - dict 形式: 既存 dict とマージ
    - その他: 上書き

    Args:
        config: 元の config dict（変更しない）
        body_overrides: API キー → 値の dict

    Returns:
        マージ済みの新しい config dict
    """
    for pattern_key in _WRITE_PATTERNS:
        existing = (config.get("test", {})
                    .get(pattern_key, {})
                    .get("body_overrides", {}))
        merged = dict(existing)
        for api_key, new_val in body_overrides.items():
            old_val = merged.get(api_key, {})
            if isinstance(new_val, list):
                # リスト形式: 既存dictのフィールドを各要素に継承
                if isinstance(old_val, dict):
                    enriched = []
                    for item in new_val:
                        enriched.append({**old_val, **item})
                    merged[api_key] = enriched
                else:
                    merged[api_key] = new_val
            elif isinstance(new_val, dict) and isinstance(old_val, dict):
                merged[api_key] = {**old_val, **new_val}
            else:
                merged[api_key] = new_val
        config = {
            **config,
            "test": {
                **config.get("test", {}),
                pattern_key: {
                    **config.get("test", {}).get(pattern_key, {}),
                    "body_overrides": merged,
                },
            },
        }
    return config
