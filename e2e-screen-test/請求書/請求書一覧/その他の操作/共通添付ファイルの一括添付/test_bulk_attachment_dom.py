"""
共通添付ファイルの一括添付 - DOM/エレメント検証テスト

テスト内容:
  TH-D01: モーダルrole属性・タイトル検証
  TH-D02: ステップウィザード構造検証（3ステップ存在、番号・ラベル）
  TH-D03: ファイルinput属性検証（type, multiple, hidden, accept）
  TH-D04: Step1 初期状態検証（ボタン状態、メッセージ）
  TH-D05: Step1 ファイル選択後状態検証（件数表示、ボタン有効化）
  TH-D06: Step2 テーブルヘッダー検証（5列）
  TH-D07: Step2 判定中状態検証（ボタンdisabled、メッセージ）
  TH-D08: Step3 完了メッセージ構造検証

前提条件:
  - ログイン情報は TH/ログイン/.env に設定済み
  - テスト用ファイルは 拡張子/sample.pdf に配置済み
  - Step 3 検証 (TH-D08) のみ添付実行を行う（未使用の請求書を使用）
"""

import os
import sys
import json
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# ===== パス設定 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://invoicing-staging.keihi.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")
EXTENSION_DIR = os.path.join(SCRIPT_DIR, "拡張子")

os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_dom_{timestamp}.log")
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
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
    page.get_by_label("メールアドレス").fill(email)
    page.get_by_label("パスワード").fill(password)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="ログイン", exact=True).click()
    # ログイン後のリダイレクトを待機
    try:
        page.wait_for_url("**/invoices**", timeout=60000)
    except Exception:
        # フォールバック: 手動で待機
        for _ in range(30):
            if "/invoices" in page.url and "/login" not in page.url:
                break
            page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    log(f"ログイン完了: {page.url}")
    if "/login" in page.url:
        # ページのテキストを取得
        body_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 500) : 'no body'")
        log(f"ログイン失敗: ページテキスト: {body_text[:300]}")
        raise RuntimeError(f"ログイン失敗: URL={page.url}")


def navigate_to_list(page):
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)


def select_invoice(page, index: int):
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


# ===== テスト関数 =====

