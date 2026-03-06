"""画面テスト共通設定 - ScreenConfig dataclass"""

from dataclasses import dataclass, field


@dataclass
class ScreenConfig:
    screen_name: str
    log_prefix: str
    env_path_parts: list = field(default_factory=list)
    action_logging: bool = True
    page_fixture_names: list = field(default_factory=lambda: ["logged_in_page", "page"])
