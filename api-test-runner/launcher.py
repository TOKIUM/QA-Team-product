"""PyInstaller 用エントリポイント.

ダブルクリックで GUI を起動する。
PyInstaller: python -m PyInstaller launcher.py ...
"""

import sys
from pathlib import Path


def main():
    # .exe の場合: sys._MEIPASS (PyInstaller 展開先) ではなく
    # .exe の置かれたディレクトリをプロジェクトルートとする
    if getattr(sys, "frozen", False):
        project_root = Path(sys.executable).resolve().parent
    else:
        project_root = Path(__file__).resolve().parent

    from api_test_runner.gui import launch
    sys.exit(launch(project_root))


if __name__ == "__main__":
    main()