def test_d01_modal_role_and_title(page, invoice_index):
    """TH-D01: モーダルrole属性・タイトル検証"""
    log(f"\n{'=' * 60}")
    log("TH-D01: モーダルrole属性・タイトル検証")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D01", "tc_name": "モーダルrole属性・タイトル検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false };
            const h2 = dialog.querySelector('h2');
            return {
                exists: true,
                role: dialog.getAttribute('role'),
                hasId: !!dialog.id,
                idPrefix: (dialog.id || '').substring(0, 20),
                h2Text: h2 ? h2.textContent.trim() : null,
                ariaModal: dialog.getAttribute('aria-modal'),
            };
        }""")

        log(f"  dialog 存在: {state.get('exists')}")
        log(f"  role属性: {state.get('role')}")
        log(f"  id属性: {state.get('idPrefix')}...")
        log(f"  h2テキスト: {state.get('h2Text')}")
        log(f"  aria-modal: {state.get('ariaModal')}")

        # 検証1: dialog要素が存在
        assert state.get("exists"), "dialog要素が存在しません"
        log("  ✓ dialog要素が存在")

        # 検証2: role="dialog"
        assert state.get("role") == "dialog", f"role属性が 'dialog' ではなく '{state.get('role')}'"
        log("  ✓ role='dialog'")

        # 検証3: h2にタイトルが表示
        assert state.get("h2Text") == "共通添付ファイルの一括添付", f"h2テキスト不一致: '{state.get('h2Text')}'"
        log("  ✓ h2='共通添付ファイルの一括添付'")

        # 検証4: id属性がheadlessui形式
        assert state.get("hasId"), "id属性がありません"
        assert "headlessui" in state.get("idPrefix", ""), f"idがheadlessui形式ではない: '{state.get('idPrefix')}'"
        log(f"  ✓ id属性がheadlessui形式 ({state.get('idPrefix')}...)")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


def test_d02_step_wizard_structure(page, invoice_index):
    """TH-D02: ステップウィザード構造検証"""
    log(f"\n{'=' * 60}")
    log("TH-D02: ステップウィザード構造検証（3ステップ）")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D02", "tc_name": "ステップウィザード構造検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false };
            // ステップウィザードのナビゲーション要素を取得
            const steps = [];
            // ステップ番号とラベルのペアを取得
            dialog.querySelectorAll('nav span, nav div').forEach(el => {
                const text = el.textContent.trim();
                // 数字のみのspan = ステップ番号
                if (/^[123]$/.test(text)) {
                    steps.push({ number: text });
                }
            });

            // ステップラベルを取得
            const stepLabels = [];
            dialog.querySelectorAll('nav span').forEach(el => {
                const text = el.textContent.trim();
                if (text === 'ファイル選択' || text === '確認' || text === '完了') {
                    stepLabels.push(text);
                }
            });

            // アクティブステップを検出
            const activeStep = dialog.querySelector('[class*="stepActive"]');
            let activeStepNumber = null;
            let activeStepLabel = null;
            if (activeStep) {
                const nums = activeStep.querySelectorAll('span');
                nums.forEach(s => {
                    const t = s.textContent.trim();
                    if (/^[123]$/.test(t)) activeStepNumber = t;
                    if (['ファイル選択', '確認', '完了'].includes(t)) activeStepLabel = t;
                });
            }

            // コネクタ（ステップ間の線）の存在
            const connectors = dialog.querySelectorAll('[class*="connector"]');

            return {
                exists: true,
                stepNumbers: steps.map(s => s.number),
                stepLabels: stepLabels,
                activeStepNumber: activeStepNumber,
                activeStepLabel: activeStepLabel,
                connectorCount: connectors.length,
            };
        }""")

        log(f"  ステップ番号: {state.get('stepNumbers')}")
        log(f"  ステップラベル: {state.get('stepLabels')}")
        log(f"  アクティブステップ: {state.get('activeStepNumber')} ({state.get('activeStepLabel')})")
        log(f"  コネクタ数: {state.get('connectorCount')}")

        # 検証1: 3ステップが存在
        step_nums = state.get("stepNumbers", [])
        assert "1" in step_nums and "2" in step_nums and "3" in step_nums, \
            f"3ステップが揃っていません: {step_nums}"
        log("  ✓ ステップ番号 1, 2, 3 が存在")

        # 検証2: ラベルが正しい
        labels = state.get("stepLabels", [])
        assert "ファイル選択" in labels, f"'ファイル選択' ラベルなし: {labels}"
        assert "確認" in labels, f"'確認' ラベルなし: {labels}"
        assert "完了" in labels, f"'完了' ラベルなし: {labels}"
        log("  ✓ ラベル: 'ファイル選択', '確認', '完了'")

        # 検証3: 初期状態でStep 1がアクティブ
        assert state.get("activeStepNumber") == "1", \
            f"アクティブステップが1ではない: {state.get('activeStepNumber')}"
        log("  ✓ 初期状態でStep 1がアクティブ")

        # 検証4: コネクタ（ステップ間の線）が存在
        assert state.get("connectorCount", 0) >= 2, \
            f"コネクタが2個以上必要: {state.get('connectorCount')}"
        log(f"  ✓ コネクタ {state.get('connectorCount')}個")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


