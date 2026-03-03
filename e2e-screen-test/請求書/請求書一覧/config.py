"""請求書画面テスト 設定ファイル"""

import os
from pathlib import Path

# ディレクトリ
BASE_DIR = Path(__file__).parent
GENERATED_TESTS_DIR = BASE_DIR / "generated_tests"

# 対象URL
BASE_URL = "https://invoicing-staging.keihi.com"

# テスト用認証情報（環境変数から取得）
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass123!")

# Playwright
HEADLESS = True
DEFAULT_TIMEOUT = 15_000  # ms（一覧画面のロードが重いため少し長め）
VIEWPORT = {"width": 1280, "height": 720}
