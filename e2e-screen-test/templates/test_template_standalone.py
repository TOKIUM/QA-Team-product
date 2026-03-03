"""
{機能名} - {カテゴリ名}テスト

方式B（独立スクリプト形式）テンプレート。
テストID別の動画録画・ログ出力を含む。
storage_stateでログイン認証を分離し、テスト操作のみを動画録画する。

テスト内容:
  TC-XX: {テスト概要1}
  TC-YY: {テスト概要2}

前提条件:
  - ログイン情報は {相対パス}/.env に設定済み
  - テスト用ファイルは {フォルダ名}/ に配置済み（必要な場合）

使い方:
  1. {プレースホルダー} を実際の値に置換
  2. テスト関数を実際のテストケースに書き換え
  3. `python test_{機能}_{カテゴリ}.py` で実行
"""

import os
import sys
import json
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# ===== パス設定（対象システムに合わせて変更） =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "{BASE_URL}"  # 例: "https://staging.example.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")

# カテゴリ名（ログファイル名に使用）
CATEGORY = "{カテゴリ}"  # 例: "normal", "error", "dom", "navigation"

# ===== ログ設定 =====
os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_{CATEGORY}_{timestamp}.log")
log_fh = None


def get_th_result_dir(th_id: str) -> str:
    """テストIDごとの証跡（動画）保存フォルダを作成して返す
    ※ 関数名はプロジェクトプレフィックスに合わせてリネーム可（例: get_tc_result_dir）
    """
    d = os.path.join(RESULT_DIR, th_id)
    os.makedirs(d, exist_ok=True)
    return d


def log(msg: str):
    """コンソール + ファイルに出力"""
    global log_fh
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    if log_fh:
        log_fh.write(line + "\n")
        log_fh.flush()
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode())


def load_env() -> dict:
    """ログイン情報を .env からロード

    .envファイルのパスは対象システムのフォルダ構成に合わせて変更すること。
    """
    env_path = os.path.normpath(
        os.path.join(SCRIPT_DIR, "..", "..", "..", "{ログインフォルダ}", ".env")
    )
    vals = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    else:
        log(f"WARNING: .env ファイルが見つかりません: {env_path}")
    return vals


def login(page, email: str, password: str):
    """共通ログイン処理

    対象システムに合わせて以下を修正:
    - ログインURL
    - メールアドレス/パスワードのラベル名
    - ログインボタンのname属性
    - ログイン後のリダイレクト先URLパターン
    """
    log("ログイン開始...")
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    page.get_by_role("button", name="{ログインボタン名}", exact=True).wait_for(
        state="visible"
    )
    page.get_by_label("{メールアドレスラベル}").fill(email)
    page.get_by_label("{パスワードラベル}").fill(password)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="{ログインボタン名}", exact=True).click()

    # ログイン後のURL遷移を待機
    try:
        page.wait_for_url("**/{ログイン後のパス}**", timeout=60000)
    except Exception:
        # フォールバック: ポーリングでログインページからの離脱を確認
        for _ in range(30):
            if "/login" not in page.url:
                break
            page.wait_for_timeout(1000)

    page.wait_for_load_state("networkidle")
    log(f"ログイン完了: {page.url}")

    if "/login" in page.url:
        raise RuntimeError(f"ログイン失敗: URL={page.url}")


# ===== テスト関数 =====
# 以下をテストケースごとに複製・修正する


def test_tc_01(page):
    """TC-01: {テスト概要}"""
    tc_id = "TC-01"
    log(f"\n{'='*60}")
    log(f"{tc_id}: {{テスト概要}}")
    log(f"{'='*60}")

    try:
        # --- Step 1: 画面遷移・前提操作 ---

        # --- Step 2: テスト操作 ---
        # ※ 動画録画が有効な場合、操作は自動的に録画される
        # ※ 特定ステップの静止画が必要な場合のみ page.screenshot() を追加

        # --- Step 3: 検証 ---
        # assert / expect で期待値チェック
        # expect(page.get_by_text("成功")).to_be_visible()

        log(f"結果: PASS")
        return {"success": True}

    except Exception as e:
        log(f"結果: FAIL ({e})")
        return {"success": False, "error": str(e)}


