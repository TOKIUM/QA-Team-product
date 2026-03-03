"""
共通添付ファイルの一括添付 - 複数請求書一括テスト

テスト内容（カテゴリG: 複数請求書一括添付）:
  TH-M01: 2件の請求書に1ファイル一括添付
  TH-M02: 5件の請求書に1ファイル一括添付
  TH-M03: 2件の請求書に3ファイル一括添付

前提条件:
  - ログイン情報は TH/ログイン/.env に設定済み
  - テスト用ファイルは 拡張子/ に sample.pdf, sample.png, sample.jpg 配置済み
  - 一覧画面に十分な数の請求書が存在すること（index 10-19 を使用）
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

os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_multi_{timestamp}.log")
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


def navigate_to_list(page, go_page2=False):
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    if go_page2:
        # 2ページ目に移動（チェックボックスが10件しか表示されないため）
        next_btn = page.locator('button[aria-label="Go to next page"], nav button:has-text("次"), a:has-text("次")')
        if next_btn.count() > 0:
            next_btn.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            log("  2ページ目に移動")
        else:
            # URLパラメータで直接2ページ目へ
            page.goto(f"{BASE_URL}/invoices?page=2")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            log("  2ページ目に移動（URL直接）")


def select_invoices(page, indices):
    """複数の請求書を選択する"""
    checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
    log(f"  チェックボックス数: {len(checkboxes)}")
    for idx in indices:
        if idx >= len(checkboxes):
            raise RuntimeError(f"index={idx} がチェックボックス数({len(checkboxes)})を超えています")
        checkboxes[idx].click(force=True)
        page.wait_for_timeout(300)
    log(f"  請求書 {len(indices)}件 チェック完了 (indices={indices})")


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
            log("  モーダルが開きました")
            return
        except Exception as e:
            log(f"  モーダルオープン失敗 (attempt {attempt + 1}): {e}")
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


def get_step2_table_rows(page):
    """Step2のテーブル行数と判定列の情報を取得"""
    return page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return { rowCount: 0, judgments: [], allText: '' };
        const table = d.querySelector('table');
        if (!table) return { rowCount: 0, judgments: [], allText: d.innerText.substring(0, 2000) };
        const rows = table.querySelectorAll('tbody tr');
        const judgments = [];
        rows.forEach(tr => {
            const cells = Array.from(tr.querySelectorAll('td'));
            if (cells.length > 0) {
                judgments.push(cells[cells.length - 1].textContent.trim());
            }
        });
        return {
            rowCount: rows.length,
            judgments: judgments,
            allText: d.innerText.substring(0, 2000)
        };
    }""")


def get_step3_message(page):
    """Step3の完了メッセージを取得"""
    return page.evaluate(r"""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return { found: false, message: '' };
        const fullText = d.innerText;
        const match = fullText.match(/(\d+)\s*件の請求書に添付されました/);
        return {
            found: !!match,
            message: match ? match[0] : '',
            count: match ? parseInt(match[1]) : 0,
            fullText: fullText.substring(0, 1000)
        };
    }""")


# ===== テストケース =====

