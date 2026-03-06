"""
TOKIUM全画面構成 自動調査スクリプト
th-02テナントにログインし、全サイドバーメニューを巡回して画面構成を記録する。

使用方法:
  .envファイル（ログイン/.env）から認証情報を読み込みます。
  必要な環境変数: TOKIUM_ID_EMAIL, TOKIUM_ID_PASSWORD, TOKIUM_ID_SUBDOMAIN
"""

import json
import os
import sys
import io
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Windows環境でのUTF-8出力対応
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# .envから認証情報を読み込み
ENV_PATH = Path(__file__).parent / "ログイン" / ".env"
load_dotenv(ENV_PATH)

TOKIUM_ID_EMAIL = os.environ["TOKIUM_ID_EMAIL"]
TOKIUM_ID_PASSWORD = os.environ["TOKIUM_ID_PASSWORD"]
# .envのTOKIUM_ID_SUBDOMAINを無視して直接指定（th-02が無効化されたため）
TOKIUM_ID_SUBDOMAIN = "th-01"
SUBDOMAIN_INPUT_URL = "https://dev.keihi.com/subdomains/input"
BASE_URL = f"https://{TOKIUM_ID_SUBDOMAIN}.dev.keihi.com"

OUTPUT_DIR = Path(__file__).parent / "screen_investigation"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"


def setup_dirs():
    OUTPUT_DIR.mkdir(exist_ok=True)
    SCREENSHOTS_DIR.mkdir(exist_ok=True)


