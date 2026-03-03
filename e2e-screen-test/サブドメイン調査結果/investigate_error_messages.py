"""
invoicing-staging側のエラーメッセージを確認するスクリプト
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

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def get_page_text_and_messages(page):
    """ページ上のエラーメッセージを収集"""
    result = page.evaluate('''() => {
        // alert/error/flash系の要素を探す
        const selectors = ['.alert', '.error', '.flash', '.message', '[role="alert"]',
                          '.card', '.card-alert', '.card-info', '.notification',
                          '.toast', '.banner', '.warning', 'p.error', 'span.error',
                          '[class*="error"]', '[class*="alert"]', '[class*="flash"]'];
        const messages = [];
        for (const sel of selectors) {
            const els = document.querySelectorAll(sel);
            for (const el of els) {
                if (el.offsetParent !== null && el.textContent.trim()) {
                    messages.push({
                        selector: sel,
                        class: el.className,
                        tag: el.tagName,
                        text: el.textContent.trim().substring(0, 300)
                    });
                }
            }
        }
        // body全文からエラーっぽいテキストを探す
        const bodyText = document.body.innerText;
        return { messages, bodyText: bodyText.substring(0, 2000), url: window.location.href };
    }''')
    return result

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ja-JP")
        page = context.new_page()

        results = {}

        # ========== 1. invoicing: 空欄でログイン ==========
        log("=== 1. invoicing: 空欄ログイン ===")
        page.goto("https://invoicing-staging.keihi.com/login", wait_until="networkidle")
        page.click('button[type="submit"]:has-text("ログイン")')
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_01_invoicing_empty.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["invoicing_empty"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        # ========== 2. invoicing: 不正メールでログイン ==========
        log("=== 2. invoicing: 不正メール ===")
        page.goto("https://invoicing-staging.keihi.com/login", wait_until="networkidle")
        page.fill('input[type="email"]', 'invalid@example.com')
        page.fill('input[type="password"]', 'wrongpassword')
        page.click('button[type="submit"]:has-text("ログイン")')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_02_invoicing_invalid.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["invoicing_invalid"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        # ========== 3. invoicing: 正しいメール+不正PW ==========
        log("=== 3. invoicing: 正しいメール+不正PW ===")
        page.goto("https://invoicing-staging.keihi.com/login", wait_until="networkidle")
        page.fill('input[type="email"]', 'ikeda_n+th3@tokium.jp')
        page.fill('input[type="password"]', 'WrongPassword123')
        page.click('button[type="submit"]:has-text("ログイン")')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_03_invoicing_wrong_pw.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["invoicing_wrong_pw"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        # ========== 4. TOKIUM ID: 不正PWでログイン ==========
        log("=== 4. TOKIUM ID: 不正PW ===")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
        page.fill('input[type="email"]', 'ikeda_n+th3@tokium.jp')
        page.fill('input[type="password"]', 'WrongPassword123')
        page.click('#sign_in_form button[type="button"]')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_04_tokiumid_wrong_pw.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["tokiumid_wrong_pw"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        # ========== 5. TOKIUM ID: 空欄でログイン ==========
        log("=== 5. TOKIUM ID: 空欄 ===")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
        page.click('#sign_in_form button[type="button"]')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_05_tokiumid_empty.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["tokiumid_empty"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        # ========== 6. サブドメインログイン: 不正PW ==========
        log("=== 6. サブドメインログイン(th-01): 不正PW ===")
        page.goto("https://dev.keihi.com/subdomains/input", wait_until="networkidle")
        page.fill('input[placeholder="サブドメイン"]', 'th-01')
        page.click('button:has-text("送信")')
        page.wait_for_url("**th-01**", timeout=10000)
        page.wait_for_load_state("networkidle")
        page.fill('input[type="email"]', 'ikeda_n+th3@tokium.jp')
        page.fill('input[type="password"]', 'WrongPassword123')
        page.click('#sign_in_form button[type="button"]')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_06_subdomain_wrong_pw.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["subdomain_wrong_pw"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        # ========== 7. サブドメインログイン: 空欄 ==========
        log("=== 7. サブドメインログイン(th-01): 空欄 ===")
        page.goto("https://th-01.dev.keihi.com/subdomains/sign_in", wait_until="networkidle")
        page.click('#sign_in_form button[type="button"]')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_07_subdomain_empty.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["subdomain_empty"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        # ========== 8. TOKIUM ID: サブドメイン必須エラー（再確認） ==========
        log("=== 8. TOKIUM ID: サブドメイン必須エラー ===")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
        page.fill('input[type="email"]', 'ikeda_n+th3@tokium.jp')
        page.fill('input[type="password"]', 'Qa12345678')
        page.click('#sign_in_form button[type="button"]')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "err_08_subdomain_required.png"), full_page=True)
        r = get_page_text_and_messages(page)
        results["subdomain_required"] = r
        log(f"  URL: {r['url']}")
        log(f"  Messages: {json.dumps(r['messages'], ensure_ascii=False)}")

        browser.close()

    # JSON保存
    json_path = os.path.join(OUTPUT_DIR, "error_messages_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"\nResults saved to {json_path}")

    # サマリー
    print("\n" + "="*60)
    print("エラーメッセージ調査サマリー")
    print("="*60)
    for key, r in results.items():
        print(f"\n  {key}:")
        print(f"    URL: {r['url']}")
        if r['messages']:
            for m in r['messages']:
                print(f"    [{m['selector']}] {m['text'][:100]}")
        else:
            # bodyTextからエラーを探す
            for line in r['bodyText'].split('\n'):
                line = line.strip()
                if any(w in line for w in ['エラー', '失敗', '無効', '許可', 'ログインに', '正しく']):
                    print(f"    (body) {line[:100]}")

if __name__ == "__main__":
    main()