def test_m01_two_invoices_one_file(page):
    """TH-M01: 2件の請求書に1ファイル一括添付"""
    log(f"\n{'=' * 60}")
    log("TH-M01: 2件の請求書に1ファイル一括添付")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-M01", "tc_name": "2件×1ファイル", "success": False, "error": ""}
    try:
        # 2ページ目を使い、index 0,1 を選択
        navigate_to_list(page, go_page2=True)
        select_invoices(page, [0, 1])
        open_modal(page)

        # Step 1: ファイル選択
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        log("  Step1: ファイル選択完了")

        # Step 2へ
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(2000)

        # 非同期判定待ち（テーブルは判定完了後に表示される）
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(60):
            page.wait_for_timeout(1000)
            table_info = get_step2_table_rows(page)
            if table_info['rowCount'] > 0 and exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了 ({i+1}秒)")
                break
            if i % 10 == 9:
                log(f"  判定中... ({i+1}秒経過, テーブル行数={table_info['rowCount']})")

        # Step2テーブル確認: 2行あること
        table_info = get_step2_table_rows(page)
        log(f"  Step2テーブル行数: {table_info['rowCount']}")
        log(f"  判定列: {table_info['judgments']}")
        assert table_info['rowCount'] == 2, f"テーブル行数が2ではない: {table_info['rowCount']}"
        log("  ✓ Step2テーブルに2行表示")

        # 全行「添付可能」
        ok_count = sum(1 for j in table_info['judgments'] if "添付可能" in j)
        assert ok_count == 2, f"「添付可能」が2件ではない: {ok_count} / {table_info['judgments']}"
        log("  ✓ 全2行「添付可能」")

        # 添付実行
        exec_btn.first.click(force=True)
        page.wait_for_timeout(8000)

        # Step3 確認
        step3 = get_step3_message(page)
        log(f"  Step3: {step3}")
        assert step3['found'], f"完了メッセージが見つからない: {step3.get('fullText', '')[:200]}"
        assert step3['count'] == 2, f"添付件数が2ではない: {step3['count']}"
        log(f"  ✓ Step3「{step3['message']}」")


        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_m02_five_invoices_one_file(page):
    """TH-M02: 5件の請求書に1ファイル一括添付"""
    log(f"\n{'=' * 60}")
    log("TH-M02: 5件の請求書に1ファイル一括添付")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-M02", "tc_name": "5件×1ファイル", "success": False, "error": ""}
    try:
        # 2ページ目、index 2-6 を選択
        navigate_to_list(page, go_page2=True)
        select_invoices(page, [2, 3, 4, 5, 6])
        open_modal(page)

        # Step 1: ファイル選択
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        log("  Step1: ファイル選択完了")

        # Step 2へ
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(2000)

        # 非同期判定待ち（テーブルは判定完了後に表示される）
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(60):
            page.wait_for_timeout(1000)
            table_info = get_step2_table_rows(page)
            if table_info['rowCount'] > 0 and exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了 ({i+1}秒)")
                break
            if i % 10 == 9:
                log(f"  判定中... ({i+1}秒経過, テーブル行数={table_info['rowCount']})")

        # Step2テーブル確認: 5行あること
        table_info = get_step2_table_rows(page)
        log(f"  Step2テーブル行数: {table_info['rowCount']}")
        log(f"  判定列: {table_info['judgments']}")
        assert table_info['rowCount'] == 5, f"テーブル行数が5ではない: {table_info['rowCount']}"
        log("  ✓ Step2テーブルに5行表示")

        # 全行「添付可能」
        ok_count = sum(1 for j in table_info['judgments'] if "添付可能" in j)
        assert ok_count == 5, f"「添付可能」が5件ではない: {ok_count} / {table_info['judgments']}"
        log("  ✓ 全5行「添付可能」")

        # 添付実行
        exec_btn.first.click(force=True)
        page.wait_for_timeout(10000)

        # Step3 確認
        step3 = get_step3_message(page)
        log(f"  Step3: {step3}")
        assert step3['found'], f"完了メッセージが見つからない: {step3.get('fullText', '')[:200]}"
        assert step3['count'] == 5, f"添付件数が5ではない: {step3['count']}"
        log(f"  ✓ Step3「{step3['message']}」")


        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_m03_two_invoices_three_files(page):
    """TH-M03: 2件の請求書に3ファイル一括添付"""
    log(f"\n{'=' * 60}")
    log("TH-M03: 2件の請求書に3ファイル一括添付")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-M03", "tc_name": "2件×3ファイル", "success": False, "error": ""}
    try:
        # 2ページ目、index 7,8 を選択
        navigate_to_list(page, go_page2=True)
        select_invoices(page, [7, 8])
        open_modal(page)

        # Step 1: 3ファイル選択
        files = [
            os.path.join(EXTENSION_DIR, "sample.pdf"),
            os.path.join(EXTENSION_DIR, "sample.png"),
            os.path.join(EXTENSION_DIR, "sample.jpg"),
        ]
        page.locator('input[type="file"]').set_input_files(files)
        page.wait_for_timeout(2000)

        # 選択済みファイル数確認
        file_count_text = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return '';
            const h3s = d.querySelectorAll('h3');
            for (const h3 of h3s) {
                if (h3.textContent.includes('選択済みファイル')) return h3.textContent.trim();
            }
            return '';
        }""")
        log(f"  Step1: {file_count_text}")
        assert "3" in file_count_text, f"選択済みファイルが3件ではない: '{file_count_text}'"
        log("  ✓ 選択済みファイル(3件)")

        # Step 2へ
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(2000)

        # 非同期判定待ち（テーブルは判定完了後に表示される）
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(60):
            page.wait_for_timeout(1000)
            table_info = get_step2_table_rows(page)
            if table_info['rowCount'] > 0 and exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了 ({i+1}秒)")
                break
            if i % 10 == 9:
                log(f"  判定中... ({i+1}秒経過, テーブル行数={table_info['rowCount']})")

        # Step2テーブル確認: 2行あること
        table_info = get_step2_table_rows(page)
        log(f"  Step2テーブル行数: {table_info['rowCount']}")
        assert table_info['rowCount'] == 2, f"テーブル行数が2ではない: {table_info['rowCount']}"
        log("  ✓ Step2テーブルに2行表示")

        # 添付するファイル数の確認（モーダル内テキスト）
        attach_file_text = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return '';
            const spans = d.querySelectorAll('span, p, h3, h4');
            for (const s of spans) {
                const t = s.textContent.trim();
                if (t.includes('添付するファイル') && t.includes('件')) return t;
            }
            return '';
        }""")
        log(f"  添付ファイル表示: '{attach_file_text}'")
        if "3" in attach_file_text:
            log("  ✓ 添付するファイル(3件)表示")

        # 全行「添付可能」確認
        ok_count = sum(1 for j in table_info['judgments'] if "添付可能" in j)
        log(f"  判定列: {table_info['judgments']}")
        assert ok_count == 2, f"「添付可能」が2件ではない: {ok_count} / {table_info['judgments']}"
        log("  ✓ 全2行「添付可能」")

        # 添付実行
        exec_btn.first.click(force=True)
        page.wait_for_timeout(8000)

        # Step3 確認
        step3 = get_step3_message(page)
        log(f"  Step3: {step3}")
        assert step3['found'], f"完了メッセージが見つからない: {step3.get('fullText', '')[:200]}"
        assert step3['count'] == 2, f"添付件数が2ではない: {step3['count']}"
        log(f"  ✓ Step3「{step3['message']}」")


        result["success"] = True
        log("  結果: PASS ✓")
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

    tests = [
        ("TH-M01", "2件×1ファイル", test_m01_two_invoices_one_file),
        ("TH-M02", "5件×1ファイル", test_m02_five_invoices_one_file),
        ("TH-M03", "2件×3ファイル", test_m03_two_invoices_three_files),
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

        for tc_id, tc_name, tc_func in tests:
            log(f"\n{'#' * 60}")
            log(f"# {tc_id}: {tc_name}")
            log(f"{'#' * 60}")
            page = context.new_page()
            try:
                page.goto(f"{BASE_URL}/invoices")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                r = tc_func(page)
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

    json_path = os.path.join(LOGS_DIR, f"test_multi_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"JSON結果: {json_path}")

    log_fh.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
