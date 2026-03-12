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


def _extract_url(url_str: str) -> tuple[str, str | None, list[str]]:
    """URLからリソース名とパスパラメータを抽出する.

    Returns:
        (url, resource, path_params)
    """
    # 先頭 / がない場合は補完
    if not url_str.startswith("/"):
        url_str = "/" + url_str

    # パスパラメータ (:param) を抽出
    path_params = re.findall(r":([a-zA-Z_]\w*)", url_str)

    # リソース名抽出: .json 末尾 or パスパラメータを除いた最後のセグメント
    # まず .json で終わるものを試す
    match = re.search(r"/([^/:]+)\.json$", url_str)
    if match:
        resource = match.group(1)
    else:
        # .json がない場合: パスパラメータでないセグメントの末尾を使用
        segments = [s for s in url_str.split("/") if s and not s.startswith(":")]
        resource = segments[-1] if segments else None

    return url_str, resource, path_params


def parse_csv(filepath: str | Path) -> dict:
    """Parse API specification CSV and extract endpoint info.

    tools/generate-tests.py の parse_csv() と同一ロジック。
    戻り値は dict（後で ApiSpec に変換する）。
    ネスト構造（配列/オブジェクト + 下記参照）を children として保持する。
    2列目フォーマット（expansion 41-54等）にも対応。
    """
    api_info: dict = {
        "url": None,
        "method": None,
        "params": [],
        "resource": None,
        "path_params": [],
    }

    section = None
    # ネスト構造: item_name → param dict のフラット参照
    all_params_by_item_name: dict[str, dict] = {}
    current_parent: dict | None = None
    # パラメータ列マッピング（ヘッダー行から自動検出）
    col_param_name: int = 10
    col_item_name: int = 3
    col_detected: bool = False

    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            first_cell = row[0].strip()

            # Detect section headers (■)
            # ■ が1列目にない場合もセクションヘッダとして検知
            section_cell = first_cell
            if not section_cell.startswith("\u25a0") and len(row) > 1:
                cell1 = row[1].strip()
                if cell1.startswith("\u25a0"):
                    section_cell = cell1

            if section_cell.startswith("\u25a0"):
                if "URL" in section_cell:
                    section = "url"
                elif "HTTP" in section_cell:
                    section = "method"
                elif "\u30d1\u30e9\u30e1\u30fc\u30bf" in section_cell or "\u30ea\u30af\u30a8\u30b9\u30c8" in section_cell:
                    section = "params"
                    current_parent = None
                    col_detected = False
                elif "\u30ec\u30b9\u30dd\u30f3\u30b9" in section_cell:
                    section = None
                else:
                    section = None
                continue

            # Parse section content
            if section == "url":
                url_cell = None
                if first_cell and (first_cell.startswith("/") or first_cell.startswith("api/")):
                    url_cell = first_cell
                elif len(row) > 1:
                    cell1 = row[1].strip()
                    if cell1 and (cell1.startswith("/") or cell1.startswith("api/")):
                        url_cell = cell1
                if url_cell:
                    url, resource, path_params = _extract_url(url_cell)
                    api_info["url"] = url
                    api_info["resource"] = resource
                    api_info["path_params"] = path_params
                    section = None

            elif section == "method":
                method_cell = first_cell
                if not method_cell:
                    method_cell = row[1].strip() if len(row) > 1 else ""
                if method_cell and method_cell.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    api_info["method"] = method_cell.upper()
                    section = None

            elif section == "params":
                # ヘッダー行から列マッピングを自動検出
                if not col_detected:
                    for ci, cell in enumerate(row):
                        cell_s = cell.strip()
                        if cell_s == "\u30d1\u30e9\u30e1\u30fc\u30bf\u540d":
                            col_param_name = ci
                        elif cell_s == "\u9805\u76ee\u540d":
                            col_item_name = ci
                    # ヘッダー行自体をスキップ
                    if any(
                        cell.strip() in ("\u30d1\u30e9\u30e1\u30fc\u30bf\u540d", "\u9805\u76ee\u540d")
                        for cell in row
                    ):
                        col_detected = True
                        continue

                if len(row) > max(col_param_name, col_item_name):
                    param_name = row[col_param_name].strip() if len(row) > col_param_name else ""
                    item_name = row[col_item_name].strip() if len(row) > col_item_name else ""

                    # ヘッダー行をスキップ（念のため再チェック）
                    if (
                        param_name == "\u30d1\u30e9\u30e1\u30fc\u30bf\u540d"
                        or item_name == "\u9805\u76ee\u540d"
                    ):
                        continue

                    if param_name:
                        # パスパラメータ（:param 形式のURL内パラメータ）はスキップ
                        if param_name in api_info.get("path_params", []):
                            continue

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
        path_params=raw.get("path_params", []),
    )


def parse_directory(
    csv_dir: str | Path,
    methods: list[str] | None = None,
    recursive: bool = False,
) -> list[ApiSpec]:
    """ディレクトリ内の全 CSV を解析して ApiSpec リストを返す.

    Args:
        csv_dir: CSV ファイルのあるディレクトリ
        methods: 対象メソッド (例: ["GET", "POST"])。None なら全メソッド。
        recursive: True の場合サブディレクトリも再帰スキャン（archive は除外）。
    """
    csv_dir = Path(csv_dir)
    specs: list[ApiSpec] = []

    pattern = "**/*.csv" if recursive else "*.csv"
    for csv_file in sorted(csv_dir.glob(pattern)):
        # archive ディレクトリは除外
        if "archive" in csv_file.parts:
            continue
        spec = parse_single(csv_file)
        if spec:
            if methods is None or spec.method in methods:
                specs.append(spec)

    return specs
