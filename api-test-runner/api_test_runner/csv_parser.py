"""CSV 仕様書の解析（generate-tests.py から移植）."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import ApiSpec, Parameter


def parse_csv(filepath: str | Path) -> dict:
    """Parse API specification CSV and extract endpoint info.

    tools/generate-tests.py の parse_csv() と同一ロジック。
    戻り値は dict（後で ApiSpec に変換する）。
    """
    api_info: dict = {
        "url": None,
        "method": None,
        "params": [],
        "resource": None,
    }

    section = None

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

                    if (
                        param_name
                        and param_name != "\u30d1\u30e9\u30e1\u30fc\u30bf\u540d"
                        and item_name != "\u9805\u76ee\u540d"
                    ):
                        data_type = row[20].strip() if len(row) > 20 else ""
                        required = row[25].strip() if len(row) > 25 else ""
                        remarks = row[27].strip() if len(row) > 27 else ""

                        api_info["params"].append({
                            "item_name": item_name,
                            "param_name": param_name,
                            "data_type": data_type,
                            "required": required,
                            "remarks": remarks,
                        })

    return api_info


def extract_api_number_and_name(filename: str) -> tuple[str | None, str | None]:
    """Extract API number and name from filename.

    Example: '... - 3部署取得API.csv' -> ('3', '部署取得API')
    """
    match = re.search(r"- (\d+)(.+?)\.csv$", filename)
    if match:
        return match.group(1), match.group(2)
    return None, None


def parse_single(filepath: str | Path) -> ApiSpec | None:
    """CSV ファイル1つを解析して ApiSpec を返す."""
    filepath = Path(filepath)
    api_number, api_name = extract_api_number_and_name(filepath.name)
    if api_number is None:
        return None

    raw = parse_csv(filepath)
    if not raw["url"] or not raw["method"]:
        return None

    params = [
        Parameter(
            item_name=p["item_name"],
            param_name=p["param_name"],
            data_type=p["data_type"],
            required=p["required"],
            remarks=p["remarks"],
        )
        for p in raw["params"]
    ]

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
