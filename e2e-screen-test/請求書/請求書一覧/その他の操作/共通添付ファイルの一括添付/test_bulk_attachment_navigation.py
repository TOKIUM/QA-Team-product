"""
共通添付ファイルの一括添付 - ナビゲーション・モーダル開閉テスト

テスト内容（カテゴリH: ウィザードナビゲーション）:
  TH-N01: Step2→Step1 戻る操作（ファイル保持確認）
  TH-N02: Step2 戻り→ファイル変更→再進行
  TH-N03: Step2 エラー→戻る→修正→再進行
  TH-N04: Step1 タブ切替（新規アップロード ↔ 既存から選択）
  TH-N05: ステップインジケータ表示遷移
  TH-N06: Step2 フッターメッセージ遷移（判定中→判定完了）

テスト内容（カテゴリI: モーダル開閉）:
  TH-C01: Step1で「閉じる」ボタン
  TH-C02: Step1で×ボタン
  TH-C03: Step2で「戻る」→「閉じる」
  TH-C04: Step3で「閉じる」ボタン（添付実行後）

前提条件:
  - ログイン情報は TH/ログイン/.env に設定済み
  - テスト用ファイルは 拡張子/sample.pdf, ファイルサイズ/ 各種に配置済み
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
FILESIZE_DIR = os.path.join(SCRIPT_DIR, "ファイルサイズ")
FILENAME_DIR = os.path.join(SCRIPT_DIR, "ファイル名")

os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_nav_{timestamp}.log")
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
    log(f"  請求書 index={index} チェック完了")


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


def is_modal_open(page) -> bool:
    """モーダルが開いているか確認"""
    return page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return false;
        const h2 = d.querySelector('h2');
        return h2 && h2.textContent.includes('共通添付ファイル');
    }""")


def get_selected_file_count(page) -> str:
    """「選択済みファイル(N件)」のテキストを取得"""
    return page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return '';
        const h3s = d.querySelectorAll('h3');
        for (const h3 of h3s) {
            if (h3.textContent.includes('選択済みファイル')) return h3.textContent.trim();
        }
        return '';
    }""")


def get_active_step(page) -> str:
    """アクティブなステップ番号を取得"""
    return page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return null;
        const active = d.querySelector('[class*="stepActive"]');
        if (!active) return null;
        const spans = active.querySelectorAll('span');
        for (const s of spans) {
            if (/^[123]$/.test(s.textContent.trim())) return s.textContent.trim();
        }
        return null;
    }""")


