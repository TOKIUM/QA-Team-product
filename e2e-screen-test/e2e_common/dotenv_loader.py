"""共通 .env ファイル読み込み"""

import os


def load_dotenv(conftest_dir: str, path_parts: list):
    if not path_parts:
        return
    env_path = os.path.join(conftest_dir, *path_parts, ".env")
    env_path = os.path.normpath(env_path)
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
