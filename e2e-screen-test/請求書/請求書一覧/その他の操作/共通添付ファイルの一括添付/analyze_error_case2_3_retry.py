"""
Case 2 (11ファイル) と Case 3 (合計10.5MB) の再分析。
前回は既添付済み請求書を使ったため「添付数上限を超過」エラーが出た可能性あり。
今回は一覧画面の後ろ（index=6, 7）の未使用請求書を使用して純粋なエラーを確認する。

追加: Case 6 (10ファイル正常系) も確認 → ファイル数10件が本当に上限内か検証
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
LOG_FILE = os.path.join(RESULT_DIR, f"analyze_error_case23_{timestamp}.log")
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


def login(page, email, password):
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


def analyze_case(page, case_name, file_paths, invoice_index, prefix):
    """1ケースの分析を実行"""
    log(f"\n{'=' * 70}")
    log(f"分析ケース: {case_name}")
    total_size = sum(os.path.getsize(f) for f in file_paths)
    log(f"ファイル数: {len(file_paths)}, 合計: {total_size / 1024 / 1024:.2f} MB")
    log(f"使用請求書: index={invoice_index}")
    log(f"{'=' * 70}")

    # 一覧画面に戻り、請求書を選択
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
    log(f"チェックボックス数: {len(checkboxes)}")
    if invoice_index >= len(checkboxes):
        log(f"ERROR: index={invoice_index} がチェックボックス数を超えています")
        return
    checkboxes[invoice_index].click(force=True)
    page.wait_for_timeout(500)

    # 選択した請求書の情報を取得
    row_info = page.evaluate(f"""() => {{
        const rows = document.querySelectorAll('table tbody tr');
        if ({invoice_index} < rows.length) {{
            const cells = Array.from(rows[{invoice_index}].querySelectorAll('td'));
            return cells.map(td => td.innerText.trim().substring(0, 50));
        }}
        return [];
    }}""")
    log(f"選択した請求書行: {row_info[:7]}")

    # モーダルを開く
    page.get_by_role("button", name="その他の操作").click()
    page.wait_for_timeout(1000)
    attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
    attach_item.first.click()
    page.locator('[role="dialog"] h2:has-text("共通添付ファイルの一括添付")').wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(1000)
    log("モーダルが開きました")

    # Step 1: ファイルをセット
    log("\n--- Step 1: ファイル選択 ---")
    file_input = page.locator('input[type="file"]')
    file_input.set_input_files(file_paths)
    page.wait_for_timeout(3000)

    # Step 1 状態チェック
    step1 = page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return { exists: false };
        const errors = [];
        d.querySelectorAll('[class*="error"], [class*="red"]').forEach(el => {
            const t = el.textContent.trim();
            if (t) errors.push(t.substring(0, 200));
        });
        const headings = [];
        d.querySelectorAll('h3, h4').forEach(h => headings.push(h.textContent.trim()));
        const confirmBtn = Array.from(d.querySelectorAll('button')).find(b => b.innerText.includes('確認へ進む'));
        return {
            exists: true,
            errors: errors,
            headings: headings,
            confirmEnabled: confirmBtn ? !confirmBtn.disabled : null,
            text: d.innerText.substring(0, 2000)
        };
    }""")

    page.screenshot(path=os.path.join(RESULT_DIR, f"{prefix}_step1.png"))
    log(f"見出し: {step1.get('headings', [])}")
    log(f"エラー要素: {step1.get('errors', [])[:5]}")
    log(f"「確認へ進む」: {'enabled' if step1.get('confirmEnabled') else 'disabled'}")

    if step1.get("errors"):
        log(f"★ Step 1 でエラー検出!")
        # テキストからサイズ/数に関するメッセージを抽出
        for line in step1.get("text", "").split("\n"):
            kws = ["エラー", "上限", "超過", "サイズ", "制限", "ファイル数", "MB", "件"]
            if any(kw in line for kw in kws):
                log(f"  >> {line.strip()[:200]}")

    # Step 1 でブロックされなければ Step 2 へ
    if step1.get("confirmEnabled"):
        log("\n--- Step 2: 確認画面へ遷移 ---")
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)

        page.screenshot(path=os.path.join(RESULT_DIR, f"{prefix}_step2_initial.png"))

        # 非同期判定を待つ (最大30秒)
        log("非同期判定完了を待機 (最大30秒)...")
        exec_btn = page.get_by_role("button", name="添付を実行する")
        exec_enabled = False
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"「添付を実行する」: enabled (待機{i+1}秒)")
                exec_enabled = True
                break
        else:
            log("「添付を実行する」: 30秒経過してもdisabled")

        # 判定後の状態
        step2 = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return { exists: false };
            const errors = [];
            d.querySelectorAll('[class*="error"], [class*="red"]').forEach(el => {
                const t = el.textContent.trim();
                if (t) errors.push(t.substring(0, 300));
            });
            const headings = [];
            d.querySelectorAll('h3, h4').forEach(h => headings.push(h.textContent.trim()));

            // テーブル判定列
            const table = d.querySelector('table');
            const judgments = [];
            if (table) {
                table.querySelectorAll('tbody tr').forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td'));
                    const lastCell = cells[cells.length - 1];
                    if (lastCell) judgments.push(lastCell.textContent.trim());
                });
            }

            // フッターメッセージ
            const footerP = d.querySelector('footer p, div:last-child p');
            let footerMsg = '';
            // 「添付を実行可能です」or「エラーがあります」を探す
            d.querySelectorAll('p, span').forEach(el => {
                const t = el.textContent.trim();
                if (t.includes('実行可能') || t.includes('エラーがあります') || t.includes('再選択')) {
                    footerMsg = t;
                }
            });

            return {
                exists: true,
                errors: errors,
                headings: headings,
                judgments: judgments,
                footerMsg: footerMsg,
                text: d.innerText.substring(0, 3000)
            };
        }""")

        page.screenshot(path=os.path.join(RESULT_DIR, f"{prefix}_step2_final.png"))
        log(f"見出し: {step2.get('headings', [])}")
        log(f"判定列: {step2.get('judgments', [])}")
        log(f"フッター: {step2.get('footerMsg', '')}")
        log(f"エラー要素: {step2.get('errors', [])[:5]}")
        log(f"「添付を実行する」: {'enabled' if exec_enabled else 'disabled'}")

        if step2.get("errors"):
            log(f"★ Step 2 でエラー検出!")
            for line in step2.get("text", "").split("\n"):
                kws = ["エラー", "上限", "超過", "サイズ", "ファイル数", "MB"]
                if any(kw in line for kw in kws):
                    log(f"  >> {line.strip()[:200]}")
    else:
        log("Step 1 でブロック（「確認へ進む」disabled）→ Step 2 スキップ")

    # モーダルを閉じる
    try:
        close_btn = page.get_by_role("button", name="閉じる")
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
        else:
            back_btn = page.get_by_role("button", name="戻る")
            if back_btn.count() > 0:
                back_btn.first.click(force=True)
                page.wait_for_timeout(500)
                close_btn2 = page.get_by_role("button", name="閉じる")
                if close_btn2.count() > 0:
                    close_btn2.first.click(force=True)
    except:
        pass
    page.wait_for_timeout(1000)


def main():
    global log_fh
    log_fh = open(LOG_FILE, "w", encoding="utf-8")

    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")

    log(f"=== Case 2/3 再分析（未使用請求書） ===")
    log(f"日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ケース定義
    cases = [
        {
            "name": "Case 2-retry: 11ファイル (未使用請求書 index=6)",
            "files": [os.path.join(FILESIZE_DIR, "04_11files_upload", f"file_{i:02d}.pdf") for i in range(1, 12)],
            "index": 6,
            "prefix": "err_case2r",
        },
        {
            "name": "Case 3-retry: 合計10.5MB (未使用請求書 index=7)",
            "files": [os.path.join(FILESIZE_DIR, "06_total_10MB_over", f"file_{i:02d}.pdf") for i in range(1, 6)],
            "index": 7,
            "prefix": "err_case3r",
        },
        {
            "name": "Case 6: 10ファイル正常系 (未使用請求書 index=8)",
            "files": [os.path.join(FILESIZE_DIR, "03_10files_upload", f"file_{i:02d}.pdf") for i in range(1, 11)],
            "index": 8,
            "prefix": "err_case6_10files",
        },
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        context.set_default_timeout(30000)
        page = context.new_page()

        login(page, email, password)

        for case in cases:
            try:
                analyze_case(page, case["name"], case["files"], case["index"], case["prefix"])
            except Exception as e:
                log(f"例外発生: {e}")
                try:
                    page.screenshot(path=os.path.join(RESULT_DIR, f"{case['prefix']}_exception.png"))
                except:
                    pass

        browser.close()

    log(f"\n=== 再分析完了: {datetime.now().strftime('%H:%M:%S')} ===")
    log_fh.close()


if __name__ == "__main__":
    main()
