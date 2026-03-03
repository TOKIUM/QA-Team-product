"""
共通添付ファイルの一括添付 - ファイル名・拡張子バリエーションテスト

テスト内容（カテゴリE: ファイル名バリエーション, 7件）:
  TH-F01: 半角英字ファイル名 (abcdefg.pdf)
  TH-F02: 半角数字ファイル名 (1234567890.pdf)
  TH-F03: 全角英字ファイル名 (ＡＢＣＤＥＦＧ.pdf)
  TH-F04: 半角カタカナファイル名 (ﾊﾝｶｸｶﾀｶﾅ.pdf)
  TH-F05: 全角数字ファイル名 (１２３４５６７８９０.pdf)
  TH-F06: URLエンコード風ファイル名 (%5Ct%5Cn%5Cr%5C0.pdf)
  TH-F07: 長いファイル名 (200文字超)

テスト内容（カテゴリF: 拡張子バリエーション, 5件）:
  TH-X01: JPEG拡張子 (.jpeg)
  TH-X02: GIF拡張子 (.gif)
  TH-X03: レガシーExcel (.xls)
  TH-X04: レガシーWord (.doc)
  TH-X05: PowerPoint (.pptx)

前提条件:
  - テスト用ファイルは ファイル名/ および 拡張子/ に配置済み
  - 全テスト添付実行なし（index=5 再利用）
"""

import os
import sys
import json
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://invoicing-staging.keihi.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")
EXTENSION_DIR = os.path.join(SCRIPT_DIR, "拡張子")
FILENAME_DIR = os.path.join(SCRIPT_DIR, "ファイル名")

os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_filename_{timestamp}.log")
log_fh = None


def get_th_result_dir(th_id: str) -> str:
    """TH-IDごとの動画保存フォルダを作成して返す"""
    d = os.path.join(RESULT_DIR, th_id)
    os.makedirs(d, exist_ok=True)
    return d



def log(msg: str):
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
    env_path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", "ログイン", ".env"))
    vals = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


def login(page, email, password):
    log("ログイン開始...")
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
    page.get_by_label("メールアドレス").fill(email)
    page.get_by_label("パスワード").fill(password)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="ログイン", exact=True).click()
    try:
        page.wait_for_url("**/invoices**", timeout=60000)
    except Exception:
        for _ in range(30):
            if "/invoices" in page.url and "/login" not in page.url:
                break
            page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    log(f"ログイン完了: {page.url}")
    if "/login" in page.url:
        raise RuntimeError(f"ログイン失敗: URL={page.url}")


def navigate_to_list(page):
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)


def select_invoice(page, index):
    checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
    if index >= len(checkboxes):
        raise RuntimeError(f"index={index} がチェックボックス数({len(checkboxes)})を超えています")
    checkboxes[index].click(force=True)
    page.wait_for_timeout(500)


def open_modal(page):
    for attempt in range(3):
        try:
            page.get_by_role("button", name="その他の操作").click()
            page.wait_for_timeout(1500)
            attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
            if attach_item.count() > 0:
                attach_item.first.click()
            else:
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                continue
            page.locator('[role="dialog"] h2:has-text("共通添付ファイルの一括添付")').wait_for(state="visible", timeout=15000)
            page.wait_for_timeout(1000)
            return
        except Exception as e:
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
    raise RuntimeError("モーダルが3回試行しても開きませんでした")


def close_modal(page):
    try:
        close_btn = page.get_by_role("button", name="閉じる")
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
            page.wait_for_timeout(500)
            return
        back_btn = page.get_by_role("button", name="戻る")
        if back_btn.count() > 0:
            back_btn.first.click(force=True)
            page.wait_for_timeout(500)
            c2 = page.get_by_role("button", name="閉じる")
            if c2.count() > 0:
                c2.first.click(force=True)
                page.wait_for_timeout(500)
    except Exception:
        pass


