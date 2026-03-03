"""設定ファイル"""

import os
from pathlib import Path

# ディレクトリ
BASE_DIR = Path(__file__).parent
SCENARIOS_DIR = BASE_DIR / "scenarios"
GENERATED_TESTS_DIR = BASE_DIR / "generated_tests"

# Anthropic API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-5-20250514"

# Playwright
HEADLESS = True
DEFAULT_TIMEOUT = 10_000  # ms
VIEWPORT = {"width": 1280, "height": 720}

# Self-healing
MAX_HEAL_ATTEMPTS = 3
