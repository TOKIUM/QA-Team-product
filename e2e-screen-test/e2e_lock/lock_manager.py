"""ロック取得・解放・ステイルチェック"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_LOCK_PATH = Path(__file__).parent.parent / ".e2e_lock.json"
DEFAULT_TIMEOUT_MINUTES = 30


class LockManager:
    def __init__(self, lock_path: Path = DEFAULT_LOCK_PATH, timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES):
        self.lock_path = lock_path
        self.timeout_minutes = timeout_minutes

    def acquire(self, screens: list[str] | None = None, source: str = "manual") -> bool:
        """ロック取得を試みる。成功時True、既にロック中ならFalse。"""
        # ステイルロック回収
        if self.lock_path.exists():
            if self._is_stale():
                self.release(force=True)
            else:
                return False

        # アトミック作成（O_CREAT | O_EXCL で競合防止）
        lock_data = {
            "pid": os.getpid(),
            "started_at": datetime.now().isoformat(),
            "timeout_at": (datetime.now() + timedelta(minutes=self.timeout_minutes)).isoformat(),
            "screens": screens or [],
            "source": source,
        }
        try:
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, json.dumps(lock_data, ensure_ascii=False, indent=2).encode("utf-8"))
            finally:
                os.close(fd)
            return True
        except FileExistsError:
            return False

    def release(self, force: bool = False) -> bool:
        """ロック解放。force=Trueで他PIDのロックも解放。"""
        if not self.lock_path.exists():
            return True
        if not force:
            info = self.get_info()
            if info and info.get("pid") != os.getpid():
                return False
        try:
            self.lock_path.unlink()
            return True
        except OSError:
            return False

    def is_locked(self) -> bool:
        """ロック中かどうか（ステイルは除外）"""
        if not self.lock_path.exists():
            return False
        if self._is_stale():
            self.release(force=True)
            return False
        return True

    def get_info(self) -> dict | None:
        """ロック情報を取得"""
        if not self.lock_path.exists():
            return None
        try:
            with open(self.lock_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _is_stale(self) -> bool:
        """ステイルロック判定: PID死亡 or タイムアウト超過"""
        info = self.get_info()
        if info is None:
            return True

        # タイムアウト超過
        timeout_at = info.get("timeout_at")
        if timeout_at:
            try:
                if datetime.fromisoformat(timeout_at) < datetime.now():
                    return True
            except ValueError:
                pass

        # PID生存チェック（Windows: tasklist）
        pid = info.get("pid")
        if pid and not self._is_pid_alive(pid):
            return True

        return False

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        """Windowsでプロセスが生存しているか確認"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        except Exception:
            # tasklist失敗時は安全側（生存と判断）
            return True
