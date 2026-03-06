"""
ikeda_n+th4でtitkサブドメイン経由ログインし画面構成を調査
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
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots" / "titk"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def extract_page_detail(page):
    return page.evaluate("""() => {
        const r = {
            title: document.title, url: location.href,
            headings: [], buttons: [], inputs: [], tables: [],
            tabs: [], selects: [], labels: [],
            body_text: document.body ? document.body.innerText.substring(0, 2000) : ''
        };
        document.querySelectorAll('h1,h2,h3,h4').forEach(h => {
            r.headings.push({tag: h.tagName, text: h.textContent.trim().substring(0, 100)});
        });
        document.querySelectorAll('button, [role="button"]').forEach(b => {
            const t = b.textContent?.trim() || b.getAttribute('aria-label') || '';
            if (t && t.length < 100) r.buttons.push(t);
        });
        document.querySelectorAll('input:not([type="hidden"]), textarea').forEach(inp => {
            r.inputs.push({type: inp.type||'text', name: inp.name||'', placeholder: inp.placeholder||'', disabled: inp.disabled});
        });
        document.querySelectorAll('table').forEach(t => {
            const h = []; t.querySelectorAll('th').forEach(th => h.push(th.textContent.trim().substring(0, 50)));
            r.tables.push({headers: h, rowCount: t.querySelectorAll('tbody tr').length});
        });
        document.querySelectorAll('[role="tab"]').forEach(t => r.tabs.push(t.textContent.trim().substring(0, 50)));
        document.querySelectorAll('select').forEach(s => {
            const o = []; s.querySelectorAll('option').forEach(op => o.push(op.textContent.trim().substring(0, 30)));
            r.selects.push({name: s.name||'', options: o});
        });
        document.querySelectorAll('label').forEach(l => {
            const t = l.textContent.trim(); if (t && t.length < 100) r.labels.push(t);
        });
        return r;
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


def login_subdomain(page, subdomain, acct, pw):
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
    page.keyboard.type(subdomain, delay=50)
    time.sleep(1)
    page.locator('button:has-text("送信")').click()
    time.sleep(3)
    try:
        page.wait_for_url(f"**{subdomain}**", timeout=15000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(2)
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


def main():
    results = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "tenants": []}

    th3 = os.environ.get("TOKIUM_ID_EMAIL", "")
    th4 = th3.replace("+th3", "+th4")
    pw = os.environ.get("TOKIUM_ID_PASSWORD", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = ctx.new_page()

        print(f"[1] titk でログイン ({th4})...")
        login_subdomain(page, "titk", th4, pw)
        print(f"  URL: {page.url}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "00_login.png"), full_page=True)

        if "sign_in" in page.url:
            body = page.evaluate("() => document.body.innerText.substring(0, 300)")
            print(f"  ログイン失敗: {body[:200]}")
            print("  titkが無効。他のサブドメインを試行...")
            browser.close()
            return

        base = "/".join(page.url.split("/")[:3])
        print(f"  ベースURL: {base}")

        header = page.evaluate("""() => {
            const h = document.querySelector('header, [class*="header"]');
            return h ? h.innerText.trim().substring(0, 500) : '';
        }""")
        print(f"  ヘッダー: {header[:200]}")

        sidebar = extract_sidebar(page)
        print(f"\n[2] サイドバー: {len(sidebar)}項目")
        for s in sidebar:
            print(f"    {s['text']}: {s['href']}")

        tenant = {"subdomain": "titk", "base_url": base, "header": header, "sidebar": sidebar, "user_screens": [], "admin_screens": []}

        # ユーザー画面
        print(f"\n[3] ユーザー画面巡回...")
        seen = set()
        paths = []
        for s in sidebar:
            h = s["href"]
            if h not in seen and not h.startswith("http"):
                seen.add(h)
                paths.append((h, s["text"]))
        extras = [
            ("/transactions", "経費"), ("/requests", "申請"),
            ("/analyses", "集計"), ("/notifications", "通知"),
            ("/invoices", "請求書"), ("/invoice_reports", "請求書レポート"),
            ("/auto_input_documents", "自動入力中書類"),
            ("/national_tax_documents", "国税関係書類"),
            ("/suppliers", "取引先"), ("/receipts", "領収書"),
            ("/e_documents", "電子帳簿"), ("/vendor_summaries", "仕入先集計"),
            ("/card_statements", "カード明細"), ("/aggregation_results", "カード明細旧"),
        ]
        for path, name in extras:
            if path not in seen:
                seen.add(path)
                paths.append((path, name))

        for i, (path, name) in enumerate(paths, 1):
            url = base + path
            try:
                resp = page.goto(url, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(1.5)
                status = resp.status if resp else 0
                if status == 200 and "sign_in" not in page.url:
                    safe = name.replace("/", "_").replace(" ", "_")
                    fname = f"user_{i:02d}_{safe}.png"
                    page.screenshot(path=str(SCREENSHOTS_DIR / fname), full_page=True)
                    detail = extract_page_detail(page)
                    detail["menu_name"] = name
                    detail["target_path"] = path
                    detail["screenshot"] = fname
                    tenant["user_screens"].append(detail)
                    print(f"    [{i}] {name}: OK")
                elif status == 404:
                    print(f"    [{i}] {name}: 404")
                else:
                    print(f"    [{i}] {name}: skip")
            except Exception as e:
                print(f"    [{i}] {name}: err")

        # 管理画面
        print(f"\n[4] 管理画面...")
        admins = [
            ("/members", "従業員"), ("/roles", "役職"), ("/departments", "部署"),
            ("/request_types", "申請フォーム"), ("/approval_flows", "申請フロー"),
            ("/preferences/export", "会計データ出力形式"),
            ("/preferences/tax_categories", "税区分"),
            ("/e_doc_options", "電子帳簿保存法"),
            ("/preferences/security", "セキュリティ"),
            ("/preferences/security/subdomain", "サブドメイン"),
        ]
        for i, (path, name) in enumerate(admins, 1):
            url = base + path
            try:
                resp = page.goto(url, timeout=15000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(1)
                status = resp.status if resp else 0
                if status == 200 and "sign_in" not in page.url:
                    safe = name.replace("/", "_").replace(" ", "_")
                    fname = f"admin_{i:02d}_{safe}.png"
                    page.screenshot(path=str(SCREENSHOTS_DIR / fname), full_page=True)
                    detail = extract_page_detail(page)
                    detail["menu_name"] = name
                    detail["target_path"] = path
                    detail["screenshot"] = fname
                    tenant["admin_screens"].append(detail)
                    print(f"    [{i}] {name}: OK")
                else:
                    print(f"    [{i}] {name}: skip (s={status})")
            except Exception as e:
                print(f"    [{i}] {name}: err")

        results["tenants"].append(tenant)

        out = OUTPUT_DIR / "titk_screen_structure.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了! user={len(tenant['user_screens'])} admin={len(tenant['admin_screens'])}")
        browser.close()


if __name__ == "__main__":
    main()
