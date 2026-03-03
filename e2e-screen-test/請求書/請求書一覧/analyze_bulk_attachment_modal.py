"""
「共通添付ファイルの一括添付」モーダルの画面構成分析
1. ログイン
2. 請求書一覧画面で1件チェック
3. 「その他の操作」→「共通添付ファイルの一括添付」クリック
4. 開いたモーダルのHTML構造を詳細取得
"""
import os
import json
from playwright.sync_api import sync_playwright

BASE_URL = "https://invoicing-staging.keihi.com"

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ログイン", ".env")
    env_path = os.path.normpath(env_path)
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
    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")
    test_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(test_dir, "analyze_bulk_attachment_result.txt")
    out = open(output_path, "w", encoding="utf-8")

    def log(msg):
        out.write(msg + "\n")
        out.flush()
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode("ascii", "replace").decode())

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        context.set_default_timeout(30000)
        page = context.new_page()

        # ===== ログイン =====
        log("=== ログイン ===")
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

        # ===== 一覧画面で1件チェック =====
        log("\n=== チェックボックス選択 ===")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        checkboxes = page.query_selector_all('table tbody tr td input[type="checkbox"]')
        log(f"チェックボックス数: {len(checkboxes)}")

        if len(checkboxes) == 0:
            log("ERROR: チェックボックスが見つかりません")
            browser.close()
            out.close()
            return

        checkboxes[0].click()
        page.wait_for_timeout(1000)
        log("1件目チェック完了")

        # ===== 「その他の操作」→「共通添付ファイルの一括添付」 =====
        log("\n=== 「その他の操作」クリック ===")
        other_btn = page.get_by_role("button", name="その他の操作")
        other_btn.click()
        page.wait_for_timeout(1500)
        log("「その他の操作」メニュー開き完了")

        page.screenshot(path=os.path.join(test_dir, "bulk_attach_step1_menu.png"))

        log("\n=== 「共通添付ファイルの一括添付」クリック ===")
        # menuitem内のbuttonをクリック
        attach_item = page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付")
        if attach_item.count() > 0:
            attach_item.first.click()
            log("「共通添付ファイルの一括添付」クリック完了")
        else:
            # フォールバック: ボタンテキストで検索
            attach_btn = page.locator('button:has-text("共通添付ファイルの一括添付")')
            if attach_btn.count() > 0:
                attach_btn.first.click()
                log("「共通添付ファイルの一括添付」クリック完了（button）")
            else:
                log("ERROR: 「共通添付ファイルの一括添付」が見つかりません")
                browser.close()
                out.close()
                return

        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(test_dir, "bulk_attach_step2_modal.png"))

        # ===== モーダル分析 =====
        log("\n=== モーダル/ダイアログ検出 ===")

        # 1. role="dialog" / role="alertdialog" / その他ポップアップ
        detected = page.evaluate("""() => {
            const results = [];
            // dialog系
            document.querySelectorAll('[role="dialog"], [role="alertdialog"]').forEach(d => {
                results.push({
                    type: d.getAttribute('role'),
                    tag: d.tagName,
                    id: d.id || '',
                    classes: d.className,
                    ariaLabel: d.getAttribute('aria-label') || '',
                    ariaLabelledby: d.getAttribute('aria-labelledby') || '',
                    innerText: (d.innerText || '').substring(0, 3000),
                    innerHTML: d.innerHTML.substring(0, 8000),
                    rect: (() => { const r = d.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; })()
                });
            });
            // MUI系
            document.querySelectorAll('.MuiDialog-root, .MuiModal-root, .MuiPopover-root, [role="presentation"]').forEach(d => {
                if (!d.getAttribute('role') || (d.getAttribute('role') !== 'dialog' && d.getAttribute('role') !== 'alertdialog')) {
                    results.push({
                        type: 'mui_' + (d.className || '').split(' ')[0],
                        tag: d.tagName,
                        id: d.id || '',
                        classes: (d.className || '').substring(0, 300),
                        ariaLabel: d.getAttribute('aria-label') || '',
                        ariaLabelledby: '',
                        innerText: (d.innerText || '').substring(0, 3000),
                        innerHTML: d.innerHTML.substring(0, 8000),
                        rect: (() => { const r = d.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; })()
                    });
                }
            });
            // headlessui panels
            document.querySelectorAll('[id*="headlessui-dialog"], [data-headlessui-state]').forEach(d => {
                const role = d.getAttribute('role');
                if (role !== 'dialog' && role !== 'menu' && role !== 'menuitem') {
                    results.push({
                        type: 'headlessui_' + (role || d.tagName),
                        tag: d.tagName,
                        id: d.id || '',
                        classes: (d.className || '').substring(0, 300),
                        ariaLabel: d.getAttribute('aria-label') || '',
                        ariaLabelledby: '',
                        innerText: (d.innerText || '').substring(0, 3000),
                        innerHTML: d.innerHTML.substring(0, 8000),
                        rect: (() => { const r = d.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; })()
                    });
                }
            });
            return results;
        }""")

        log(f"検出された要素数: {len(detected)}")
        for i, d in enumerate(detected):
            log(f"\n--- 要素 {i+1}: type={d['type']} ---")
            log(f"tag: {d['tag']}")
            log(f"id: {d['id']}")
            log(f"classes: {d['classes'][:300]}")
            log(f"aria-label: {d['ariaLabel']}")
            log(f"aria-labelledby: {d['ariaLabelledby']}")
            log(f"rect: x={d['rect']['x']}, y={d['rect']['y']}, w={d['rect']['w']}, h={d['rect']['h']}")
            log(f"innerText:\n{d['innerText']}")
            log(f"innerHTML (先頭5000文字):\n{d['innerHTML'][:5000]}")

        # 2. モーダル内のフォーム要素
        log("\n=== モーダル内フォーム要素 ===")
        form_elements = page.evaluate("""() => {
            const results = [];
            const containers = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .MuiDialog-root, .MuiModal-root');
            containers.forEach(c => {
                // input
                c.querySelectorAll('input').forEach(el => {
                    results.push({
                        type: 'input',
                        inputType: el.type,
                        name: el.name || '',
                        placeholder: el.placeholder || '',
                        value: el.value || '',
                        id: el.id || '',
                        classes: (el.className || '').substring(0, 200),
                        ariaLabel: el.getAttribute('aria-label') || '',
                        disabled: el.disabled,
                        required: el.required,
                        accept: el.getAttribute('accept') || ''
                    });
                });
                // select
                c.querySelectorAll('select').forEach(el => {
                    const opts = Array.from(el.options).map(o => ({value: o.value, text: o.text, selected: o.selected}));
                    results.push({
                        type: 'select',
                        inputType: '',
                        name: el.name || '',
                        placeholder: '',
                        value: el.value || '',
                        id: el.id || '',
                        classes: (el.className || '').substring(0, 200),
                        ariaLabel: el.getAttribute('aria-label') || '',
                        disabled: el.disabled,
                        required: el.required,
                        accept: '',
                        options: opts
                    });
                });
                // textarea
                c.querySelectorAll('textarea').forEach(el => {
                    results.push({
                        type: 'textarea',
                        inputType: '',
                        name: el.name || '',
                        placeholder: el.placeholder || '',
                        value: el.value || '',
                        id: el.id || '',
                        classes: (el.className || '').substring(0, 200),
                        ariaLabel: el.getAttribute('aria-label') || '',
                        disabled: el.disabled,
                        required: el.required,
                        accept: ''
                    });
                });
            });
            return results;
        }""")

        log(f"フォーム要素数: {len(form_elements)}")
        for i, el in enumerate(form_elements):
            log(f"  [{i+1}] type={el['type']} inputType={el.get('inputType','')} name=\"{el['name']}\" placeholder=\"{el['placeholder']}\" value=\"{el['value']}\" disabled={el['disabled']} required={el['required']} accept=\"{el.get('accept','')}\" aria-label=\"{el['ariaLabel']}\"")
            if 'options' in el:
                for o in el['options']:
                    log(f"      option: value=\"{o['value']}\" text=\"{o['text']}\" selected={o['selected']}")

        # 3. モーダル内のボタン
        log("\n=== モーダル内ボタン ===")
        modal_buttons = page.evaluate("""() => {
            const results = [];
            const containers = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .MuiDialog-root, .MuiModal-root');
            containers.forEach(c => {
                c.querySelectorAll('button, a, [role="button"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        results.push({
                            tag: el.tagName,
                            text: (el.innerText || '').trim().substring(0, 200),
                            type: el.type || '',
                            disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                            classes: (el.className || '').substring(0, 200),
                            href: el.getAttribute('href') || '',
                            ariaLabel: el.getAttribute('aria-label') || '',
                            dataTestid: el.getAttribute('data-testid') || '',
                            rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                        });
                    }
                });
            });
            return results;
        }""")

        log(f"ボタン数: {len(modal_buttons)}")
        for i, btn in enumerate(modal_buttons):
            log(f"  [{i+1}] <{btn['tag']}> text=\"{btn['text']}\" type={btn['type']} disabled={btn['disabled']} href=\"{btn['href']}\" aria-label=\"{btn['ariaLabel']}\" testid=\"{btn['dataTestid']}\" rect=({btn['rect']['x']:.0f},{btn['rect']['y']:.0f},{btn['rect']['w']:.0f},{btn['rect']['h']:.0f})")

        # 4. モーダル内のテキスト要素（見出し、ラベル等）
        log("\n=== モーダル内テキスト要素（見出し・ラベル） ===")
        text_elements = page.evaluate("""() => {
            const results = [];
            const containers = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .MuiDialog-root, .MuiModal-root');
            containers.forEach(c => {
                c.querySelectorAll('h1, h2, h3, h4, h5, h6, label, legend, [class*="title"], [class*="header"], [class*="heading"], p').forEach(el => {
                    const text = (el.innerText || '').trim();
                    if (text) {
                        results.push({
                            tag: el.tagName,
                            text: text.substring(0, 300),
                            classes: (el.className || '').substring(0, 200),
                            forAttr: el.getAttribute('for') || '',
                            id: el.id || ''
                        });
                    }
                });
            });
            return results;
        }""")

        log(f"テキスト要素数: {len(text_elements)}")
        for i, el in enumerate(text_elements):
            log(f"  [{i+1}] <{el['tag']}> text=\"{el['text']}\" class=\"{el['classes']}\" for=\"{el['forAttr']}\" id=\"{el['id']}\"")

        # 5. ドロップゾーン / ファイルアップロード領域
        log("\n=== ファイルアップロード領域 ===")
        upload_areas = page.evaluate("""() => {
            const results = [];
            const containers = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .MuiDialog-root, .MuiModal-root');
            containers.forEach(c => {
                // file input
                c.querySelectorAll('input[type="file"]').forEach(el => {
                    results.push({
                        type: 'file_input',
                        accept: el.getAttribute('accept') || '',
                        multiple: el.multiple,
                        name: el.name || '',
                        id: el.id || '',
                        classes: (el.className || '').substring(0, 200)
                    });
                });
                // dropzone
                c.querySelectorAll('[class*="dropzone"], [class*="drop-zone"], [class*="upload"], [class*="drag"]').forEach(el => {
                    results.push({
                        type: 'dropzone',
                        accept: '',
                        multiple: false,
                        name: '',
                        id: el.id || '',
                        classes: (el.className || '').substring(0, 200),
                        text: (el.innerText || '').trim().substring(0, 300)
                    });
                });
            });
            return results;
        }""")

        log(f"アップロード領域数: {len(upload_areas)}")
        for i, area in enumerate(upload_areas):
            log(f"  [{i+1}] type={area['type']} accept=\"{area.get('accept','')}\" multiple={area.get('multiple','')} name=\"{area.get('name','')}\" id=\"{area.get('id','')}\" class=\"{area['classes']}\"")
            if 'text' in area:
                log(f"      text=\"{area['text']}\"")

        # 6. iframe検出
        log("\n=== iframe検出 ===")
        iframes = page.evaluate("""() => {
            const results = [];
            const containers = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .MuiDialog-root, .MuiModal-root');
            containers.forEach(c => {
                c.querySelectorAll('iframe').forEach(el => {
                    results.push({
                        src: el.src || '',
                        name: el.name || '',
                        id: el.id || '',
                        classes: (el.className || '').substring(0, 200),
                        rect: (() => { const r = el.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; })()
                    });
                });
            });
            // ページ全体のiframeも確認
            document.querySelectorAll('iframe').forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) {
                    results.push({
                        src: el.src || '',
                        name: el.name || '',
                        id: el.id || '',
                        classes: (el.className || '').substring(0, 200),
                        rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                        location: 'page_level'
                    });
                }
            });
            return results;
        }""")

        log(f"iframe数: {len(iframes)}")
        for i, iframe in enumerate(iframes):
            loc = iframe.get('location', 'in_modal')
            log(f"  [{i+1}] ({loc}) src=\"{iframe['src'][:200]}\" name=\"{iframe['name']}\" id=\"{iframe['id']}\" rect=({iframe['rect']['x']:.0f},{iframe['rect']['y']:.0f},{iframe['rect']['w']:.0f},{iframe['rect']['h']:.0f})")

        # 7. 全体のDOM構造概要
        log("\n=== モーダル全体のDOM構造概要 ===")
        dom_tree = page.evaluate("""() => {
            function getTree(el, depth, maxDepth) {
                if (depth > maxDepth) return '';
                const tag = el.tagName.toLowerCase();
                const role = el.getAttribute('role') ? ` role="${el.getAttribute('role')}"` : '';
                const cls = el.className ? ` class="${(typeof el.className === 'string' ? el.className : '').substring(0, 80)}"` : '';
                const id = el.id ? ` id="${el.id}"` : '';
                const text = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 ? ` "${(el.textContent || '').trim().substring(0, 50)}"` : '';
                const indent = '  '.repeat(depth);
                let result = indent + `<${tag}${role}${id}${cls}>${text}\\n`;
                for (const child of el.children) {
                    result += getTree(child, depth + 1, maxDepth);
                }
                return result;
            }
            const containers = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .MuiDialog-root, .MuiModal-root');
            let output = '';
            containers.forEach((c, i) => {
                output += `--- Dialog ${i+1} ---\\n`;
                output += getTree(c, 0, 6);
            });
            return output;
        }""")
        log(dom_tree[:8000])

        page.screenshot(path=os.path.join(test_dir, "bulk_attach_step3_analysis.png"))

        browser.close()

    out.close()
    print(f"\n結果出力: {output_path}")

if __name__ == "__main__":
    main()
