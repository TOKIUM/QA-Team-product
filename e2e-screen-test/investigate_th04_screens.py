"""
ikeda_n+th4でth-02サブドメイン経由ログインし、
初期テナント(マルチテナント検証用2)とtitkテナントの画面構成を調査
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
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots" / "th04"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def extract_page_detail(page):
    return page.evaluate("""() => {
        const result = {
            title: document.title, url: location.href,
            headings: [], buttons: [], inputs: [], tables: [],
            tabs: [], selects: [], labels: [],
            body_text: document.body ? document.body.innerText.substring(0, 2000) : ''
        };
        document.querySelectorAll('h1,h2,h3,h4').forEach(h => {
            result.headings.push({tag: h.tagName, text: h.textContent.trim().substring(0, 100)});
        });
        document.querySelectorAll('button, [role="button"]').forEach(b => {
            const text = b.textContent?.trim() || b.getAttribute('aria-label') || '';
            if (text && text.length < 100) result.buttons.push(text);
        });
        document.querySelectorAll('input:not([type="hidden"]), textarea').forEach(inp => {
            result.inputs.push({
                type: inp.type || 'text', name: inp.name || '',
                placeholder: inp.placeholder || '', disabled: inp.disabled
            });
        });
        document.querySelectorAll('table').forEach(t => {
            const headers = [];
            t.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim().substring(0, 50)));
            result.tables.push({headers, rowCount: t.querySelectorAll('tbody tr').length});
        });
        document.querySelectorAll('[role="tab"]').forEach(tab => {
            result.tabs.push(tab.textContent.trim().substring(0, 50));
        });
        document.querySelectorAll('select').forEach(sel => {
            const opts = [];
            sel.querySelectorAll('option').forEach(o => opts.push(o.textContent.trim().substring(0, 30)));
            result.selects.push({name: sel.name || '', options: opts});
        });
        document.querySelectorAll('label').forEach(l => {
            const text = l.textContent.trim();
            if (text && text.length < 100) result.labels.push(text);
        });
        return result;
    }""")


def extract_sidebar(page):
    return page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('a[href]').forEach(a => {
            const text = a.textContent.trim();
            const href = a.getAttribute('href');
            const rect = a.getBoundingClientRect();
            if (text && href && !href.startsWith('javascript:') && !href.startsWith('#')
                && rect.width > 0 && rect.x < 200) {
                items.push({text: text.substring(0, 80), href, x: Math.round(rect.x), y: Math.round(rect.y)});
            }
        });
        items.sort((a, b) => a.y - b.y);
        return items;
    }""")


