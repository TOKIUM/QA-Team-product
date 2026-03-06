"""Hook用チェックスクリプト: E2Eテスト実行検知時にロック状態を情報表示

直接実行対応（相対インポートなし）: python hook_check.py
"""

import json
import sys
from pathlib import Path

LOCK_PATH = Path(__file__).parent.parent / ".e2e_lock.json"


def main():
    if not LOCK_PATH.exists():
        print(json.dumps({"ok": True}))
        return

    try:
        with open(LOCK_PATH, encoding="utf-8") as f:
            info = json.load(f)
        pid = info.get("pid", "?")
        screens = ", ".join(info.get("screens", [])) or "all"
        print(json.dumps({
            "ok": True,
            "reason": f"E2E test running (PID {pid}, {screens}). Queue will handle waiting.",
        }))
    except Exception:
        print(json.dumps({"ok": True}))


if __name__ == "__main__":
    main()
