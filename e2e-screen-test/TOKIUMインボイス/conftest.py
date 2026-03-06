"""pytest-playwright 共通設定（TOKIUMインボイス画面テスト用）- e2e_common委譲

tkti10テナント（dev.keihi.com）にth-02経由でth4ログイン→テナント切替。
"""

import os
import sys
import time
import pytest
from playwright.sync_api import Page

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from e2e_common import ScreenConfig, setup_screen


def _login_tkti10(page, state):
    """th-02サブドメイン経由でth4ログイン→tkti10テナントに切替"""
    subdomain = os.environ.get("TOKIUM_ID_SUBDOMAIN", "th-02")
    th3_email = os.environ.get("TOKIUM_ID_EMAIL", "")
    th4_email = th3_email.replace("+th3", "+th4")
    password = os.environ.get("TOKIUM_ID_PASSWORD", "")

    # 1. サブドメイン入力→th-02ログインページへ
    page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
    time.sleep(2)

    btn = page.locator('button:has-text("サブドメインを入力")')
    if btn.count() > 0:
        btn.click()
        page.wait_for_url("**/subdomains/input**", timeout=10000)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

    page.locator('input[placeholder="サブドメイン"]').click()
    time.sleep(0.5)
    page.keyboard.press("Control+a")
    page.keyboard.type(subdomain, delay=50)
    time.sleep(1)
    page.locator('button:has-text("送信")').click()
    time.sleep(3)
    try:
        page.wait_for_url(f"**{subdomain}**", timeout=15000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # 2. th4アカウントでログイン
    email_input = page.query_selector('input[type="email"]')
    pw_input = page.query_selector('input[type="password"]')
    if email_input and pw_input:
        page.fill('input[type="email"]', th4_email)
        page.fill('input[type="password"]', password)
        login_btn = (page.query_selector('#sign_in_form button[type="button"]')
                     or page.query_selector('button[type="submit"]'))
        if login_btn:
            login_btn.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")

    # ログイン確認
    current_base = "/".join(page.url.split("/")[:3])
    page.goto(current_base + "/transactions", wait_until="networkidle")
    time.sleep(2)
    if "sign_in" in page.url:
        raise RuntimeError("tkti10ログイン失敗: ログインページにリダイレクトされた")

    # 3. テナント切替（react-autosuggest）
    page.goto("/".join(page.url.split("/")[:3]), wait_until="networkidle")
    time.sleep(2)

    dropdown = page.locator('button:has-text("マルチテナント検証用")').first
    if not dropdown.is_visible():
        dropdown = page.locator('button:has-text("テナント切り替え")').first
    dropdown.click()
    time.sleep(1)

    search = page.locator('input[placeholder*="テナント名"]').first
    if search.is_visible():
        search.click()
        page.keyboard.type("QA", delay=100)
        time.sleep(2)
        suggestion = page.locator('li.react-autosuggest-suggestion').first
        if suggestion.count() > 0:
            suggestion.click()
            time.sleep(5)
            page.wait_for_load_state("networkidle")

    # tkti10はサブドメインなし→dev.keihi.comに移動
    if subdomain in page.url:
        page.goto("https://dev.keihi.com/payment_requests/reports",
                   wait_until="networkidle")
        time.sleep(3)

    if "sign_in" in page.url:
        raise RuntimeError("tkti10テナント切替失敗")


_state = setup_screen(ScreenConfig(
    screen_name="invoice",
    log_prefix="test_invoice",
    env_path_parts=["..", "ログイン"],
    base_url="https://dev.keihi.com",
    custom_login=_login_tkti10,
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
