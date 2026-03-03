"""
サブドメイン画面調査スクリプト Part 2
- 空欄時の送信ボタン状態確認
- TOKIUM IDでログイン実行
- ログイン後のリダイレクト確認
- パスワードリセット画面
- サブドメインログイン画面（有効なサブドメイン探索）
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
    ss_path = os.path.join(OUTPUT_DIR, screenshot_name)
    page.screenshot(path=ss_path, full_page=True)
    log(f"  Screenshot: {screenshot_name}")

    for sel in ["input", "button", "a", "select", "textarea"]:
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
                    "visible": el.is_visible(),
                    "disabled": el.get_attribute("disabled") is not None,
                }
                info["elements"].append(el_info)
            except:
                pass

    for sel in [".card", ".alert", ".flash", ".error", ".message", "[role='alert']",
                ".card-content", ".card-alert", ".card-info"]:
        msgs = page.query_selector_all(sel)
        for m in msgs:
            try:
                if m.is_visible():
                    info.setdefault("messages", []).append({
                        "selector": sel,
                        "text": m.inner_text()[:200],
                        "class": m.get_attribute("class") or ""
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

        # ========== 5. 空欄時の送信ボタン状態 ==========
        log("=== 5. サブドメイン入力画面 - 空欄時ボタン状態 ===")
        page.goto("https://dev.keihi.com/subdomains/input", wait_until="networkidle")
        # 空欄状態のボタンがdisabledであることを確認
        btn = page.query_selector('button:has-text("送信")')
        btn_disabled = btn.get_attribute("disabled") if btn else None
        btn_class = btn.get_attribute("class") if btn else None
        log(f"  送信ボタン disabled={btn_disabled}, class={btn_class}")
        capture_page_info(page, "5_サブドメイン_空欄時ボタン状態", "05_subdomain_empty_disabled.png")

        # ========== 6. 「ログイン画面に戻る」遷移 ==========
        log("=== 6. ログイン画面に戻るリンク ===")
        page.click('a[href="/users/sign_in"]')
        page.wait_for_url("**/users/sign_in**", timeout=10000)
        page.wait_for_load_state("networkidle")
        capture_page_info(page, "6_ログイン画面に戻る", "06_back_to_login.png")

        # ========== 7. TOKIUM IDでログイン実行 ==========
        log("=== 7. TOKIUM IDでログイン ===")
        page.fill('input[type="email"]', EMAIL)
        page.fill('input[type="password"]', PASSWORD)
        capture_page_info(page, "7_TOKIUM_ID認証情報入力", "07_tokium_id_credentials.png")

        log("  ログインボタンクリック...")
        page.click('#sign_in_form button[type="button"]')

        # ログイン後のリダイレクトを待つ
        try:
            page.wait_for_url("**/invoicing**|**/invoices**|**/members**|**/transactions**", timeout=15000)
        except PlaywrightTimeout:
            log(f"  Timeout. Current URL: {page.url}")
        page.wait_for_load_state("networkidle")
        capture_page_info(page, "8_ログイン後リダイレクト先", "08_after_login_redirect.png")
        log(f"  ログイン後URL: {page.url}")

        # ========== 8. ログイン済み状態でのサブドメイン入力画面 ==========
        log("=== 9. ログイン済みでサブドメイン入力画面アクセス ===")
        page.goto("https://dev.keihi.com/subdomains/input", wait_until="networkidle")
        capture_page_info(page, "9_ログイン済み_サブドメイン入力", "09_subdomain_logged_in.png")
        log(f"  URL: {page.url}")

        # ========== 9. パスワードリセット画面 ==========
        log("=== 10. パスワードリセット画面 ===")
        page.goto("https://dev.keihi.com/users/password/new", wait_until="networkidle")
        capture_page_info(page, "10_パスワードリセット画面", "10_password_reset.png")

        # ========== 10. TOKIUM IDログイン画面の各formアクション ==========
        log("=== 11. ログイン画面のform情報取得 ===")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")

        forms_info = page.evaluate('''() => {
            const forms = document.querySelectorAll('form');
            return Array.from(forms).map(f => ({
                action: f.action,
                method: f.method,
                id: f.id || '(none)',
                buttonText: f.querySelector('button') ? f.querySelector('button').textContent.trim() : '(no button)',
                inputTypes: Array.from(f.querySelectorAll('input')).map(i => i.type)
            }));
        }''')
        log(f"  Forms: {json.dumps(forms_info, ensure_ascii=False, indent=2)}")
        capture_page_info(page, "11_ログイン画面_form情報", "11_login_forms_detail.png")

        # ========== 11. サブドメインログイン画面を複数パターン試行 ==========
        log("=== 12. サブドメインログイン画面の探索 ===")

        # まずログアウト
        page.goto("https://dev.keihi.com/users/sign_out", wait_until="networkidle")
        log(f"  ログアウト後URL: {page.url}")

        # 複数のサブドメインパターンを試行
        subdomain_candidates = ["th3", "tokium", "test", "staging", "demo", "dev"]
        for sd in subdomain_candidates:
            log(f"  サブドメイン試行: {sd}")
            page.goto("https://dev.keihi.com/subdomains/input", wait_until="networkidle")
            page.fill('input[placeholder="サブドメイン"]', sd)
            page.click('button:has-text("送信")')
            page.wait_for_timeout(2000)

            # エラーメッセージチェック
            error_el = page.query_selector('[role="alert"], .error, .card-alert')
            page_text = page.inner_text('body')
            if "無効なサブドメイン" in page_text:
                log(f"    → 無効: {sd}")
            else:
                log(f"    → 有効かも! URL: {page.url}")
                capture_page_info(page, f"12_サブドメイン_{sd}_成功", f"12_subdomain_{sd}_success.png")
                break

        # ========== 12. サブドメインログイン画面（直接URL） ==========
        # 前回の調査で ti-saml.dev-ti.keihi.com が存在したので、
        # dev 環境での類似パターンを試す
        log("=== 13. サブドメインURL直接アクセス ===")
        subdomain_urls = [
            "https://th3.dev.keihi.com/subdomains/sign_in",
            "https://tokium.dev.keihi.com/subdomains/sign_in",
        ]
        for url in subdomain_urls:
            log(f"  試行: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=10000)
                capture_page_info(page, f"13_直接URL_{url.split('//')[1].split('.')[0]}", f"13_direct_{url.split('//')[1].split('.')[0]}.png")
                log(f"    → URL: {page.url}, Title: {page.title()}")
            except Exception as e:
                log(f"    → エラー: {str(e)[:100]}")

        # ========== 完了 ==========
        browser.close()

    # 結果をJSON保存
    json_path = os.path.join(OUTPUT_DIR, "investigation_results_part2.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"\nResults saved to {json_path}")

    # サマリー
    print("\n" + "="*60)
    print("Part 2 調査完了サマリー")
    print("="*60)
    for r in results:
        print(f"  {r['name']}")
        print(f"    URL: {r['url']}")
        vis_elements = [e for e in r['elements'] if e.get('visible')]
        print(f"    可視要素数: {len(vis_elements)}")
        if r.get('messages'):
            for m in r['messages']:
                print(f"    メッセージ: {m['text'][:80]}")
        print()

if __name__ == "__main__":
    main()
