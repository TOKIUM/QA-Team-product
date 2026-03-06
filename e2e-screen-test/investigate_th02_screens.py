"""
th-02（マルチテナント検証用1）の全画面構成を調査するスクリプト
TOKIUM IDでth-02にログイン後、サイドバー+管理画面を巡回
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
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots" / "th02"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def login(page):
    """TOKIUM IDでth-02にログイン"""
    print("[1] TOKIUM IDログイン -> th-02...")
    page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")
    time.sleep(2)

    btn = page.locator('button:has-text("サブドメインを入力")')
    if btn.count() > 0:
        btn.click()
        page.wait_for_url("**/subdomains/input**", timeout=10000)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

    page.locator('input[placeholder="サブドメイン"]').click()
    time.sleep(0.5)
    page.keyboard.press("Control+a")
    page.keyboard.type(SUBDOMAIN, delay=50)
    time.sleep(1)
    page.locator('button:has-text("送信")').click()
    time.sleep(3)

    try:
        page.wait_for_url(f"**{SUBDOMAIN}**", timeout=15000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    acct = os.environ.get("TOKIUM_ID_EMAIL", "")
    pw = os.environ.get("TOKIUM_ID_PASSWORD", "")
    if page.query_selector('input[type="email"]') and page.query_selector('input[type="password"]'):
        page.fill('input[type="email"]', acct)
        page.fill('input[type="password"]', pw)
        login_btn = page.query_selector('#sign_in_form button[type="button"]')
        if not login_btn:
            login_btn = page.query_selector('button[type="submit"]')
        if login_btn:
            login_btn.click()
        time.sleep(5)
        page.wait_for_load_state("networkidle")

    print(f"  ログイン後: {page.url}")
    page.screenshot(path=str(SCREENSHOTS_DIR / "00_after_login.png"), full_page=True)


def extract_page_detail(page):
    """ページの詳細構造を取得"""
    return page.evaluate("""() => {
        const result = {
            title: document.title,
            url: location.href,
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
    """サイドバーのメニュー構造を取得（左端200px以内の可視リンク）"""
    return page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('a[href]').forEach(a => {
            const text = a.textContent.trim();
            const href = a.getAttribute('href');
            const rect = a.getBoundingClientRect();
            if (text && href && !href.startsWith('javascript:') && !href.startsWith('#')
                && rect.width > 0 && rect.x < 200) {
                items.push({
                    text: text.substring(0, 80), href,
                    active: a.className.includes('active') || a.className.includes('current'),
                    x: Math.round(rect.x), y: Math.round(rect.y)
                });
            }
        });
        items.sort((a, b) => a.y - b.y);
        return items;
    }""")


def main():
    results = {
        "tenant": "マルチテナント検証用1",
        "subdomain": SUBDOMAIN,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sidebar": [], "user_screens": [], "admin_screens": [], "header_info": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = context.new_page()

        login(page)

        # ヘッダー情報
        print("\n[2] ヘッダー情報...")
        results["header_info"] = page.evaluate("""() => {
            const result = {text: '', links: [], buttons: []};
            const header = document.querySelector('header, [class*="header"], [class*="Header"]');
            if (header) {
                result.text = header.innerText.trim().substring(0, 500);
                header.querySelectorAll('a').forEach(a => {
                    result.links.push({text: a.textContent.trim().substring(0, 50), href: a.getAttribute('href') || ''});
                });
                header.querySelectorAll('button').forEach(b => {
                    result.buttons.push(b.textContent.trim().substring(0, 50));
                });
            }
            return result;
        }""")
        print(f"  {results['header_info']['text'][:200]}")

        # サイドバー
        print("\n[3] サイドバー...")
        sidebar = extract_sidebar(page)
        results["sidebar"] = sidebar
        for s in sidebar:
            mark = " *" if s.get("active") else ""
            print(f"  {s['text']}: {s['href']}{mark}")

        # ユーザー画面巡回
        print("\n[4] ユーザー画面巡回...")
        seen = set()
        user_paths = []
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
            ("/card_statements", "カード明細"), ("/aggregation_results", "カード明細(旧)"),
        ]
        for path, name in extras:
            if path not in seen:
                seen.add(path)
                user_paths.append((path, name))

        for i, (path, name) in enumerate(user_paths, 1):
            url = BASE + path
            print(f"  [{i}/{len(user_paths)}] {name} ({path})...")
            try:
                resp = page.goto(url, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(2)
                status = resp.status if resp else 0
                if status == 200 and SUBDOMAIN in page.url:
                    safe = name.replace("/", "_").replace(" ", "_")
                    page.screenshot(path=str(SCREENSHOTS_DIR / f"user_{i:02d}_{safe}.png"), full_page=True)
                    detail = extract_page_detail(page)
                    detail["menu_name"] = name
                    detail["target_path"] = path
                    detail["screenshot"] = f"user_{i:02d}_{safe}.png"
                    results["user_screens"].append(detail)
                    print(f"    OK: h={len(detail['headings'])} btn={len(detail['buttons'])} tbl={len(detail['tables'])}")
                else:
                    print(f"    skip: status={status}")
            except Exception as e:
                print(f"    err: {e}")

        # 管理画面巡回
        print("\n[5] 管理画面巡回...")
        admin_paths = [
            ("/members", "従業員"), ("/roles", "役職"), ("/departments", "部署"),
            ("/companions", "参加者"), ("/preferences/company_expense_accounts", "支払口座"),
            ("/request_types", "申請フォーム"), ("/approval_flows", "申請フロー"),
            ("/preferences/projects", "プロジェクト"), ("/preferences/foreign_currencies", "外貨"),
            ("/preferences/export", "会計データ出力形式"), ("/preferences/expense_categories", "科目"),
            ("/preferences/tax_categories", "税区分"), ("/preferences/business_categories", "自動入力科目"),
            ("/preferences/reports", "経費入力・レポート"), ("/preferences/allowances", "日当・手当"),
            ("/preferences/alert_rules", "アラート"), ("/preferences/ic_card_option", "IC乗車券"),
            ("/preferences/metadata", "付加情報"), ("/closing_dates", "締め日"),
            ("/preferences/analyses_config", "会計データ出力"), ("/e_doc_options", "電子帳簿保存法"),
            ("/preferences/list_options", "一覧表示"), ("/preferences/corporate_cards", "法人カード"),
            ("/journal_entries", "仕訳フォーマット"), ("/preferences/security", "セキュリティ"),
            ("/accounting_data_scheduled_exports", "会計データ定期出力"),
            ("/generic_fields/data_sets", "汎用マスタ"),
            ("/kernels/organizations/reorganizations/changes", "組織変更の予約"),
        ]
        for i, (path, name) in enumerate(admin_paths, 1):
            url = BASE + path
            print(f"  [{i}/{len(admin_paths)}] {name}...")
            try:
                resp = page.goto(url, timeout=15000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(1.5)
                status = resp.status if resp else 0
                if status == 200 and SUBDOMAIN in page.url:
                    safe = name.replace("/", "_").replace(" ", "_")
                    page.screenshot(path=str(SCREENSHOTS_DIR / f"admin_{i:02d}_{safe}.png"), full_page=True)
                    detail = extract_page_detail(page)
                    detail["menu_name"] = name
                    detail["target_path"] = path
                    detail["screenshot"] = f"admin_{i:02d}_{safe}.png"
                    results["admin_screens"].append(detail)
                    print(f"    OK")
                else:
                    print(f"    skip: status={status}")
            except Exception as e:
                print(f"    err: {e}")

        # 保存
        out = OUTPUT_DIR / "th02_screen_structure.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了! user={len(results['user_screens'])} admin={len(results['admin_screens'])}")
        browser.close()


if __name__ == "__main__":
    main()
