"""
th-01テナントのセキュリティ > サブドメイン設定画面を確認・操作するスクリプト
認証情報は.envから読み込み
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
BASE = f"https://{SUBDOMAIN}.dev.keihi.com"

OUTPUT_DIR = Path(__file__).parent / "screen_investigation"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def login(page):
    """th-01にTOKIUM IDでログイン"""
    print("[1] TOKIUM IDログイン -> th-01...")
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

    email_field = 'input[type="email"]'
    pw_field = 'input[type="password"]'
    if page.query_selector(email_field) and page.query_selector(pw_field):
        page.fill(email_field, os.environ["TOKIUM_ID_EMAIL"])
        page.fill(pw_field, os.environ["TOKIUM_ID_PASSWORD"])
        login_btn = page.query_selector('#sign_in_form button[type="button"]')
        if not login_btn:
            login_btn = page.query_selector('button[type="submit"]')
        if login_btn:
            login_btn.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")

    print(f"  ログイン後: {page.url}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        login(page)

        # セキュリティ設定ページにアクセス
        print("\n[2] セキュリティ設定にアクセス...")
        page.goto(f"{BASE}/preferences/security/ip_restriction", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        print(f"  URL: {page.url}")

        # 「サブドメイン」タブをクリック
        print("\n[3] サブドメイン タブをクリック...")
        subdomain_link = page.locator('a:has-text("サブドメイン"), [class*="tab"]:has-text("サブドメイン"), li:has-text("サブドメイン")')
        if subdomain_link.count() > 0:
            subdomain_link.first.click()
            time.sleep(3)
            page.wait_for_load_state("networkidle")
            print(f"  遷移後URL: {page.url}")
        else:
            page.locator('text=サブドメイン').first.click()
            time.sleep(3)
            page.wait_for_load_state("networkidle")
            print(f"  遷移後URL: {page.url}")

        page.screenshot(path=str(SCREENSHOTS_DIR / "subdomain_setting_page.png"), full_page=True)

        # ページの全内容を取得
        page_info = page.evaluate("""() => {
            const result = {
                url: location.href,
                all_text: document.body.innerText.substring(0, 3000),
                inputs: [],
                buttons: [],
                labels: []
            };

            document.querySelectorAll('input:not([type="hidden"]), textarea, select').forEach(inp => {
                result.inputs.push({
                    type: inp.type || inp.tagName.toLowerCase(),
                    name: inp.name || '',
                    value: inp.value || '',
                    placeholder: inp.placeholder || '',
                    id: inp.id || '',
                    checked: inp.checked || false,
                    disabled: inp.disabled || false
                });
            });

            document.querySelectorAll('button, [role="button"], input[type="submit"]').forEach(b => {
                result.buttons.push({
                    text: b.textContent?.trim().substring(0, 80) || b.value || '',
                    disabled: b.disabled || false
                });
            });

            document.querySelectorAll('label').forEach(l => {
                result.labels.push(l.textContent.trim().substring(0, 100));
            });

            return result;
        }""")

        print("\n=== サブドメイン設定画面 ===")
        print(f"URL: {page_info['url']}")
        print(f"\n--- ページテキスト ---")
        print(page_info['all_text'])
        print(f"\n--- 入力フィールド ---")
        for inp in page_info['inputs']:
            print(f"  {inp}")
        print(f"\n--- ボタン ---")
        for btn in page_info['buttons']:
            print(f"  {btn}")
        print(f"\n--- ラベル ---")
        for label in page_info['labels']:
            print(f"  {label}")

        # 結果保存
        with open(OUTPUT_DIR / "subdomain_setting_detail.json", "w", encoding="utf-8") as f:
            json.dump(page_info, f, ensure_ascii=False, indent=2)

        print(f"\n結果保存完了")
        print("\n[INFO] 30秒待機...")
        time.sleep(30)
        browser.close()


if __name__ == "__main__":
    main()
