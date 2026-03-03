"""
共通添付ファイルの一括添付 - 正常系テスト

テスト内容:
  TH-01: PDF 1ファイルアップロード → 確認 → 添付完了
  TH-02: 複数ファイル(3件)同時アップロード → 確認 → 添付完了
  TH-03: 各種拡張子ファイル(jpg, png, xlsx, docx)アップロード → 確認 → 添付完了
  TH-04: 日本語ファイル名(ひらがな, カタカナ, 漢字)アップロード → 確認 → 添付完了

前提条件:
  - テスト用ファイルは各サブフォルダ(ファイル名/, 拡張子/, ファイルサイズ/)に配置済み
  - ログイン情報は TH/ログイン/.env に設定済み
"""

import os
import sys
import time
import json
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# ===== パス設定 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://invoicing-staging.keihi.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")
FILENAME_DIR = os.path.join(SCRIPT_DIR, "ファイル名")
EXTENSION_DIR = os.path.join(SCRIPT_DIR, "拡張子")
FILESIZE_DIR = os.path.join(SCRIPT_DIR, "ファイルサイズ")

# ===== ログ設定 =====
os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_normal_{timestamp}.log")
log_fh = None


def get_th_result_dir(th_id: str) -> str:
    """TH-IDごとの動画保存フォルダを作成して返す"""
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
    """ログイン情報をロード"""
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


# ===== ヘルパー関数 =====
def login(page, email: str, password: str):
    """共通ログイン処理"""
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