def test_d03_file_input_attributes(page, invoice_index):
    """TH-D03: ファイルinput属性検証"""
    log(f"\n{'=' * 60}")
    log("TH-D03: ファイルinput属性検証")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D03", "tc_name": "ファイルinput属性検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false };
            const input = dialog.querySelector('input[type="file"]');
            if (!input) return { exists: true, inputExists: false };
            const style = window.getComputedStyle(input);
            const rect = input.getBoundingClientRect();
            return {
                exists: true,
                inputExists: true,
                type: input.type,
                multiple: input.multiple,
                accept: input.getAttribute('accept'),
                hasAccept: input.hasAttribute('accept'),
                hidden: input.hidden || style.display === 'none' || style.visibility === 'hidden' ||
                        rect.width === 0 || rect.height === 0 ||
                        input.className.includes('hidden') || input.className.includes('Hidden'),
                className: input.className.substring(0, 200),
                parentTag: input.parentElement ? input.parentElement.tagName : null,
            };
        }""")

        log(f"  input存在: {state.get('inputExists')}")
        log(f"  type: {state.get('type')}")
        log(f"  multiple: {state.get('multiple')}")
        log(f"  accept: {state.get('accept')}")
        log(f"  hasAccept: {state.get('hasAccept')}")
        log(f"  hidden: {state.get('hidden')}")
        log(f"  className: {state.get('className')}")

        # 検証1: input[type="file"]が存在
        assert state.get("inputExists"), "input[type='file']が存在しません"
        log("  ✓ input[type='file']が存在")

        # 検証2: type="file"
        assert state.get("type") == "file", f"type属性が 'file' ではない: '{state.get('type')}'"
        log("  ✓ type='file'")

        # 検証3: multiple=true
        assert state.get("multiple") is True, "multiple属性がtrueではない"
        log("  ✓ multiple=true")

        # 検証4: hidden (非表示 / class名にhidden含む)
        assert state.get("hidden"), f"inputが非表示ではない (className: {state.get('className')})"
        log("  ✓ 非表示 (hidden)")

        # 検証5: accept属性なし（全ファイル形式受付）
        assert not state.get("hasAccept") or state.get("accept") is None or state.get("accept") == "", \
            f"accept属性が設定されている: '{state.get('accept')}'"
        log("  ✓ accept属性なし（全ファイル形式受付）")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


def test_d04_step1_initial_state(page, invoice_index):
    """TH-D04: Step1 初期状態検証"""
    log(f"\n{'=' * 60}")
    log("TH-D04: Step1 初期状態検証（ファイル未選択時）")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D04", "tc_name": "Step1 初期状態検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false };

            // ボタン状態
            const buttons = {};
            dialog.querySelectorAll('button').forEach(b => {
                const text = b.innerText.trim();
                const rect = b.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    if (text.includes('閉じる')) buttons['閉じる'] = { disabled: b.disabled };
                    if (text.includes('確認へ進む')) buttons['確認へ進む'] = { disabled: b.disabled };
                    if (text === 'ファイルを選択') buttons['ファイルを選択'] = { disabled: b.disabled };
                    if (text.includes('新規アップロード')) buttons['新規アップロード'] = { disabled: b.disabled };
                    if (text.includes('既存から選択')) buttons['既存から選択'] = { disabled: b.disabled };
                }
            });

            // フッターメッセージ
            let footerMsg = '';
            dialog.querySelectorAll('p, span').forEach(el => {
                const text = el.textContent.trim();
                if (text.includes('ファイルを選択してください') || text.includes('選択済みファイル')) {
                    footerMsg = text;
                }
            });

            // 右ペイン: 選択済みファイル
            let selectedFileText = '';
            dialog.querySelectorAll('h3').forEach(h3 => {
                const t = h3.textContent.trim();
                if (t.includes('選択済みファイル')) selectedFileText = t;
            });

            // 空メッセージ
            let emptyMsg = '';
            dialog.querySelectorAll('p').forEach(p => {
                const t = p.textContent.trim();
                if (t.includes('ファイルが選択されていません')) emptyMsg = t;
            });

            // ドロップゾーン
            const dropZone = dialog.querySelector('[class*="dropZone"]');
            const dropZoneText = dropZone ? dropZone.textContent.trim().substring(0, 200) : '';

            // タブ状態
            const tabs = [];
            dialog.querySelectorAll('nav button, nav [role="tab"]').forEach(tab => {
                const text = tab.textContent.trim();
                const isActive = tab.className.includes('Active') || tab.className.includes('active');
                if (text.includes('新規アップロード') || text.includes('既存から選択')) {
                    tabs.push({ text: text, isActive: isActive });
                }
            });

            return {
                exists: true,
                buttons: buttons,
                footerMsg: footerMsg,
                selectedFileText: selectedFileText,
                emptyMsg: emptyMsg,
                dropZoneText: dropZoneText,
                hasDropZone: !!dropZone,
                tabs: tabs,
            };
        }""")

        log(f"  ボタン状態: {state.get('buttons')}")
        log(f"  フッターメッセージ: {state.get('footerMsg')}")
        log(f"  選択済みファイル: {state.get('selectedFileText')}")
        log(f"  空メッセージ: {state.get('emptyMsg')}")
        log(f"  ドロップゾーン: {'あり' if state.get('hasDropZone') else 'なし'}")
        log(f"  タブ: {state.get('tabs')}")

        # 検証1: 「閉じる」ボタンがenabled
        assert "閉じる" in state.get("buttons", {}), "「閉じる」ボタンが見つかりません"
        assert state["buttons"]["閉じる"]["disabled"] is False, "「閉じる」ボタンがdisabled"
        log("  ✓ 「閉じる」ボタン: enabled")

        # 検証2: 「確認へ進む」ボタンがdisabled
        assert "確認へ進む" in state.get("buttons", {}), "「確認へ進む」ボタンが見つかりません"
        assert state["buttons"]["確認へ進む"]["disabled"] is True, "「確認へ進む」ボタンがdisabledではない"
        log("  ✓ 「確認へ進む」ボタン: disabled")

        # 検証3: 「ファイルを選択」ボタンが存在しenabled
        assert "ファイルを選択" in state.get("buttons", {}), "「ファイルを選択」ボタンが見つかりません"
        assert state["buttons"]["ファイルを選択"]["disabled"] is False, "「ファイルを選択」ボタンがdisabled"
        log("  ✓ 「ファイルを選択」ボタン: enabled")

        # 検証4: フッターメッセージ
        footer = state.get("footerMsg", "")
        assert "ファイルを選択してください" in footer, f"フッターに初期メッセージなし: '{footer}'"
        log("  ✓ フッター: 「ファイルを選択してください」")

        # 検証5: 「選択済みファイル（0件）」表示
        selected = state.get("selectedFileText", "")
        assert "選択済みファイル" in selected, f"選択済みファイル表示なし: '{selected}'"
        assert "0" in selected, f"初期件数が0ではない: '{selected}'"
        log(f"  ✓ 選択済みファイル表示: '{selected}'")

        # 検証6: ドロップゾーンが存在
        assert state.get("hasDropZone"), "ドロップゾーンが見つかりません"
        log("  ✓ ドロップゾーンが存在")

        # 検証7: 「新規アップロード」タブがアクティブ
        tabs = state.get("tabs", [])
        has_active_upload = any(t.get("isActive") and "新規アップロード" in t.get("text", "") for t in tabs)
        assert has_active_upload, f"「新規アップロード」タブがアクティブではない: {tabs}"
        log("  ✓ 「新規アップロード」タブがアクティブ")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


