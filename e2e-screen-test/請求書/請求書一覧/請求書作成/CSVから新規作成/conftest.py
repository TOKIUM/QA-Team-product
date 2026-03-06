"""
pytest-playwright 共通設定（CSVインポートテスト用）+ test_results対応

e2e_common パッケージに委譲。テスト結果（ログ、動画、JSONサマリー）を
test_results/ に自動保存する。
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from e2e_common import ScreenConfig, setup_screen

_state = setup_screen(ScreenConfig(
    screen_name="csv_import",
    log_prefix="test_csv_import",
    env_path_parts=["..", "..", "..", "..", "ログイン"],
    action_logging=False,
    page_fixture_names=["page"],
), __file__)


def get_th_result_dir(th_id: str) -> str:
    """後方互換: テストコードから参照される関数"""
    return _state.get_th_result_dir(th_id)


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
