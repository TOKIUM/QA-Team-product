"""pytest-playwright 共通設定（PDF取り込み画面テスト用）- e2e_common委譲

BUG FIX: 旧版ではaction_stepsフィールドがresultsに含まれていなかった。
e2e_common移行により自動的に修正。
"""

import os
import sys
import pytest
from playwright.sync_api import Page

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from e2e_common import ScreenConfig, setup_screen

_state = setup_screen(ScreenConfig(
    screen_name="pdf_organizer",
    log_prefix="test_pdf_organizer",
    env_path_parts=["..", "..", "..", "..", "ログイン"],
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