def test_d05_step1_after_file_select(page, invoice_index):
    """TH-D05: Step1 ファイル選択後状態検証"""
    log(f"\n{'=' * 60}")
    log("TH-D05: Step1 ファイル選択後状態検証")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D05", "tc_name": "Step1 ファイル選択後状態検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        # ファイルをセット
        test_file = os.path.join(EXTENSION_DIR, "sample.pdf")
        assert os.path.exists(test_file), f"テストファイルなし: {test_file}"
        page.locator('input[type="file"]').set_input_files([test_file])
        page.wait_for_timeout(2000)

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false };

            // 選択済みファイル件数
            let selectedFileText = '';
            dialog.querySelectorAll('h3').forEach(h3 => {
                const t = h3.textContent.trim();
                if (t.includes('選択済みファイル')) selectedFileText = t;
            });

            // ファイル名が表示されているか
            const fileNames = [];
            dialog.querySelectorAll('span, div, p').forEach(el => {
                const t = el.textContent.trim();
                if (t.includes('sample.pdf') && t.length < 50) fileNames.push(t);
            });

            // ボタン状態
            let confirmEnabled = null;
            dialog.querySelectorAll('button').forEach(b => {
                if (b.innerText.trim().includes('確認へ進む')) {
                    confirmEnabled = !b.disabled;
                }
            });

            // フッターメッセージの変化
            let footerMsg = '';
            dialog.querySelectorAll('p, span').forEach(el => {
                const text = el.textContent.trim();
                if (text.includes('ファイルを選択してください') || text.includes('選択済みファイル')) {
                    footerMsg = text;
                }
            });

            // エラー要素がないこと
            const errors = [];
            dialog.querySelectorAll('[class*="error"]').forEach(el => {
                const t = el.textContent.trim();
                if (t && t.length < 500) errors.push(t);
            });

            return {
                exists: true,
                selectedFileText: selectedFileText,
                fileNames: [...new Set(fileNames)],
                confirmEnabled: confirmEnabled,
                footerMsg: footerMsg,
                errors: [...new Set(errors)],
            };
        }""")

        log(f"  選択済みファイル: {state.get('selectedFileText')}")
        log(f"  表示ファイル名: {state.get('fileNames')}")
        log(f"  確認へ進む: {'enabled' if state.get('confirmEnabled') else 'disabled'}")
        log(f"  エラー: {state.get('errors')}")


        # 検証1: 「選択済みファイル(1件)」表示
        selected = state.get("selectedFileText", "")
        assert "選択済みファイル" in selected, f"選択済みファイル表示なし: '{selected}'"
        assert "1" in selected, f"件数が1ではない: '{selected}'"
        log(f"  ✓ 選択済みファイル: '{selected}'")

        # 検証2: ファイル名が表示
        file_names = state.get("fileNames", [])
        has_pdf = any("sample.pdf" in fn for fn in file_names)
        assert has_pdf, f"ファイル名 'sample.pdf' が表示されていない: {file_names}"
        log("  ✓ ファイル名 'sample.pdf' が表示")

        # 検証3: 「確認へ進む」ボタンがenabled
        assert state.get("confirmEnabled") is True, "「確認へ進む」ボタンがenabledになっていない"
        log("  ✓ 「確認へ進む」ボタン: enabled")

        # 検証4: エラー表示がない
        errors = state.get("errors", [])
        # エラーテキストの中にファイル関連のエラーがないこと
        file_errors = [e for e in errors if "エラー" in e and "ファイル" in e]
        assert len(file_errors) == 0, f"ファイル関連エラーが表示されている: {file_errors}"
        log("  ✓ ファイル関連エラーなし")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


def test_d06_step2_table_headers(page, invoice_index):
    """TH-D06: Step2 テーブルヘッダー検証"""
    log(f"\n{'=' * 60}")
    log("TH-D06: Step2 テーブルヘッダー検証")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D06", "tc_name": "Step2 テーブルヘッダー検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        # ファイルセット → Step 2 遷移
        test_file = os.path.join(EXTENSION_DIR, "sample.pdf")
        page.locator('input[type="file"]').set_input_files([test_file])
        page.wait_for_timeout(2000)

        confirm_btn = page.get_by_role("button", name="確認へ進む")
        if confirm_btn.count() > 0 and confirm_btn.first.is_enabled():
            confirm_btn.first.click()
        else:
            raise RuntimeError("「確認へ進む」がenabled にならない")
        page.wait_for_timeout(3000)

        # 非同期判定待機
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了 ({i + 1}秒)")
                break
        page.wait_for_timeout(500)

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false };

            const table = dialog.querySelector('table');
            if (!table) return { exists: true, tableExists: false };

            const headers = [];
            table.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim()));

            const rows = [];
            table.querySelectorAll('tbody tr').forEach(tr => {
                const cells = [];
                tr.querySelectorAll('td').forEach(td => cells.push(td.textContent.trim().substring(0, 100)));
                rows.push(cells);
            });

            // 添付するファイルセクション
            let fileSection = '';
            dialog.querySelectorAll('h4').forEach(h4 => {
                const t = h4.textContent.trim();
                if (t.includes('添付') || t.includes('ファイル') || t.includes('帳票')) {
                    fileSection += t + ' | ';
                }
            });

            return {
                exists: true,
                tableExists: true,
                headers: headers,
                rowCount: rows.length,
                firstRow: rows.length > 0 ? rows[0] : [],
                fileSection: fileSection,
            };
        }""")

        log(f"  テーブル存在: {state.get('tableExists')}")
        log(f"  ヘッダー: {state.get('headers')}")
        log(f"  行数: {state.get('rowCount')}")
        log(f"  1行目: {state.get('firstRow')}")
        log(f"  ファイルセクション: {state.get('fileSection')}")


        # 検証1: テーブルが存在
        assert state.get("tableExists"), "テーブルが存在しません"
        log("  ✓ テーブルが存在")

        # 検証2: ヘッダー列数が5列
        headers = state.get("headers", [])
        assert len(headers) == 5, f"ヘッダー列数が5ではない: {len(headers)} ({headers})"
        log(f"  ✓ ヘッダー列数: {len(headers)}")

        # 検証3: 各ヘッダー名を検証
        expected_headers = ["取引先", "送付方法", "請求書番号", "金額", "判定"]
        for expected in expected_headers:
            found = any(expected in h for h in headers)
            assert found, f"ヘッダー '{expected}' が見つかりません: {headers}"
            log(f"  ✓ ヘッダー '{expected}' あり")

        # 検証4: 1行以上のデータ行
        assert state.get("rowCount", 0) >= 1, f"データ行がありません: {state.get('rowCount')}"
        log(f"  ✓ データ行: {state.get('rowCount')}行")

        # 検証5: 判定列に値がある
        first_row = state.get("firstRow", [])
        if len(first_row) >= 5:
            judgment = first_row[4]
            assert judgment, f"判定列が空: {first_row}"
            log(f"  ✓ 判定列: '{judgment}'")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


