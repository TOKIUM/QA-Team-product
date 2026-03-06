"""pytest-playwright 共通設定（ログイン画面テスト用）- e2e_common委譲

action logging無効（ログイン画面テストはLocatorパッチ不要）。
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from e2e_common import ScreenConfig, setup_screen

_state = setup_screen(ScreenConfig(
    screen_name="login",
    log_prefix="test_login",
    action_logging=False,
    page_fixture_names=["tokium_id_page", "page"],
), __file__)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return _state.browser_context_args(browser_context_args)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return _state.browser_type_launch_args(browser_type_launch_args)


def pytest_sessionstart(session):
    _state.on_session_start(session)


def pytest_sessionfinish(session, exitstatus):
    _state.on_session_finish(session, exitstatus)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    _state.on_makereport(item, call, outcome)
