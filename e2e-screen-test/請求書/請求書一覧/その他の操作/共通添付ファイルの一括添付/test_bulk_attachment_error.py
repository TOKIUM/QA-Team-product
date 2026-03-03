"""
共通添付ファイルの一括添付 - 異常系・境界値テスト

テスト内容:
  TH-E01: ファイルサイズ超過 (10.1MB) → Step 1 でエラー（確認へ進む disabled）
  TH-E02: 11ファイル同時選択 → Step 2 でエラー（添付数上限を超過しています）
  TH-E03: 合計サイズ超過 (5ファイル 10.5MB) → Step 2 でエラー（ファイルサイズ上限を超過しています）
  TH-E04: 拡張子なしファイル → Step 1 でエラー（確認へ進む disabled）
  TH-E05: 9.9MB 1ファイル → Step 2 でエラー（ファイルサイズ上限を超過しています）
  TH-E06: 10ファイル同時 → 正常添付（境界値 OK）
  TH-E07: 合計9.5MB (5ファイル) → 正常添付（境界値 OK）
  TH-E08: 特殊記号ファイル名 (!@#$%&()=~.pdf) → 正常添付
  TH-E09: 5.0MB 1ファイル → 正常添付（境界値 OK）

前提条件:
  - テスト用ファイルは各サブフォルダに配置済み
  - ログイン情報は TH/ログイン/.env に設定済み
  - 使用する請求書はテストごとに異なるindex（添付数上限回避）

分析結果に基づくエラー仕様:
  [Step 1 エラー] ファイルセット直後にフロントで弾く
    - ファイル横に「エラー」表示
    - 「選択済みファイル(0件)」（エラーファイルはカウントされない）
    - フッター: 「選択済みファイルにエラーがあります。選択から削除してください」
    - 「確認へ進む」ボタン: disabled

  [Step 2 エラー] 非同期判定（サーバー側）で弾く
    - 判定列: 「添付数上限を超過しています」or「ファイルサイズ上限を超過しています」
    - h4: 「添付先の帳票一覧エラー」
    - フッター: 「エラーがあります。ファイルを再選択してください」
    - 「添付を実行する」ボタン: disabled
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
FILESIZE_DIR = os.path.join(SCRIPT_DIR, "ファイルサイズ")
FILENAME_DIR = os.path.join(SCRIPT_DIR, "ファイル名")
EXTENSION_DIR = os.path.join(SCRIPT_DIR, "拡張子")

os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_error_{timestamp}.log")
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


# ===== ヘルパー関数 =====
def login(page, email: str, password: str):
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


def navigate_to_list(page):
    """一覧画面に戻る"""
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)


def select_invoice(page, index: int):
    """一覧画面で指定番号のチェックボックスを選択"""
    checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
    if index >= len(checkboxes):
        raise RuntimeError(f"index={index} がチェックボックス数({len(checkboxes)})を超えています")
    checkboxes[index].click(force=True)
    page.wait_for_timeout(500)
    log(f"  請求書 index={index} チェック完了")


def open_modal(page):
    """「その他の操作」→「共通添付ファイルの一括添付」でモーダルを開く（リトライ付き）"""
    for attempt in range(3):
        try:
            page.get_by_role("button", name="その他の操作").click()
            page.wait_for_timeout(1500)
            attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
            if attach_item.count() > 0:
                attach_item.first.click()
            else:
                log(f"  メニュー項目が見つかりません (attempt {attempt + 1})")
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
    """モーダルを閉じる（「閉じる」or「戻る」→「閉じる」）"""
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
            close_btn2 = page.get_by_role("button", name="閉じる")
            if close_btn2.count() > 0:
                close_btn2.first.click(force=True)
                page.wait_for_timeout(500)
    except Exception:
        pass


def get_step1_state(page) -> dict:
    """Step 1 のダイアログ状態を取得"""
    return page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return { exists: false };
        const errors = [];
        d.querySelectorAll('[class*="error"]').forEach(el => {
            const t = el.textContent.trim();
            if (t && t.length < 500) errors.push(t);
        });
        const headings = [];
        d.querySelectorAll('h3').forEach(h => headings.push(h.textContent.trim()));
        const confirmBtn = Array.from(d.querySelectorAll('button')).find(b => b.innerText.includes('確認へ進む'));
        return {
            exists: true,
            errors: [...new Set(errors)],
            headings: headings,
            confirmEnabled: confirmBtn ? !confirmBtn.disabled : null,
        };
    }""")