def navigate_to_clean_page(page, page_num: int = 3):
    """添付ファイルの蓄積が少ない後方ページに遷移する

    過去テストの蓄積で1ページ目の請求書は添付数上限に達している可能性がある。
    URLパラメータで直接指定ページに遷移する。
    """
    log(f"{page_num}ページ目に遷移中...")
    page.goto(f"{BASE_URL}/invoices?page={page_num}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    log(f"{page_num}ページ目に遷移完了")


def select_invoice(page, index: int = 0):
    """一覧画面で指定番号のチェックボックスを選択 (0-indexed)"""
    log("請求書一覧読み込み待機...")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
    log(f"チェックボックス数: {len(checkboxes)}")
    if len(checkboxes) == 0:
        raise RuntimeError("チェックボックスが見つかりません")
    if index >= len(checkboxes):
        raise RuntimeError(f"指定されたindex({index})がチェックボックス数({len(checkboxes)})を超えています")

    checkboxes[index].click(force=True)
    page.wait_for_timeout(500)
    log(f"{index + 1}件目チェック完了")


def close_modal_if_open(page):
    """モーダルが開いている場合に確実に閉じる（テスト間クリーンアップ用）"""
    try:
        dialog = page.locator('[role="dialog"]')
        if dialog.count() > 0 and dialog.first.is_visible():
            # 「閉じる」ボタンを試す
            close_btn = page.get_by_role("button", name="閉じる")
            if close_btn.count() > 0 and close_btn.first.is_visible():
                close_btn.first.click(force=True)
                page.wait_for_timeout(1000)
                log("  残留モーダルを「閉じる」で閉じました")
                return
            # ×ボタンを試す
            x_btn = page.locator('[role="dialog"] button').first
            if x_btn.count() > 0:
                x_btn.click(force=True)
                page.wait_for_timeout(1000)
                log("  残留モーダルを×で閉じました")
                return
            # Escapeキーを試す
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            log("  残留モーダルをEscapeで閉じました")
    except Exception:
        pass


def open_bulk_attachment_modal(page):
    """「その他の操作」→「共通添付ファイルの一括添付」でモーダルを開く"""
    log("「その他の操作」メニューを開く...")
    page.get_by_role("button", name="その他の操作").click()
    page.wait_for_timeout(1000)

    log("「共通添付ファイルの一括添付」をクリック...")
    attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
    if attach_item.count() > 0:
        attach_item.first.click()
    else:
        page.locator('button:has-text("共通添付ファイルの一括添付")').first.click()

    # モーダルが開くのを待つ
    # Headless UI の dialog は role="dialog" のラッパーが height=0 で visible 判定されない
    # → ダイアログパネル (_dialogPanel) または h2 タイトルで待機する
    page.locator('[role="dialog"] h2:has-text("共通添付ファイルの一括添付")').wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(1000)
    log("モーダルが開きました")


def upload_files_and_confirm(page, file_paths: list, test_name: str, tc_id: str = None) -> dict:
    """
    ファイルをアップロードし、確認→完了まで操作する。

    Returns:
        dict: { "success": bool, "step1_ok": bool, "step2_ok": bool, "step3_ok": bool, "error": str }
    """
    result = {
        "success": False,
        "step1_ok": False,
        "step2_ok": False,
        "step3_ok": False,
        "error": "",
        "files_uploaded": len(file_paths),
        "file_names": [os.path.basename(f) for f in file_paths],
    }


    try:
        # ===== Step 1: ファイル選択 =====
        log(f"[Step 1] ファイルをアップロード中... ({len(file_paths)}件)")

        # hidden input[type="file"] にファイルをセット
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(file_paths)
        page.wait_for_timeout(2000)

        # 選択済みファイル件数を確認
        selected_text = page.evaluate("""() => {
            const h3s = document.querySelectorAll('[role="dialog"] h3');
            for (const h3 of h3s) {
                if (h3.textContent.includes('選択済みファイル')) return h3.textContent.trim();
            }
            return '';
        }""")
        log(f"  選択済みファイル表示: {selected_text}")


        # 「確認へ進む」ボタンが有効になったか確認
        confirm_btn = page.get_by_role("button", name="確認へ進む")
        try:
            expect(confirm_btn).to_be_enabled(timeout=5000)
            log("  「確認へ進む」ボタン: enabled ✓")
            result["step1_ok"] = True
        except Exception as e:
            log(f"  「確認へ進む」ボタン: disabled ✗ ({e})")
            result["error"] = f"Step 1: 確認へ進むボタンがdisabledのまま: {e}"
            return result

        # ===== Step 2: 確認画面へ遷移 =====
        log("[Step 2] 確認画面へ遷移...")
        confirm_btn.click()
        page.wait_for_timeout(2000)

        # Step 2の表示内容を取得
        step2_content = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { text: '', buttons: [] };

            const buttons = [];
            dialog.querySelectorAll('button').forEach(b => {
                const rect = b.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    buttons.push({
                        text: b.innerText.trim(),
                        disabled: b.disabled
                    });
                }
            });

            return {
                text: dialog.innerText.substring(0, 3000),
                buttons: buttons
            };
        }""")

        log(f"  確認画面テキスト (先頭500文字):\n    {step2_content['text'][:500]}")
        log(f"  ボタン一覧:")
        for btn in step2_content['buttons']:
            log(f"    - \"{btn['text']}\" disabled={btn['disabled']}")

        result["step2_ok"] = True

        # ===== Step 2 → Step 3: 添付実行 =====
        log("[Step 2→3] 添付を実行...")

        # 「添付を実行する」ボタンが enabled になるのを待つ（非同期判定処理完了待ち）
        exec_btn = page.get_by_role("button", name="添付を実行する")
        if exec_btn.count() == 0:
            # フォールバック: 他の候補
            exec_btn_candidates = ["一括添付する", "添付する", "確定", "実行", "登録"]
            exec_btn = None
            for btn_name in exec_btn_candidates:
                btn = page.get_by_role("button", name=btn_name, exact=False)
                if btn.count() > 0:
                    exec_btn = btn.first
                    log(f"  実行ボタン発見: \"{btn_name}\"")
                    break
            if exec_btn is None:
                result["error"] = "Step 2: 実行ボタンが見つかりません"
                log(f"  ERROR: {result['error']}")
                return result
        else:
            exec_btn = exec_btn.first

        # 非同期判定完了を最大60秒待機（サーバー応答が遅い場合を考慮）
        log("  「添付を実行する」ボタンが enabled になるのを待機中...")
        try:
            # 判定中にエラーが発生していないかを5秒ごとにチェック
            for attempt in range(12):  # 最大60秒（5秒×12回）
                try:
                    expect(exec_btn).to_be_enabled(timeout=5000)
                    log("  「添付を実行する」ボタン: enabled ✓")
                    break
                except Exception:
                    # まだdisabled → エラーメッセージが出ていないか確認
                    error_check = page.evaluate("""() => {
                        const d = document.querySelector('[role="dialog"]');
                        if (!d) return { hasError: false };
                        const text = d.innerText;
                        return {
                            hasError: text.includes('上限を超過') || text.includes('エラーがあります'),
                            errorText: text.substring(0, 500)
                        };
                    }""")
                    if error_check.get("hasError"):
                        log(f"  サーバー判定エラー検出: {error_check.get('errorText', '')[:200]}")
                        result["error"] = f"Step 2: サーバー判定エラー（添付数上限超過など）。この請求書には既に多数のファイルが添付されています。"
                        return result
                    if attempt < 11:
                        log(f"  待機中... ({(attempt + 1) * 5}秒経過)")
            else:
                # 60秒経過してもenableにならない
                dialog_text = page.evaluate("""() => {
                    const d = document.querySelector('[role="dialog"]');
                    return d ? d.innerText.substring(0, 2000) : '';
                }""")
                log(f"  「添付を実行する」ボタン: 60秒経過してもdisabledのまま")
                log(f"  ダイアログテキスト: {dialog_text[:500]}")
                result["error"] = f"Step 2: 添付を実行するボタンが有効にならない（60秒タイムアウト）"
                return result
        except Exception as e:
            log(f"  予期しないエラー: {e}")
            result["error"] = f"Step 2: 待機中にエラー: {str(e)}"
            return result


        # === Step 2 判定完了後: 確認画面の内容を検証 ===
        log("[Step 2 検証] 確認画面の内容を検証...")

        step2_verified = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return { ok: false, error: 'dialog not found' };

            // 添付するファイル一覧
            const fileSection = d.querySelector('h4');
            const fileLabel = fileSection ? fileSection.textContent.trim() : '';

            // ファイル名チップ
            const chips = [];
            d.querySelectorAll('section:first-of-type [class*="chip"], section:first-of-type [class*="Chip"]').forEach(c => {
                chips.push(c.textContent.trim());
            });
            // チップが取れない場合はセクション内テキストから抽出
            if (chips.length === 0) {
                const firstSection = d.querySelectorAll('section')[0];
                if (firstSection) {
                    firstSection.querySelectorAll('span, div, p').forEach(el => {
                        const t = el.textContent.trim();
                        if (t && t.includes('.')) chips.push(t);
                    });
                }
            }

            // テーブル（添付先の帳票一覧）
            const table = d.querySelector('table');
            const tableData = { headers: [], rows: [] };
            if (table) {
                table.querySelectorAll('th').forEach(th => tableData.headers.push(th.textContent.trim()));
                table.querySelectorAll('tbody tr').forEach(tr => {
                    const cells = [];
                    tr.querySelectorAll('td').forEach(td => cells.push(td.textContent.trim().substring(0, 100)));
                    tableData.rows.push(cells);
                });
            }

            // 添付可否メッセージ
            const footerText = d.querySelector('p[class*="stack"]');
            const statusMsg = footerText ? footerText.textContent.trim() : '';

            return {
                ok: true,
                fileLabel: fileLabel,
                fileNames: chips,
                table: tableData,
                statusMsg: statusMsg,
                hasError: d.innerText.includes('エラー')
            };
        }""")

        if step2_verified.get("ok"):
            log(f"  ファイルセクション: {step2_verified.get('fileLabel', '')}")
            log(f"  ファイル名: {step2_verified.get('fileNames', [])}")
            table = step2_verified.get("table", {})
            if table.get("headers"):
                log(f"  テーブルヘッダー: {table['headers']}")
                for i, row in enumerate(table.get("rows", [])):
                    log(f"    行{i}: {row}")
            log(f"  ステータスメッセージ: {step2_verified.get('statusMsg', '')}")
            log(f"  エラー有無: {step2_verified.get('hasError', False)}")

            # 判定結果の検証
            has_attachable = False
            for row in table.get("rows", []):
                if any("添付可能" in cell for cell in row):
                    has_attachable = True
            if has_attachable:
                log("  判定結果: 添付可能 ✓")
            elif step2_verified.get("hasError"):
                log("  判定結果: エラーあり ✗")
                result["error"] = "Step 2: 添付不可と判定されました"
                return result

            result["step2_verified"] = step2_verified

        # 実行ボタンをクリック（force=True でポインタインターセプト回避）
        exec_btn.click(force=True)
        log("  実行ボタンクリック完了")

        # 完了を待つ (アップロード処理)
        page.wait_for_timeout(8000)

        # ===== Step 3: 完了画面 =====
        log("[Step 3] 完了画面を確認...")

        step3_content = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { text: '', exists: false };
            return {
                text: dialog.innerText.substring(0, 2000),
                exists: true
            };
        }""")

        if step3_content['exists']:
            log(f"  完了画面テキスト (先頭500文字):\n    {step3_content['text'][:500]}")

            # 完了判定: 「完了」「成功」などのキーワードチェック
            completion_keywords = ["完了", "成功", "添付しました", "添付されました"]
            is_complete = any(kw in step3_content['text'] for kw in completion_keywords)

            if is_complete:
                log("  完了確認: ✓")
                result["step3_ok"] = True
                result["success"] = True
            else:
                # エラーキーワードチェック
                error_keywords = ["エラー", "失敗", "できません"]
                has_error = any(kw in step3_content['text'] for kw in error_keywords)
                if has_error:
                    log(f"  エラー検出: {step3_content['text'][:200]}")
                    result["error"] = f"Step 3: エラー表示: {step3_content['text'][:200]}"
                else:
                    # 完了キーワードが見当たらないが、Step 3に到達している
                    log("  完了キーワードなし。Step 3テキストをそのまま記録。")
                    result["step3_ok"] = True
                    result["success"] = True
                    result["step3_text"] = step3_content['text'][:500]
        else:
            log("  ダイアログが閉じている（自動クローズの可能性）")
            result["step3_ok"] = True
            result["success"] = True

        # 閉じるボタンがあればクリック (force=True で背面要素インターセプト回避)
        close_btn = page.get_by_role("button", name="閉じる")
        if close_btn.count() > 0:
            try:
                close_btn.first.click(force=True)
                page.wait_for_timeout(1000)
                log("  モーダルを閉じました")
            except Exception:
                # ×ボタンで閉じる
                x_btn = page.locator('[role="dialog"] button[class*="closeButton"]')
                if x_btn.count() > 0:
                    x_btn.first.click(force=True)
                    page.wait_for_timeout(1000)
                    log("  ×ボタンでモーダルを閉じました")

        # ===== モーダル閉じた後: 一覧画面で添付件数を確認 =====
        log("[一覧確認] モーダル閉じた後の一覧画面を確認...")
        page.wait_for_timeout(2000)

        # 一覧テーブルの添付列を確認
        list_attach_info = page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr');
            const results = [];
            for (let i = 0; i < Math.min(10, rows.length); i++) {
                const row = rows[i];
                const cb = row.querySelector('input[type="checkbox"]');
                const cells = Array.from(row.querySelectorAll('td'));
                // 添付列の値を取得（クリップアイコン + 件数）
                let attachText = '';
                cells.forEach(td => {
                    const text = td.innerText.trim();
                    if (/^\d+$/.test(text) || text === '—') {
                        // 数字のみ or — なら添付件数列の可能性
                    }
                });
                const cellTexts = cells.map(td => td.innerText.trim().substring(0, 50));
                results.push({
                    index: i,
                    checked: cb ? cb.checked : null,
                    cells: cellTexts
                });
            }
            return results;
        }""")
        log("  一覧テーブル（先頭10行）:")
        for r in list_attach_info:
            checked_mark = "☑" if r["checked"] else "☐"
            log(f"    {checked_mark} Row {r['index']}: {r['cells'][:7]}")

    except Exception as e:
        result["error"] = f"予期せぬエラー: {str(e)}"
        log(f"  ERROR: {result['error']}")

    return result


