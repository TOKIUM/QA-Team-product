"""テストセッション状態管理 - TestSessionState"""

import os
import re
import json
import shutil
from datetime import datetime
from playwright.sync_api import expect

from .action_tracker import _ts


class TestSessionState:
    """各画面テストの可変状態とpytest hook実装を保持するクラス。

    conftest.pyのhook関数から委譲される形で使う。
    """

    def __init__(self, config, conftest_dir):
        self.config = config
        self.conftest_dir = conftest_dir

        # ディレクトリ
        self.result_dir = os.path.join(conftest_dir, "test_results")
        self.logs_dir = os.path.join(self.result_dir, "_logs")
        self.videos_dir = os.path.join(self.result_dir, "_videos_tmp")
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)

        # 可変状態
        self._timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file_path = os.path.join(
            self.logs_dir, f"{config.log_prefix}_{self._timestamp}.log")
        self._log_fh = None
        self._test_results = []
        self._session_start = None
        self._pending_video_copies = []
        self._current_test_steps = []

        # 認証情報（.envロード後に読み取る）
        self.base_url = "https://invoicing-staging.keihi.com"
        self.test_email = os.environ.get("TEST_EMAIL", "test@example.com")
        self.test_password = os.environ.get("TEST_PASSWORD", "TestPass123!")

    @property
    def current_test_steps(self):
        """操作ステップリスト（action_trackerと共有する参照）"""
        return self._current_test_steps

    def get_th_result_dir(self, th_id: str) -> str:
        d = os.path.join(self.result_dir, th_id)
        os.makedirs(d, exist_ok=True)
        return d

    def _log(self, msg: str):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        if self._log_fh:
            self._log_fh.write(line + "\n")
            self._log_fh.flush()
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("ascii", "replace").decode())

    # === Fixture実装 ===

    def browser_context_args(self, base_args):
        return {
            **base_args,
            "viewport": {"width": 1280, "height": 720},
            "locale": "ja-JP",
            "timezone_id": "Asia/Tokyo",
            "record_video_dir": self.videos_dir,
            "record_video_size": {"width": 1280, "height": 720},
        }

    def browser_type_launch_args(self, base_args):
        return {
            **base_args,
            "slow_mo": 0,
        }

    def do_login(self, page):
        """logged_in_page fixtureの実装。ログイン済みページを返す。"""
        if self.config.action_logging:
            _orig_goto = page.goto

            def _logged_goto(url, **kw):
                self._current_test_steps.append(f"[{_ts()}] ページ遷移: {url}")
                return _orig_goto(url, **kw)

            page.goto = _logged_goto

        page.goto(f"{self.base_url}/login")
        page.get_by_role("button", name="ログイン", exact=True).wait_for(
            state="visible")
        page.get_by_label("メールアドレス").fill(self.test_email)
        page.get_by_label("パスワード").fill(self.test_password)
        page.get_by_role("button", name="ログイン", exact=True).click()
        expect(page).to_have_url(re.compile(r"/invoices"), timeout=30000)

        if self.config.action_logging:
            self._current_test_steps.append(
                f"[{_ts()}] ログイン完了: {page.url}")

        return page

    # === pytest hook実装 ===

    def on_session_start(self, session):
        self._log_fh = open(self._log_file_path, "w", encoding="utf-8")
        self._session_start = datetime.now()
        self._log(f"===== テストセッション開始: "
                  f"{self._session_start.strftime('%Y-%m-%d %H:%M:%S')} =====")
        self._log(f"ログ保存先: {self._log_file_path}")
        self._log(f"結果保存先: {self.result_dir}")

    def on_session_finish(self, session, exitstatus):
        session_end = datetime.now()
        duration = ((session_end - self._session_start).total_seconds()
                    if self._session_start else 0)
        passed = sum(1 for r in self._test_results if r["result"] == "PASS")
        failed = sum(1 for r in self._test_results if r["result"] == "FAIL")
        total = len(self._test_results)

        self._log(f"===== テストセッション終了: "
                  f"{session_end.strftime('%Y-%m-%d %H:%M:%S')} =====")
        self._log(f"結果: {passed} PASS / {failed} FAIL / {total} TOTAL "
                  f"（{duration:.1f}秒）")

        # 遅延コピー
        for src_path, dest_path in self._pending_video_copies:
            try:
                if os.path.exists(src_path) and os.path.getsize(src_path) > 0:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    self._log(f"  動画保存: {dest_path}")
                else:
                    self._log(f"  動画保存スキップ（ファイルなしまたは空）: "
                              f"{src_path}")
            except Exception as e:
                self._log(f"  動画保存失敗: {e}")

        if os.path.exists(self.videos_dir):
            try:
                shutil.rmtree(self.videos_dir)
            except Exception:
                pass

        summary = {
            "session_start": (self._session_start.isoformat()
                              if self._session_start else None),
            "session_end": session_end.isoformat(),
            "duration_seconds": round(duration, 1),
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": self._test_results,
        }
        json_path = os.path.join(
            self.logs_dir,
            f"{self.config.log_prefix}_{self._timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        self._log(f"JSONサマリー保存: {json_path}")

        if self._log_fh:
            self._log_fh.close()
            self._log_fh = None

    def on_runtest_setup(self, item):
        """テスト開始前にステップログをリセット（action_logging有効時のみ呼ぶ）"""
        self._current_test_steps.clear()
        self._current_test_steps.append(f"[{_ts()}] テスト開始: {item.name}")

    def on_makereport(self, item, call, outcome):
        report = outcome.get_result()
        if report.when != "call":
            return

        th_id = getattr(item, "_th_id", None)
        test_name = item.name
        result = "PASS" if report.passed else "FAIL"
        duration = round(report.duration, 2)

        self._log(f"[{result}] {test_name} ({duration}s)"
                  + (f" TH-ID: {th_id}" if th_id else ""))

        # 動画パスを記録
        if th_id:
            page = None
            for name in self.config.page_fixture_names:
                page = item.funcargs.get(name)
                if page:
                    break
            if page:
                try:
                    video = page.video
                    if video:
                        video_path = video.path()
                        if video_path:
                            result_dir = self.get_th_result_dir(th_id)
                            dest_path = os.path.join(
                                result_dir, f"{th_id}.webm")
                            self._pending_video_copies.append(
                                (video_path, dest_path))
                except Exception as e:
                    self._log(f"  動画パス記録失敗: {e}")

        # 操作テキストログ保存（action_logging有効時のみ）
        if self.config.action_logging:
            self._current_test_steps.append(
                f"[{_ts()}] テスト終了: {result} ({duration}s)")
            if self._current_test_steps:
                log_dir = (self.get_th_result_dir(th_id)
                           if th_id else self.logs_dir)
                log_id = th_id or test_name
                action_log_path = os.path.join(
                    log_dir, f"{log_id}_actions.log")
                with open(action_log_path, "w", encoding="utf-8") as af:
                    af.write(f"テスト: {test_name}\n")
                    af.write(f"TH-ID: {th_id or 'N/A'}\n")
                    af.write(f"結果: {result}\n")
                    af.write(f"実行時間: {duration}s\n")
                    af.write(f"{'='*60}\n")
                    af.write("\n".join(self._current_test_steps))
                    if report.failed:
                        af.write(f"\n{'='*60}\n")
                        af.write(f"エラー:\n{report.longrepr}\n")
                    af.write("\n")

        # 結果記録
        result_entry = {
            "th_id": th_id,
            "test_name": test_name,
            "result": result,
            "duration": duration,
            "error": str(report.longrepr) if report.failed else None,
        }
        if self.config.action_logging:
            result_entry["action_steps"] = len(self._current_test_steps)
        self._test_results.append(result_entry)
