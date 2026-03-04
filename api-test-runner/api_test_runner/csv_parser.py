"""CSV 仕様書の解析（generate-tests.py から移植）."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import ApiSpec, Parameter


def _extract_max_value(remarks: str) -> int | None:
    """備考欄から「最大N」の上限値を抽出する.

    例: "最大1000" → 1000, "最大取得件数" → None（数字直後でないため非マッチ）
    """
    match = re.search(r"最大(\d+)", remarks)
    return int(match.group(1)) if match else None


def parse_csv(filepath: str | Path) -> dict:
    """Parse API specification CSV and extract endpoint info.

    tools/generate-tests.py の parse_csv() と同一ロジック。
    戻り値は dict（後で ApiSpec に変換する）。
    ネスト構造（配列/オブジェクト + 下記参照）を children として保持する。
    """
    api_info: dict = {
        "url": None,
        "method": None,
        "params": [],
        "resource": None,
    }

    section = None
    # ネスト構造: item_name → param dict のフラット参照
    all_params_by_item_name: dict[str, dict] = {}
    current_parent: dict | None = None

    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            first_cell = row[0].strip()

            # Detect section headers (■)
            if first_cell.startswith("\u25a0"):
                if "URL" in first_cell:
                    section = "url"
                elif "HTTP" in first_cell:
                    section = "method"
                elif "\u30d1\u30e9\u30e1\u30fc\u30bf" in first_cell:
                    section = "params"
                    current_parent = None
                else:
                    section = None
                continue

            # Parse section content
            if section == "url" and first_cell and first_cell.startswith("/"):
                api_info["url"] = first_cell
                match = re.search(r"/([^/]+)\.json$", first_cell)
                if match:
                    api_info["resource"] = match.group(1)
                section = None

            elif section == "method" and first_cell:
                api_info["method"] = first_cell.upper()
                section = None

            elif section == "params":
                if len(row) > 10:
                    param_name = row[10].strip() if len(row) > 10 else ""
                    item_name = row[3].strip() if len(row) > 3 else ""

                    # ヘッダー行をスキップ
                    if (
                        param_name == "\u30d1\u30e9\u30e1\u30fc\u30bf\u540d"
                        or item_name == "\u9805\u76ee\u540d"
                    ):
                        continue

                    if param_name:
                        # パラメータ行
                        data_type = row[20].strip() if len(row) > 20 else ""
                        required = row[25].strip() if len(row) > 25 else ""
                        remarks = row[27].strip() if len(row) > 27 else ""

                        param: dict = {
                            "item_name": item_name,
                            "param_name": param_name,
                            "data_type": data_type,
                            "required": required,
                            "remarks": remarks,
                            "max_value": _extract_max_value(remarks),
                            "children": [],
                        }

                        # 配列/オブジェクト型はネスト親の候補として登録
                        if data_type in ("\u914d\u5217", "\u30aa\u30d6\u30b8\u30a7\u30af\u30c8"):
                            all_params_by_item_name[item_name] = param

                        # 現在サブセクション内なら親の children に追加
                        if current_parent is not None:
                            current_parent["children"].append(param)
                        else:
                            api_info["params"].append(param)

                    elif item_name:
                        # サブセクション境界: item_name あり + param_name なし
                        if item_name in all_params_by_item_name:
                            current_parent = all_params_by_item_name[item_name]

    return api_info


def extract_api_number_and_name(filename: str) -> tuple[str | None, str | None]:
    """Extract API number and name from filename.

    Example: '... - 3部署取得API.csv' -> ('3', '部署取得API')
    """
    match = re.search(r"- (\d+)(.+?)\.csv$", filename)
    if match:
        return match.group(1), match.group(2)
    return None, None


def _dict_to_parameter(d: dict) -> Parameter:
    """param dict を Parameter dataclass に再帰変換."""
    children = [_dict_to_parameter(c) for c in d.get("children", [])]
    return Parameter(
        item_name=d["item_name"],
        param_name=d["param_name"],
        data_type=d["data_type"],
        required=d["required"],
        remarks=d["remarks"],
        max_value=d.get("max_value"),
        children=children,
    )


def parse_single(filepath: str | Path) -> ApiSpec | None:
    """CSV ファイル1つを解析して ApiSpec を返す."""
    filepath = Path(filepath)
    api_number, api_name = extract_api_number_and_name(filepath.name)
    if api_number is None:
        return None

    raw = parse_csv(filepath)
    if not raw["url"] or not raw["method"]:
        return None

    params = [_dict_to_parameter(p) for p in raw["params"]]

    return ApiSpec(
        number=api_number,
        name=api_name,
        url=raw["url"],
        method=raw["method"],
        resource=raw["resource"] or "",
        params=params,
    )


def parse_directory(
    csv_dir: str | Path, methods: list[str] | None = None,
) -> list[ApiSpec]:
    """ディレクトリ内の全 CSV を解析して ApiSpec リストを返す.

    Args:
        csv_dir: CSV ファイルのあるディレクトリ
        methods: 対象メソッド (例: ["GET", "POST"])。None なら全メソッド。
    """
    csv_dir = Path(csv_dir)
    specs: list[ApiSpec] = []

    for csv_file in sorted(csv_dir.glob("*.csv")):
        spec = parse_single(csv_file)
        if spec:
            if methods is None or spec.method in methods:
                specs.append(spec)

    return specs
