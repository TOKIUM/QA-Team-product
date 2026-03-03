"""
「既存から選択」タブのUI構造を分析するスクリプト

目的: Category L テスト実装のための事前分析
- 「既存から選択」タブの内部DOM構造
- 表示される要素（ファイル一覧、検索UI等）
- ファイル選択の操作方法
- Step2への遷移可否
"""

import os
import sys
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://invoicing-staging.keihi.com"
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")
os.makedirs(RESULT_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(RESULT_DIR, f"analyze_existing_tab_{timestamp}.log")
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

    log(f"分析開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
        navigate_to_list(page)
        select_invoice(page, 5)
        open_modal(page)

        # ==================================================
        # 1. 初期タブ状態の分析
        # ==================================================
        log("\n========== 1. 初期タブ状態 ==========")
        tab_info = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return { error: 'dialog not found' };
            const result = { tabs: [], navHTML: '' };
            const nav = d.querySelector('nav');
            if (nav) {
                result.navHTML = nav.outerHTML.substring(0, 2000);
                nav.querySelectorAll('button').forEach(b => {
                    result.tabs.push({
                        text: b.textContent.trim(),
                        className: b.className,
                        ariaSelected: b.getAttribute('aria-selected'),
                        tagName: b.tagName,
                        role: b.getAttribute('role')
                    });
                });
            }
            return result;
        }""")
        log(f"  タブ数: {len(tab_info.get('tabs', []))}")
        for t in tab_info.get("tabs", []):
            log(f"  タブ: '{t['text']}' | class='{t['className'][:100]}' | aria-selected={t.get('ariaSelected')}")

        # スクリーンショット: Step1初期
        page.screenshot(path=os.path.join(RESULT_DIR, f"existing_tab_step1_initial_{timestamp}.png"))

        # ==================================================
        # 2. 「既存から選択」タブクリック
        # ==================================================
        log("\n========== 2. 「既存から選択」タブクリック ==========")
        existing_tab = page.locator('button').filter(has_text="既存から選択")
        if existing_tab.count() > 0:
            existing_tab.first.click()
            page.wait_for_timeout(3000)
            log("  「既存から選択」タブをクリック")

            # スクリーンショット
            page.screenshot(path=os.path.join(RESULT_DIR, f"existing_tab_clicked_{timestamp}.png"))

            # タブ状態
            tab_after = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return { error: 'dialog not found' };
                const result = { tabs: [] };
                const nav = d.querySelector('nav');
                if (nav) {
                    nav.querySelectorAll('button').forEach(b => {
                        result.tabs.push({
                            text: b.textContent.trim(),
                            className: b.className,
                            ariaSelected: b.getAttribute('aria-selected'),
                        });
                    });
                }
                return result;
            }""")
            for t in tab_after.get("tabs", []):
                log(f"  タブ状態: '{t['text']}' | class='{t['className'][:100]}' | aria-selected={t.get('ariaSelected')}")

            # ==================================================
            # 3. 「既存から選択」タブの内部DOM構造分析
            # ==================================================
            log("\n========== 3. 「既存から選択」タブのDOM構造 ==========")
            dom_info = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return { error: 'dialog not found' };
                const result = {
                    allText: '',
                    inputs: [],
                    buttons: [],
                    tables: [],
                    lists: [],
                    checkboxes: [],
                    divStructure: [],
                    searchInputs: [],
                };

                // ダイアログ内の全テキスト
                result.allText = d.innerText.substring(0, 3000);

                // input要素
                d.querySelectorAll('input').forEach(inp => {
                    result.inputs.push({
                        type: inp.type,
                        name: inp.name,
                        placeholder: inp.placeholder,
                        className: inp.className.substring(0, 100),
                        value: inp.value,
                        hidden: inp.hidden || inp.type === 'hidden',
                    });
                });

                // ボタン
                d.querySelectorAll('button').forEach(btn => {
                    result.buttons.push({
                        text: btn.textContent.trim().substring(0, 100),
                        className: btn.className.substring(0, 100),
                        disabled: btn.disabled,
                    });
                });

                // テーブル
                d.querySelectorAll('table').forEach(tbl => {
                    const headers = [];
                    tbl.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim()));
                    const rowCount = tbl.querySelectorAll('tbody tr').length;
                    result.tables.push({ headers, rowCount });
                });

                // チェックボックス
                d.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    result.checkboxes.push({
                        name: cb.name,
                        id: cb.id,
                        checked: cb.checked,
                        className: cb.className.substring(0, 100),
                    });
                });

                // リスト要素
                d.querySelectorAll('ul, ol').forEach(list => {
                    const items = [];
                    list.querySelectorAll('li').forEach(li => items.push(li.textContent.trim().substring(0, 100)));
                    if (items.length > 0) result.lists.push(items);
                });

                // 検索入力
                d.querySelectorAll('input[type="search"], input[type="text"], input[placeholder*="検索"]').forEach(inp => {
                    result.searchInputs.push({
                        type: inp.type,
                        placeholder: inp.placeholder,
                        className: inp.className.substring(0, 100),
                    });
                });

                // 主要なdivの子要素構造（最初の3レベル）
                function getStructure(el, depth) {
                    if (depth > 3) return null;
                    const children = [];
                    for (let child of el.children) {
                        const info = {
                            tag: child.tagName.toLowerCase(),
                            className: child.className ? child.className.toString().substring(0, 80) : '',
                            text: child.childNodes.length === 1 && child.childNodes[0].nodeType === 3
                                  ? child.textContent.trim().substring(0, 50) : '',
                            role: child.getAttribute('role') || '',
                        };
                        const sub = getStructure(child, depth + 1);
                        if (sub && sub.length > 0) info.children = sub;
                        children.push(info);
                    }
                    return children;
                }

                // ダイアログ直下の構造
                result.divStructure = getStructure(d, 0);

                return result;
            }""")

            log(f"\n  === テキスト内容 ===")
            log(f"  {dom_info.get('allText', '')[:1500]}")

            log(f"\n  === input要素 ({len(dom_info.get('inputs', []))}) ===")
            for inp in dom_info.get("inputs", []):
                log(f"    type={inp['type']} | name='{inp['name']}' | placeholder='{inp['placeholder']}' | hidden={inp['hidden']}")

            log(f"\n  === ボタン ({len(dom_info.get('buttons', []))}) ===")
            for btn in dom_info.get("buttons", []):
                log(f"    '{btn['text']}' | disabled={btn['disabled']} | class='{btn['className'][:60]}'")

            log(f"\n  === テーブル ({len(dom_info.get('tables', []))}) ===")
            for tbl in dom_info.get("tables", []):
                log(f"    headers={tbl['headers']} | rows={tbl['rowCount']}")

            log(f"\n  === チェックボックス ({len(dom_info.get('checkboxes', []))}) ===")
            for cb in dom_info.get("checkboxes", []):
                log(f"    name='{cb['name']}' | id='{cb['id']}' | checked={cb['checked']}")

            log(f"\n  === リスト ({len(dom_info.get('lists', []))}) ===")
            for lst in dom_info.get("lists", []):
                log(f"    items({len(lst)}): {lst[:5]}")

            log(f"\n  === 検索入力 ({len(dom_info.get('searchInputs', []))}) ===")
            for si in dom_info.get("searchInputs", []):
                log(f"    type={si['type']} | placeholder='{si['placeholder']}'")

            # ==================================================
            # 4. 既存ファイルの有無チェック
            # ==================================================
            log("\n========== 4. 既存ファイル一覧チェック ==========")
            file_list = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return [];
                const files = [];
                // テーブル行からファイル情報取得
                d.querySelectorAll('table tbody tr').forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td'));
                    const row = cells.map(c => c.textContent.trim().substring(0, 100));
                    files.push(row);
                });
                // リストアイテムからもチェック
                if (files.length === 0) {
                    d.querySelectorAll('li, [class*="file"], [class*="item"]').forEach(el => {
                        const t = el.textContent.trim();
                        if (t.length > 0 && t.length < 200) files.push([t]);
                    });
                }
                return files;
            }""")
            log(f"  ファイル数: {len(file_list)}")
            for i, row in enumerate(file_list[:20]):
                log(f"  [{i}] {row}")

            # ==================================================
            # 5. ファイルを選択して「確認へ進む」の状態確認
            # ==================================================
            log("\n========== 5. ファイル選択操作の試行 ==========")

            # チェックボックスがあればクリック
            checkboxes_in_dialog = page.locator('[role="dialog"] input[type="checkbox"]')
            cb_count = checkboxes_in_dialog.count()
            log(f"  ダイアログ内チェックボックス数: {cb_count}")

            if cb_count > 0:
                # 最初のチェックボックスをクリック
                checkboxes_in_dialog.first.click(force=True)
                page.wait_for_timeout(1000)

                # 選択後の状態
                after_select = page.evaluate("""() => {
                    const d = document.querySelector('[role="dialog"]');
                    if (!d) return {};
                    const confirmBtn = d.querySelector('button');
                    const buttons = [];
                    d.querySelectorAll('button').forEach(b => {
                        buttons.push({ text: b.textContent.trim().substring(0, 50), disabled: b.disabled });
                    });
                    const selectedText = d.innerText.match(/選択済み[^\\n]*/)?.[0] || '';
                    return { buttons, selectedText };
                }""")
                log(f"  選択済みテキスト: {after_select.get('selectedText', '')}")
                for btn in after_select.get("buttons", []):
                    log(f"  ボタン: '{btn['text']}' | disabled={btn['disabled']}")

                page.screenshot(path=os.path.join(RESULT_DIR, f"existing_tab_selected_{timestamp}.png"))

            # テーブル行クリック（チェックボックスがない場合）
            elif len(file_list) > 0:
                table_rows = page.locator('[role="dialog"] table tbody tr')
                if table_rows.count() > 0:
                    table_rows.first.click()
                    page.wait_for_timeout(1000)
                    log("  テーブル行クリック実行")
                    page.screenshot(path=os.path.join(RESULT_DIR, f"existing_tab_row_click_{timestamp}.png"))

            # ==================================================
            # 6. 「確認へ進む」ボタンの状態
            # ==================================================
            log("\n========== 6. 「確認へ進む」ボタン状態 ==========")
            confirm_btn_state = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return null;
                const btns = d.querySelectorAll('button');
                for (const b of btns) {
                    if (b.textContent.includes('確認へ進む')) {
                        return {
                            text: b.textContent.trim(),
                            disabled: b.disabled,
                            className: b.className.substring(0, 100),
                        };
                    }
                }
                return null;
            }""")
            if confirm_btn_state:
                log(f"  「確認へ進む」: disabled={confirm_btn_state['disabled']} | class='{confirm_btn_state['className']}'")
            else:
                log("  「確認へ進む」ボタンが見つかりません")

            # ==================================================
            # 7. 新規アップロードに戻る
            # ==================================================
            log("\n========== 7. 新規アップロードに戻る ==========")
            upload_tab = page.locator('button').filter(has_text="新規アップロード")
            if upload_tab.count() > 0:
                upload_tab.first.click()
                page.wait_for_timeout(1000)

                tab_final = page.evaluate("""() => {
                    const d = document.querySelector('[role="dialog"]');
                    if (!d) return {};
                    const result = { tabs: [] };
                    const nav = d.querySelector('nav');
                    if (nav) {
                        nav.querySelectorAll('button').forEach(b => {
                            result.tabs.push({
                                text: b.textContent.trim(),
                                className: b.className.substring(0, 100),
                            });
                        });
                    }
                    // ドロップゾーンの存在
                    result.hasDropZone = !!d.querySelector('[class*="dropZone"], [class*="drop"]');
                    return result;
                }""")
                log(f"  タブ状態: {[t['text'] for t in tab_final.get('tabs', [])]}")
                log(f"  ドロップゾーン復帰: {tab_final.get('hasDropZone')}")

                page.screenshot(path=os.path.join(RESULT_DIR, f"existing_tab_back_to_upload_{timestamp}.png"))

        else:
            log("  ERROR: 「既存から選択」タブが見つかりません")

        # クリーンアップ
        try:
            close_btn = page.get_by_role("button", name="閉じる")
            if close_btn.count() > 0:
                close_btn.first.click(force=True)
        except:
            pass

        browser.close()

    log(f"\n分析完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"ログ: {LOG_FILE}")
    log_fh.close()


if __name__ == "__main__":
    main()
