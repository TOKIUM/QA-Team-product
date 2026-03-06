"""
テナント切り替えメニューから全テナント一覧を取得するスクリプト
th-01にログイン後、テナント切り替えメニューの内容を確認する。
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

OUTPUT_DIR = Path(__file__).parent / "screen_investigation"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        # th-01にTOKIUM IDでログイン
        print("[1] th-01にログイン...")
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
        page.keyboard.type("th-01", delay=50)
        time.sleep(1)
        page.locator('button:has-text("送信")').click()
        time.sleep(3)

        try:
            page.wait_for_url("**th-01**", timeout=15000)
        except Exception:
            pass
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        acct = os.environ.get("TOKIUM_ID_EMAIL", "")
        pw = os.environ.get("TOKIUM_ID_PASSWORD", "")

        email_el = page.query_selector('input[type="email"]')
        pw_el = page.query_selector('input[type="password"]')
        if email_el and pw_el:
            page.fill('input[type="email"]', acct)
            page.fill('input[type="password"]', pw)
            login_btn = page.query_selector('#sign_in_form button[type="button"]')
            if not login_btn:
                login_btn = page.query_selector('button[type="submit"]')
            if login_btn:
                login_btn.click()
            time.sleep(5)
            page.wait_for_load_state("networkidle")

        print(f"  ログイン後: {page.url}")

        # ヘッダー右上のテナント情報・切り替えメニューを取得
        print("\n[2] ヘッダー右上の情報を取得...")
        header_info = page.evaluate("""() => {
            const result = { header_text: '', all_buttons: [], all_links: [] };
            const header = document.querySelector('header, [class*="header"], [class*="Header"]');
            if (header) {
                result.header_text = header.innerText.trim().substring(0, 500);
                header.querySelectorAll('button, [role="button"]').forEach(b => {
                    result.all_buttons.push(b.textContent?.trim().substring(0, 100) || '');
                });
                header.querySelectorAll('a[href]').forEach(a => {
                    result.all_links.push({
                        text: a.textContent?.trim().substring(0, 80) || '',
                        href: a.getAttribute('href') || ''
                    });
                });
            }
            return result;
        }""")
        print(f"  ヘッダーテキスト: {header_info['header_text']}")

        # テナント切り替えボタンをクリック
        print("\n[3] テナント切り替えメニューを開く...")
        # 「テナント切り替え」リンクまたはユーザー名のドロップダウンをクリック
        tenant_switch = page.locator('text=テナント切り替え')
        if tenant_switch.count() > 0:
            tenant_switch.first.click()
            time.sleep(2)
            page.screenshot(path=str(SCREENSHOTS_DIR / "tenant_switch_01.png"), full_page=True)

            # ドロップダウンやモーダルの内容を取得
            dropdown_info = page.evaluate("""() => {
                const result = { visible_text: '', dropdown_items: [], all_links: [] };
                // ドロップダウンやモーダル内のリンク
                document.querySelectorAll('[class*="dropdown"], [class*="Dropdown"], [role="menu"], [class*="modal"], [class*="Modal"], [class*="popover"], [class*="Popover"]').forEach(el => {
                    if (el.offsetHeight > 0) {
                        result.visible_text += el.innerText.trim().substring(0, 500) + '\\n';
                        el.querySelectorAll('a[href], button, [role="menuitem"]').forEach(item => {
                            result.dropdown_items.push({
                                text: item.textContent?.trim().substring(0, 100) || '',
                                href: item.getAttribute('href') || '',
                                tag: item.tagName
                            });
                        });
                    }
                });
                // ページ全体で新しく表示された要素
                document.querySelectorAll('a[href]').forEach(a => {
                    const text = a.textContent?.trim() || '';
                    const href = a.getAttribute('href') || '';
                    if (text.includes('テナント') || href.includes('tenant') || href.includes('switch')) {
                        result.all_links.push({text: text.substring(0, 100), href});
                    }
                });
                return result;
            }""")
            print(f"  ドロップダウンテキスト: {dropdown_info['visible_text']}")
            print(f"  ドロップダウンアイテム:")
            for item in dropdown_info['dropdown_items']:
                print(f"    {item}")

        # ユーザー名部分のドロップダウンも試す
        print("\n[4] ユーザー名ドロップダウンを確認...")
        user_btn = page.locator('[class*="hUCUMA"], button:has-text("ikeda")')
        if user_btn.count() > 0:
            user_btn.first.click()
            time.sleep(2)
            page.screenshot(path=str(SCREENSHOTS_DIR / "tenant_switch_02_user.png"), full_page=True)

            user_dropdown = page.evaluate("""() => {
                const items = [];
                document.querySelectorAll('[class*="dropdown"], [class*="Dropdown"], [role="menu"], [class*="popover"], [class*="Popover"]').forEach(el => {
                    if (el.offsetHeight > 0) {
                        el.querySelectorAll('a, button, [role="menuitem"], li').forEach(item => {
                            const text = item.textContent?.trim();
                            if (text && text.length < 200) {
                                items.push({
                                    text: text.substring(0, 100),
                                    href: item.getAttribute('href') || '',
                                    tag: item.tagName
                                });
                            }
                        });
                    }
                });
                return items;
            }""")
            print(f"  ユーザードロップダウン:")
            for item in user_dropdown:
                print(f"    {item}")

        # テナント名検索欄があれば確認
        print("\n[5] テナント検索欄の確認...")
        search_input = page.locator('input[placeholder="テナント名で検索"]')
        if search_input.count() > 0 and search_input.is_visible():
            print("  テナント検索欄あり。全テナント一覧を取得...")
            page.screenshot(path=str(SCREENSHOTS_DIR / "tenant_switch_03_search.png"), full_page=True)

            # 検索せずに表示されているテナント一覧を取得
            tenant_list = page.evaluate("""() => {
                const tenants = [];
                // テナント一覧のリスト要素を探す
                document.querySelectorAll('li, [class*="tenant"], [class*="Tenant"], [role="option"]').forEach(el => {
                    const text = el.textContent?.trim();
                    if (text && text.length < 200 && text.length > 2) {
                        const href = el.querySelector('a')?.getAttribute('href') || '';
                        tenants.push({text: text.substring(0, 100), href});
                    }
                });
                return tenants;
            }""")
            print(f"  テナント一覧:")
            for t in tenant_list:
                print(f"    {t}")

        # 全ページテキストからテナント関連情報を抽出
        full_text = page.evaluate("() => document.body.innerText.substring(0, 5000)")
        print(f"\n[6] ページ全体テキスト（テナント関連）:")
        for line in full_text.split("\n"):
            line = line.strip()
            if any(k in line for k in ["テナント", "th-", "TH-", "マルチ", "検証", "ikeda"]):
                print(f"  {line}")

        # 結果保存
        result = {
            "header": header_info,
            "full_text_excerpt": full_text[:3000]
        }
        with open(OUTPUT_DIR / "tenant_info.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print("\n[INFO] 30秒待機...")
        time.sleep(30)
        browser.close()


if __name__ == "__main__":
    main()
