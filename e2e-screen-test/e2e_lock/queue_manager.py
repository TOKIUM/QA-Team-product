"""ファイルベースFIFOキュー管理"""

import json
import os
import random
import time
from pathlib import Path

DEFAULT_QUEUE_PATH = Path(__file__).parent.parent / ".e2e_queue.json"

# Windows用ファイルロック
try:
    import msvcrt

    def _lock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock_file(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
except ImportError:
    # 非Windows（フォールバック: fcntl）
    import fcntl

    def _lock_file(f):
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_file(f):
        fcntl.flock(f, fcntl.LOCK_UN)


class QueueManager:
    def __init__(self, queue_path: Path = DEFAULT_QUEUE_PATH):
        self.queue_path = queue_path

    def enqueue(self, pid: int | None = None, screens: list[str] | None = None) -> str:
        """キュー末尾に追加。エントリIDを返す。"""
        entry_id = f"q-{int(time.time())}-{random.randint(1000, 9999)}"
        entry = {
            "id": entry_id,
            "pid": pid or os.getpid(),
            "screens": screens or [],
            "enqueued_at": time.time(),
        }
        queue = self._read_queue()
        queue.append(entry)
        self._write_queue(queue)
        return entry_id

    def is_my_turn(self, entry_id: str) -> bool:
        """自分が先頭かどうか（前のエントリのPID死亡もチェック）"""
        from .lock_manager import LockManager
        queue = self._read_queue()
        # 死んだエントリを除去
        cleaned = []
        changed = False
        for entry in queue:
            if LockManager._is_pid_alive(entry["pid"]):
                cleaned.append(entry)
            else:
                changed = True
        if changed:
            self._write_queue(cleaned)
            queue = cleaned

        if not queue:
            return True
        return queue[0]["id"] == entry_id

    def dequeue(self, entry_id: str) -> bool:
        """指定エントリをキューから削除"""
        queue = self._read_queue()
        new_queue = [e for e in queue if e["id"] != entry_id]
        if len(new_queue) != len(queue):
            self._write_queue(new_queue)
            return True
        return False

    def get_queue(self) -> list[dict]:
        """現在のキュー内容を取得"""
        return self._read_queue()

    def _read_queue(self) -> list:
        """キューファイル読み込み（破損時は空キュー）"""
        if not self.queue_path.exists():
            return []
        try:
            with open(self.queue_path, "r", encoding="utf-8") as f:
                try:
                    _lock_file(f)
                except (OSError, BlockingIOError):
                    pass  # ロック取得失敗時はそのまま読む
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            # 破損JSON → 空キューとして再作成
            self._write_queue([])
            return []

    def _write_queue(self, queue: list):
        """キューファイル書き込み（排他制御付き）"""
        tmp_path = self.queue_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)
            # アトミックリネーム（Windows: 上書き許可）
            if self.queue_path.exists():
                self.queue_path.unlink()
            tmp_path.rename(self.queue_path)
        except OSError:
            # フォールバック: 直接書き込み
            with open(self.queue_path, "w", encoding="utf-8") as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)
