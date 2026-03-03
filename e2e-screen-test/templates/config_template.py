"""{システム名}テスト 設定ファイル

方式A（pytest + conftest.py）で使用。
conftest_template.py と同じディレクトリに配置する。
"""

import os
from pathlib import Path

# ディレクトリ
BASE_DIR = Path(__file__).parent
GENERATED_TESTS_DIR = BASE_DIR / "generated_tests"

# 対象URL（対象システムに合わせて変更）
BASE_URL = "{BASE_URL}"  # 例: "https://staging.example.com"

# テスト用認証情報（環境変数から取得）
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass123!")

# Playwright設定
HEADLESS = True
DEFAULT_TIMEOUT = 15_000  # ms（ページロードが重い場合は増やす）
VIEWPORT = {"width": 1280, "height": 720}