def test_tc_02(page):
    """TC-02: {テスト概要}"""
    tc_id = "TC-02"
    log(f"\n{'='*60}")
    log(f"{tc_id}: {{テスト概要}}")
    log(f"{'='*60}")

    try:
        # --- テスト操作 ---

        # --- 検証 ---

        log(f"結果: PASS")
        return {"success": True}

    except Exception as e:
        log(f"結果: FAIL ({e})")
        return {"success": False, "error": str(e)}


# ===== メイン =====
def main():
    global log_fh
    log_fh = open(LOG_FILE, "w", encoding="utf-8")

    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")

    if not email or not password:
        log("ERROR: TEST_EMAIL / TEST_PASSWORD が .env に設定されていません")
        log_fh.close()
        return

    log(f"テスト開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # テストケース定義: (テストID, テスト名, 関数)
    tests = [
        ("TC-01", "{テスト概要1}", test_tc_01),
        ("TC-02", "{テスト概要2}", test_tc_02),
    ]

    results = []
    pending_video_copies = []
    storage_state_path = os.path.join(RESULT_DIR, "_auth_state.json")
    VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # === Phase 1: ログイン + 認証状態保存（動画なし） ===
        login_context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        login_context.set_default_timeout(30000)
        login_page = login_context.new_page()
        login(login_page, email, password)
        login_context.storage_state(path=storage_state_path)
        login_context.close()
        log("認証状態を保存しました")

        # === Phase 2: 動画録画付きコンテキストでテスト実行 ===
        os.makedirs(VIDEOS_TMP_DIR, exist_ok=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            storage_state=storage_state_path,
            record_video_dir=VIDEOS_TMP_DIR,
            record_video_size={"width": 1280, "height": 720},
        )
        context.set_default_timeout(30000)

        for tc_id, tc_name, tc_func in tests:
            page = context.new_page()
            log(f"\n{'#'*60}")
            log(f"# {tc_id}: {tc_name}")
            log(f"{'#'*60}")

            try:
                # テスト前に対象ページに遷移（テスト間の独立性を保つ）
                page.goto(f"{BASE_URL}/{{対象ページパス}}")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)

                result = tc_func(page)
                result["tc_id"] = tc_id
                result["tc_name"] = tc_name
                results.append(result)

                status = "PASS" if result["success"] else "FAIL"
                log(f"\n結果: {status}")

            except Exception as e:
                log(f"\n結果: FAIL (例外: {e})")
                results.append(
                    {
                        "tc_id": tc_id,
                        "tc_name": tc_name,
                        "success": False,
                        "error": str(e),
                    }
                )

            finally:
                # 動画パスを記録（遅延コピー用）
                try:
                    video = page.video
                    if video:
                        video_src = video.path()
                        if video_src:
                            dest_dir = get_th_result_dir(tc_id)
                            dest_path = os.path.join(dest_dir, f"{tc_id}.webm")
                            pending_video_copies.append((str(video_src), dest_path))
                except Exception:
                    pass
                page.close()

        context.close()

        # === Phase 3: 遅延コピー（動画確定後にコピー） ===
        log("\n動画ファイルをコピー中...")
        for src, dest in pending_video_copies:
            try:
                if os.path.exists(src) and os.path.getsize(src) > 0:
                    shutil.copy2(src, dest)
                    size_kb = os.path.getsize(dest) / 1024
                    log(f"  動画保存: {dest} ({size_kb:.1f} KB)")
            except Exception as e:
                log(f"  動画保存失敗: {e}")

        # クリーンアップ
        if os.path.exists(VIDEOS_TMP_DIR):
            try:
                shutil.rmtree(VIDEOS_TMP_DIR)
            except Exception:
                pass
        if os.path.exists(storage_state_path):
            try:
                os.remove(storage_state_path)
            except Exception:
                pass

        browser.close()

    # サマリー
    pass_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - pass_count
    log(f"\n{'='*60}")
    log(f"テスト結果サマリー")
    log(f"{'='*60}")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        err = f" - {r.get('error', '')}" if not r["success"] else ""
        log(f"  [{status}] {r['tc_id']}: {r['tc_name']}{err}")
    log(f"\n合計: {len(results)}件 | PASS: {pass_count}件 | FAIL: {fail_count}件")

    # JSON結果出力
    json_path = os.path.join(LOGS_DIR, f"test_{CATEGORY}_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log(f"テスト完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"JSON結果: {json_path}")

    log_fh.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
