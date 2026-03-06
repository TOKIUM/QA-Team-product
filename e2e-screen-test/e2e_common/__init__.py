"""E2Eテスト共通基盤パッケージ

各画面のconftest.pyから利用する公開API:
  - ScreenConfig: 画面ごとの設定
  - setup_screen: 初期化関数（.envロード + 状態生成 + アクションログ設定）
"""

import os

from .config import ScreenConfig
from .state import TestSessionState
from .dotenv_loader import load_dotenv
from .action_tracker import install_action_logging


def setup_screen(config: ScreenConfig, conftest_file: str) -> TestSessionState:
    """画面テストの初期化を行い、TestSessionStateを返す。

    Args:
        config: 画面ごとの設定
        conftest_file: 呼び出し元conftest.pyの__file__
    """
    conftest_dir = os.path.dirname(os.path.abspath(conftest_file))

    # .env読み込み
    load_dotenv(conftest_dir, config.env_path_parts)

    # 状態オブジェクト生成
    state = TestSessionState(config, conftest_dir)

    # Locator操作ログ設定
    if config.action_logging:
        install_action_logging(state.current_test_steps)

    return state
