"""
画面調査結果の差分検出モジュール

前回実行結果（_previous/）と今回結果を比較し、変更点を検出する。
- JSON構造比較: キーの追加/削除/値変更
- スクリーンショット比較: ピクセル差分（Pillow使用、>5%変化をフラグ）
"""

import json
from pathlib import Path
from typing import Any


def compare_json_files(current: Path, previous: Path) -> dict:
    """2つのJSONファイルを比較し、差分を返す"""
    if not previous.exists():
        return {"status": "new", "file": current.name, "detail": "前回データなし（初回実行）"}
    if not current.exists():
        return {"status": "deleted", "file": current.name, "detail": "今回データなし"}

    try:
        with open(current, encoding="utf-8") as f:
            curr_data = json.load(f)
        with open(previous, encoding="utf-8") as f:
            prev_data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"status": "error", "file": current.name, "detail": str(e)}

    diffs = _deep_diff(prev_data, curr_data, prefix="")
    if not diffs:
        return {"status": "unchanged", "file": current.name}
    return {"status": "changed", "file": current.name, "changes": diffs}


def _deep_diff(old: Any, new: Any, prefix: str) -> list[dict]:
    """再帰的にJSON構造を比較"""
    diffs = []
    path = prefix or "(root)"

    if type(old) != type(new):
        diffs.append({"path": path, "type": "type_changed",
                       "old_type": type(old).__name__, "new_type": type(new).__name__})
        return diffs

    if isinstance(old, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())
        for k in sorted(new_keys - old_keys):
            diffs.append({"path": f"{prefix}.{k}", "type": "key_added"})
        for k in sorted(old_keys - new_keys):
            diffs.append({"path": f"{prefix}.{k}", "type": "key_removed"})
        for k in sorted(old_keys & new_keys):
            diffs.extend(_deep_diff(old[k], new[k], f"{prefix}.{k}"))
    elif isinstance(old, list):
        if len(old) != len(new):
            diffs.append({"path": path, "type": "array_length_changed",
                           "old_length": len(old), "new_length": len(new)})
        for i in range(min(len(old), len(new))):
            diffs.extend(_deep_diff(old[i], new[i], f"{prefix}[{i}]"))
    else:
        if old != new:
            old_str = str(old)[:100]
            new_str = str(new)[:100]
            diffs.append({"path": path, "type": "value_changed",
                           "old": old_str, "new": new_str})
    return diffs


def compare_screenshots(current_dir: Path, previous_dir: Path, threshold: float = 0.05) -> list[dict]:
    """スクリーンショットのピクセル差分比較（Pillow使用）"""
    results = []

    if not current_dir.exists():
        return results
    if not previous_dir.exists():
        # 前回データなし - 全て新規
        for img in sorted(current_dir.rglob("*.png")):
            rel = img.relative_to(current_dir)
            results.append({"file": str(rel), "status": "new", "detail": "前回データなし"})
        return results

    try:
        from PIL import Image, ImageChops
        has_pillow = True
    except ImportError:
        has_pillow = False

    current_imgs = {p.relative_to(current_dir): p for p in current_dir.rglob("*.png")}
    previous_imgs = {p.relative_to(previous_dir): p for p in previous_dir.rglob("*.png")}

    all_keys = sorted(set(current_imgs.keys()) | set(previous_imgs.keys()))

    for rel in all_keys:
        if rel not in previous_imgs:
            results.append({"file": str(rel), "status": "new"})
        elif rel not in current_imgs:
            results.append({"file": str(rel), "status": "deleted"})
        elif has_pillow:
            try:
                curr_img = Image.open(current_imgs[rel]).convert("RGB")
                prev_img = Image.open(previous_imgs[rel]).convert("RGB")

                if curr_img.size != prev_img.size:
                    results.append({"file": str(rel), "status": "changed",
                                    "detail": f"サイズ変更: {prev_img.size} → {curr_img.size}"})
                    continue

                diff = ImageChops.difference(curr_img, prev_img)
                pixels = list(diff.getdata())
                total = len(pixels) * 255 * 3
                diff_sum = sum(sum(p) for p in pixels)
                diff_ratio = diff_sum / total if total > 0 else 0

                if diff_ratio > threshold:
                    results.append({
                        "file": str(rel), "status": "changed",
                        "diff_ratio": round(diff_ratio * 100, 2),
                        "detail": f"ピクセル差分: {diff_ratio*100:.1f}%"
                    })
            except Exception as e:
                results.append({"file": str(rel), "status": "error", "detail": str(e)})
        else:
            # Pillow なし - ファイルサイズ比較のみ
            curr_size = current_imgs[rel].stat().st_size
            prev_size = previous_imgs[rel].stat().st_size
            if curr_size != prev_size:
                results.append({"file": str(rel), "status": "changed",
                                "detail": f"ファイルサイズ変更: {prev_size} → {curr_size}B（Pillow未インストール）"})

    return results


def run_diff(investigation_dir: Path, previous_dir: Path) -> dict:
    """メインの差分検出処理"""
    report = {
        "json_diffs": [],
        "screenshot_diffs": [],
        "summary": {"total_json": 0, "changed_json": 0, "total_screenshots": 0, "changed_screenshots": 0}
    }

    # JSON差分
    for json_file in sorted(investigation_dir.glob("*.json")):
        prev_file = previous_dir / json_file.name
        diff = compare_json_files(json_file, prev_file)
        report["json_diffs"].append(diff)
        report["summary"]["total_json"] += 1
        if diff["status"] not in ("unchanged",):
            report["summary"]["changed_json"] += 1

    # スクリーンショット差分
    curr_ss = investigation_dir / "screenshots"
    prev_ss = previous_dir / "screenshots"
    ss_diffs = compare_screenshots(curr_ss, prev_ss)
    report["screenshot_diffs"] = ss_diffs
    report["summary"]["total_screenshots"] = len(ss_diffs)
    report["summary"]["changed_screenshots"] = len([d for d in ss_diffs if d["status"] != "unchanged"])

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="画面調査結果の差分検出")
    parser.add_argument("--current", default="screen_investigation", help="今回の調査結果ディレクトリ")
    parser.add_argument("--previous", default="screen_investigation/_previous", help="前回の調査結果ディレクトリ")
    args = parser.parse_args()

    base = Path(__file__).parent
    result = run_diff(base / args.current, base / args.previous)
    print(json.dumps(result, ensure_ascii=False, indent=2))