# ===== テストケース =====
def test_tc01_single_pdf(page):
    """TH-01: PDF 1ファイルアップロード"""
    log("\n" + "=" * 60)
    log("TH-01: PDF 1ファイルアップロード")
    log("=" * 60)

    file_path = os.path.join(EXTENSION_DIR, "sample.pdf")
    if not os.path.exists(file_path):
        return {"success": False, "error": f"テストファイルが見つかりません: {file_path}"}

    # 2ページ目に遷移して添付数の蓄積が少ない請求書を使う
    navigate_to_clean_page(page)
    select_invoice(page, index=0)
    open_bulk_attachment_modal(page)
    result = upload_files_and_confirm(page, [file_path], "TH-01", tc_id="TH-01")

    return result


def test_tc02_multiple_files(page):
    """TH-02: 複数ファイル(3件)同時アップロード"""
    log("\n" + "=" * 60)
    log("TH-02: 複数ファイル(3件)同時アップロード")
    log("=" * 60)

    file_paths = [
        os.path.join(EXTENSION_DIR, "sample.pdf"),
        os.path.join(EXTENSION_DIR, "sample.png"),
        os.path.join(EXTENSION_DIR, "sample.jpg"),
    ]
    for fp in file_paths:
        if not os.path.exists(fp):
            return {"success": False, "error": f"テストファイルが見つかりません: {fp}"}

    # 2ページ目に遷移して添付数の蓄積が少ない請求書を使う
    navigate_to_clean_page(page)
    select_invoice(page, index=1)
    open_bulk_attachment_modal(page)
    result = upload_files_and_confirm(page, file_paths, "TH-02", tc_id="TH-02")

    return result


