"""pytest-playwright 共通設定（WDL画面テスト用）- e2e_common委譲

WDL(Webダウンロードサイト)は独立ドメイン・独立認証。
メール+パスワードのシンプルなフォーム認証。
"""

import os
import sys
import time
import pytest
from playwright.sync_api import Page

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from e2e_common import ScreenConfig, setup_screen


WDL_BASE_URL = "https://invoicing-wdl-staging.keihi.com"


def _login_wdl(page, state):
    """WDL独自認証: メール+パスワードでログイン"""
    email = os.environ.get("WDL_EMAIL", "")
    password = os.environ.get("WDL_PW", "")

    if not email or not password:
        raise RuntimeError(
            "WDL認証情報が未設定です。ログイン/.env に WDL_EMAIL / WDL_PW を設定してください"
        )

    # ログインページへ
    page.goto(f"{WDL_BASE_URL}/login", wait_until="networkidle")
    time.sleep(2)

    # ログインフォーム入力
    email_input = page.locator('input[name="email"]').first
    pw_input = page.locator('input[type="password"]').first

    if email_input.is_visible() and pw_input.is_visible():
        email_input.fill(email)
        pw_input.fill(password)
        page.locator('button[type="submit"]').first.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")

    # WDLはSPA: ログイン後URLが/loginのままだがコンテンツは変わる
    # ナビゲーションリンクの表示でログイン成功を確認
    nav = page.locator('a[href="/invoices"]')
    nav.wait_for(state="visible", timeout=15000)

    # /invoices に明示的に遷移
    page.goto(f"{WDL_BASE_URL}/invoices", wait_until="networkidle")
    time.sleep(2)

    if page.locator("table").count() == 0:
        raise RuntimeError("WDLログイン失敗: 帳票テーブルが表示されない")


_state = setup_screen(ScreenConfig(
    screen_name="wdl",
    log_prefix="test_wdl",
    env_path_parts=["..", "ログイン"],
    base_url=WDL_BASE_URL,
    custom_login=_login_wdl,
), __file__)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return _state.browser_context_args(browser_context_args)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return _state.browser_type_launch_args(browser_type_launch_args)


@pytest.fixture
def logged_in_page(page: Page) -> Page:
    return _state.do_login(page)


def pytest_sessionstart(session):
    _state.on_session_start(session)


def pytest_sessionfinish(session, exitstatus):
    _state.on_session_finish(session, exitstatus)


def pytest_runtest_setup(item):
    _state.on_runtest_setup(item)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    _state.on_makereport(item, call, outcome)