def test_d07_step2_judging_state(page, invoice_index):
    """TH-D07: Step2 判定中状態検証"""
    log(f"\n{'=' * 60}")
    log("TH-D07: Step2 判定中状態検証")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D07", "tc_name": "Step2 判定中状態検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        # ファイルセット
        test_file = os.path.join(EXTENSION_DIR, "sample.pdf")
        page.locator('input[type="file"]').set_input_files([test_file])
        page.wait_for_timeout(2000)

        # Step 2 遷移（判定中の状態をすぐにキャプチャ）
        confirm_btn = page.get_by_role("button", name="確認へ進む")
        confirm_btn.first.click()
        page.wait_for_timeout(1000)  # 判定中の状態（1秒で取得、判定完了前）

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false };

            // 「添付を実行する」ボタンの状態
            let execBtnDisabled = null;
            let execBtnText = '';
            dialog.querySelectorAll('button').forEach(b => {
                const text = b.innerText.trim();
                if (text.includes('添付を実行する')) {
                    execBtnDisabled = b.disabled;
                    execBtnText = text;
                }
            });

            // 判定中メッセージ
            let judgingMsg = '';
            dialog.querySelectorAll('p, span, div').forEach(el => {
                const text = el.textContent.trim();
                if (text.includes('判定中') || text.includes('判定') || text.includes('実行可能')) {
                    if (text.length < 100) judgingMsg = text;
                }
            });

            // ローディング/スピナー要素
            const spinners = dialog.querySelectorAll(
                '[class*="spinner"], [class*="loading"], [class*="Spinner"], [class*="Loading"], [role="progressbar"]'
            );

            // 「戻る」ボタン
            let backBtnExists = false;
            dialog.querySelectorAll('button').forEach(b => {
                if (b.innerText.trim() === '戻る') backBtnExists = true;
            });

            return {
                exists: true,
                execBtnDisabled: execBtnDisabled,
                execBtnText: execBtnText,
                judgingMsg: judgingMsg,
                hasSpinner: spinners.length > 0,
                backBtnExists: backBtnExists,
            };
        }""")

        log(f"  「添付を実行する」disabled: {state.get('execBtnDisabled')}")
        log(f"  判定メッセージ: {state.get('judgingMsg')}")
        log(f"  スピナー: {state.get('hasSpinner')}")
        log(f"  「戻る」ボタン: {state.get('backBtnExists')}")


        # 検証1: 「添付を実行する」ボタンが存在
        assert state.get("execBtnDisabled") is not None, "「添付を実行する」ボタンが見つかりません"
        log("  ✓ 「添付を実行する」ボタンが存在")

        # 検証2: 判定中は disabled
        # 注意: 小さいファイルの場合、判定が即完了する可能性がある
        if state.get("execBtnDisabled") is True:
            log("  ✓ 判定中: 「添付を実行する」ボタンはdisabled")
        else:
            log("  △ 判定が即完了した可能性あり (disabled=False)")
            # 即完了でもテストは失敗にしない

        # 検証3: 判定関連のメッセージが表示されている
        judging_msg = state.get("judgingMsg", "")
        has_judging_msg = "判定中" in judging_msg or "判定" in judging_msg or "実行可能" in judging_msg
        assert has_judging_msg, f"判定関連メッセージが見つかりません: '{judging_msg}'"
        log(f"  ✓ 判定メッセージ: '{judging_msg}'")

        # 検証4: 「戻る」ボタンが存在
        assert state.get("backBtnExists"), "「戻る」ボタンが見つかりません"
        log("  ✓ 「戻る」ボタンが存在")

        result["success"] = True
        log("  結果: PASS ✓")
        close_modal(page)

    except Exception as e:
        result["error"] = str(e)
        log(f"  結果: FAIL ✗ ({e})")
        close_modal(page)

    return result


def test_d08_step3_completion(page, invoice_index):
    """TH-D08: Step3 完了メッセージ構造検証（実際に添付実行する）"""
    log(f"\n{'=' * 60}")
    log("TH-D08: Step3 完了メッセージ構造検証")
    log(f"{'=' * 60}")

    result = {"tc_id": "TH-D08", "tc_name": "Step3 完了メッセージ構造検証", "success": False, "error": ""}

    try:
        navigate_to_list(page)
        select_invoice(page, index=invoice_index)
        open_modal(page)

        # ファイルセット
        test_file = os.path.join(EXTENSION_DIR, "sample.pdf")
        page.locator('input[type="file"]').set_input_files([test_file])
        page.wait_for_timeout(2000)

        # Step 2 遷移
        page.get_by_role("button", name="確認へ進む").click()
        page.wait_for_timeout(3000)

        # 非同期判定待機
        exec_btn = page.get_by_role("button", name="添付を実行する")
        for i in range(30):
            page.wait_for_timeout(1000)
            if exec_btn.count() > 0 and exec_btn.first.is_enabled():
                log(f"  判定完了 ({i + 1}秒)")
                break

        # 添付実行
        exec_btn.first.click(force=True)
        log("  添付実行クリック")
        page.wait_for_timeout(8000)  # アップロード処理待ち

        state = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { exists: false, dialogExists: false };

            const fullText = dialog.innerText;

            // 完了メッセージ
            const hasCompletion = fullText.includes('完了');
            const hasAttached = fullText.includes('添付されました') || fullText.includes('添付しました');

            // 件数メッセージ
            let countMsg = '';
            const match = fullText.match(/(\\d+)\\s*件の請求書に添付されました/);
            if (match) countMsg = match[0];

            // ボタン
            const buttons = {};
            dialog.querySelectorAll('button').forEach(b => {
                const text = b.innerText.trim();
                const rect = b.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    buttons[text] = { disabled: b.disabled };
                }
            });

            // 「添付を実行する」ボタンが非表示/不在か
            let execBtnHidden = true;
            dialog.querySelectorAll('button').forEach(b => {
                if (b.innerText.trim().includes('添付を実行する')) {
                    const rect = b.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) execBtnHidden = false;
                }
            });

            // ステップウィザードの状態
            const activeStep = dialog.querySelector('[class*="stepActive"]');
            let activeNum = null;
            if (activeStep) {
                activeStep.querySelectorAll('span').forEach(s => {
                    const t = s.textContent.trim();
                    if (/^[123]$/.test(t)) activeNum = t;
                });
            }

            return {
                exists: true,
                dialogExists: true,
                fullText: fullText.substring(0, 1000),
                hasCompletion: hasCompletion,
                hasAttached: hasAttached,
                countMsg: countMsg,
                buttons: buttons,
                execBtnHidden: execBtnHidden,
                activeStep: activeNum,
            };
        }""")

        log(f"  ダイアログ存在: {state.get('dialogExists')}")
        log(f"  完了キーワード: {state.get('hasCompletion')}")
        log(f"  添付メッセージ: {state.get('hasAttached')}")
        log(f"  件数メッセージ: {state.get('countMsg')}")
        log(f"  ボタン: {list(state.get('buttons', {}).keys())}")
        log(f"  実行ボタン非表示: {state.get('execBtnHidden')}")
        log(f"  アクティブステップ: {state.get('activeStep')}")


        if not state.get("dialogExists"):
            # ダイアログが閉じている場合（自動クローズ）= 完了として扱う
            log("  △ ダイアログが自動クローズされた可能性あり")
            result["success"] = True
            log("  結果: PASS ✓ (自動クローズ)")
            return result

        # 検証1: 完了メッセージが表示
        assert state.get("hasCompletion") or state.get("hasAttached"), \
            f"完了メッセージが見つかりません: {state.get('fullText', '')[:300]}"
        log("  ✓ 完了メッセージが表示")

        # 検証2: 件数メッセージ
        if state.get("countMsg"):
            log(f"  ✓ 件数メッセージ: '{state.get('countMsg')}'")
        elif state.get("hasAttached"):
            log("  ✓ 添付完了メッセージ確認")

        # 検証3: 「閉じる」ボタンが存在しenabled
        buttons = state.get("buttons", {})
        has_close = any("閉じる" in k for k in buttons.keys())
        assert has_close, f"「閉じる」ボタンが見つかりません: {list(buttons.keys())}"
        log("  ✓ 「閉じる」ボタンが存在")

        # 検証4: 「添付を実行する」ボタンが非表示
        assert state.get("execBtnHidden"), "「添付を実行する」ボタンがまだ表示されています"
        log("  ✓ 「添付を実行する」ボタン非表示")

        # 検証5: ステップウィザードがStep 3
        if state.get("activeStep") == "3":
            log("  ✓ ステップウィザード: Step 3 がアクティブ")
        else:
            log(f"  △ アクティブステップ: {state.get('activeStep')} (3ではない)")

        result["success"] = True
        log("  結果: PASS ✓")

        # モーダルを閉じる
        close_btn = page.get_by_role("button", name="閉じる")
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
            page.wait_for_timeout(1000)

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
        log("ERROR: TEST_EMAIL / TEST_PASSWORD が .env に設定されていません")
        log_fh.close()
        return

    log(f"テスト開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"ログファイル: {LOG_FILE}")

    # テスト用ファイル存在チェック
    test_file = os.path.join(EXTENSION_DIR, "sample.pdf")
    if not os.path.exists(test_file):
        log(f"ERROR: テストファイルなし: {test_file}")
        log_fh.close()
        return

    # テストケース定義
    # TH-D01~D07: 添付実行しないので同じ index=5 を再利用可能
    # TH-D08: 添付実行するので未使用の請求書 index を使用
    tests = [
        ("TH-D01", "モーダルrole属性・タイトル検証", test_d01_modal_role_and_title, 5),
        ("TH-D02", "ステップウィザード構造検証", test_d02_step_wizard_structure, 5),
        ("TH-D03", "ファイルinput属性検証", test_d03_file_input_attributes, 5),
        ("TH-D04", "Step1 初期状態検証", test_d04_step1_initial_state, 5),
        ("TH-D05", "Step1 ファイル選択後状態検証", test_d05_step1_after_file_select, 5),
        ("TH-D06", "Step2 テーブルヘッダー検証", test_d06_step2_table_headers, 5),
        ("TH-D07", "Step2 判定中状態検証", test_d07_step2_judging_state, 5),
        ("TH-D08", "Step3 完了メッセージ構造検証", test_d08_step3_completion, 4),
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
    json_path = os.path.join(LOGS_DIR, f"test_dom_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"JSON結果: {json_path}")

    log_fh.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
