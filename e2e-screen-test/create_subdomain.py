"""
マルチテナント検証用1テナントにサブドメインを設定するスクリプト
1. ikeda_n+th3でサブドメインなしログイン
2. セキュリティ > サブドメイン画面へ
3. サブドメイン入力 → 使用可能か確認 → 作成する
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

SUBDOMAIN_TO_SET = "th-02"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        # Step 1: ログイン
        print("[1] ログイン...")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
        time.sleep(2)

        acct = os.environ.get("TOKIUM_ID_EMAIL", "")
        pw = os.environ.get("TOKIUM_ID_PASSWORD", "")

        page.fill('input[type="email"]', acct)
        page.fill('input[type="password"]', pw)
        login_btn = page.query_selector('#sign_in_form button[type="button"]')
        if not login_btn:
            login_btn = page.query_selector('button[type="submit"]')
        if login_btn:
            login_btn.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")
        print(f"  ログイン後URL: {page.url}")

        # Step 2: セキュリティ > サブドメイン設定にアクセス
        print("\n[2] セキュリティ > サブドメインにアクセス...")
        page.goto("https://dev.keihi.com/preferences/security/subdomain", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        print(f"  URL: {page.url}")

        # Step 3: サブドメインを入力
        print(f"\n[3] サブドメイン '{SUBDOMAIN_TO_SET}' を入力...")
        subdomain_input = page.locator('input[type="text"]').last
        subdomain_input.click()
        subdomain_input.fill(SUBDOMAIN_TO_SET)
        time.sleep(1)
        page.screenshot(path=str(SCREENSHOTS_DIR / "create_sub_01_filled.png"), full_page=True)

        # Step 4: 「使用可能か確認する」をクリック
        print("\n[4] 使用可能か確認する...")
        check_btn = page.locator('button:has-text("使用可能か確認する")')
        check_btn.click()
        time.sleep(3)
        page.screenshot(path=str(SCREENSHOTS_DIR / "create_sub_02_checked.png"), full_page=True)

        # 確認結果を取得
        result_text = page.evaluate("() => document.body.innerText.substring(0, 3000)")
        print(f"  確認結果:")
        for line in result_text.split("\n"):
            line = line.strip()
            if any(k in line for k in ["使用", "サブドメイン", "利用", "エラー", "可能", "不可"]):
                print(f"    {line}")

        # Step 5: 「作成する」をクリック
        print(f"\n[5] サブドメイン '{SUBDOMAIN_TO_SET}' を作成する...")
        create_btn = page.locator('button:has-text("作成する")')
        if create_btn.is_enabled():
            create_btn.click()
            time.sleep(5)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(SCREENSHOTS_DIR / "create_sub_03_created.png"), full_page=True)
            print(f"  作成後URL: {page.url}")

            # 作成後の画面内容を取得
            after_info = page.evaluate("""() => {
                return {
                    url: location.href,
                    text: document.body.innerText.substring(0, 3000),
                    inputs: Array.from(document.querySelectorAll('input:not([type="hidden"])')).map(i => ({
                        type: i.type, value: i.value, disabled: i.disabled, checked: i.checked
                    })),
                    buttons: Array.from(document.querySelectorAll('button, [role="button"]')).map(b => ({
                        text: b.textContent?.trim().substring(0, 80) || ''
                    }))
                };
            }""")
            print(f"\n=== 作成後の画面 ===")
            print(after_info['text'])

            with open(OUTPUT_DIR / "subdomain_created_result.json", "w", encoding="utf-8") as f:
                json.dump(after_info, f, ensure_ascii=False, indent=2)
        else:
            print("  「作成する」ボタンが無効です")

        print("\n[INFO] 60秒待機...")
        time.sleep(60)
        browser.close()


if __name__ == "__main__":
    main()
