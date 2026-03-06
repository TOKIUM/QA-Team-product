"""ステータス確認CLI: python -m e2e_lock.status"""

import argparse
import json
import sys
from datetime import datetime

from .lock_manager import LockManager
from .queue_manager import QueueManager


def get_status() -> dict:
    """ロック状態とキュー一覧を取得"""
    lm = LockManager()
    qm = QueueManager()

    lock_info = lm.get_info()
    is_locked = lm.is_locked()
    queue = qm.get_queue()

    return {
        "locked": is_locked,
        "lock_info": lock_info,
        "queue_length": len(queue),
        "queue": queue,
    }


def print_status():
    """ステータスを人間可読形式で表示"""
    status = get_status()

    if status["locked"]:
        info = status["lock_info"]
        print(f"[LOCKED] E2Eテスト実行中")
        print(f"  PID:     {info.get('pid')}")
        print(f"  開始:    {info.get('started_at', '?')[:19]}")
        print(f"  期限:    {info.get('timeout_at', '?')[:19]}")
        print(f"  画面:    {', '.join(info.get('screens', [])) or '全画面'}")
        print(f"  ソース:  {info.get('source', '?')}")
    else:
        print("[FREE] ロックなし - 実行可能")

    if status["queue"]:
        print(f"\nキュー ({status['queue_length']}件):")
        for i, entry in enumerate(status["queue"]):
            ts = datetime.fromtimestamp(entry.get("enqueued_at", 0))
            print(f"  {i+1}. {entry['id']} (PID:{entry['pid']}, {ts:%H:%M:%S})")
    elif status["locked"]:
        print("\nキュー: 待機なし")


def main():
    parser = argparse.ArgumentParser(description="E2Eテスト ロック/キュー状態確認")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    if args.json:
        print(json.dumps(get_status(), ensure_ascii=False, indent=2, default=str))
    else:
        print_status()


if __name__ == "__main__":
    main()