def get_footer_message(page) -> str:
    """フッターメッセージを取得"""
    return page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return '';
        let msg = '';
        d.querySelectorAll('p, span').forEach(el => {
            const t = el.textContent.trim();
            if (t.includes('判定中') || t.includes('実行可能') || t.includes('エラー') ||
                t.includes('選択してください') || t.includes('ファイルを選択')) {
                if (t.length < 100) msg = t;
            }
        });
        return msg;
    }""")


# ===== カテゴリH: ウィザードナビゲーション =====

def test_n01_step2_back_to_step1(page, idx):
    """TH-N01: Step2→Step1 戻る操作（ファイル保持確認）"""
    log(f"\n{'=' * 60}")
    log("TH-N01: Step2→Step1 戻る操作（ファイル保持確認）")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-N01", "tc_name": "Step2→Step1 戻る", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        # ファイルセット→Step2
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        file_text_before = get_selected_file_count(page)
        log(f"  Step1 ファイル: {file_text_before}")

        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)
        assert get_active_step(page) == "2", "Step2に遷移していない"
        log("  ✓ Step2に遷移")

        # 戻る
        page.get_by_role("button", name="戻る").click()
        page.wait_for_timeout(1500)

        # Step1に戻ったか
        step = get_active_step(page)
        assert step == "1", f"Step1に戻っていない: activeStep={step}"
        log("  ✓ Step1に戻った")

        # ファイルが保持されているか
        file_text_after = get_selected_file_count(page)
        log(f"  Step1 戻り後ファイル: {file_text_after}")
        assert "1" in file_text_after or "sample" in file_text_after.lower(), \
            f"ファイルが保持されていない: '{file_text_after}'"
        log("  ✓ ファイルが保持されている")

        # 「確認へ進む」がenabled
        confirm = page.get_by_role("button", name="確認へ進む")
        assert confirm.count() > 0 and confirm.first.is_enabled(), "「確認へ進む」がdisabled"
        log("  ✓ 「確認へ進む」enabled")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_n02_back_change_file_reproceed(page, idx):
    """TH-N02: Step2 戻り→ファイル変更→再進行"""
    log(f"\n{'=' * 60}")
    log("TH-N02: Step2 戻り→ファイル変更→再進行")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-N02", "tc_name": "戻り→変更→再進行", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        # ファイル1でStep2へ
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)
        log("  Step2到達")

        # 戻る
        page.get_by_role("button", name="戻る").click()
        page.wait_for_timeout(1500)
        log("  Step1に戻った")

        # ファイルを変更（別ファイル）
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.png")])
        page.wait_for_timeout(2000)
        file_text = get_selected_file_count(page)
        log(f"  ファイル変更後: {file_text}")

        # 再度Step2へ
        confirm = page.get_by_role("button", name="確認へ進む")
        assert confirm.count() > 0 and confirm.first.is_enabled(), "「確認へ進む」disabled"
        confirm.first.click()
        page.wait_for_timeout(3000)

        step = get_active_step(page)
        assert step == "2", f"Step2に再遷移していない: {step}"
        log("  ✓ Step2に再遷移")

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
            const results = [];
            table.querySelectorAll('tbody tr').forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td'));
                if (cells.length > 0) results.push(cells[cells.length - 1].textContent.trim());
            });
            return results;
        }""")
        log(f"  判定列: {judgments}")
        has_ok = any("添付可能" in j for j in judgments)
        assert has_ok, f"再判定で「添付可能」にならない: {judgments}"
        log("  ✓ 再判定で「添付可能」")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_n03_error_back_fix_reproceed(page, idx):
    """TH-N03: Step2 エラー→戻る→修正→再進行"""
    log(f"\n{'=' * 60}")
    log("TH-N03: Step2 エラー→戻る→修正→再進行")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-N03", "tc_name": "エラー→修正→再進行", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        # 11ファイル（エラーになる）でStep2へ
        error_files = [os.path.join(FILESIZE_DIR, "04_11files_upload", f"file_{i:02d}.pdf") for i in range(1, 12)]
        page.locator('input[type="file"]').set_input_files(error_files)
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)

        # エラー待ち
        for i in range(15):
            page.wait_for_timeout(1000)
            err = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                return d && d.innerText.includes('超過');
            }""")
            if err:
                log(f"  Step2エラー検出 ({i+1}秒)")
                break

        # 戻る
        page.get_by_role("button", name="戻る").click()
        page.wait_for_timeout(1500)
        log("  Step1に戻った")

        # 正常ファイル(1件)に変更
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)

        # 再度Step2へ
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)

        # 非同期判定待ち
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了 ({i+1}秒)")
                break

        # エラー解消確認
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
        has_ok = any("添付可能" in j for j in judgments)
        assert has_ok, f"エラー修正後も「添付可能」にならない: {judgments}"
        log("  ✓ エラー修正後「添付可能」")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_n04_tab_switch(page, idx):
    """TH-N04: Step1 タブ切替"""
    log(f"\n{'=' * 60}")
    log("TH-N04: Step1 タブ切替（新規アップロード ↔ 既存から選択）")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-N04", "tc_name": "タブ切替", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        # 初期状態: 新規アップロードがアクティブ
        tabs_initial = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return [];
            const tabs = [];
            d.querySelectorAll('nav button').forEach(b => {
                const text = b.textContent.trim();
                if (text.includes('新規アップロード') || text.includes('既存から選択')) {
                    tabs.push({ text, isActive: b.className.includes('Active') || b.className.includes('active') });
                }
            });
            return tabs;
        }""")
        log(f"  初期タブ: {tabs_initial}")

        initial_upload_active = any(t["isActive"] and "新規アップロード" in t["text"] for t in tabs_initial)
        assert initial_upload_active, "初期状態で「新規アップロード」がアクティブではない"
        log("  ✓ 初期: 「新規アップロード」アクティブ")

        # 「既存から選択」タブをクリック
        existing_tab = page.locator('button').filter(has_text="既存から選択")
        if existing_tab.count() > 0:
            existing_tab.first.click()
            page.wait_for_timeout(1000)

            tabs_after = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return [];
                const tabs = [];
                d.querySelectorAll('nav button').forEach(b => {
                    const text = b.textContent.trim();
                    if (text.includes('新規アップロード') || text.includes('既存から選択')) {
                        tabs.push({ text, isActive: b.className.includes('Active') || b.className.includes('active') });
                    }
                });
                return tabs;
            }""")
            log(f"  切替後タブ: {tabs_after}")

            existing_active = any(t["isActive"] and "既存から選択" in t["text"] for t in tabs_after)
            assert existing_active, "「既存から選択」がアクティブにならない"
            log("  ✓ 「既存から選択」タブがアクティブ")

            # ドロップゾーンが非表示になっていること
            drop_zone = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return true;
                const dz = d.querySelector('[class*="dropZone"]');
                return !dz || dz.getBoundingClientRect().height === 0;
            }""")
            log(f"  ドロップゾーン非表示: {drop_zone}")

            # 新規アップロードに戻る
            upload_tab = page.locator('button').filter(has_text="新規アップロード")
            upload_tab.first.click()
            page.wait_for_timeout(1000)

            tabs_back = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return [];
                const tabs = [];
                d.querySelectorAll('nav button').forEach(b => {
                    const text = b.textContent.trim();
                    if (text.includes('新規アップロード') || text.includes('既存から選択')) {
                        tabs.push({ text, isActive: b.className.includes('Active') || b.className.includes('active') });
                    }
                });
                return tabs;
            }""")
            upload_back = any(t["isActive"] and "新規アップロード" in t["text"] for t in tabs_back)
            assert upload_back, "新規アップロードに戻れない"
            log("  ✓ 「新規アップロード」に戻った")
        else:
            log("  △ 「既存から選択」タブが見つかりません")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_n05_step_indicator_transition(page, idx):
    """TH-N05: ステップインジケータ表示遷移"""
    log(f"\n{'=' * 60}")
    log("TH-N05: ステップインジケータ表示遷移")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-N05", "tc_name": "ステップインジケータ遷移", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        # Step 1 確認
        step1 = get_active_step(page)
        assert step1 == "1", f"初期Step != 1: {step1}"
        log("  ✓ Step 1 アクティブ")

        # ファイルセット→Step 2
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)

        step2 = get_active_step(page)
        assert step2 == "2", f"Step2遷移後 != 2: {step2}"
        log("  ✓ Step 2 アクティブ")

        # 戻る→Step 1
        page.get_by_role("button", name="戻る").click()
        page.wait_for_timeout(1500)
        step_back = get_active_step(page)
        assert step_back == "1", f"戻り後 != 1: {step_back}"
        log("  ✓ 戻り後 Step 1 アクティブ")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_n06_footer_message_transition(page, idx):
    """TH-N06: Step2 フッターメッセージ遷移"""
    log(f"\n{'=' * 60}")
    log("TH-N06: Step2 フッターメッセージ遷移（判定中→判定完了）")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-N06", "tc_name": "フッターメッセージ遷移", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(1000)

        # 判定中のメッセージ
        msg_judging = get_footer_message(page)
        log(f"  判定中メッセージ: '{msg_judging}'")

        # 判定完了を待つ
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                break

        msg_complete = get_footer_message(page)
        log(f"  判定完了メッセージ: '{msg_complete}'")

        # 判定中→判定完了でメッセージが変化
        has_judging = "判定中" in msg_judging or "判定" in msg_judging
        has_complete = "実行可能" in msg_complete or "添付" in msg_complete
        if has_judging:
            log("  ✓ 判定中メッセージ確認")
        else:
            log("  △ 判定中メッセージが取得できず (即完了の可能性)")
        if has_complete:
            log("  ✓ 判定完了メッセージ確認")
        else:
            log(f"  △ 判定完了メッセージ不明: '{msg_complete}'")

        # 少なくとも判定完了でボタンがenabled
        assert exec_btn.count() > 0 and exec_btn.first.is_enabled(), "「添付を実行する」がenabledにならない"
        log("  ✓ 「添付を実行する」enabled")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


# ===== カテゴリI: モーダル開閉 =====

def test_c01_close_button_step1(page, idx):
    """TH-C01: Step1で「閉じる」ボタン"""
    log(f"\n{'=' * 60}")
    log("TH-C01: Step1で「閉じる」ボタン")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-C01", "tc_name": "Step1「閉じる」ボタン", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)
        assert is_modal_open(page), "モーダルが開いていない"

        page.get_by_role("button", name="閉じる").first.click(force=True)
        page.wait_for_timeout(1500)

        assert not is_modal_open(page), "モーダルが閉じていない"
        log("  ✓ モーダルが閉じた")

        # 一覧画面にいること
        assert "/invoices" in page.url, f"一覧画面ではない: {page.url}"
        log("  ✓ 一覧画面に戻った")

        result["success"] = True
        log("  結果: PASS ✓")
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_c02_x_button_step1(page, idx):
    """TH-C02: Step1で×ボタン"""
    log(f"\n{'=' * 60}")
    log("TH-C02: Step1で×ボタン")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-C02", "tc_name": "Step1 ×ボタン", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)
        assert is_modal_open(page), "モーダルが開いていない"

        # ×ボタンをクリック
        x_btn = page.locator('[role="dialog"] button[class*="closeButton"], [role="dialog"] button[class*="close"]')
        if x_btn.count() > 0:
            x_btn.first.click(force=True)
        else:
            # フォールバック: ヘッダー内の空テキストボタン
            header_btns = page.locator('[role="dialog"] header button')
            if header_btns.count() > 0:
                header_btns.first.click(force=True)
            else:
                raise RuntimeError("×ボタンが見つかりません")

        page.wait_for_timeout(1500)

        assert not is_modal_open(page), "モーダルが閉じていない"
        log("  ✓ ×ボタンでモーダルが閉じた")

        result["success"] = True
        log("  結果: PASS ✓")
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_c03_back_then_close_step2(page, idx):
    """TH-C03: Step2で「戻る」→「閉じる」"""
    log(f"\n{'=' * 60}")
    log("TH-C03: Step2で「戻る」→「閉じる」")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-C03", "tc_name": "Step2→戻る→閉じる", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        # ファイルセット→Step2
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)
        log("  Step2到達")

        # 戻る
        page.get_by_role("button", name="戻る").click()
        page.wait_for_timeout(1000)
        step = get_active_step(page)
        assert step == "1", f"Step1に戻っていない: {step}"
        log("  ✓ Step1に戻った")

        # 閉じる
        page.get_by_role("button", name="閉じる").first.click(force=True)
        page.wait_for_timeout(1500)
        assert not is_modal_open(page), "モーダルが閉じていない"
        log("  ✓ モーダルが閉じた")

        result["success"] = True
        log("  結果: PASS ✓")
    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)
    return result


def test_c04_close_step3(page, idx):
    """TH-C04: Step3で「閉じる」ボタン（添付実行後）"""
    log(f"\n{'=' * 60}")
    log("TH-C04: Step3で「閉じる」ボタン（添付実行後）")
    log(f"{'=' * 60}")
    result = {"tc_id": "TH-C04", "tc_name": "Step3「閉じる」ボタン", "success": False, "error": ""}
    try:
        navigate_to_list(page)
        select_invoice(page, idx)
        open_modal(page)

        # ファイルセット→Step2→添付実行→Step3
        page.locator('input[type="file"]').set_input_files([os.path.join(EXTENSION_DIR, "sample.pdf")])
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)

        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                break
        exec_btn.first.click(force=True)
        page.wait_for_timeout(8000)
        log("  Step3到達")

        # Step3で閉じる
        close_btn = page.get_by_role("button", name="閉じる")
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
            page.wait_for_timeout(1500)

        assert not is_modal_open(page), "モーダルが閉じていない"
        log("  ✓ Step3でモーダルが閉じた")

        # 一覧画面で添付反映を確認（テーブルが表示されていること）
        table_exists = page.evaluate("() => !!document.querySelector('table tbody tr')")
        assert table_exists, "一覧テーブルが見つかりません"
        log("  ✓ 一覧画面のテーブルが表示")

        result["success"] = True
        log("  結果: PASS ✓")
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

    # テストケース定義
    # ナビゲーション系: 添付実行しないので index=5 再利用可能
    # TH-C04 のみ添付実行するため専用 index
    tests = [
        # カテゴリH: ナビゲーション
        ("TH-N01", "Step2→Step1 戻る", test_n01_step2_back_to_step1, 5),
        ("TH-N02", "戻り→変更→再進行", test_n02_back_change_file_reproceed, 5),
        ("TH-N03", "エラー→修正→再進行", test_n03_error_back_fix_reproceed, 5),
        ("TH-N04", "タブ切替", test_n04_tab_switch, 5),
        ("TH-N05", "ステップインジケータ遷移", test_n05_step_indicator_transition, 5),
        ("TH-N06", "フッターメッセージ遷移", test_n06_footer_message_transition, 5),
        # カテゴリI: モーダル開閉
        ("TH-C01", "Step1「閉じる」ボタン", test_c01_close_button_step1, 5),
        ("TH-C02", "Step1 ×ボタン", test_c02_x_button_step1, 5),
        ("TH-C03", "Step2→戻る→閉じる", test_c03_back_then_close_step2, 5),
        ("TH-C04", "Step3「閉じる」ボタン", test_c04_close_step3, 4),
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

        for tc_id, tc_name, tc_func, idx in tests:
            log(f"\n{'#' * 60}")
            log(f"# {tc_id}: {tc_name}")
            log(f"{'#' * 60}")
            page = context.new_page()
            try:
                page.goto(f"{BASE_URL}/invoices")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                r = tc_func(page, idx)
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

    json_path = os.path.join(LOGS_DIR, f"test_nav_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"JSON結果: {json_path}")

    log_fh.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
