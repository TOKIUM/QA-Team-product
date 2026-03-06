"""
テナント一覧を取得するスクリプト
th-01ログイン後、「別のテナントに切替」をクリックしてテナント一覧を確認する。
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


def login_th01(page):
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
    if page.query_selector('input[type="email"]') and page.query_selector('input[type="password"]'):
        page.fill('input[type="email"]', acct)
        page.fill('input[type="password"]', pw)
        login_btn = page.query_selector('#sign_in_form button[type="button"]')
        if not login_btn:
            login_btn = page.query_selector('button[type="submit"]')
        if login_btn:
            login_btn.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        print("[1] th-01にログイン...")
        login_th01(page)
        print(f"  URL: {page.url}")

        # ユーザードロップダウンを開く
        print("\n[2] ユーザードロップダウンを開く...")
        page.locator('button:has-text("ikeda")').first.click()
        time.sleep(1)

        # 「別のテナントに切替」をクリック
        print("[3] 「別のテナントに切替」をクリック...")
        page.locator('a:has-text("別のテナントに切替")').first.click()
        time.sleep(3)
        page.wait_for_load_state("networkidle")
        print(f"  遷移後URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "tenant_list_01.png"), full_page=True)

        # ページ内容を取得
        page_text = page.evaluate("() => document.body.innerText.substring(0, 5000)")
        print(f"\n=== テナント切替画面 ===")
        print(page_text[:2000])

        # テナント一覧を構造的に取得
        tenant_data = page.evaluate("""() => {
            const result = {
                url: location.href,
                tenants: [],
                all_links: [],
                all_buttons: []
            };
            // リスト・カード形式のテナント一覧を探す
            document.querySelectorAll('a[href], button, [role="button"]').forEach(el => {
                const text = el.textContent?.trim() || '';
                const href = el.getAttribute('href') || '';
                if (text && text.length < 200) {
                    result.all_links.push({text: text.substring(0, 100), href, tag: el.tagName});
                }
            });
            // テナント名っぽい要素
            document.querySelectorAll('[class*="tenant"], [class*="Tenant"], [class*="company"], [class*="Company"], li, tr, [class*="card"], [class*="Card"]').forEach(el => {
                const text = el.textContent?.trim();
                if (text && text.length > 3 && text.length < 200) {
                    const link = el.querySelector('a');
                    result.tenants.push({
                        text: text.substring(0, 150),
                        href: link ? link.getAttribute('href') : ''
                    });
                }
            });
            return result;
        }""")

        print(f"\n--- テナント候補 ---")
        seen = set()
        for t in tenant_data['tenants']:
            key = t['text'][:50]
            if key not in seen:
                seen.add(key)
                print(f"  {t['text'][:100]} -> {t['href']}")

        with open(OUTPUT_DIR / "tenant_list.json", "w", encoding="utf-8") as f:
            json.dump(tenant_data, f, ensure_ascii=False, indent=2)

        print("\n[INFO] 30秒待機...")
        time.sleep(30)
        browser.close()


if __name__ == "__main__":
    main()