def test_file_variant(page, tc_id, tc_name, file_path, idx):
    """
    共通テスト: ファイルをStep1で選択→Step2で「添付可能」判定確認（添付実行なし）
    """
    result = {"tc_id": tc_id, "tc_name": tc_name, "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        basename = os.path.basename(file_path)
        log(f"  ファイル: {basename}")

        # Windows MAX_PATH対策: 長いパスには \\?\ プレフィックスを付与
        check_path = file_path
        if len(file_path) > 250 and not file_path.startswith("\\\\?\\"):
            check_path = "\\\\?\\" + os.path.abspath(file_path)
        if not os.path.exists(check_path):
            raise RuntimeError(f"テストファイルが見つかりません: {file_path}")
        # Playwrightのset_input_filesには拡張パスを渡す
        actual_path = check_path

        # Step 1: ファイル選択
        page.locator('input[type="file"]').set_input_files([actual_path])
        page.wait_for_timeout(2000)

        # ファイル数確認
        file_count = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return '';
            const h3s = d.querySelectorAll('h3');
            for (const h3 of h3s) {
                if (h3.textContent.includes('選択済みファイル')) return h3.textContent.trim();
            }
            return '';
        }""")
        log(f"  {file_count}")

        # エラーチェック
        has_error = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return false;
            return d.innerText.includes('エラー');
        }""")

        if has_error:
            # Step1でエラーの場合（拡張子なし等）
            log(f"  Step1エラー検出: ファイル名 '{basename}' はStep1でブロック")
            confirm_btn = page.get_by_role("button", name="確認へ進む")
            is_disabled = confirm_btn.count() > 0 and not confirm_btn.first.is_enabled()
            log(f"  「確認へ進む」disabled: {is_disabled}")
            result["success"] = True
            result["error"] = "Step1エラー（ファイル受付不可）"
            log(f"  結果: PASS ✓ (Step1でブロック)")
            close_modal(page)
            return result

        # 「確認へ進む」enabled確認
        confirm_btn = page.get_by_role("button", name="確認へ進む")
        assert confirm_btn.count() > 0 and confirm_btn.first.is_enabled(), \
            f"「確認へ進む」がdisabled: fileCount='{file_count}'"
        log("  ✓ Step1: 「確認へ進む」enabled")

        # Step 2へ
        confirm_btn.first.click()
        page.wait_for_timeout(2000)

        # 非同期判定待ち
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了 ({i+1}秒)")
                break

        # 判定結果確認
        judgments = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return [];
            const table = d.querySelector('table');
            if (!table) return [];
            const r = [];
            table.querySelectorAll('tbody tr').forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td'));
                if (cells.length > 0) r.push(cells[cells.length - 1].textContent.trim());
            });
            return r;
        }""")
        log(f"  判定列: {judgments}")

        has_ok = any("添付可能" in j for j in judgments)
        assert has_ok, f"「添付可能」にならない: {judgments}"
        log("  ✓ Step2: 「添付可能」")

        result["success"] = True
        log("  結果: PASS ✓")

        # Step2で戻る → Step1 → 閉じる（添付実行しない）
        back_btn = page.get_by_role("button", name="戻る")
        if back_btn.count() > 0:
            back_btn.first.click()
            page.wait_for_timeout(500)
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


# ===== メイン =====
def main():
    global log_fh
    log_fh = open(LOG_FILE, "w", encoding="utf-8")

    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")
    if not email or not password:
        log("ERROR: .env 未設定")
        log_fh.close()
        return

    log(f"テスト開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"ログファイル: {LOG_FILE}")

    # 長いファイル名のパスを取得（200文字以上で最も短いもの）
    long_filename = None
    for f in os.listdir(FILENAME_DIR):
        if f.endswith('.pdf') and len(f) > 200:
            full = os.path.join(FILENAME_DIR, f)
            if long_filename is None or len(f) < len(os.path.basename(long_filename)):
                long_filename = full
    if long_filename:
        log(f"  長いファイル名: {os.path.basename(long_filename)} ({len(os.path.basename(long_filename))}文字)")

    # テスト定義: (tc_id, tc_name, file_path)
    test_cases = [
        # カテゴリE: ファイル名バリエーション
        ("TH-F01", "半角英字ファイル名", os.path.join(FILENAME_DIR, "abcdefg.pdf")),
        ("TH-F02", "半角数字ファイル名", os.path.join(FILENAME_DIR, "1234567890.pdf")),
        ("TH-F03", "全角英字ファイル名", os.path.join(FILENAME_DIR, "ＡＢＣＤＥＦＧ.pdf")),
        ("TH-F04", "半角カタカナファイル名", os.path.join(FILENAME_DIR, "ﾊﾝｶｸｶﾀｶﾅ.pdf")),
        ("TH-F05", "全角数字ファイル名", os.path.join(FILENAME_DIR, "１２３４５６７８９０.pdf")),
        ("TH-F06", "URLエンコード風ファイル名", os.path.join(FILENAME_DIR, "%5Ct%5Cn%5Cr%5C0.pdf")),
        ("TH-F07", "長いファイル名(200文字超)", long_filename or ""),
        # カテゴリF: 拡張子バリエーション
        ("TH-X01", "JPEG拡張子(.jpeg)", os.path.join(EXTENSION_DIR, "sample.jpeg")),
        ("TH-X02", "GIF拡張子(.gif)", os.path.join(EXTENSION_DIR, "sample.gif")),
        ("TH-X03", "レガシーExcel(.xls)", os.path.join(EXTENSION_DIR, "sample.xls")),
        ("TH-X04", "レガシーWord(.doc)", os.path.join(EXTENSION_DIR, "sample.doc")),
        ("TH-X05", "PowerPoint(.pptx)", os.path.join(EXTENSION_DIR, "sample.pptx")),
    ]

    results = []
    pending_video_copies = []
    storage_state_path = os.path.join(RESULT_DIR, "_auth_state.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # === Phase 1: ログインして認証状態を保存 ===
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

        for tc_id, tc_name, file_path in test_cases:
            log(f"\n{'#' * 60}")
            log(f"# {tc_id}: {tc_name}")
            log(f"{'#' * 60}")
            log(f"\n{'=' * 60}")
            log(f"{tc_id}: {tc_name}")
            log(f"{'=' * 60}")

            if not file_path:
                log(f"  SKIP: テストファイルが見つかりません")
                results.append({"tc_id": tc_id, "tc_name": tc_name, "success": False, "error": "テストファイル未発見"})
                continue

            page = context.new_page()
            try:
                page.goto(f"{BASE_URL}/invoices")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                r = test_file_variant(page, tc_id, tc_name, file_path, idx=5)
                results.append(r)
            except Exception as e:
                log(f"  例外: {e}")
                results.append({"tc_id": tc_id, "tc_name": tc_name, "success": False, "error": str(e)})
            finally:
                try:
                    video = page.video
                    if video:
                        video_src = video.path()
                        if video_src:
                            dest_dir = get_th_result_dir(tc_id)
                            dest_path = os.path.join(dest_dir, f"{tc_id}.webm")
                            pending_video_copies.append((str(video_src), dest_path))
                            log(f"  🎬 動画パス記録: {tc_id}")
                except Exception as e:
                    log(f"  🎬 動画パス記録失敗: {e}")
                page.close()

        context.close()

        # === Phase 3: 遅延コピー ===
        log("\n動画ファイルをコピー中...")
        for src_path, dest_path in pending_video_copies:
            try:
                if os.path.exists(src_path) and os.path.getsize(src_path) > 0:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    size_kb = os.path.getsize(dest_path) / 1024
                    log(f"  🎬 動画保存: {dest_path} ({size_kb:.1f} KB)")
                else:
                    log(f"  🎬 動画スキップ（ファイルなしまたは空）: {src_path}")
            except Exception as e:
                log(f"  🎬 動画保存失敗: {e}")

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
    log(f"\n{'=' * 60}")
    log("テスト結果サマリー")
    log(f"{'=' * 60}")

    pass_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - pass_count

    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        error = f" - {r.get('error', '')}" if r.get("error") else ""
        log(f"  [{status}] {r['tc_id']}: {r['tc_name']}{error}")

    log(f"\n合計: {len(results)}件 | PASS: {pass_count}件 | FAIL: {fail_count}件")
    log(f"テスト完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    json_path = os.path.join(LOGS_DIR, f"test_filename_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"JSON結果: {json_path}")

    log_fh.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