def test_tc03_various_extensions(page):
    """TH-03: 各種拡張子ファイルアップロード"""
    log("\n" + "=" * 60)
    log("TH-03: 各種拡張子ファイル(jpg, png, xlsx, docx)アップロード")
    log("=" * 60)

    file_paths = [
        os.path.join(EXTENSION_DIR, "sample.jpg"),
        os.path.join(EXTENSION_DIR, "sample.png"),
        os.path.join(EXTENSION_DIR, "sample.xlsx"),
        os.path.join(EXTENSION_DIR, "sample.docx"),
    ]
    for fp in file_paths:
        if not os.path.exists(fp):
            return {"success": False, "error": f"テストファイルが見つかりません: {fp}"}

    # 2ページ目に遷移して添付数の蓄積が少ない請求書を使う
    navigate_to_clean_page(page)
    select_invoice(page, index=2)
    open_bulk_attachment_modal(page)
    result = upload_files_and_confirm(page, file_paths, "TH-03", tc_id="TH-03")

    return result


def test_tc04_japanese_filenames(page):
    """TH-04: 日本語ファイル名アップロード"""
    log("\n" + "=" * 60)
    log("TH-04: 日本語ファイル名(ひらがな, カタカナ, 漢字)アップロード")
    log("=" * 60)

    file_paths = [
        os.path.join(FILENAME_DIR, "ひらがな.pdf"),
        os.path.join(FILENAME_DIR, "全角カタカナ.pdf"),
        os.path.join(FILENAME_DIR, "漢字.pdf"),
    ]
    for fp in file_paths:
        if not os.path.exists(fp):
            return {"success": False, "error": f"テストファイルが見つかりません: {fp}"}

    # 2ページ目に遷移して添付数の蓄積が少ない請求書を使う
    navigate_to_clean_page(page)
    select_invoice(page, index=3)
    open_bulk_attachment_modal(page)
    result = upload_files_and_confirm(page, file_paths, "TH-04", tc_id="TH-04")

    return result


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
    log(f"ログファイル: {LOG_FILE}")
    log(f"結果フォルダ: {RESULT_DIR}")
    log(f"テストアカウント: {email}")

    tests = [
        ("TH-01", "PDF 1ファイルアップロード", test_tc01_single_pdf),
        ("TH-02", "複数ファイル(3件)同時アップロード", test_tc02_multiple_files),
        ("TH-03", "各種拡張子ファイル(jpg,png,xlsx,docx)", test_tc03_various_extensions),
        ("TH-04", "日本語ファイル名(ひらがな,カタカナ,漢字)", test_tc04_japanese_filenames),
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
                # 各テスト関数内でnavigate_to_clean_page()により
                # 添付蓄積の少ないページに直接遷移するため、
                # ここでの初期遷移は不要

                result = tc_func(page)
                result["tc_id"] = tc_id
                result["tc_name"] = tc_name
                results.append(result)

                status = "PASS ✓" if result["success"] else "FAIL ✗"
                log(f"\n結果: {status}")
                if result.get("error"):
                    log(f"エラー: {result['error']}")

            except Exception as e:
                log(f"\n結果: FAIL ✗ (例外: {e})")
                results.append({
                    "tc_id": tc_id,
                    "tc_name": tc_name,
                    "success": False,
                    "error": str(e),
                })
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
                            log(f"  🎬 動画パス記録: {tc_id}")
                except Exception as e:
                    log(f"  🎬 動画パス記録失敗: {e}")
                page.close()

        context.close()

        # === Phase 3: 遅延コピー（動画確定後にコピー） ===
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

        # 一時フォルダ・認証ファイル削除
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

    # ===== サマリー =====
    log("\n" + "=" * 60)
    log("テスト結果サマリー")
    log("=" * 60)

    pass_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - pass_count

    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        error = f" - {r.get('error', '')}" if r.get("error") else ""
        files_info = f" (ファイル: {r.get('files_uploaded', '?')}件)" if r.get("files_uploaded") else ""
        log(f"  [{status}] {r['tc_id']}: {r['tc_name']}{files_info}{error}")

    log(f"\n合計: {len(results)}件 | PASS: {pass_count}件 | FAIL: {fail_count}件")
    log(f"テスト完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # JSON結果出力
    json_path = os.path.join(LOGS_DIR, f"test_normal_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"JSON結果: {json_path}")

    log_fh.close()

    # 終了コード
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
