"""
TOKIUM ユーザー画面サイドバー調査
th-01にログイン後、/transactionsに遷移してユーザー画面のサイドバーメニューを取得する。
認証情報は環境変数から読み込み（.envファイル参照）。
"""

import json
import os
import sys
import io
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ENV_PATH = Path(__file__).parent / "ログイン" / ".env"
load_dotenv(ENV_PATH)

SUBDOMAIN = "th-01"
SUBDOMAIN_INPUT_URL = "https://dev.keihi.com/subdomains/input"
BASE = f"https://{SUBDOMAIN}.dev.keihi.com"

OUTPUT_DIR = Path(__file__).parent / "screen_investigation"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def login(page):
    """サブドメインログイン"""
    print("[1] ログイン開始...")
    page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
    time.sleep(2)

    btn = page.locator('button:has-text("サブドメインを入力")')
    if btn.count() > 0:
        btn.click()
        page.wait_for_url("**/subdomains/input**", timeout=10000)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

    page.locator('input[placeholder="サブドメイン"]').click()
    time.sleep(0.5)
    page.keyboard.press("Control+a")
    page.keyboard.type(SUBDOMAIN, delay=50)
    time.sleep(1)
    page.locator('button:has-text("送信")').click()
    time.sleep(3)

    try:
        page.wait_for_url(f"**{SUBDOMAIN}**", timeout=15000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    email_sel = 'input[type="email"]'
    pw_sel = 'input[type="password"]'
    if page.query_selector(email_sel) and page.query_selector(pw_sel):
        page.fill(email_sel, os.environ["TOKIUM_ID_EMAIL"])
        page.fill(pw_sel, os.environ["TOKIUM_ID_PASSWORD"])
        login_btn = page.query_selector('#sign_in_form button[type="button"]') or page.query_selector('button[type="submit"]')
        if login_btn:
            login_btn.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")

    print(f"  ログイン後: {page.url}")


def extract_page_detail(page):
    """ページの詳細構造を取得"""
    return page.evaluate("""() => {
        const result = {
            title: document.title,
            url: location.href,
            headings: [], buttons: [], inputs: [], tables: [],
            tabs: [], selects: [], iframes: [], sidebar_links: []
        };

        document.querySelectorAll('h1,h2,h3,h4').forEach(h => {
            result.headings.push({tag: h.tagName, text: h.textContent.trim().substring(0, 100)});
        });

        document.querySelectorAll('button, [role="button"]').forEach(b => {
            const text = b.textContent?.trim() || b.getAttribute('aria-label') || '';
            if (text && text.length < 100) result.buttons.push(text);
        });

        document.querySelectorAll('input:not([type="hidden"]), textarea').forEach(inp => {
            result.inputs.push({type: inp.type || 'text', name: inp.name || '', placeholder: inp.placeholder || ''});
        });

        document.querySelectorAll('table').forEach(t => {
            const headers = [];
            t.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim().substring(0, 50)));
            result.tables.push({headers: headers, rowCount: t.querySelectorAll('tbody tr').length});
        });

        document.querySelectorAll('[role="tab"]').forEach(tab => {
            result.tabs.push(tab.textContent.trim().substring(0, 50));
        });

        document.querySelectorAll('select').forEach(sel => {
            const opts = [];
            sel.querySelectorAll('option').forEach(o => opts.push(o.textContent.trim().substring(0, 30)));
            result.selects.push({name: sel.name || '', options: opts});
        });

        document.querySelectorAll('iframe').forEach(f => {
            result.iframes.push({name: f.name || '', src: f.src || '', id: f.id || ''});
        });

        // サイドバーのリンク
        const sidebar = document.querySelector('nav, [class*="sidebar"], aside, [class*="side-menu"]');
        if (sidebar) {
            sidebar.querySelectorAll('a[href]').forEach(a => {
                result.sidebar_links.push({
                    text: a.textContent.trim().substring(0, 80),
                    href: a.getAttribute('href'),
                    active: a.className.includes('active') || a.className.includes('current')
                });
            });
        }

        return result;
    }""")


def main():
    results = {"tenant": SUBDOMAIN, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "pages": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        login(page)

        # ユーザー業務画面を巡回
        user_urls = [
            ("/transactions", "経費一覧"),
            ("/requests", "申請一覧"),
            ("/analyses", "集計"),
            ("/notifications", "通知"),
        ]

        for url_path, name in user_urls:
            full_url = BASE + url_path
            print(f"\n[調査] {name} ({url_path})...")
            try:
                page.goto(full_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(2)

                safe_name = name.replace("/", "_")
                page.screenshot(path=str(SCREENSHOTS_DIR / f"user_{safe_name}.png"), full_page=True)

                detail = extract_page_detail(page)
                detail["menu_name"] = name
                detail["target_path"] = url_path
                detail["screenshot"] = f"user_{safe_name}.png"

                if detail.get("sidebar_links"):
                    print(f"  サイドバー: {len(detail['sidebar_links'])}リンク")
                    for sl in detail["sidebar_links"]:
                        active_mark = " *" if sl.get("active") else ""
                        print(f"    {sl['text']}: {sl['href']}{active_mark}")

                print(f"  ボタン: {len(detail['buttons'])}, 入力: {len(detail['inputs'])}, テーブル: {len(detail['tables'])}")
                results["pages"].append(detail)

            except Exception as e:
                print(f"  エラー: {e}")

        # 「新規」ボタンのドロップダウン調査
        print("\n[調査] 新規ボタンのドロップダウン...")
        page.goto(f"{BASE}/transactions", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        new_btn = page.locator('button:has-text("新規"), a:has-text("新規")').first
        if new_btn.is_visible():
            new_btn.click()
            time.sleep(1)
            page.screenshot(path=str(SCREENSHOTS_DIR / "user_new_dropdown.png"), full_page=True)

            dropdown_items = page.evaluate("""() => {
                const items = [];
                document.querySelectorAll('[role="menu"] a, [role="menuitem"], .dropdown-menu a, [class*="dropdown"] a').forEach(el => {
                    const text = el.textContent.trim();
                    const href = el.getAttribute('href') || '';
                    if (text && text.length < 100) items.push({text, href});
                });
                return items;
            }""")
            results["new_button_dropdown"] = dropdown_items
            for item in dropdown_items:
                print(f"  - {item['text']}: {item['href']}")

        # 結果保存
        output_file = OUTPUT_DIR / "user_screen_structure.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了! {output_file}")
        browser.close()


if __name__ == "__main__":
    main()
