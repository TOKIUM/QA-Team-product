"""
マルチテナント検証用1テナントのサブドメイン設定を確認・操作するスクリプト
ikeda_n+th3でサブドメインなしログイン → システム設定 → セキュリティ → サブドメイン
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

        # Step 1: サブドメインなしで直接ログイン
        print("[1] dev.keihi.com/users/sign_in にアクセス...")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
        time.sleep(2)

        account = os.environ.get("TOKIUM_ID_EMAIL", "")
        password = os.environ.get("TOKIUM_ID_PASSWORD", "")
        print(f"  アカウント: {account}")

        page.fill('input[type="email"]', account)
        page.fill('input[type="password"]', password)
        login_btn = page.query_selector('#sign_in_form button[type="button"]')
        if not login_btn:
            login_btn = page.query_selector('button[type="submit"]')
        if login_btn:
            login_btn.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")
        print(f"  ログイン後URL: {page.url}")

        # Step 2: セキュリティ設定にアクセス
        print("\n[2] セキュリティ > サブドメイン設定にアクセス...")
        # 現在のベースURLを取得
        current_url = page.url
        # dev.keihi.comのままの可能性があるのでそのまま使う
        base = current_url.split("/users")[0] if "/users" in current_url else current_url.rsplit("/", 1)[0]
        # preferences/security/subdomainに直接アクセス
        security_url = f"{base}/preferences/security/subdomain"
        print(f"  アクセス先: {security_url}")
        page.goto(security_url, timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        print(f"  URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "multi_01_security_subdomain.png"), full_page=True)

        # ページ内容を取得
        page_info = page.evaluate("""() => {
            return {
                url: location.href,
                text: document.body.innerText.substring(0, 3000),
                inputs: Array.from(document.querySelectorAll('input:not([type="hidden"])')).map(i => ({
                    type: i.type, name: i.name, value: i.value,
                    placeholder: i.placeholder, disabled: i.disabled,
                    checked: i.checked, id: i.id
                })),
                buttons: Array.from(document.querySelectorAll('button, [role="button"]')).map(b => ({
                    text: b.textContent?.trim().substring(0, 80) || '',
                    disabled: b.disabled,
                    class: b.className?.substring(0, 100) || ''
                })),
                links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.textContent?.trim().substring(0, 80) || '',
                    href: a.getAttribute('href') || ''
                }))
            };
        }""")

        print(f"\n=== サブドメイン設定画面 ===")
        print(page_info['text'])
        print(f"\n--- 入力フィールド ---")
        for inp in page_info['inputs']:
            print(f"  {inp}")
        print(f"\n--- ボタン ---")
        for btn in page_info['buttons']:
            print(f"  {btn}")

        # 結果保存
        with open(OUTPUT_DIR / "multi_subdomain_setting.json", "w", encoding="utf-8") as f:
            json.dump(page_info, f, ensure_ascii=False, indent=2)

        print(f"\n結果保存完了")
        print("\n[INFO] 60秒待機...")
        time.sleep(60)
        browser.close()


if __name__ == "__main__":
    main()
