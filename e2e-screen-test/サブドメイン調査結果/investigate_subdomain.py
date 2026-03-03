"""
サブドメイン画面調査スクリプト
TOKIUM IDログイン → サブドメイン関連画面の遷移と構成を調査
"""
import json
import os
import sys
import io
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
INVOICING_URL = "https://invoicing-staging.keihi.com/login"
TOKIUM_ID_URL = "https://dev.keihi.com/users/sign_in"
SUBDOMAIN_INPUT_URL = "https://dev.keihi.com/subdomains/input"
EMAIL = "ikeda_n+th3@tokium.jp"
PASSWORD = "Qa12345678"

results = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def capture_page_info(page, name, screenshot_name):
    """ページの情報をキャプチャする"""
    info = {
        "name": name,
        "url": page.url,
        "title": page.title(),
        "screenshot": screenshot_name,
        "elements": [],
        "timestamp": datetime.now().isoformat()
    }

    # スクリーンショット
    ss_path = os.path.join(OUTPUT_DIR, screenshot_name)
    page.screenshot(path=ss_path, full_page=True)
    log(f"  Screenshot: {screenshot_name}")

    # インタラクティブ要素を収集
    for sel, etype in [
        ("input", "input"), ("button", "button"), ("a", "link"),
        ("select", "select"), ("textarea", "textarea")
    ]:
        elements = page.query_selector_all(sel)
        for el in elements:
            try:
                el_info = {
                    "tag": sel,
                    "type": el.get_attribute("type") or "",
                    "name": el.get_attribute("name") or "",
                    "id": el.get_attribute("id") or "",
                    "class": el.get_attribute("class") or "",
                    "placeholder": el.get_attribute("placeholder") or "",
                    "href": el.get_attribute("href") or "",
                    "text": el.inner_text()[:100] if el.is_visible() else "(hidden)",
                    "visible": el.is_visible()
                }
                info["elements"].append(el_info)
            except:
                pass

    # フラッシュメッセージ等のテキスト要素
    for sel in [".card", ".alert", ".flash", ".error", ".message", "[role='alert']"]:
        msgs = page.query_selector_all(sel)
        for m in msgs:
            try:
                if m.is_visible():
                    info.setdefault("messages", []).append({
                        "selector": sel,
                        "text": m.inner_text()[:200]
                    })
            except:
                pass

    results.append(info)
    return info


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ja-JP"
        )
        page = context.new_page()

        # ========== 1. invoicing ログイン画面 ==========
        log("=== 1. invoicing ログイン画面 ===")
        page.goto(INVOICING_URL, wait_until="networkidle")
        capture_page_info(page, "1_invoicing_ログイン画面", "01_invoicing_login.png")

        # ========== 2. 「TOKIUM IDでログイン」クリック → TOKIUM IDログイン画面 ==========
        log("=== 2. TOKIUM IDでログイン → リダイレクト ===")
        page.click('a[href="/auth-redirect"]')
        page.wait_for_url("**/users/sign_in**", timeout=15000)
        page.wait_for_load_state("networkidle")
        capture_page_info(page, "2_TOKIUM_IDログイン画面", "02_tokium_id_login.png")

        # ========== 3. 「サブドメインを入力」クリック → サブドメイン入力画面 ==========
        log("=== 3. サブドメインを入力 → サブドメイン入力画面 ===")
        page.click('button:has-text("サブドメインを入力")')
        page.wait_for_url("**/subdomains/input**", timeout=10000)
        page.wait_for_load_state("networkidle")
        capture_page_info(page, "3_サブドメイン入力画面", "03_subdomain_input.png")

        # ========== 4. 無効なサブドメイン入力 → エラー表示 ==========
        log("=== 4. 無効なサブドメイン入力 → エラー ===")
        page.fill('input[placeholder="サブドメイン"]', 'invalid-test-subdomain')
        page.click('button:has-text("送信")')
        page.wait_for_timeout(2000)
        capture_page_info(page, "4_サブドメイン入力_エラー", "04_subdomain_error.png")

        # ========== 5. 空のサブドメイン送信 ==========
        log("=== 5. 空のサブドメイン送信 ===")
        page.fill('input[placeholder="サブドメイン"]', '')
        page.click('button:has-text("送信")')
        page.wait_for_timeout(2000)
        capture_page_info(page, "5_サブドメイン入力_空欄エラー", "05_subdomain_empty.png")

        # ========== 6. 「ログイン画面に戻る」リンク ==========
        log("=== 6. ログイン画面に戻る ===")
        page.click('a[href="/users/sign_in"]')
        page.wait_for_url("**/users/sign_in**", timeout=10000)
        page.wait_for_load_state("networkidle")
        capture_page_info(page, "6_ログイン画面に戻る", "06_back_to_login.png")

        # ========== 7. TOKIUM IDでログイン実行 ==========
        log("=== 7. TOKIUM IDでログイン実行 ===")
        page.fill('input[type="email"]', EMAIL)
        page.fill('input[type="password"]', PASSWORD)
        capture_page_info(page, "7_TOKIUM_ID_認証情報入力", "07_tokium_id_credentials.png")

        page.click('#sign_in_form button[type="button"]')
        try:
            page.wait_for_url("**invoicing**", timeout=15000)
        except PlaywrightTimeout:
            log(f"  Timeout waiting for invoicing redirect. Current URL: {page.url}")
        page.wait_for_load_state("networkidle")
        capture_page_info(page, "8_ログイン後画面", "08_after_login.png")

        # ========== 8. ログイン後にサブドメイン情報を確認 ==========
        log(f"=== 8. ログイン後URL: {page.url} ===")

        # サブドメイン入力画面に直接アクセスしてみる（ログイン済み状態）
        log("=== 9. ログイン済み状態でサブドメイン入力画面にアクセス ===")
        page.goto(SUBDOMAIN_INPUT_URL, wait_until="networkidle")
        capture_page_info(page, "9_ログイン済み_サブドメイン入力", "09_subdomain_input_logged_in.png")

        # ========== 9. パスワードリセット画面 ==========
        log("=== 10. パスワードリセット画面 ===")
        page.goto("https://dev.keihi.com/users/password/new", wait_until="networkidle")
        capture_page_info(page, "10_パスワードリセット画面", "10_password_reset.png")

        # ========== 10. Googleログインボタンのform情報 ==========
        log("=== 11. ログイン画面に戻ってGoogleボタンのform確認 ===")
        page.goto(TOKIUM_ID_URL, wait_until="networkidle")

        # 各ボタンのform action を取得
        google_form = page.evaluate('''() => {
            const forms = document.querySelectorAll('form');
            return Array.from(forms).map(f => ({
                action: f.action,
                method: f.method,
                id: f.id,
                buttonText: f.querySelector('button') ? f.querySelector('button').textContent.trim() : ''
            }));
        }''')
        log(f"  Forms: {json.dumps(google_form, ensure_ascii=False)}")
        capture_page_info(page, "11_ログイン画面_再確認", "11_login_forms.png")

        # ========== 完了 ==========
        browser.close()

    # 結果をJSONに保存
    json_path = os.path.join(OUTPUT_DIR, "investigation_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"Results saved to {json_path}")

    # サマリー出力
    print("\n" + "="*60)
    print("調査完了サマリー")
    print("="*60)
    for r in results:
        print(f"  {r['name']}")
        print(f"    URL: {r['url']}")
        print(f"    要素数: {len(r['elements'])}")
        if r.get('messages'):
            for m in r['messages']:
                print(f"    メッセージ: {m['text'][:80]}")
        print()

if __name__ == "__main__":
    main()
