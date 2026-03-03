"""
Case 1 (10.1MBファイル) のみを再分析するスクリプト。
前回の分析でモーダルが開かないエラーが発生したため、単独で再実行。
"""

import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://invoicing-staging.keihi.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")
FILESIZE_DIR = os.path.join(SCRIPT_DIR, "ファイルサイズ")

os.makedirs(RESULT_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(RESULT_DIR, f"analyze_error_case1_{timestamp}.log")
log_fh = None


def log(msg):
    global log_fh
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    if log_fh:
        log_fh.write(line + "\n")
        log_fh.flush()
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode())


def load_env():
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


def main():
    global log_fh
    log_fh = open(LOG_FILE, "w", encoding="utf-8")

    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")

    file_path = os.path.join(FILESIZE_DIR, "02_single_10MB_over", "file_10.1MB.pdf")
    file_size = os.path.getsize(file_path)
    log(f"=== Case 1 再分析: ファイルサイズ超過 (10.1MB) ===")
    log(f"ファイル: {file_path}")
    log(f"サイズ: {file_size / 1024 / 1024:.2f} MB ({file_size} bytes)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        context.set_default_timeout(30000)
        page = context.new_page()

        # ログイン
        log("ログイン中...")
        page.goto(f"{BASE_URL}/login")
        page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
        page.get_by_label("メールアドレス").fill(email)
        page.get_by_label("パスワード").fill(password)
        page.wait_for_timeout(500)
        page.get_by_role("button", name="ログイン", exact=True).click()
        for _ in range(30):
            if "/invoices" in page.url and "/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        log(f"ログイン完了: {page.url}")

        # 一覧画面で5番目のチェックボックスを選択 (他のケースと被らないように)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
        log(f"チェックボックス数: {len(checkboxes)}")
        checkboxes[5].click(force=True)  # index=5 (6件目) を使用
        page.wait_for_timeout(500)
        log("6件目チェック完了")

        # 「その他の操作」→「共通添付ファイルの一括添付」
        log("「その他の操作」クリック...")
        page.get_by_role("button", name="その他の操作").click()
        page.wait_for_timeout(1500)

        # メニュー項目のスクリーンショット
        page.screenshot(path=os.path.join(RESULT_DIR, "err_case1_retry_menu.png"))

        # メニューのDOM分析
        menu_info = page.evaluate("""() => {
            const items = document.querySelectorAll('[role="menuitem"]');
            const result = [];
            items.forEach(el => {
                result.push({
                    text: el.textContent.trim(),
                    visible: el.getBoundingClientRect().width > 0,
                    disabled: el.getAttribute('aria-disabled') === 'true' || el.disabled
                });
            });
            return result;
        }""")
        log("メニュー項目:")
        for item in menu_info:
            log(f"  - \"{item['text']}\" visible={item['visible']} disabled={item['disabled']}")

        # 「共通添付ファイルの一括添付」をクリック
        log("「共通添付ファイルの一括添付」クリック...")
        attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
        if attach_item.count() > 0:
            attach_item.first.click()
        else:
            log("menuitem が見つかりません。button で試行...")
            page.locator('button:has-text("共通添付ファイルの一括添付")').first.click()

        # モーダルが開くのを待つ (タイムアウトを長めに設定)
        log("モーダルオープン待機 (最大20秒)...")
        try:
            page.locator('[role="dialog"] h2:has-text("共通添付ファイルの一括添付")').wait_for(state="visible", timeout=20000)
            log("モーダルが開きました ✓")
        except Exception as e:
            log(f"モーダルオープン失敗: {e}")
            # ダイアログの存在を確認
            dialog_exists = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return 'dialog not found';
                return {
                    text: d.innerText.substring(0, 1000),
                    rect: d.getBoundingClientRect(),
                    display: window.getComputedStyle(d).display,
                    visibility: window.getComputedStyle(d).visibility
                };
            }""")
            log(f"ダイアログ情報: {dialog_exists}")
            page.screenshot(path=os.path.join(RESULT_DIR, "err_case1_retry_modal_fail.png"))
            browser.close()
            log_fh.close()
            return

        page.wait_for_timeout(1000)

        # ===== Step 1: 10.1MB ファイルをセット =====
        log("\n--- Step 1: 10.1MB ファイルをセット ---")
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files([file_path])
        page.wait_for_timeout(3000)

        # Step 1 状態をキャプチャ
        step1_state = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return { exists: false };

            const buttons = [];
            d.querySelectorAll('button').forEach(b => {
                const r = b.getBoundingClientRect();
                if (r.width > 0 || r.height > 0) {
                    buttons.push({ text: b.innerText.trim().substring(0, 100), disabled: b.disabled });
                }
            });

            const errors = [];
            d.querySelectorAll('[class*="red"], [class*="error"], [class*="danger"], [class*="warning"], [class*="alert"]').forEach(el => {
                const text = el.textContent.trim();
                if (text) errors.push({ text: text.substring(0, 300), class: el.className.substring(0, 200), tag: el.tagName });
            });

            const headings = [];
            d.querySelectorAll('h3, h4').forEach(h => headings.push({ tag: h.tagName, text: h.textContent.trim() }));

            return {
                exists: true,
                fullText: d.innerText.substring(0, 3000),
                buttons: buttons,
                errors: errors,
                headings: headings
            };
        }""")

        page.screenshot(path=os.path.join(RESULT_DIR, "err_case1_retry_step1.png"))

        log("ボタン状態:")
        for b in step1_state.get("buttons", []):
            log(f"  - \"{b['text']}\" disabled={b['disabled']}")

        if step1_state.get("errors"):
            log(f"エラー要素 ({len(step1_state['errors'])}件):")
            for e in step1_state["errors"]:
                log(f"  [{e['tag']}] {e['text'][:200]}")
                log(f"    class: {e['class'][:200]}")
        else:
            log("エラー要素: なし")

        log(f"見出し:")
        for h in step1_state.get("headings", []):
            log(f"  <{h['tag']}> {h['text']}")

        # 「確認へ進む」ボタンの状態
        confirm_btn = page.get_by_role("button", name="確認へ進む")
        confirm_enabled = confirm_btn.count() > 0 and confirm_btn.first.is_enabled()
        log(f"「確認へ進む」ボタン: {'enabled' if confirm_enabled else 'disabled'}")

        # テキスト全体からエラーパターンを探す
        full_text = step1_state.get("fullText", "")
        error_keywords = ["エラー", "上限", "超過", "不可", "サイズ", "制限", "MB"]
        found = [kw for kw in error_keywords if kw in full_text]
        if found:
            log(f"テキスト内エラー関連キーワード: {found}")
            for line in full_text.split("\n"):
                if any(kw in line for kw in found):
                    log(f"  >> {line.strip()[:200]}")

        # ===== Step 1 でエラーなし＆ボタンenabled なら Step 2 へ =====
        if confirm_enabled:
            log("\n--- Step 2: 確認画面へ遷移 ---")
            confirm_btn.first.click()
            page.wait_for_timeout(3000)

            page.screenshot(path=os.path.join(RESULT_DIR, "err_case1_retry_step2_initial.png"))

            # 非同期判定を待つ (最大20秒)
            log("非同期判定完了を待機 (最大20秒)...")
            exec_btn = page.get_by_role("button", name="添付を実行する")
            for i in range(20):
                page.wait_for_timeout(1000)
                if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                    log(f"「添付を実行する」ボタン: enabled (待機{i+1}秒)")
                    break
            else:
                log("「添付を実行する」ボタン: 20秒経過してもdisabledのまま")

            # 判定後の状態をキャプチャ
            step2_state = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return { exists: false };

                const buttons = [];
                d.querySelectorAll('button').forEach(b => {
                    const r = b.getBoundingClientRect();
                    if (r.width > 0 || r.height > 0) {
                        buttons.push({ text: b.innerText.trim().substring(0, 100), disabled: b.disabled });
                    }
                });

                const errors = [];
                d.querySelectorAll('[class*="red"], [class*="error"], [class*="danger"], [class*="warning"], [class*="alert"]').forEach(el => {
                    const text = el.textContent.trim();
                    if (text) errors.push({ text: text.substring(0, 300), class: el.className.substring(0, 200), tag: el.tagName });
                });

                const headings = [];
                d.querySelectorAll('h3, h4').forEach(h => headings.push({ tag: h.tagName, text: h.textContent.trim() }));

                // テーブル情報
                const table = d.querySelector('table');
                const tableInfo = { exists: false };
                if (table) {
                    tableInfo.exists = true;
                    tableInfo.headers = [];
                    tableInfo.rows = [];
                    table.querySelectorAll('th').forEach(th => tableInfo.headers.push(th.textContent.trim()));
                    table.querySelectorAll('tbody tr').forEach(tr => {
                        const cells = [];
                        tr.querySelectorAll('td').forEach(td => cells.push(td.textContent.trim().substring(0, 100)));
                        tableInfo.rows.push(cells);
                    });
                }

                return {
                    exists: true,
                    fullText: d.innerText.substring(0, 3000),
                    buttons: buttons,
                    errors: errors,
                    headings: headings,
                    table: tableInfo
                };
            }""")

            page.screenshot(path=os.path.join(RESULT_DIR, "err_case1_retry_step2_final.png"))

            log("ボタン状態:")
            for b in step2_state.get("buttons", []):
                log(f"  - \"{b['text']}\" disabled={b['disabled']}")

            if step2_state.get("errors"):
                log(f"エラー要素 ({len(step2_state['errors'])}件):")
                for e in step2_state["errors"]:
                    log(f"  [{e['tag']}] {e['text'][:200]}")
            else:
                log("エラー要素: なし")

            log(f"見出し:")
            for h in step2_state.get("headings", []):
                log(f"  <{h['tag']}> {h['text']}")

            if step2_state.get("table", {}).get("exists"):
                log(f"テーブルヘッダー: {step2_state['table']['headers']}")
                for i, row in enumerate(step2_state['table']['rows']):
                    log(f"  行{i}: {row}")

            # テキスト全体からエラーパターン
            full_text2 = step2_state.get("fullText", "")
            found2 = [kw for kw in error_keywords if kw in full_text2]
            if found2:
                log(f"Step 2テキスト内エラーキーワード: {found2}")
                for line in full_text2.split("\n"):
                    if any(kw in line for kw in found2):
                        log(f"  >> {line.strip()[:200]}")

            # 「添付を実行する」の状態
            exec_enabled = exec_btn.count() > 0 and exec_btn.first.is_enabled()
            log(f"「添付を実行する」: {'enabled' if exec_enabled else 'disabled'}")
        else:
            log("Step 1 でブロック（「確認へ進む」disabled）")

        # モーダルを閉じる
        try:
            close_btn = page.get_by_role("button", name="閉じる")
            if close_btn.count() > 0:
                close_btn.first.click(force=True)
        except:
            pass

        browser.close()

    log(f"\n=== Case 1 再分析完了: {datetime.now().strftime('%H:%M:%S')} ===")
    log_fh.close()


if __name__ == "__main__":
    main()