def get_step2_state(page) -> dict:
    """Step 2 のダイアログ状態を取得"""
    return page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return { exists: false };
        const errors = [];
        d.querySelectorAll('[class*="error"]').forEach(el => {
            const t = el.textContent.trim();
            if (t && t.length < 500) errors.push(t);
        });
        const headings = [];
        d.querySelectorAll('h4').forEach(h => headings.push(h.textContent.trim()));
        // 判定列
        const table = d.querySelector('table');
        const judgments = [];
        if (table) {
            table.querySelectorAll('tbody tr').forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td'));
                const last = cells[cells.length - 1];
                if (last) judgments.push(last.textContent.trim());
            });
        }
        // フッターメッセージ
        let footerMsg = '';
        d.querySelectorAll('p, span').forEach(el => {
            const t = el.textContent.trim();
            if (t.includes('実行可能') || t.includes('エラーがあります') || t.includes('再選択')) {
                footerMsg = t;
            }
        });
        const execBtn = Array.from(d.querySelectorAll('button')).find(b => b.innerText.includes('添付を実行する'));
        return {
            exists: true,
            errors: [...new Set(errors)],
            headings: headings,
            judgments: judgments,
            footerMsg: footerMsg,
            execEnabled: execBtn ? !execBtn.disabled : null,
        };
    }""")


# ===== Step 1 でエラーになるテスト =====
def test_step1_error(page, tc_id, tc_name, file_paths, invoice_index, expected_error_keyword):
    """
    Step 1 でフロントエンドバリデーションによりブロックされるケースのテスト。
    期待動作:
      - ファイルセット後、エラー表示
      - 「確認へ進む」ボタンが disabled
    """
    log(f"\n{'=' * 60}")
    log(f"{tc_id}: {tc_name}")
    log(f"{'=' * 60}")

    result = {"tc_id": tc_id, "tc_name": tc_name, "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        # ファイルセット
        total_size = sum(os.path.getsize(f) for f in file_paths)
        log(f"  ファイル: {len(file_paths)}件, 合計 {total_size / 1024 / 1024:.2f} MB")
        page.locator('input[type="file"]').set_input_files(file_paths)
        page.wait_for_timeout(3000)


        # Step 1 状態を取得
        state = get_step1_state(page)
        log(f"  見出し: {state.get('headings', [])}")
        log(f"  エラー: {state.get('errors', [])[:3]}")
        log(f"  「確認へ進む」: {'enabled' if state.get('confirmEnabled') else 'disabled'}")

        # 検証1: エラー表示があること
        has_error = any(expected_error_keyword in e for e in state.get("errors", []))
        if not has_error:
            # エラーキーワードが見つからない場合、全エラーテキストで再確認
            has_error = any("エラー" in e for e in state.get("errors", []))

        if has_error:
            log(f"  ✓ エラー表示あり（'{expected_error_keyword}' 含む）")
        else:
            log(f"  ✗ エラー表示なし（期待: '{expected_error_keyword}'）")
            result["error"] = f"エラー表示が見つかりません（期待: {expected_error_keyword}）"
            close_modal(page)
            return result

        # 検証2: 「確認へ進む」ボタンが disabled
        if state.get("confirmEnabled") is False:
            log("  ✓ 「確認へ進む」ボタン: disabled")
        else:
            log("  ✗ 「確認へ進む」ボタン: enabled（期待: disabled）")
            result["error"] = "「確認へ進む」ボタンがdisabledになっていません"
            close_modal(page)
            return result

        result["success"] = True
        log(f"  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = f"例外: {str(e)}"
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


# ===== Step 2 でエラーになるテスト =====
def test_step2_error(page, tc_id, tc_name, file_paths, invoice_index, expected_judgment):
    """
    Step 2 でサーバー側バリデーションによりブロックされるケースのテスト。
    期待動作:
      - Step 1: エラーなし、「確認へ進む」enabled
      - Step 2: 非同期判定後、テーブル判定列にエラー表示
      - フッター: 「エラーがあります。ファイルを再選択してください」
      - 「添付を実行する」ボタン: disabled
    """
    log(f"\n{'=' * 60}")
    log(f"{tc_id}: {tc_name}")
    log(f"{'=' * 60}")

    result = {"tc_id": tc_id, "tc_name": tc_name, "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        # ファイルセット
        total_size = sum(os.path.getsize(f) for f in file_paths)
        log(f"  ファイル: {len(file_paths)}件, 合計 {total_size / 1024 / 1024:.2f} MB")
        page.locator('input[type="file"]').set_input_files(file_paths)
        page.wait_for_timeout(3000)


        # Step 1: エラーなし・確認へ進むが enabled であること
        step1 = get_step1_state(page)
        log(f"  Step 1 見出し: {step1.get('headings', [])}")
        if step1.get("confirmEnabled"):
            log("  ✓ Step 1: エラーなし、「確認へ進む」enabled")
        else:
            log("  ✗ Step 1: 「確認へ進む」がdisabled（Step 2 に進めない）")
            result["error"] = "Step 1 で予期せずブロックされました"
            close_modal(page)
            return result

        # Step 2 へ遷移
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)


        # 非同期判定を待つ（最大30秒、判定完了 = ボタンの状態が変化 or エラー表示）
        log("  非同期判定待機中...")
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            # エラー表示が出たか確認
            err_check = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return false;
                return d.innerText.includes('エラー') || d.innerText.includes('超過');
            }""")
            if err_check:
                log(f"  判定完了（エラー検出、{i + 1}秒）")
                break
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了（ボタンenabled、{i + 1}秒）")
                break
        else:
            log("  判定: 30秒経過")

        page.wait_for_timeout(1000)

        # Step 2 状態を取得
        step2 = get_step2_state(page)
        log(f"  Step 2 見出し: {step2.get('headings', [])}")
        log(f"  判定列: {step2.get('judgments', [])}")
        log(f"  フッター: {step2.get('footerMsg', '')}")
        log(f"  エラー要素: {step2.get('errors', [])[:3]}")

        # 検証1: 判定列に期待エラーメッセージ
        has_judgment_error = any(expected_judgment in j for j in step2.get("judgments", []))
        if has_judgment_error:
            log(f"  ✓ 判定列にエラー（'{expected_judgment}'）")
        else:
            log(f"  ✗ 判定列にエラーなし（期待: '{expected_judgment}'）")
            result["error"] = f"判定列に期待エラーなし（期待: {expected_judgment}）"
            close_modal(page)
            return result

        # 検証2: フッターに「エラーがあります。ファイルを再選択してください」
        footer = step2.get("footerMsg", "")
        if "エラーがあります" in footer:
            log("  ✓ フッターにエラーメッセージ")
        else:
            log(f"  △ フッター確認: '{footer}'")

        # 検証3: 「添付を実行する」ボタンが disabled
        if step2.get("execEnabled") is False:
            log("  ✓ 「添付を実行する」ボタン: disabled")
        else:
            log("  ✗ 「添付を実行する」ボタン: enabled（期待: disabled）")
            result["error"] = "「添付を実行する」ボタンがdisabledになっていません"
            close_modal(page)
            return result

        # 検証4: h4 に「エラー」が含まれる
        has_heading_error = any("エラー" in h for h in step2.get("headings", []))
        if has_heading_error:
            log("  ✓ 見出しに「エラー」表示")

        result["success"] = True
        log(f"  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = f"例外: {str(e)}"
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


# ===== 境界値 正常系テスト =====
def test_boundary_ok(page, tc_id, tc_name, file_paths, invoice_index):
    """
    境界値の正常系テスト。ファイルをセット → Step 2 で「添付可能」判定を確認。
    ※実際の添付実行は行わない（テスト用請求書の保護）
    """
    log(f"\n{'=' * 60}")
    log(f"{tc_id}: {tc_name}")
    log(f"{'=' * 60}")

    result = {"tc_id": tc_id, "tc_name": tc_name, "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        # ファイルセット
        total_size = sum(os.path.getsize(f) for f in file_paths)
        log(f"  ファイル: {len(file_paths)}件, 合計 {total_size / 1024 / 1024:.2f} MB")
        page.locator('input[type="file"]').set_input_files(file_paths)
        page.wait_for_timeout(3000)


        # Step 1: 確認
        step1 = get_step1_state(page)
        if not step1.get("confirmEnabled"):
            log(f"  ✗ Step 1: 「確認へ進む」disabled")
            log(f"  エラー: {step1.get('errors', [])}")
            result["error"] = "Step 1 でブロックされました"
            close_modal(page)
            return result
        log("  ✓ Step 1: 「確認へ進む」enabled")

        # Step 2 へ
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)

        # 非同期判定待機
        log("  非同期判定待機中...")
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了（{i + 1}秒）")
                break
        else:
            log("  判定: 30秒経過してもボタンdisabled")

        page.wait_for_timeout(1000)

        # Step 2 状態
        step2 = get_step2_state(page)
        log(f"  判定列: {step2.get('judgments', [])}")
        log(f"  フッター: {step2.get('footerMsg', '')}")

        # 検証1: 判定列に「添付可能」
        has_ok = any("添付可能" in j for j in step2.get("judgments", []))
        if has_ok:
            log("  ✓ 判定列: 「添付可能」")
        else:
            log(f"  ✗ 判定列に「添付可能」なし: {step2.get('judgments', [])}")
            result["error"] = f"判定が「添付可能」ではない: {step2.get('judgments', [])}"
            close_modal(page)
            return result

        # 検証2: 「添付を実行する」enabled
        if step2.get("execEnabled"):
            log("  ✓ 「添付を実行する」ボタン: enabled")
        else:
            log("  ✗ 「添付を実行する」ボタン: disabled")
            result["error"] = "「添付を実行する」ボタンがdisabledです"
            close_modal(page)
            return result

        # 検証3: フッターメッセージ
        if "実行可能" in step2.get("footerMsg", ""):
            log("  ✓ フッター: 「添付を実行可能です」")

        result["success"] = True
        log(f"  結果: PASS ✓")

        # ※添付実行はしない（「戻る」→「閉じる」で終了）
        close_modal(page)

    except Exception as e:
        result["error"] = f"例外: {str(e)}"
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
        log("ERROR: TEST_EMAIL / TEST_PASSWORD が .env に設定されていません")
        log_fh.close()
        return

    log(f"テスト開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"ログファイル: {LOG_FILE}")

    # ===== テストケース定義 =====
    # 使用する請求書index: 各テストで異なるものを使用
    # index 0-4: 正常系テスト(TH-01~04)で使用済みの可能性あり
    # index 5-9: 異常系テスト用

    tests = []

    # ====================================================================
    # 注意: index 0-3 は正常系テスト(TH-01~04)で使用済みの可能性あり。
    # 既添付の請求書を使うと「添付数上限を超過」エラーが出るため、
    # 全テストで一覧の後ろ（index 0-9）を使い、
    # Step 1 エラー系は既添付でも影響なし（Step 2 に進まない）ので前方を使用。
    # Step 2 エラー系・境界値系は未使用の請求書を使用する。
    # ====================================================================

    # --- 異常系: Step 1 エラー（既添付でも影響なし） ---
    tests.append({
        "type": "step1_error",
        "tc_id": "TH-E01",
        "tc_name": "ファイルサイズ超過 (10.1MB)",
        "files": [os.path.join(FILESIZE_DIR, "02_single_10MB_over", "file_10.1MB.pdf")],
        "index": 5,
        "expected": "エラー",
    })
    tests.append({
        "type": "step1_error",
        "tc_id": "TH-E04",
        "tc_name": "拡張子なしファイル",
        "files": [os.path.join(EXTENSION_DIR, "_")],
        "index": 5,  # Step 1 でブロックされるので同じ請求書でOK
        "expected": "エラー",
    })

    # --- 異常系: Step 2 エラー（未使用の請求書を使用） ---
    tests.append({
        "type": "step2_error",
        "tc_id": "TH-E02",
        "tc_name": "11ファイル同時選択（ファイル数超過）",
        "files": [os.path.join(FILESIZE_DIR, "04_11files_upload", f"file_{i:02d}.pdf") for i in range(1, 12)],
        "index": 6,
        "expected": "添付数上限を超過しています",
    })
    tests.append({
        "type": "step2_error",
        "tc_id": "TH-E03",
        "tc_name": "合計サイズ超過 (5ファイル 10.5MB)",
        "files": [os.path.join(FILESIZE_DIR, "06_total_10MB_over", f"file_{i:02d}.pdf") for i in range(1, 6)],
        "index": 7,
        "expected": "ファイルサイズ上限を超過しています",
    })

    # --- 異常系: Step 2 エラー（9.9MB = サイズ超過） ---
    # 分析結果: 9.9MB (10,380,902 bytes) はサーバー側でサイズ上限超過と判定される
    tests.append({
        "type": "step2_error",
        "tc_id": "TH-E05",
        "tc_name": "9.9MB 1ファイル（ファイルサイズ超過）",
        "files": [os.path.join(FILESIZE_DIR, "01_single_10MB_under", "file_9.9MB.pdf")],
        "index": 8,
        "expected": "ファイルサイズ上限を超過しています",
    })

    # --- 境界値 正常系（未使用の請求書を使用） ---
    tests.append({
        "type": "boundary_ok",
        "tc_id": "TH-E06",
        "tc_name": "10ファイル同時（境界値 OK）",
        "files": [os.path.join(FILESIZE_DIR, "03_10files_upload", f"file_{i:02d}.pdf") for i in range(1, 11)],
        "index": 9,
    })
    tests.append({
        "type": "boundary_ok",
        "tc_id": "TH-E07",
        "tc_name": "合計9.5MB (5ファイル)（境界値 OK）",
        "files": [os.path.join(FILESIZE_DIR, "05_total_10MB_under", f"file_{i:02d}.pdf") for i in range(1, 6)],
        "index": 5,  # Step 1 エラー系で使ったが添付実行しないので再利用可能
    })
    tests.append({
        "type": "boundary_ok",
        "tc_id": "TH-E08",
        "tc_name": "特殊記号ファイル名 (!@#$%&()=~.pdf)",
        "files": [os.path.join(FILENAME_DIR, "!@#$%&()=~.pdf")],
        "index": 5,  # 同上
    })
    tests.append({
        "type": "boundary_ok",
        "tc_id": "TH-E09",
        "tc_name": "5.0MB 1ファイル（境界値 OK）",
        "files": [os.path.join(FILESIZE_DIR, "07_single_5MB", "file_5.0MB.pdf")],
        "index": 5,  # 同上（添付実行しないので再利用可能）
    })

    # ファイル存在チェック
    all_ok = True
    for t in tests:
        for fp in t["files"]:
            if not os.path.exists(fp):
                log(f"WARNING: ファイルなし: {fp}")
                all_ok = False
    if not all_ok:
        log("テストファイルが不足しています。中断します。")
        log_fh.close()
        return

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

        for t in tests:
            tc_id = t["tc_id"]
            page = context.new_page()
            try:
                page.goto(f"{BASE_URL}/invoices")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)

                if t["type"] == "step1_error":
                    r = test_step1_error(page, t["tc_id"], t["tc_name"], t["files"], t["index"], t["expected"])
                elif t["type"] == "step2_error":
                    r = test_step2_error(page, t["tc_id"], t["tc_name"], t["files"], t["index"], t["expected"])
                elif t["type"] == "boundary_ok":
                    r = test_boundary_ok(page, t["tc_id"], t["tc_name"], t["files"], t["index"])
                else:
                    r = {"tc_id": tc_id, "tc_name": t["tc_name"], "success": False, "error": "unknown type"}
                results.append(r)
            except Exception as e:
                log(f"\n結果: FAIL ✗ (例外: {e})")
                results.append({
                    "tc_id": tc_id,
                    "tc_name": t["tc_name"],
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

    # JSON保存
    json_path = os.path.join(LOGS_DIR, f"test_error_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"JSON結果: {json_path}")

    log_fh.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
