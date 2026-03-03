"""
pytest-playwright 共通設定（CSVインポートテスト用）+ test_results対応

テスト結果（ログ、動画、JSONサマリー）をtest_results/に自動保存する。
各テストの操作を動画録画し、TH-IDフォルダに保存する。

動画保存の仕組み:
  フック時点では動画ファイルが空のため、パスだけ記録し、
  pytest_sessionfinish で全動画を一括コピーする。
"""

import os
import json
import shutil
import pytest
from datetime import datetime


# .envファイル読み込み（ログインフォルダの.envを使用）
def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ログイン", ".env")
    env_path = os.path.normpath(env_path)
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

_load_env()


# ===== test_results設定 =====
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(_SCRIPT_DIR, "test_results")
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
VIDEOS_DIR = os.path.join(RESULT_DIR, "_videos_tmp")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
_log_file_path = os.path.join(LOGS_DIR, f"test_csv_import_{_timestamp}.log")
_log_fh = None
_test_results = []
_session_start = None
_pending_video_copies = []


def _log(msg: str):
    """コンソール + ファイルに出力"""
    global _log_fh
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    if _log_fh:
        _log_fh.write(line + "\n")
        _log_fh.flush()
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode())


def get_th_result_dir(th_id: str) -> str:
    d = os.path.join(RESULT_DIR, th_id)
    os.makedirs(d, exist_ok=True)
    return d


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """ブラウザコンテキストの共通設定（動画録画有効）"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
        "record_video_dir": VIDEOS_DIR,
        "record_video_size": {"width": 1280, "height": 720},
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "slow_mo": 0,
    }


# ===== セッションレベルのフック =====

def pytest_sessionstart(session):
    global _log_fh, _session_start
    _log_fh = open(_log_file_path, "w", encoding="utf-8")
    _session_start = datetime.now()
    _log(f"===== テストセッション開始: {_session_start.strftime('%Y-%m-%d %H:%M:%S')} =====")
    _log(f"ログ保存先: {_log_file_path}")
    _log(f"結果保存先: {RESULT_DIR}")


def pytest_sessionfinish(session, exitstatus):
    global _log_fh
    session_end = datetime.now()
    duration = (session_end - _session_start).total_seconds() if _session_start else 0

    passed = sum(1 for r in _test_results if r["result"] == "PASS")
    failed = sum(1 for r in _test_results if r["result"] == "FAIL")
    total = len(_test_results)

    _log(f"===== テストセッション終了: {session_end.strftime('%Y-%m-%d %H:%M:%S')} =====")
    _log(f"結果: {passed} PASS / {failed} FAIL / {total} TOTAL （{duration:.1f}秒）")

    # 遅延コピー
    for src_path, dest_path in _pending_video_copies:
        try:
            if os.path.exists(src_path) and os.path.getsize(src_path) > 0:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_path, dest_path)
                _log(f"  🎬 動画保存: {dest_path}")
            else:
                _log(f"  🎬 動画保存スキップ（ファイルなしまたは空）: {src_path}")
        except Exception as e:
            _log(f"  🎬 動画保存失敗: {e}")

    # 一時動画フォルダのクリーンアップ
    if os.path.exists(VIDEOS_DIR):
        try:
            shutil.rmtree(VIDEOS_DIR)
        except Exception:
            pass

    # JSONサマリー保存
    summary = {
        "session_start": _session_start.isoformat() if _session_start else None,
        "session_end": session_end.isoformat(),
        "duration_seconds": round(duration, 1),
        "total": total, "passed": passed, "failed": failed,
        "results": _test_results,
    }
    json_path = os.path.join(LOGS_DIR, f"test_csv_import_{_timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    _log(f"JSONサマリー保存: {json_path}")

    if _log_fh:
        _log_fh.close()
        _log_fh = None


# ===== テストレベルのフック =====

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        th_id = getattr(item, "_th_id", None)
        test_name = item.name
        result = "PASS" if report.passed else "FAIL"
        duration = round(report.duration, 2)
        _log(f"[{result}] {test_name} ({duration}s)" + (f" TH-ID: {th_id}" if th_id else ""))
        if th_id:
            page = item.funcargs.get("page")
            if page:
                try:
                    video = page.video
                    if video:
                        video_path = video.path()
                        if video_path:
                            result_dir = get_th_result_dir(th_id)
                            dest_path = os.path.join(result_dir, f"{th_id}.webm")
                            _pending_video_copies.append((video_path, dest_path))
                except Exception as e:
                    _log(f"  🎬 動画パス記録失敗: {e}")
        _test_results.append({
            "th_id": th_id, "test_name": test_name, "result": result,
            "duration": duration, "error": str(report.longrepr) if report.failed else None,
        })