def login(page):
    """TOKIUM IDでログインしてテナントにアクセスする
    フロー: TOKIUM IDログイン画面 → サブドメインを入力ボタン → サブドメイン入力 → 送信 → ログイン
    """
    print("[1/5] TOKIUM IDログイン開始...")

    # Step 1: TOKIUM IDログイン画面にアクセス（セッション確立のため）
    page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
    time.sleep(2)
    print(f"  TOKIUM IDログイン画面: {page.url}")
    page.screenshot(path=str(SCREENSHOTS_DIR / "00_step1_tokium_id.png"), full_page=True)

    # Step 2: 「サブドメインを入力」ボタンをクリック
    subdomain_btn = page.locator('button:has-text("サブドメインを入力")')
    if subdomain_btn.count() > 0:
        subdomain_btn.click()
        page.wait_for_url("**/subdomains/input**", timeout=10000)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        print(f"  サブドメイン入力画面: {page.url}")
    else:
        # 直接アクセス
        page.goto(SUBDOMAIN_INPUT_URL, wait_until="networkidle")
        time.sleep(1)
        print(f"  サブドメイン入力画面（直接）: {page.url}")

    page.screenshot(path=str(SCREENSHOTS_DIR / "00_step2_subdomain_input.png"), full_page=True)

    # Step 3: サブドメインを入力して送信（React SPA対応）
    subdomain_input = page.locator('input[placeholder="サブドメイン"]')
    subdomain_input.click()
    time.sleep(0.5)

    # React state更新のためkeyboard.typeで入力
    # 先にCtrl+Aで全選択→入力
    page.keyboard.press("Control+a")
    page.keyboard.type(TOKIUM_ID_SUBDOMAIN, delay=50)
    time.sleep(1)

    # 入力値をデバッグ確認
    input_value = subdomain_input.input_value()
    print(f"  入力値: '{input_value}'")

    submit_btn = page.locator('button:has-text("送信")')
    print(f"  送信ボタン disabled: {submit_btn.is_disabled()}")
    page.screenshot(path=str(SCREENSHOTS_DIR / "00_step2b_before_submit.png"), full_page=True)

    # クリック（通常 + 待機）
    submit_btn.click()
    time.sleep(3)  # ナビゲーション待ち

    # サブドメインのログイン画面に遷移を待つ
    try:
        page.wait_for_url(f"**{TOKIUM_ID_SUBDOMAIN}**", timeout=15000)
    except Exception:
        print(f"  URL変化待ちタイムアウト。現在: {page.url}")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print(f"  サブドメインログイン画面: {page.url}")
    page.screenshot(path=str(SCREENSHOTS_DIR / "00_step3_subdomain_login.png"), full_page=True)

    # Step 4: メールアドレス・パスワード入力
    email_sel = 'input[name="user[email]"]'
    pw_sel = 'input[name="user[password]"]'
    email_input = page.query_selector(email_sel)
    pw_input = page.query_selector(pw_sel)

    if not email_input:
        email_sel = 'input[type="email"]'
        email_input = page.query_selector(email_sel)
    if not pw_input:
        pw_sel = 'input[type="password"]'
        pw_input = page.query_selector(pw_sel)

    if email_input and pw_input:
        page.fill(email_sel, TOKIUM_ID_EMAIL)
        page.fill(pw_sel, TOKIUM_ID_PASSWORD)

        # ログインボタンクリック
        login_btn = page.query_selector('#sign_in_form button[type="button"]')
        if not login_btn:
            login_btn = page.query_selector('#sign_in_form button')
        if not login_btn:
            login_btn = page.query_selector('button[type="submit"]')
        if login_btn:
            login_btn.click()
            print("  ログインボタンクリック完了")
        else:
            print("  WARNING: ログインボタンが見つかりません")

        time.sleep(5)
        page.wait_for_load_state("networkidle")
    else:
        print(f"  WARNING: メール/パスワード入力欄が見つかりません（URL: {page.url}）")
        # ページのHTMLの一部をデバッグ出力
        html_snippet = page.evaluate("() => document.body ? document.body.innerHTML.substring(0, 500) : 'no body'")
        print(f"  HTML snippet: {html_snippet}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "00_login_error.png"), full_page=True)

    print(f"  ログイン後URL: {page.url}")
    page.screenshot(path=str(SCREENSHOTS_DIR / "00_after_login.png"), full_page=True)


def extract_sidebar_links(page):
    """サイドバーからメニューリンクを抽出する"""
    print("[2/5] サイドバーメニュー抽出...")
    links = page.evaluate("""() => {
        const results = [];
        const sidebar = document.querySelector('nav, [class*="sidebar"], [class*="side-menu"], [id*="sidebar"], aside');
        const container = sidebar || document;
        const anchors = container.querySelectorAll('a[href]');
        anchors.forEach(a => {
            const href = a.getAttribute('href');
            const text = a.textContent.trim();
            if (href && text && !href.startsWith('javascript:') && !href.startsWith('#')) {
                results.push({text: text, href: href, classes: a.className});
            }
        });
        return results;
    }""")

    print(f"  サイドバーリンク数: {len(links)}")
    for link in links:
        print(f"    - {link['text']}: {link['href']}")

    return links


def extract_page_structure(page, name):
    """現在のページの構造を抽出する"""
    structure = page.evaluate("""() => {
        const result = {
            title: document.title,
            url: location.href,
            headings: [],
            buttons: [],
            inputs: [],
            tables: [],
            forms: [],
            tabs: [],
            links: [],
            selects: [],
            iframes: []
        };

        document.querySelectorAll('h1, h2, h3, h4').forEach(h => {
            result.headings.push({tag: h.tagName, text: h.textContent.trim().substring(0, 100)});
        });

        document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]').forEach(b => {
            const text = b.textContent?.trim() || b.value || b.getAttribute('aria-label') || '';
            if (text) result.buttons.push(text.substring(0, 80));
        });

        document.querySelectorAll('input, textarea').forEach(inp => {
            const type = inp.type || 'text';
            if (['hidden', 'submit', 'button'].includes(type)) return;
            result.inputs.push({
                type: type,
                name: inp.name || '',
                placeholder: inp.placeholder || '',
                label: ''
            });
        });

        document.querySelectorAll('label').forEach(label => {
            const forId = label.getAttribute('for');
            if (forId) {
                const inp = document.getElementById(forId);
                if (inp) {
                    const match = result.inputs.find(i => i.name === inp.name);
                    if (match) match.label = label.textContent.trim().substring(0, 50);
                }
            }
        });

        document.querySelectorAll('table').forEach(t => {
            const headers = [];
            t.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim().substring(0, 50)));
            const rowCount = t.querySelectorAll('tbody tr').length;
            result.tables.push({headers: headers, rowCount: rowCount});
        });

        document.querySelectorAll('form').forEach(f => {
            result.forms.push({
                action: f.action || '',
                method: f.method || '',
                id: f.id || '',
                inputCount: f.querySelectorAll('input, textarea, select').length
            });
        });

        document.querySelectorAll('[role="tab"], [class*="tab"][class*="active"], [class*="Tab"]').forEach(tab => {
            result.tabs.push(tab.textContent.trim().substring(0, 50));
        });

        document.querySelectorAll('select').forEach(sel => {
            const options = [];
            sel.querySelectorAll('option').forEach(opt => options.push(opt.textContent.trim().substring(0, 30)));
            result.selects.push({name: sel.name || '', options: options});
        });

        document.querySelectorAll('iframe').forEach(iframe => {
            result.iframes.push({
                name: iframe.name || '',
                src: iframe.src || '',
                id: iframe.id || ''
            });
        });

        return result;
    }""")

    return structure


def investigate_menu(page, url, name, index):
    """個別メニューページを調査する"""
    safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    screenshot_name = f"{index:02d}_{safe_name}.png"

    try:
        if url.startswith("http"):
            page.goto(url, timeout=30000)
        else:
            full_url = BASE_URL + (url if url.startswith("/") else "/" + url)
            page.goto(full_url, timeout=30000)

        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)

        page.screenshot(path=str(SCREENSHOTS_DIR / screenshot_name), full_page=True)

        structure = extract_page_structure(page, name)
        structure["screenshot"] = screenshot_name
        structure["menu_name"] = name

        print(f"  [{index}] {name}: {structure['url']}")
        print(f"      見出し: {len(structure['headings'])}, ボタン: {len(structure['buttons'])}, "
              f"入力: {len(structure['inputs'])}, テーブル: {len(structure['tables'])}")

        return structure

    except Exception as e:
        print(f"  [{index}] {name}: エラー - {e}")
        return {"menu_name": name, "url": url, "error": str(e), "screenshot": screenshot_name}


