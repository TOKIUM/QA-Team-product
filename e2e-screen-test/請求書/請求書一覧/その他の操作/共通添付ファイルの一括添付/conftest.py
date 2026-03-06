"""
共通添付ファイルの一括添付 - pytest共通fixture

pytest-playwright の page fixture をオーバーライドし、
ログイン済みの状態でテスト関数に渡す。
"""

import os
import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-staging.keihi.com"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_env() -> dict:
    env_path = os.path.normpath(
        os.path.join(_SCRIPT_DIR, "..", "..", "..", "..", "ログイン", ".env")
    )
    vals = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


@pytest.fixture
def page(page: Page) -> Page:
    """ログイン済みの page を返す"""
    env = _load_env()
    email = env.get("TEST_EMAIL") or os.environ.get("TEST_EMAIL", "")
    password = env.get("TEST_PASSWORD") or os.environ.get("TEST_PASSWORD", "")

    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
    page.get_by_label("メールアドレス").fill(email)
    page.get_by_label("パスワード").fill(password)
    page.get_by_role("button", name="ログイン", exact=True).click()

    expect(page).to_have_url(re.compile(r"/invoices"), timeout=30000)

    return page
