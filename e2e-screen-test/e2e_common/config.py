"""画面テスト共通設定 - ScreenConfig dataclass"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ScreenConfig:
    screen_name: str
    log_prefix: str
    env_path_parts: list = field(default_factory=list)
    action_logging: bool = True
    page_fixture_names: list = field(default_factory=lambda: ["logged_in_page", "page"])
    base_url: str = "https://invoicing-staging.keihi.com"
    custom_login: Optional[Callable] = None
