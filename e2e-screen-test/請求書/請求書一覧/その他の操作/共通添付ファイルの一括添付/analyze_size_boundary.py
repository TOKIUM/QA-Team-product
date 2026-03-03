"""
ファイルサイズ境界値を特定するための分析スクリプト。
5.0MB, 5.1MB, 9.9MB をそれぞれ未使用請求書で試行し、
実際のファイルサイズ上限を特定する。
"""

import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://invoicing-staging.keihi.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")
FILESIZE_DIR = os.path.join(SCRIPT_DIR, "ファイルサイズ")

os.makedirs(RESULT_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(RESULT_DIR, f"analyze_size_boundary_{timestamp}.log")
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


def test_file_size(page, file_paths, invoice_index, case_name):
    """1つのファイルサイズケースをテストする"""
    log(f"\n{'='*70}")
    log(f"ケース: {case_name}")
    total_size = sum(os.path.getsize(f) for f in file_paths)
    log(f"ファイル数: {len(file_paths)}, 合計: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    for fp in file_paths:
        sz = os.path.getsize(fp)
        log(f"  - {os.path.basename(fp)}: {sz:,} bytes ({sz/1024/1024:.4f} MB)")
    log(f"使用請求書: index={invoice_index}")
    log(f"{'='*70}")

    # 一覧画面に戻る
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # チェックボックス選択
    checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
    log(f"チェックボックス数: {len(checkboxes)}")
    if invoice_index >= len(checkboxes):
        log(f"ERROR: index={invoice_index} は範囲外 (max={len(checkboxes)-1})")
        return None

    checkboxes[invoice_index].click(force=True)
    page.wait_for_timeout(500)

    # 請求書行の情報
    rows = page.query_selector_all("table tbody tr")
    if invoice_index < len(rows):
        cells = rows[invoice_index].query_selector_all("td")
        row_texts = [c.inner_text().strip() for c in cells]
        log(f"選択した請求書行: {row_texts}")

    # 「その他の操作」→「共通添付ファイルの一括添付」
    page.get_by_role("button", name="その他の操作").click()
    page.wait_for_timeout(1500)

    attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
    if attach_item.count() > 0:
        attach_item.first.click()
    else:
        page.locator('button:has-text("共通添付ファイルの一括添付")').first.click()

    # モーダル待機
    try:
        page.locator('[role="dialog"] h2:has-text("共通添付ファイルの一括添付")').wait_for(
            state="visible", timeout=20000
        )
        log("モーダルが開きました")
    except Exception as e:
        log(f"モーダルオープン失敗: {e}")
        page.screenshot(path=os.path.join(RESULT_DIR, f"size_boundary_{case_name}_modal_fail.png"))
        return None

    page.wait_for_timeout(1000)

    # ファイルセット
    file_input = page.locator('input[type="file"]')
    file_input.set_input_files(file_paths)
    page.wait_for_timeout(3000)

    # Step 1 の状態確認
    headings = page.locator('[role="dialog"] h3, [role="dialog"] h4').all_inner_texts()
    log(f"Step 1 見出し: {headings}")

    # エラー要素
    error_els = page.locator('[role="dialog"] [class*="error"], [role="dialog"] [role="alert"]').all_inner_texts()
    error_els = [e.strip() for e in error_els if e.strip()]
    log(f"Step 1 エラー要素: {error_els}")

    confirm_btn = page.get_by_role("button", name="確認へ進む")
    confirm_enabled = confirm_btn.count() > 0 and confirm_btn.first.is_enabled()
    log(f"「確認へ進む」: {'enabled' if confirm_enabled else 'disabled'}")

    if not confirm_enabled:
        log(f"★ Step 1 でブロック！エラー: {error_els}")
        # モーダル閉じる
        try:
            page.get_by_role("button", name="閉じる").first.click(force=True)
        except:
            page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
        return {"step": 1, "result": "error", "errors": error_els}

    # Step 2 へ遷移
    log("\n--- Step 2: 確認画面へ遷移 ---")
    confirm_btn.first.click()
    page.wait_for_timeout(3000)

    # 非同期判定待機
    log("非同期判定完了を待機 (最大30秒)...")
    exec_btn = page.get_by_role("button", name="添付を実行する")
    for i in range(30):
        page.wait_for_timeout(1000)
        if exec_btn.count() > 0 and exec_btn.first.is_enabled():
            log(f"「添付を実行する」: enabled (待機{i+1}秒)")
            break
    else:
        log("「添付を実行する」: 30秒経過してもdisabled")

    # Step 2 状態キャプチャ
    headings2 = page.locator('[role="dialog"] h3, [role="dialog"] h4').all_inner_texts()
    log(f"Step 2 見出し: {headings2}")

    # 判定列の情報
    judgment_cells = page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return [];
        const table = d.querySelector('table');
        if (!table) return [];
        const results = [];
        const headers = [];
        table.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim()));
        const judgIdx = headers.indexOf('判定');
        if (judgIdx < 0) return ['判定列なし'];
        table.querySelectorAll('tbody tr').forEach(tr => {
            const cells = tr.querySelectorAll('td');
            if (cells[judgIdx]) results.push(cells[judgIdx].textContent.trim());
        });
        return results;
    }""")
    log(f"判定列: {judgment_cells}")

    # フッター情報
    footer_text = page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return '';
        const footer = d.querySelector('footer') || d.querySelector('[class*="footer"]');
        if (footer) return footer.textContent.trim();
        return '';
    }""")
    log(f"フッター: {footer_text}")

    error_els2 = page.locator('[role="dialog"] [class*="error"], [role="dialog"] [role="alert"]').all_inner_texts()
    error_els2 = [e.strip() for e in error_els2 if e.strip()]
    log(f"エラー要素: {error_els2}")

    exec_enabled = exec_btn.count() > 0 and exec_btn.first.is_enabled()
    log(f"「添付を実行する」: {'enabled' if exec_enabled else 'disabled'}")

    page.screenshot(path=os.path.join(RESULT_DIR, f"size_boundary_{case_name}.png"))

    # モーダル閉じる
    try:
        close_btn = page.get_by_role("button", name="閉じる")
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
        else:
            page.keyboard.press("Escape")
    except:
        page.keyboard.press("Escape")
    page.wait_for_timeout(1500)

    if exec_enabled:
        return {"step": 2, "result": "ok", "judgment": judgment_cells}
    else:
        return {"step": 2, "result": "error", "judgment": judgment_cells, "errors": error_els2}