def investigate_tenant(page, tenant_name, base_url, screenshots_prefix):
    """1テナント分の画面調査"""
    result = {"tenant_name": tenant_name, "base_url": base_url, "sidebar": [], "user_screens": [], "admin_screens": []}

    # ヘッダー情報
    result["header_info"] = page.evaluate("""() => {
        const result = {text: '', links: [], buttons: []};
        const header = document.querySelector('header, [class*="header"], [class*="Header"]');
        if (header) {
            result.text = header.innerText.trim().substring(0, 500);
        }
        return result;
    }""")
    print(f"  ヘッダー: {result['header_info']['text'][:150]}")

    # サイドバー
    sidebar = extract_sidebar(page)
    result["sidebar"] = sidebar
    print(f"  サイドバー: {len(sidebar)}項目")
    for s in sidebar:
        print(f"    {s['text']}: {s['href']}")

    # ユーザー画面巡回
    user_paths = []
    seen = set()
    for s in sidebar:
        h = s["href"]
        if h not in seen and not h.startswith("http"):
            seen.add(h)
            user_paths.append((h, s["text"]))

    extras = [
        ("/transactions", "経費一覧"), ("/requests", "申請一覧"),
        ("/analyses", "集計"), ("/notifications", "通知"),
        ("/invoices", "請求書"), ("/invoice_reports", "請求書レポート"),
        ("/auto_input_documents", "自動入力中書類"),
        ("/national_tax_documents", "国税関係書類"),
        ("/suppliers", "取引先"), ("/receipts", "領収書"),
        ("/e_documents", "電子帳簿"), ("/vendor_summaries", "仕入先集計"),
        ("/card_statements", "カード明細(新)"), ("/aggregation_results", "カード明細(旧)"),
    ]
    for path, name in extras:
        if path not in seen:
            seen.add(path)
            user_paths.append((path, name))

    for i, (path, name) in enumerate(user_paths, 1):
        url = base_url + path
        try:
            resp = page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(1.5)
            status = resp.status if resp else 0
            if status == 200 and "sign_in" not in page.url:
                safe = name.replace("/", "_").replace(" ", "_")
                fname = f"{screenshots_prefix}_user_{i:02d}_{safe}.png"
                page.screenshot(path=str(SCREENSHOTS_DIR / fname), full_page=True)
                detail = extract_page_detail(page)
                detail["menu_name"] = name
                detail["target_path"] = path
                detail["screenshot"] = fname
                result["user_screens"].append(detail)
                print(f"    [{i}] {name}: OK")
            else:
                print(f"    [{i}] {name}: skip (status={status})")
        except Exception as e:
            print(f"    [{i}] {name}: err ({e})")

    # 管理画面巡回
    admin_paths = [
        ("/members", "従業員"), ("/roles", "役職"), ("/departments", "部署"),
        ("/companions", "参加者"), ("/preferences/company_expense_accounts", "支払口座"),
        ("/request_types", "申請フォーム"), ("/approval_flows", "申請フロー"),
        ("/preferences/projects", "プロジェクト"),
        ("/preferences/export", "会計データ出力形式"),
        ("/preferences/tax_categories", "税区分"),
        ("/preferences/business_categories", "自動入力科目"),
        ("/preferences/reports", "経費入力・レポート"),
        ("/preferences/allowances", "日当・手当"),
        ("/preferences/alert_rules", "アラート"),
        ("/preferences/metadata", "付加情報"),
        ("/closing_dates", "締め日"),
        ("/e_doc_options", "電子帳簿保存法"),
        ("/preferences/list_options", "一覧表示"),
        ("/preferences/corporate_cards", "法人カード"),
        ("/preferences/security", "セキュリティ"),
        ("/generic_fields/data_sets", "汎用マスタ"),
    ]
    for i, (path, name) in enumerate(admin_paths, 1):
        url = base_url + path
        try:
            resp = page.goto(url, timeout=15000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            time.sleep(1)
            status = resp.status if resp else 0
            if status == 200 and "sign_in" not in page.url:
                safe = name.replace("/", "_").replace(" ", "_")
                fname = f"{screenshots_prefix}_admin_{i:02d}_{safe}.png"
                page.screenshot(path=str(SCREENSHOTS_DIR / fname), full_page=True)
                detail = extract_page_detail(page)
                detail["menu_name"] = name
                detail["target_path"] = path
                detail["screenshot"] = fname
                result["admin_screens"].append(detail)
                print(f"    [admin {i}] {name}: OK")
            else:
                print(f"    [admin {i}] {name}: skip (status={status})")
        except Exception as e:
            print(f"    [admin {i}] {name}: err ({e})")

    return result


def main():
    results = {
        "account": "ikeda_n+th4",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tenants": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        # ikeda_n+th4でth-02サブドメイン経由ログイン
        th3_acct = os.environ.get("TOKIUM_ID_EMAIL", "")
        th4_acct = th3_acct.replace("+th3", "+th4")
        pw = os.environ.get("TOKIUM_ID_PASSWORD", "")

        print(f"[1] th-02サブドメイン経由で {th4_acct} ログイン...")
        page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
        time.sleep(2)

        # サブドメイン入力
        btn = page.locator('button:has-text("サブドメインを入力")')
        if btn.count() > 0:
            btn.click()
            page.wait_for_url("**/subdomains/input**", timeout=10000)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

        page.locator('input[placeholder="サブドメイン"]').click()
        time.sleep(0.5)
        page.keyboard.press("Control+a")
        page.keyboard.type("th-02", delay=50)
        time.sleep(1)
        page.locator('button:has-text("送信")').click()
        time.sleep(3)
        try:
            page.wait_for_url("**th-02**", timeout=15000)
        except Exception:
            pass
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # ログイン
        if page.query_selector('input[type="email"]') and page.query_selector('input[type="password"]'):
            page.fill('input[type="email"]', th4_acct)
            page.fill('input[type="password"]', pw)
            login_btn = page.query_selector('#sign_in_form button[type="button"]')
            if not login_btn:
                login_btn = page.query_selector('button[type="submit"]')
            if login_btn:
                login_btn.click()
            time.sleep(5)
            page.wait_for_load_state("networkidle")

        print(f"  ログイン後URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "00_initial_login.png"), full_page=True)

        if "sign_in" in page.url:
            body = page.evaluate("() => document.body.innerText.substring(0, 300)")
            print(f"  ログイン失敗: {body[:200]}")
            browser.close()
            return

        base_url = "/".join(page.url.split("/")[:3])
        print(f"  ベースURL: {base_url}")

        # 初期テナント（マルチテナント検証用2）を調査
        print("\n[2] 初期テナント(マルチテナント検証用2)調査...")
        tenant1 = investigate_tenant(page, "マルチテナント検証用2", base_url, "t1")
        results["tenants"].append(tenant1)

        # テナント切替でtitkに切替
        print("\n[3] テナント切替...")
        # まずトップに戻る
        page.goto(base_url, wait_until="networkidle")
        time.sleep(2)

        # ヘッダーのユーザードロップダウンボタンをクリック
        dropdown_btn = page.locator('button:has-text("マルチテナント検証用")').first
        if not dropdown_btn.is_visible():
            dropdown_btn = page.locator('button:has-text("テナント切り替え")').first
        dropdown_btn.click()
        time.sleep(1)
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_dropdown.png"), full_page=True)

        # ドロップダウン内の「テナント名で検索」検索ボックスにtitkを入力
        search_box = page.locator('input[placeholder*="テナント名"]').first
        if not search_box.is_visible():
            search_box = page.locator('input[placeholder*="検索"]').first
        if search_box.is_visible():
            print("  テナント検索ボックス発見...")

            # 「QA」で検索してテナント候補を表示
            search_box.click()
            page.keyboard.type("QA", delay=100)
            time.sleep(2)
            page.screenshot(path=str(SCREENSHOTS_DIR / "02_tenant_search.png"), full_page=True)

            # react-autosuggest-suggestion をクリック
            suggestion = page.locator('li.react-autosuggest-suggestion').first
            if suggestion.count() > 0:
                text = suggestion.text_content()
                print(f"  テナント候補発見: {text}")
                suggestion.click()
                time.sleep(5)
                page.wait_for_load_state("networkidle")
                print(f"  切替後URL: {page.url}")
                page.screenshot(path=str(SCREENSHOTS_DIR / "03_tenant_switched.png"), full_page=True)

                base_url2 = "/".join(page.url.split("/")[:3])
                print(f"  切替後ベースURL: {base_url2}")

                print("\n[4] 切替先テナント調査...")
                tenant2 = investigate_tenant(page, text.strip(), base_url2, "t2")
                results["tenants"].append(tenant2)
            else:
                # tkti10で検索
                search_box.click()
                page.keyboard.press("Control+a")
                page.keyboard.type("tkti", delay=100)
                time.sleep(2)
                suggestion2 = page.locator('li.react-autosuggest-suggestion').first
                if suggestion2.count() > 0:
                    text = suggestion2.text_content()
                    print(f"  テナント候補発見: {text}")
                    suggestion2.click()
                    time.sleep(5)
                    page.wait_for_load_state("networkidle")
                    print(f"  切替後URL: {page.url}")
                    page.screenshot(path=str(SCREENSHOTS_DIR / "03_tenant_switched.png"), full_page=True)

                    base_url2 = "/".join(page.url.split("/")[:3])
                    print(f"  切替後ベースURL: {base_url2}")

                    print("\n[4] 切替先テナント調査...")
                    tenant2 = investigate_tenant(page, text.strip(), base_url2, "t2")
                    results["tenants"].append(tenant2)
                else:
                    print("  テナント候補が見つかりません")
        else:
            print("  テナント検索ボックスが見つかりません")
            # フォールバック: ページ内のすべてのinputを表示
            inputs = page.evaluate("""() => {
                const inputs = [];
                document.querySelectorAll('input').forEach(i => {
                    inputs.push({type: i.type, name: i.name, placeholder: i.placeholder, visible: i.offsetParent !== null});
                });
                return inputs;
            }""")
            for inp in inputs:
                print(f"    input: {inp}")

        # 保存
        out = OUTPUT_DIR / "th04_screen_structure.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了! テナント数: {len(results['tenants'])}")
        for t in results["tenants"]:
            print(f"  {t['tenant_name']}: user={len(t['user_screens'])} admin={len(t['admin_screens'])}")

        browser.close()


if __name__ == "__main__":
    main()