def probe_settings_urls(page, results):
    """設定系URLを探索する"""
    print("[4/5] 設定系URL探索...")
    settings_paths = [
        # 通常業務画面
        "/transactions", "/reports", "/requests",
        "/invoices", "/invoice_reports",
        "/expenses", "/expense_reports",
        "/receipts", "/receipt_reports",
        "/card_statements", "/card_transactions",
        "/applications", "/application_reports",
        # TOKIUMインボイス系
        "/auto_input_documents", "/national_tax_documents",
        "/suppliers", "/vendor_summaries",
        # 管理・分析系
        "/notifications", "/analyses",
        "/dashboard", "/home",
        # TOKIUM電子帳簿保存
        "/e_documents", "/e_doc_options",
        # 経費精算固有
        "/allowance_applications", "/transport_applications",
        "/mileage_applications",
        # 集計・出力
        "/accounting_data", "/fb_data",
        # ユーザー管理（追加）
        "/users/edit", "/preferences",
    ]

    settings_results = []
    for i, path in enumerate(settings_paths):
        try:
            full_url = BASE_URL + path
            response = page.goto(full_url, timeout=15000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            time.sleep(1)

            status = response.status if response else 0
            final_url = page.url

            if status == 200 and TOKIUM_ID_SUBDOMAIN in final_url:
                safe_name = path.strip("/").replace("/", "_")
                screenshot_name = f"settings_{i:02d}_{safe_name}.png"
                page.screenshot(path=str(SCREENSHOTS_DIR / screenshot_name), full_page=True)

                structure = extract_page_structure(page, f"settings:{path}")
                structure["screenshot"] = screenshot_name
                structure["probe_path"] = path
                settings_results.append(structure)
                print(f"  [OK] {path} -> {final_url}")
            else:
                print(f"  [--] {path} -> status={status}, redirect={final_url}")

        except Exception as e:
            print(f"  [ERR] {path} -> {e}")

    results["settings_probe"] = settings_results


def extract_header_info(page):
    """ヘッダーメニュー情報を抽出する"""
    print("  ヘッダー情報抽出...")
    header_info = page.evaluate("""() => {
        const result = {links: [], buttons: [], user_info: '', dropdowns: []};
        const header = document.querySelector('header, [class*="header"], [class*="Header"], [role="banner"]');
        if (!header) return result;

        header.querySelectorAll('a').forEach(a => {
            result.links.push({text: a.textContent.trim().substring(0, 50), href: a.getAttribute('href') || ''});
        });
        header.querySelectorAll('button, [role="button"]').forEach(b => {
            result.buttons.push(b.textContent.trim().substring(0, 50));
        });
        const userEl = header.querySelector('[class*="user"], [class*="User"], [class*="account"]');
        if (userEl) result.user_info = userEl.textContent.trim().substring(0, 100);

        return result;
    }""")

    print(f"  ヘッダーリンク: {len(header_info['links'])}, ボタン: {len(header_info['buttons'])}")
    return header_info


def main():
    setup_dirs()
    results = {"tenant": TOKIUM_ID_SUBDOMAIN, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "screens": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        login(page)

        results["header"] = extract_header_info(page)

        sidebar_links = extract_sidebar_links(page)
        results["sidebar_links"] = sidebar_links

        # 重複除去
        visited_urls = set()
        unique_links = []
        for link in sidebar_links:
            href = link["href"]
            if href not in visited_urls:
                visited_urls.add(href)
                unique_links.append(link)

        print(f"\n[3/5] 全メニュー巡回 ({len(unique_links)}件)...")
        for i, link in enumerate(unique_links, 1):
            structure = investigate_menu(page, link["href"], link["text"], i)
            results["screens"].append(structure)

        probe_settings_urls(page, results)

        print("\n[5/5] 結果保存...")
        output_file = OUTPUT_DIR / "screen_structure.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了! 結果: {output_file}")
        print(f"スクリーンショット: {SCREENSHOTS_DIR}")
        print(f"画面数: {len(results['screens'])}")

        browser.close()


if __name__ == "__main__":
    main()