def main():
    global log_fh
    log_fh = open(LOG_FILE, "w", encoding="utf-8")

    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")

    # テストケース定義
    test_cases = [
        {
            "name": "5.0MB_single",
            "files": [os.path.join(FILESIZE_DIR, "07_single_5MB", "file_5.0MB.pdf")],
            "index": 5,  # 未使用
        },
        {
            "name": "5.1MB_single",
            "files": [os.path.join(FILESIZE_DIR, "08_single_5MB_over_10MB_under", "file_5.1MB.pdf")],
            "index": 6,  # 未使用
        },
        {
            "name": "9.9MB_single",
            "files": [os.path.join(FILESIZE_DIR, "01_single_10MB_under", "file_9.9MB.pdf")],
            "index": 7,  # 未使用
        },
    ]

    log(f"=== ファイルサイズ境界値分析 ===")
    log(f"日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

        # 各ケース実行
        results = {}
        for tc in test_cases:
            result = test_file_size(page, tc["files"], tc["index"], tc["name"])
            results[tc["name"]] = result

        browser.close()

    # サマリー
    log(f"\n{'='*70}")
    log("=== サマリー ===")
    for name, result in results.items():
        if result is None:
            log(f"  {name}: SKIPPED (modal failure)")
        elif result["result"] == "ok":
            log(f"  {name}: ✓ OK (判定: {result.get('judgment', [])})")
        else:
            log(f"  {name}: ✗ ERROR (Step {result['step']}, エラー: {result.get('errors', result.get('judgment', []))})")

    log(f"\n=== 分析完了: {datetime.now().strftime('%H:%M:%S')} ===")
    log_fh.close()
    print(f"\nログ: {LOG_FILE}")


if __name__ == "__main__":
    main()
