"""
th-02テナントにサブドメインなしで直接ログインするスクリプト
th-02はサブドメインが無効化されているため、サブドメイン入力なしでログイン可能。
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

SUBDOMAIN = "th-02"
BASE = f"https://{SUBDOMAIN}.dev.keihi.com"

OUTPUT_DIR = Path(__file__).parent / "screen_investigation"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        # Step 1: th-02に直接アクセス（サブドメイン無効なので直接ログイン画面が出るはず）
        print("[1] th-02.dev.keihi.com に直接アクセス...")
        page.goto(f"{BASE}/users/sign_in", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        print(f"  URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "th02_01_initial.png"), full_page=True)

        # ページの状態を確認
        page_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 1000) : ''")
        print(f"  ページテキスト: {page_text[:300]}")

        # メール/パスワード入力欄を探す
        email_sel = 'input[type="email"]'
        pw_sel = 'input[type="password"]'
        email_input = page.query_selector(email_sel)
        pw_input = page.query_selector(pw_sel)

        if not email_input:
            # name属性でも探す
            email_sel = 'input[name="user[email]"]'
            email_input = page.query_selector(email_sel)
        if not pw_input:
            pw_sel = 'input[name="user[password]"]'
            pw_input = page.query_selector(pw_sel)

        if email_input and pw_input:
            # ikeda_n+th2でログイン
            account = os.environ.get("TOKIUM_ID_EMAIL", "").replace("+th3", "+th2")
            password = os.environ.get("TOKIUM_ID_PASSWORD", "")
            print(f"  アカウント: {account}")

            page.fill(email_sel, account)
            page.fill(pw_sel, password)
            page.screenshot(path=str(SCREENSHOTS_DIR / "th02_02_login_form.png"), full_page=True)

            # ログインボタン
            login_btn = page.query_selector('#sign_in_form button[type="button"]')
            if not login_btn:
                login_btn = page.query_selector('button[type="submit"]')
            if not login_btn:
                login_btn = page.locator('button:has-text("ログイン")').first
                if login_btn.is_visible():
                    login_btn.click()
                    login_btn = None  # already clicked
            if login_btn:
                login_btn.click()

            time.sleep(5)
            page.wait_for_load_state("networkidle")
            print(f"  ログイン後URL: {page.url}")
            page.screenshot(path=str(SCREENSHOTS_DIR / "th02_03_after_login.png"), full_page=True)

            # エラーチェック
            error_text = page.evaluate("""() => {
                const el = document.querySelector('.flash-message, [role="alert"], .alert, [class*="error"]');
                return el ? el.textContent.trim() : '';
            }""")
            if error_text:
                print(f"  エラー: {error_text}")

                # th3でもリトライ
                print("  ikeda_n+th3で再試行...")
                account3 = os.environ.get("TOKIUM_ID_EMAIL", "")
                page.fill(email_sel, account3)
                page.fill(pw_sel, password)
                if page.query_selector('#sign_in_form button[type="button"]'):
                    page.query_selector('#sign_in_form button[type="button"]').click()
                else:
                    page.locator('button:has-text("ログイン")').first.click()
                time.sleep(5)
                page.wait_for_load_state("networkidle")
                print(f"  再試行後URL: {page.url}")
                page.screenshot(path=str(SCREENSHOTS_DIR / "th02_04_retry_login.png"), full_page=True)
        else:
            print("  ログインフォームが見つかりません")
            # 全フォーム要素を取得
            all_inputs = page.evaluate("""() => {
                const inputs = [];
                document.querySelectorAll('input, button, a').forEach(el => {
                    inputs.push({
                        tag: el.tagName,
                        type: el.type || '',
                        name: el.name || '',
                        text: el.textContent?.trim().substring(0, 80) || '',
                        href: el.getAttribute('href') || '',
                        placeholder: el.placeholder || ''
                    });
                });
                return inputs;
            }""")
            print(f"  全要素: {json.dumps(all_inputs, ensure_ascii=False, indent=2)}")

        # ログイン成功していればセキュリティ設定を確認
        if SUBDOMAIN in page.url and "sign_in" not in page.url:
            print("\n[2] セキュリティ設定にアクセス...")
            page.goto(f"{BASE}/preferences/security/subdomain", timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            print(f"  URL: {page.url}")
            page.screenshot(path=str(SCREENSHOTS_DIR / "th02_05_security_subdomain.png"), full_page=True)

            page_info = page.evaluate("""() => {
                return {
                    url: location.href,
                    text: document.body.innerText.substring(0, 3000),
                    inputs: Array.from(document.querySelectorAll('input:not([type="hidden"])')).map(i => ({
                        type: i.type, name: i.name, value: i.value, disabled: i.disabled, checked: i.checked
                    })),
                    buttons: Array.from(document.querySelectorAll('button, [role="button"]')).map(b => ({
                        text: b.textContent?.trim().substring(0, 80) || '', disabled: b.disabled
                    }))
                };
            }""")
            print(f"\n=== th-02 セキュリティ > サブドメイン ===")
            print(page_info['text'])

            with open(OUTPUT_DIR / "th02_subdomain_setting.json", "w", encoding="utf-8") as f:
                json.dump(page_info, f, ensure_ascii=False, indent=2)

        print("\n[INFO] 30秒待機...")
        time.sleep(30)
        browser.close()


if __name__ == "__main__":
    main()
