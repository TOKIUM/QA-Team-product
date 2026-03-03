"""
「その他の操作」モーダルの画面構成分析
1. ログイン
2. 請求書一覧画面で1件チェック
3. 「その他の操作」ボタンクリック
4. モーダルのHTML構造を詳細取得
"""
import re
import os
import time
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
    output_path = os.path.join(test_dir, "analyze_modal_result.txt")
    out = open(output_path, "w", encoding="utf-8")

    def log(msg):
        out.write(msg + "\n")
        out.flush()
        print(msg)

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
        
        if len(checkboxes) > 0:
            checkboxes[0].click()
            page.wait_for_timeout(1000)
            log("1件目チェック完了")
            
            page.screenshot(path=os.path.join(test_dir, "modal_step1_checked.png"))
            
            buttons = page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                return Array.from(btns).map(b => ({
                    text: (b.innerText || '').trim(),
                    disabled: b.disabled,
                    visible: b.offsetParent !== null
                })).filter(b => b.visible && b.text);
            }""")
            log(f"\n表示中のボタン一覧:")
            for b in buttons:
                log(f"  [{b['text']}] disabled={b['disabled']}")

        log("\n=== 「その他の操作」ボタンクリック ===")
        
        other_btn = page.get_by_role("button", name="その他の操作")
        if other_btn.is_visible():
            other_btn.click()
            log("「その他の操作」クリック完了")
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(test_dir, "modal_step2_modal_open.png"))
        else:
            other_btn2 = page.locator('button:has-text("その他の操作")')
            if other_btn2.count() > 0:
                other_btn2.first.click()
                log("「その他の操作」クリック完了（locator）")
                page.wait_for_timeout(2000)
                page.screenshot(path=os.path.join(test_dir, "modal_step2_modal_open.png"))
            else:
                log("ERROR: 「その他の操作」ボタンが見つかりません")

        log("\n=== モーダル/メニュー分析 ===")

        dialogs = page.evaluate("""() => {
            const results = [];
            const dlgs = document.querySelectorAll('[role="dialog"]');
            dlgs.forEach(d => {
                results.push({
                    type: 'dialog',
                    tag: d.tagName,
                    classes: d.className,
                    innerHTML: d.innerHTML.substring(0, 5000),
                    innerText: (d.innerText || '').substring(0, 2000)
                });
            });
            const menus = document.querySelectorAll('[role="menu"]');
            menus.forEach(m => {
                results.push({
                    type: 'menu',
                    tag: m.tagName,
                    classes: m.className,
                    innerHTML: m.innerHTML.substring(0, 5000),
                    innerText: (m.innerText || '').substring(0, 2000)
                });
            });
            const lbs = document.querySelectorAll('[role="listbox"]');
            lbs.forEach(lb => {
                results.push({
                    type: 'listbox',
                    tag: lb.tagName,
                    classes: lb.className,
                    innerHTML: lb.innerHTML.substring(0, 5000),
                    innerText: (lb.innerText || '').substring(0, 2000)
                });
            });
            const popups = document.querySelectorAll('.MuiPopover-root, .MuiPopper-root, .MuiMenu-root, .MuiDialog-root, [role="presentation"]');
            popups.forEach(pp => {
                results.push({
                    type: 'popup_' + pp.className.split(' ')[0],
                    tag: pp.tagName,
                    classes: pp.className,
                    innerHTML: pp.innerHTML.substring(0, 5000),
                    innerText: (pp.innerText || '').substring(0, 2000)
                });
            });
            return results;
        }""")
        
        log(f"検出された要素数: {len(dialogs)}")
        for i, d in enumerate(dialogs):
            log(f"\n--- 要素 {i+1}: type={d['type']} ---")
            log(f"tag: {d['tag']}")
            log(f"classes: {d['classes'][:200]}")
            log(f"innerText:\n{d['innerText']}")
            log(f"innerHTML (先頭2000文字):\n{d['innerHTML'][:2000]}")

        log("\n=== メニュー項目の詳細 ===")
        menu_items = page.evaluate("""() => {
            const items = [];
            const mis = document.querySelectorAll('[role="menuitem"]');
            mis.forEach(mi => {
                items.push({
                    type: 'menuitem',
                    tag: mi.tagName,
                    text: (mi.innerText || '').trim(),
                    classes: mi.className,
                    disabled: mi.getAttribute('aria-disabled') === 'true' || mi.disabled,
                    dataTestid: mi.getAttribute('data-testid') || '',
                    href: mi.getAttribute('href') || ''
                });
            });
            const lis = document.querySelectorAll('[role="menu"] li, .MuiMenu-list li, .MuiList-root li');
            lis.forEach(li => {
                if (!li.getAttribute('role') || li.getAttribute('role') !== 'menuitem') {
                    items.push({
                        type: 'li',
                        tag: li.tagName,
                        text: (li.innerText || '').trim(),
                        classes: li.className,
                        disabled: li.getAttribute('aria-disabled') === 'true',
                        dataTestid: li.getAttribute('data-testid') || '',
                        href: ''
                    });
                }
            });
            return items;
        }""")
        
        log(f"メニュー項目数: {len(menu_items)}")
        for item in menu_items:
            log(f"  [{item['type']}] text=\"{item['text']}\" disabled={item['disabled']} tag={item['tag']} class={item['classes'][:100]} testid={item['dataTestid']}")

        log("\n=== クリック可能な要素 ===")
        clickables = page.evaluate("""() => {
            const items = [];
            const containers = document.querySelectorAll('.MuiPopover-root, .MuiPopper-root, .MuiMenu-root, .MuiDialog-root, [role="presentation"], [role="menu"], [role="dialog"]');
            containers.forEach(c => {
                const els = c.querySelectorAll('button, a, [role="menuitem"], [role="option"], li[tabindex], div[tabindex]');
                els.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        items.push({
                            tag: el.tagName,
                            role: el.getAttribute('role') || '',
                            text: (el.innerText || '').trim().substring(0, 100),
                            classes: (el.className || '').substring(0, 200),
                            disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                            tabindex: el.getAttribute('tabindex'),
                            href: el.getAttribute('href') || '',
                            dataTestid: el.getAttribute('data-testid') || '',
                            ariaLabel: el.getAttribute('aria-label') || '',
                            rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height }
                        });
                    }
                });
            });
            return items;
        }""")
        
        log(f"クリック可能要素数: {len(clickables)}")
        for item in clickables:
            log(f"  <{item['tag']}> role=\"{item['role']}\" text=\"{item['text']}\" disabled={item['disabled']} href=\"{item['href']}\" testid=\"{item['dataTestid']}\" aria-label=\"{item['ariaLabel']}\"")

        page.screenshot(path=os.path.join(test_dir, "modal_step3_analysis.png"))

        log("\n=== 各メニュー項目の確認 ===")
        visible_items = [c for c in clickables if c['text'] and not c['disabled'] and c['role'] == 'menuitem']
        log(f"有効なメニュー項目: {len(visible_items)}")
        for item in visible_items:
            log(f"  \"{item['text']}\"")

        browser.close()
    
    out.close()
    print(f"\n結果: {output_path}")

if __name__ == "__main__":
    main()
