"""
共通添付ファイルの一括添付 - 異常系エラー挙動分析スクリプト

目的:
  異常系テスト実装前に、実際のエラー表示を確認する。
  以下の5パターンのエラー挙動を分析:
    1. ファイルサイズ超過 (10.1MB 1ファイル)
    2. ファイル数超過 (11ファイル)
    3. 合計サイズ超過 (5ファイル合計10.5MB)
    4. 拡張子なしファイル
    5. 特殊記号ファイル名

分析観点:
  - エラーはどのステップで表示されるか (Step 1 / Step 2 / Step 3)
  - エラーメッセージの具体的な文言
  - 「確認へ進む」ボタンの状態 (enabled / disabled)
  - 「添付を実行する」ボタンの状態
  - エラー表示のDOM要素 (class, role, 色)
  - エラー発生後の画面遷移可否
"""

import os
import sys
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# ===== パス設定 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://invoicing-staging.keihi.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")
FILESIZE_DIR = os.path.join(SCRIPT_DIR, "ファイルサイズ")
FILENAME_DIR = os.path.join(SCRIPT_DIR, "ファイル名")
EXTENSION_DIR = os.path.join(SCRIPT_DIR, "拡張子")

os.makedirs(RESULT_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(RESULT_DIR, f"analyze_error_{timestamp}.log")
log_fh = None


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


def select_invoice(page, index=0):
    log(f"請求書 index={index} を選択...")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
    log(f"  チェックボックス数: {len(checkboxes)}")
    if index >= len(checkboxes):
        raise RuntimeError(f"index={index} がチェックボックス数 {len(checkboxes)} を超えています")
    checkboxes[index].click(force=True)
    page.wait_for_timeout(500)
    log(f"  {index + 1}件目チェック完了")


def open_bulk_attachment_modal(page):
    log("「その他の操作」→「共通添付ファイルの一括添付」...")
    page.get_by_role("button", name="その他の操作").click()
    page.wait_for_timeout(1000)
    attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
    if attach_item.count() > 0:
        attach_item.first.click()
    else:
        page.locator('button:has-text("共通添付ファイルの一括添付")').first.click()
    page.locator('[role="dialog"] h2:has-text("共通添付ファイルの一括添付")').wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(1000)
    log("  モーダルが開きました")


def close_modal_if_open(page):
    """モーダルが開いていれば閉じる"""
    try:
        close_btn = page.get_by_role("button", name="閉じる")
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
            page.wait_for_timeout(500)
            return
        # ×ボタンを試す
        x_btns = page.locator('[role="dialog"] button').all()
        for btn in x_btns:
            text = btn.inner_text().strip()
            if text in ["×", "✕", ""]:
                btn.click(force=True)
                page.wait_for_timeout(500)
                return
    except:
        pass


def capture_full_dialog_state(page, prefix: str, step_name: str) -> dict:
    """
    ダイアログの完全な状態をキャプチャする。
    エラーメッセージ、ボタン状態、DOM構造を詳細に取得。
    """
    log(f"  [{step_name}] ダイアログ状態をキャプチャ...")

    state = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return { exists: false };

        // 全テキスト
        const fullText = dialog.innerText.substring(0, 5000);

        // ボタン一覧 (状態含む)
        const buttons = [];
        dialog.querySelectorAll('button').forEach(b => {
            const rect = b.getBoundingClientRect();
            if (rect.width > 0 || rect.height > 0) {
                buttons.push({
                    text: b.innerText.trim().substring(0, 100),
                    disabled: b.disabled,
                    visible: rect.width > 0 && rect.height > 0
                });
            }
        });

        // エラー表示要素を探す
        const errorElements = [];
        // 1. role="alert" 要素
        dialog.querySelectorAll('[role="alert"]').forEach(el => {
            errorElements.push({
                type: 'role=alert',
                text: el.textContent.trim(),
                className: el.className,
                tagName: el.tagName
            });
        });
        // 2. 赤色テキスト (text-red, text-error, text-danger 等)
        dialog.querySelectorAll('[class*="red"], [class*="error"], [class*="danger"], [class*="warning"], [class*="alert"]').forEach(el => {
            const text = el.textContent.trim();
            if (text) {
                errorElements.push({
                    type: 'class-error',
                    text: text.substring(0, 300),
                    className: el.className,
                    tagName: el.tagName
                });
            }
        });
        // 3. style で赤色指定されている要素
        dialog.querySelectorAll('*').forEach(el => {
            const style = window.getComputedStyle(el);
            const color = style.color;
            // rgb(239, 68, 68) = red-500, rgb(220, 38, 38) = red-600 等
            if (color && (color.includes('239, 68') || color.includes('220, 38') || color.includes('248, 113') || color.includes('185, 28'))) {
                const text = el.textContent.trim();
                if (text && text.length < 500) {
                    errorElements.push({
                        type: 'red-colored',
                        text: text,
                        color: color,
                        tagName: el.tagName,
                        className: el.className.substring(0, 200)
                    });
                }
            }
        });

        // input[type="file"] の状態
        const fileInput = dialog.querySelector('input[type="file"]');
        const fileInputState = fileInput ? {
            exists: true,
            accept: fileInput.getAttribute('accept') || '',
            multiple: fileInput.multiple,
            files: fileInput.files ? fileInput.files.length : 0
        } : { exists: false };

        // h3/h4 見出し (件数表示等)
        const headings = [];
        dialog.querySelectorAll('h3, h4').forEach(h => {
            headings.push({
                tag: h.tagName,
                text: h.textContent.trim()
            });
        });

        // テーブル情報
        const table = dialog.querySelector('table');
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

        // "添付可否" 関連のステータステキスト
        const statusTexts = [];
        dialog.querySelectorAll('p, span, div').forEach(el => {
            const text = el.textContent.trim();
            if (text.includes('判定') || text.includes('添付') || text.includes('エラー') ||
                text.includes('上限') || text.includes('超過') || text.includes('不可') ||
                text.includes('サイズ') || text.includes('ファイル数') || text.includes('MB')) {
                statusTexts.push({
                    text: text.substring(0, 300),
                    tagName: el.tagName,
                    className: el.className ? el.className.substring(0, 100) : ''
                });
            }
        });

        return {
            exists: true,
            fullText: fullText,
            buttons: buttons,
            errorElements: errorElements,
            fileInput: fileInputState,
            headings: headings,
            table: tableInfo,
            statusTexts: statusTexts
        };
    }""")

    # スクリーンショット
    ss_path = os.path.join(RESULT_DIR, f"{prefix}_{step_name}.png")
    page.screenshot(path=ss_path)

    if not state.get("exists"):
        log(f"  [{step_name}] ダイアログが見つかりません")
        return state

    # ログ出力
    log(f"  [{step_name}] ボタン状態:")
    for b in state.get("buttons", []):
        log(f"    - \"{b['text']}\" disabled={b['disabled']}")

    if state.get("errorElements"):
        log(f"  [{step_name}] エラー要素 ({len(state['errorElements'])}件):")
        for e in state["errorElements"]:
            log(f"    [{e['type']}] {e['text'][:200]}")
    else:
        log(f"  [{step_name}] エラー要素: なし")

    if state.get("headings"):
        log(f"  [{step_name}] 見出し:")
        for h in state["headings"]:
            log(f"    <{h['tag']}> {h['text']}")

    if state.get("statusTexts"):
        log(f"  [{step_name}] ステータステキスト (上位5件):")
        # 重複排除して短いものを優先
        seen = set()
        for st in state["statusTexts"][:10]:
            t = st["text"][:200]
            if t not in seen:
                seen.add(t)
                log(f"    [{st['tagName']}] {t}")
                if len(seen) >= 5:
                    break

    return state


def analyze_error_case(page, case_name: str, file_paths: list, screenshot_prefix: str, invoice_index: int) -> dict:
    """
    1つのエラーケースを分析する。
    ファイルをセットした後、各ステップのUI状態を詳細に記録。
    """
    log(f"\n{'=' * 70}")
    log(f"分析ケース: {case_name}")
    log(f"ファイル数: {len(file_paths)}")
    total_size = sum(os.path.getsize(f) for f in file_paths)
    log(f"合計サイズ: {total_size / 1024 / 1024:.2f} MB")
    for f in file_paths:
        sz = os.path.getsize(f)
        log(f"  {os.path.basename(f)}: {sz / 1024 / 1024:.2f} MB")
    log(f"{'=' * 70}")

    result = {
        "case_name": case_name,
        "file_count": len(file_paths),
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "step1": {},
        "step2": {},
        "error_location": "",
        "error_message": "",
        "error_timing": "",
    }

    try:
        # 一覧画面に戻り、請求書を選択
        page.goto(f"{BASE_URL}/invoices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        select_invoice(page, index=invoice_index)
        open_bulk_attachment_modal(page)

        # ===== Step 1: ファイル選択 =====
        log("\n--- Step 1: ファイル選択 ---")
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(file_paths)
        page.wait_for_timeout(3000)  # エラー表示を待つ

        step1_state = capture_full_dialog_state(page, screenshot_prefix, "step1_after_select")
        result["step1"] = step1_state

        # Step 1でエラーが出ているか判定
        step1_has_error = False
        if step1_state.get("errorElements"):
            step1_has_error = True
            result["error_location"] = "Step 1 (ファイル選択直後)"
            error_texts = [e["text"] for e in step1_state["errorElements"]]
            result["error_message"] = " | ".join(set(error_texts))
            result["error_timing"] = "ファイルセット直後"
            log(f"  ★ Step 1 でエラー検出!")

        # 「確認へ進む」ボタンの状態を確認
        confirm_btn = page.get_by_role("button", name="確認へ進む")
        confirm_enabled = False
        try:
            if confirm_btn.count() > 0:
                confirm_enabled = confirm_btn.first.is_enabled()
        except:
            pass
        log(f"  「確認へ進む」ボタン: {'enabled' if confirm_enabled else 'disabled'}")
        result["step1"]["confirm_btn_enabled"] = confirm_enabled

        # Step 1 でエラーが出ていてもボタンが押せる場合、Step 2 に進んでみる
        if confirm_enabled:
            log("\n--- Step 2: 確認画面へ遷移 ---")
            confirm_btn.first.click()
            page.wait_for_timeout(3000)  # 非同期判定を待つ

            step2_state = capture_full_dialog_state(page, screenshot_prefix, "step2_after_confirm")
            result["step2"] = step2_state

            # 非同期判定を更に待つ (最大15秒)
            log("  非同期判定完了を待機 (最大15秒)...")
            for wait_sec in range(15):
                page.wait_for_timeout(1000)
                exec_btn = page.get_by_role("button", name="添付を実行する")
                if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                    log(f"  「添付を実行する」ボタン: enabled (待機{wait_sec + 1}秒)")
                    break
            else:
                log("  「添付を実行する」ボタン: 15秒経過してもdisabledのまま")

            # 判定完了後の状態を再キャプチャ
            step2_final = capture_full_dialog_state(page, screenshot_prefix, "step2_final")
            result["step2_final"] = step2_final

            # Step 2でのエラー判定
            if step2_final.get("errorElements"):
                if not result["error_location"]:
                    result["error_location"] = "Step 2 (確認画面)"
                    error_texts = [e["text"] for e in step2_final["errorElements"]]
                    result["error_message"] = " | ".join(set(error_texts))
                    result["error_timing"] = "非同期判定完了後"
                log(f"  ★ Step 2 でエラー検出!")

            # ダイアログの全文テキストからもエラーパターンを探す
            full_text = step2_final.get("fullText", "")
            error_keywords = ["エラー", "上限", "超過", "不可", "失敗", "サイズ", "制限"]
            found_keywords = [kw for kw in error_keywords if kw in full_text]
            if found_keywords:
                log(f"  Step 2 テキスト内にエラー関連キーワード: {found_keywords}")
                # 該当行を抽出
                for line in full_text.split("\n"):
                    if any(kw in line for kw in found_keywords):
                        log(f"    >> {line.strip()[:200]}")

            # 「添付を実行する」の状態
            exec_btn = page.get_by_role("button", name="添付を実行する")
            exec_enabled = False
            if exec_btn.count() > 0:
                exec_enabled = exec_btn.first.is_enabled()
            result["step2"]["exec_btn_enabled"] = exec_enabled
            log(f"  「添付を実行する」ボタン: {'enabled' if exec_enabled else 'disabled'}")

        else:
            log("  「確認へ進む」ボタンがdisabled → Step 2 に進めません")
            if not result["error_location"]:
                result["error_location"] = "Step 1 (確認へ進むボタンdisabled)"
                result["error_timing"] = "ファイルセット後、確認画面遷移前"

        # モーダルを閉じる
        close_modal_if_open(page)
        page.wait_for_timeout(1000)

    except Exception as e:
        result["error"] = str(e)
        log(f"  例外発生: {e}")
        try:
            page.screenshot(path=os.path.join(RESULT_DIR, f"{screenshot_prefix}_exception.png"))
        except:
            pass
        close_modal_if_open(page)

    return result


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

    log(f"=== 異常系エラー挙動分析 開始 ===")
    log(f"日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"ログ: {LOG_FILE}")

    # ===== 分析ケース定義 =====
    cases = [
        {
            "name": "Case 1: ファイルサイズ超過 (10.1MB 1ファイル)",
            "files": [os.path.join(FILESIZE_DIR, "02_single_10MB_over", "file_10.1MB.pdf")],
            "prefix": "err_case1_size_over",
            "invoice_index": 0,
        },
        {
            "name": "Case 2: ファイル数超過 (11ファイル)",
            "files": [
                os.path.join(FILESIZE_DIR, "04_11files_upload", f"file_{i:02d}.pdf")
                for i in range(1, 12)
            ],
            "prefix": "err_case2_count_over",
            "invoice_index": 1,
        },
        {
            "name": "Case 3: 合計サイズ超過 (5ファイル 合計10.5MB)",
            "files": [
                os.path.join(FILESIZE_DIR, "06_total_10MB_over", f"file_{i:02d}.pdf")
                for i in range(1, 6)
            ],
            "prefix": "err_case3_total_over",
            "invoice_index": 2,
        },
        {
            "name": "Case 4: 拡張子なしファイル",
            "files": [os.path.join(EXTENSION_DIR, "_")],
            "prefix": "err_case4_no_ext",
            "invoice_index": 3,
        },
        {
            "name": "Case 5: 特殊記号ファイル名 (!@#$%&()=~)",
            "files": [os.path.join(FILENAME_DIR, "!@#$%&()=~.pdf")],
            "prefix": "err_case5_special_chars",
            "invoice_index": 4,
        },
    ]

    # ファイル存在チェック
    for case in cases:
        for fp in case["files"]:
            if not os.path.exists(fp):
                log(f"WARNING: ファイルが見つかりません: {fp}")

    all_results = []

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
            result = analyze_error_case(
                page,
                case_name=case["name"],
                file_paths=case["files"],
                screenshot_prefix=case["prefix"],
                invoice_index=case["invoice_index"],
            )
            all_results.append(result)
            log(f"\n  >>> 結果: エラー箇所={result.get('error_location', '不明')}")
            log(f"  >>> メッセージ: {result.get('error_message', 'なし')[:200]}")

        browser.close()

    # ===== 分析結果サマリー =====
    log(f"\n\n{'#' * 70}")
    log("分析結果サマリー")
    log(f"{'#' * 70}")

    for r in all_results:
        log(f"\n--- {r['case_name']} ---")
        log(f"  ファイル数: {r['file_count']}, 合計: {r['total_size_mb']} MB")
        log(f"  エラー箇所: {r.get('error_location', '(エラーなし/不明)')}")
        log(f"  エラータイミング: {r.get('error_timing', '不明')}")
        log(f"  エラーメッセージ: {r.get('error_message', 'なし')[:300]}")
        step1 = r.get("step1", {})
        log(f"  Step 1 「確認へ進む」: {'enabled' if step1.get('confirm_btn_enabled') else 'disabled/不明'}")
        step2 = r.get("step2", {})
        if step2:
            log(f"  Step 2 「添付を実行する」: {'enabled' if step2.get('exec_btn_enabled') else 'disabled/不明'}")

    # JSON保存
    json_path = os.path.join(RESULT_DIR, f"analyze_error_{timestamp}.json")
    # JSON serializable にする (DOM state から不要な大きなデータを除去)
    clean_results = []
    for r in all_results:
        cr = {
            "case_name": r["case_name"],
            "file_count": r["file_count"],
            "total_size_mb": r["total_size_mb"],
            "error_location": r.get("error_location", ""),
            "error_message": r.get("error_message", ""),
            "error_timing": r.get("error_timing", ""),
            "step1_confirm_enabled": r.get("step1", {}).get("confirm_btn_enabled"),
            "step1_errors": [e.get("text", "")[:200] for e in r.get("step1", {}).get("errorElements", [])],
            "step2_exec_enabled": r.get("step2", {}).get("exec_btn_enabled"),
            "step2_errors": [e.get("text", "")[:200] for e in r.get("step2_final", {}).get("errorElements", [])],
        }
        clean_results.append(cr)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean_results, f, ensure_ascii=False, indent=2)
    log(f"\nJSON結果: {json_path}")

    log(f"\n=== 分析完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    log_fh.close()


if __name__ == "__main__":
    main()
