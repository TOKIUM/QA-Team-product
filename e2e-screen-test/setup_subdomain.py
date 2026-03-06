"""
TOKIUM サブドメイン設定スクリプト
ti-saml.dev-ti.keihi.com にログインし、セキュリティ設定内のサブドメインを確認・設定する。
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

TARGET_URL = "https://th-01.dev.keihi.com"
SECURITY_URL = f"{TARGET_URL}/preferences/security/ip_restriction"
SUBDOMAIN = "th-01"

OUTPUT_DIR = Path(__file__).parent / "screen_investigation"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        # Step 1: ti-saml.dev-ti.keihi.com にアクセス
        print("[1] ti-saml.dev-ti.keihi.com/transactions にアクセス...")
        page.goto(f"{TARGET_URL}/transactions", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        print(f"  現在URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "subdomain_01_initial.png"), full_page=True)

        # ログイン画面が表示された場合
        current_url = page.url
        if "sign_in" in current_url or "login" in current_url or "subdomains" in current_url:
            print("[2] ログインが必要です。ログイン処理開始...")

            # メール/パスワード入力欄を探す
            email_input = page.query_selector('input[type="email"]') or page.query_selector('input[name="user[email]"]')
            pw_input = page.query_selector('input[type="password"]') or page.query_selector('input[name="user[password]"]')

            if email_input and pw_input:
                # ikeda_n+th2 でログイン試行（ti-samlテナント用）
                account = "ikeda_n+th2@tokium.jp"
                password = os.environ.get("TOKIUM_ID_PASSWORD", "")
                print(f"  アカウント: {account}")

                page.fill('input[type="email"]', account)
                page.fill('input[type="password"]', password)
                page.screenshot(path=str(SCREENSHOTS_DIR / "subdomain_02_login_form.png"), full_page=True)

                # ログインボタンクリック（テキスト「ログイン」を持つボタン）
                login_btn = page.locator('button:has-text("ログイン")').first
                if not login_btn.is_visible():
                    login_btn = (page.query_selector('#sign_in_form button[type="button"]')
                                 or page.query_selector('button[type="submit"]')
                                 or page.query_selector('input[type="submit"]'))
                if login_btn:
                    try:
                        login_btn.click()
                    except Exception:
                        # Locator vs ElementHandle の違いを吸収
                        page.locator('button:has-text("ログイン")').first.click()
                    time.sleep(5)
                    page.wait_for_load_state("networkidle")
                    print(f"  ログイン後URL: {page.url}")
                    page.screenshot(path=str(SCREENSHOTS_DIR / "subdomain_03_after_login.png"), full_page=True)

                    # ログイン失敗チェック
                    if "sign_in" in page.url:
                        error_text = page.evaluate("() => { const el = document.querySelector('.flash-message, [role=alert], .alert'); return el ? el.textContent.trim() : ''; }")
                        if error_text:
                            print(f"  ログインエラー: {error_text}")

                        # ikeda_n+th3も試す
                        print("  ikeda_n+th3@tokium.jp で再試行...")
                        page.fill('input[type="email"]', "ikeda_n+th3@tokium.jp")
                        page.fill('input[type="password"]', password)
                        page.locator('button:has-text("ログイン")').first.click()
                        time.sleep(5)
                        page.wait_for_load_state("networkidle")
                        print(f"  再試行後URL: {page.url}")
                        page.screenshot(path=str(SCREENSHOTS_DIR / "subdomain_03b_retry_login.png"), full_page=True)
            else:
                print(f"  ログインフォームが見つかりません。URL: {page.url}")
                # ページのHTML構造をダンプ
                html = page.evaluate("() => document.body ? document.body.innerHTML.substring(0, 1000) : 'no body'")
                print(f"  HTML: {html}")
                page.screenshot(path=str(SCREENSHOTS_DIR / "subdomain_02_no_login_form.png"), full_page=True)

        # Step 3: セキュリティ設定に移動
        print(f"\n[3] セキュリティ設定に移動: {SECURITY_URL}")
        page.goto(SECURITY_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        print(f"  現在URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "subdomain_04_security.png"), full_page=True)

        # ページの構造を取得
        page_info = page.evaluate("""() => {
            const result = {
                url: location.href,
                title: document.title,
                headings: [],
                labels: [],
                inputs: [],
                buttons: [],
                links: [],
                tabs: [],
                text_content: []
            };

            document.querySelectorAll('h1,h2,h3,h4,h5').forEach(h => {
                result.headings.push({tag: h.tagName, text: h.textContent.trim().substring(0, 100)});
            });

            document.querySelectorAll('label').forEach(l => {
                result.labels.push(l.textContent.trim().substring(0, 100));
            });

            document.querySelectorAll('input:not([type="hidden"]), textarea, select').forEach(inp => {
                result.inputs.push({
                    type: inp.type || inp.tagName.toLowerCase(),
                    name: inp.name || '',
                    value: inp.value || '',
                    placeholder: inp.placeholder || '',
                    id: inp.id || ''
                });
            });

            document.querySelectorAll('button, [role="button"]').forEach(b => {
                result.buttons.push(b.textContent.trim().substring(0, 80));
            });

            // タブやナビゲーション
            document.querySelectorAll('[role="tab"], .tab, [class*="Tab"]').forEach(t => {
                result.tabs.push(t.textContent.trim().substring(0, 50));
            });

            // サブドメイン関連のテキストを探す
            const allText = document.body.innerText;
            const lines = allText.split('\\n').filter(l => l.trim());
            lines.forEach(line => {
                const trimmed = line.trim();
                if (trimmed.includes('サブドメイン') || trimmed.includes('subdomain') ||
                    trimmed.includes('ドメイン') || trimmed.includes('IP') ||
                    trimmed.includes('セキュリティ') || trimmed.includes('制限')) {
                    result.text_content.push(trimmed.substring(0, 200));
                }
            });

            return result;
        }""")

        print("\n=== セキュリティ設定画面の構造 ===")
        print(f"見出し: {json.dumps(page_info['headings'], ensure_ascii=False)}")
        print(f"ラベル: {json.dumps(page_info['labels'], ensure_ascii=False)}")
        print(f"入力: {json.dumps(page_info['inputs'], ensure_ascii=False)}")
        print(f"ボタン: {json.dumps(page_info['buttons'], ensure_ascii=False)}")
        print(f"タブ: {json.dumps(page_info['tabs'], ensure_ascii=False)}")
        print(f"サブドメイン関連テキスト: {json.dumps(page_info['text_content'], ensure_ascii=False)}")

        # セキュリティページ内のリンク・ナビゲーションも確認
        nav_links = page.evaluate("""() => {
            const links = [];
            document.querySelectorAll('a[href]').forEach(a => {
                const text = a.textContent.trim();
                const href = a.getAttribute('href');
                if (text && (text.includes('サブドメイン') || text.includes('セキュリティ') ||
                    text.includes('IP') || text.includes('SAML') || text.includes('SSO') ||
                    href.includes('security') || href.includes('subdomain'))) {
                    links.push({text: text.substring(0, 80), href});
                }
            });
            return links;
        }""")
        print(f"\nセキュリティ関連リンク: {json.dumps(nav_links, ensure_ascii=False)}")

        # 結果をJSONに保存
        result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_url": TARGET_URL,
            "security_url": SECURITY_URL,
            "final_url": page.url,
            "page_info": page_info,
            "security_links": nav_links
        }
        with open(OUTPUT_DIR / "subdomain_setup_info.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n結果保存: {OUTPUT_DIR / 'subdomain_setup_info.json'}")

        # ブラウザを閉じずに待機（手動確認用）
        print("\n[INFO] ブラウザを30秒間開いたままにします...")
        time.sleep(30)

        browser.close()


if __name__ == "__main__":
    main()
