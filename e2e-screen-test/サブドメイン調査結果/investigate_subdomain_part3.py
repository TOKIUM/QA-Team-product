"""
サブドメイン画面調査スクリプト Part 3
有効なサブドメイン th-01, th-02 での画面遷移・構成調査
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
SUBDOMAINS = ["th-01", "th-02"]

results = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def capture_page_info(page, name, screenshot_name):
    info = {
        "name": name,
        "url": page.url,
        "title": page.title(),
        "screenshot": screenshot_name,
        "elements": [],
        "messages": [],
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

    # メッセージ系要素
    for sel in [".card", ".alert", ".flash", ".error", ".message", "[role='alert']",
                ".card-content", ".card-alert", ".card-info"]:
        msgs = page.query_selector_all(sel)
        for m in msgs:
            try:
                if m.is_visible():
                    info["messages"].append({
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

        step = 14  # 前回の続きの番号

        for sd in SUBDOMAINS:
            log(f"\n{'='*60}")
            log(f"サブドメイン: {sd}")
            log(f"{'='*60}")

            # ========== サブドメイン入力 → 送信 ==========
            log(f"=== {step}. サブドメイン '{sd}' を入力して送信 ===")
            page.goto("https://dev.keihi.com/subdomains/input", wait_until="networkidle")
            page.fill('input[placeholder="サブドメイン"]', sd)
            page.click('button:has-text("送信")')

            # 遷移を待つ
            try:
                page.wait_for_url(f"**{sd}**", timeout=10000)
            except PlaywrightTimeout:
                log(f"  URL変化なし。現在: {page.url}")
            page.wait_for_load_state("networkidle")

            current_url = page.url
            log(f"  遷移先URL: {current_url}")
            capture_page_info(page, f"{step}_サブドメイン_{sd}_送信後", f"{step}_subdomain_{sd}_result.png")
            step += 1

            # ========== サブドメインログイン画面の詳細調査 ==========
            if "sign_in" in current_url or "subdomains" in current_url:
                log(f"=== {step}. サブドメインログイン画面 ({sd}) の詳細 ===")

                # HTML構造の詳細取得
                page_structure = page.evaluate('''() => {
                    const forms = document.querySelectorAll('form');
                    const formData = Array.from(forms).map(f => ({
                        action: f.action,
                        method: f.method,
                        id: f.id || '(none)',
                        buttonText: f.querySelector('button') ? f.querySelector('button').textContent.trim() : '(no button)',
                        inputTypes: Array.from(f.querySelectorAll('input')).map(i => ({
                            type: i.type,
                            name: i.name,
                            placeholder: i.placeholder,
                            id: i.id
                        }))
                    }));

                    // SAML/SSOボタンの確認
                    const samlButtons = Array.from(document.querySelectorAll('button, a')).filter(
                        el => el.textContent.includes('SAML') || el.textContent.includes('SSO') ||
                              el.textContent.includes('TOKIUM ID') || el.textContent.includes('サブドメイン')
                    ).map(el => ({
                        tag: el.tagName,
                        text: el.textContent.trim().substring(0, 100),
                        href: el.getAttribute('href') || '',
                        type: el.getAttribute('type') || ''
                    }));

                    // フラッシュメッセージ構造
                    const flashElements = Array.from(document.querySelectorAll('.card, .alert, .flash, [role="alert"]'));
                    const flashInfo = flashElements.map(el => ({
                        tag: el.tagName,
                        class: el.className,
                        text: el.textContent.trim().substring(0, 200),
                        visible: el.offsetParent !== null
                    }));

                    return { forms: formData, samlButtons, flashElements: flashInfo };
                }''')
                log(f"  Forms: {json.dumps(page_structure.get('forms', []), ensure_ascii=False)}")
                log(f"  SAML/SSO: {json.dumps(page_structure.get('samlButtons', []), ensure_ascii=False)}")
                if page_structure.get('flashElements'):
                    log(f"  Flash: {json.dumps(page_structure['flashElements'], ensure_ascii=False)}")

                # 結果に構造情報を追加
                results[-1]["page_structure"] = page_structure
                step += 1

                # ========== ログイン試行 ==========
                log(f"=== {step}. サブドメイン '{sd}' 経由でログイン試行 ===")

                # メール・パスワード入力
                email_input = page.query_selector('input[type="email"]')
                pw_input = page.query_selector('input[type="password"]')

                if email_input and pw_input:
                    page.fill('input[type="email"]', EMAIL)
                    page.fill('input[type="password"]', PASSWORD)
                    capture_page_info(page, f"{step}_サブドメイン_{sd}_認証情報入力", f"{step}_subdomain_{sd}_credentials.png")
                    step += 1

                    # ログインボタンクリック
                    log(f"=== {step}. ログインボタンクリック ===")
                    login_btn = page.query_selector('#sign_in_form button[type="button"]') or \
                                page.query_selector('button:has-text("ログイン")')
                    if login_btn:
                        login_btn.click()
                        try:
                            page.wait_for_url("**invoic**|**members**|**transactions**|**dashboard**", timeout=15000)
                        except PlaywrightTimeout:
                            log(f"  リダイレクトタイムアウト。現在URL: {page.url}")

                        page.wait_for_load_state("networkidle")
                        log(f"  ログイン後URL: {page.url}")
                        capture_page_info(page, f"{step}_サブドメイン_{sd}_ログイン後", f"{step}_subdomain_{sd}_after_login.png")
                        step += 1

                        # ログイン成功した場合、ログイン後の状態を記録
                        if "sign_in" not in page.url and "login" not in page.url:
                            log(f"  ✅ ログイン成功! URL: {page.url}")

                            # ログアウトしてから次のサブドメインへ
                            page.goto("https://dev.keihi.com/users/sign_out", wait_until="networkidle")
                            log(f"  ログアウト完了。URL: {page.url}")
                        else:
                            log(f"  ❌ ログイン失敗。URL: {page.url}")
                            # エラーメッセージのスクリーンショット
                            capture_page_info(page, f"{step}_サブドメイン_{sd}_ログインエラー", f"{step}_subdomain_{sd}_login_error.png")
                            step += 1
                    else:
                        log(f"  ログインボタンが見つからない")
                else:
                    log(f"  メール/パスワード入力欄がない（SAML専用?）")
                    # SAML等のボタンがあるか確認
                    capture_page_info(page, f"{step}_サブドメイン_{sd}_ログイン要素なし", f"{step}_subdomain_{sd}_no_login_form.png")
                    step += 1
            else:
                log(f"  ⚠ サブドメインログイン画面への遷移失敗。URL: {current_url}")

        # ========== 追加: サブドメインログイン画面の比較 ==========
        log(f"\n{'='*60}")
        log(f"=== {step}. 2つのサブドメインの直接URL比較 ===")
        log(f"{'='*60}")

        for sd in SUBDOMAINS:
            url = f"https://{sd}.dev.keihi.com/subdomains/sign_in"
            log(f"  直接アクセス: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
                log(f"  → URL: {page.url}, Title: {page.title()}")
                capture_page_info(page, f"{step}_直接URL_{sd}", f"{step}_direct_{sd}.png")
            except Exception as e:
                log(f"  → エラー: {str(e)[:100]}")
            step += 1

        browser.close()

    # JSON保存
    json_path = os.path.join(OUTPUT_DIR, "investigation_results_part3.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"\nResults saved to {json_path}")

    # サマリー
    print("\n" + "="*60)
    print("Part 3 調査完了サマリー")
    print("="*60)
    for r in results:
        print(f"\n  {r['name']}")
        print(f"    URL: {r['url']}")
        vis = [e for e in r['elements'] if e.get('visible')]
        print(f"    可視要素数: {len(vis)}")
        if r.get('messages'):
            for m in r['messages']:
                print(f"    メッセージ: {m['text'][:80]}")
        if r.get('page_structure', {}).get('forms'):
            for f in r['page_structure']['forms']:
                print(f"    Form: {f.get('id','?')} → {f.get('action','?')} [{f.get('buttonText','')}]")

if __name__ == "__main__":
    main()
