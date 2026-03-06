"""
サブドメイン入力なしでTOKIUM IDログインを試みるスクリプト
th-02はサブドメインが無効＝サブドメイン入力不要でログインできるはず。
dev.keihi.comのログイン画面でサブドメインを入力せず直接ログインを試す。
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

        # Step 1: TOKIUM IDログイン画面にアクセス
        print("[1] dev.keihi.com/users/sign_in にアクセス...")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
        time.sleep(2)
        print(f"  URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "th02_nosub_01_login.png"), full_page=True)

        # ページの全体構造を確認
        page_info = page.evaluate("""() => {
            return {
                url: location.href,
                text: document.body ? document.body.innerText.substring(0, 2000) : '',
                inputs: Array.from(document.querySelectorAll('input')).map(i => ({
                    type: i.type, name: i.name, placeholder: i.placeholder,
                    id: i.id, value: i.value
                })),
                buttons: Array.from(document.querySelectorAll('button, a[role="button"], input[type="submit"]')).map(b => ({
                    text: b.textContent?.trim().substring(0, 80) || b.value || '',
                    href: b.getAttribute('href') || '',
                    type: b.type || ''
                })),
                links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.textContent?.trim().substring(0, 80) || '',
                    href: a.getAttribute('href') || ''
                }))
            };
        }""")

        print(f"\n=== ログイン画面の構造 ===")
        print(f"テキスト:\n{page_info['text'][:500]}")
        print(f"\n入力フィールド:")
        for inp in page_info['inputs']:
            print(f"  {inp}")
        print(f"\nボタン:")
        for btn in page_info['buttons']:
            print(f"  {btn}")
        print(f"\nリンク:")
        for link in page_info['links']:
            print(f"  {link}")

        # メール/パスワード入力欄がこの画面にあるか確認
        email_input = page.query_selector('input[type="email"]')
        pw_input = page.query_selector('input[type="password"]')

        if email_input and pw_input:
            # サブドメインなしで直接ログイン
            account = os.environ.get("TOKIUM_ID_EMAIL", "")  # ikeda_n+th3@tokium.jp
            password = os.environ.get("TOKIUM_ID_PASSWORD", "")
            print(f"\n[2] サブドメインなしで直接ログイン: {account}")
            page.fill('input[type="email"]', account)
            page.fill('input[type="password"]', password)
            page.screenshot(path=str(SCREENSHOTS_DIR / "th02_nosub_02_filled.png"), full_page=True)

            login_btn = page.query_selector('#sign_in_form button[type="button"]')
            if not login_btn:
                login_btn = page.query_selector('button[type="submit"]')
            if login_btn:
                login_btn.click()
            time.sleep(5)
            page.wait_for_load_state("networkidle")
            print(f"  ログイン後URL: {page.url}")
            page.screenshot(path=str(SCREENSHOTS_DIR / "th02_nosub_03_after.png"), full_page=True)

            # 結果確認
            after_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 500) : ''")
            print(f"  ページテキスト: {after_text[:300]}")
        else:
            print("\n[2] この画面にはメール/パスワード入力欄がありません")
            print("  「サブドメインを入力」ボタンをクリックせずに他のログイン方法を探します")

            # 「TOKIUM IDでログイン」等のボタンがないか確認
            all_clickable = page.evaluate("""() => {
                const elements = [];
                document.querySelectorAll('button, a, [role="button"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        elements.push({
                            tag: el.tagName,
                            text: el.textContent?.trim().substring(0, 100) || '',
                            href: el.getAttribute('href') || '',
                            class: el.className?.substring(0, 100) || ''
                        });
                    }
                });
                return elements;
            }""")
            print(f"\n  表示中のクリック可能要素:")
            for el in all_clickable:
                print(f"    {el}")

        # 結果保存
        with open(OUTPUT_DIR / "th02_login_investigation.json", "w", encoding="utf-8") as f:
            json.dump(page_info, f, ensure_ascii=False, indent=2)

        print("\n[INFO] 30秒待機...")
        time.sleep(30)
        browser.close()


if __name__ == "__main__":
    main()
