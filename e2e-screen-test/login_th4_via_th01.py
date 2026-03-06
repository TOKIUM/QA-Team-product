"""
ikeda_n+th4でth-01/th-02経由ログイン→テナント切替でtitkにアクセス
認証情報は.envから読み込み
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


def main():
    base_acct = os.environ.get("TOKIUM_ID_EMAIL", "")
    th4 = base_acct.replace("+th3", "+th4")
    pw = os.environ.get("TOKIUM_ID_PASSWORD", "")

    results = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "tenants": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = ctx.new_page()

        for sd in ["th-01", "th-02"]:
            print(f"\n=== {sd} で th4 ログイン試行 ===")
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
            page.keyboard.type(sd, delay=50)
            time.sleep(1)
            page.locator('button:has-text("送信")').click()
            time.sleep(3)
            try:
                page.wait_for_url(f"**{sd}**", timeout=15000)
            except Exception:
                pass
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            if page.query_selector('input[type="email"]') and page.query_selector('input[type="password"]'):
                page.fill('input[type="email"]', th4)
                page.fill('input[type="password"]', pw)
                login_btn = page.query_selector('#sign_in_form button[type="button"]')
                if not login_btn:
                    login_btn = page.query_selector('button[type="submit"]')
                if login_btn:
                    login_btn.click()
                time.sleep(5)
                page.wait_for_load_state("networkidle")

            print(f"  URL: {page.url}")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"try_{sd}.png"), full_page=True)

            if "sign_in" not in page.url:
                print(f"  ログイン成功! ({sd})")
                base = "/".join(page.url.split("/")[:3])
                header = page.evaluate("() => { const h = document.querySelector('header, [class*=\"header\"]'); return h ? h.innerText.trim().substring(0, 500) : ''; }")
                print(f"  ヘッダー: {header[:200]}")

                sidebar = extract_sidebar(page)
                print(f"  サイドバー: {len(sidebar)}項目")
                for s in sidebar:
                    print(f"    {s['text']}: {s['href']}")

                # テナント切替
                print(f"\n  テナント切替...")
                # ヘッダー右上のユーザー名/テナント名ドロップダウンをクリック
                # 「テナント切り替え」テキストを含むボタンを探す
                tenant_btn = page.locator('text=テナント切り替え').first
                if not tenant_btn.is_visible():
                    tenant_btn = page.locator('text=テナント切替').first
                if not tenant_btn.is_visible():
                    # マルチテナント検証用のテキストを含む要素
                    tenant_btn = page.locator('text=マルチテナント検証用').first
                tenant_btn.click()
                time.sleep(1)
                page.screenshot(path=str(SCREENSHOTS_DIR / f"try_{sd}_dropdown.png"), full_page=True)

                # ドロップダウンが開いたら「別のテナントに切替」をクリック
                switch = page.locator('a:has-text("別のテナントに切替")')
                if switch.count() > 0:
                    switch.first.dispatch_event("click")
                    time.sleep(3)
                    page.wait_for_load_state("networkidle")
                    print(f"  切替画面URL: {page.url}")
                    page.screenshot(path=str(SCREENSHOTS_DIR / f"try_{sd}_switch.png"), full_page=True)

                    body = page.evaluate("() => document.body.innerText.substring(0, 3000)")
                    for line in body.split("\n"):
                        line = line.strip()
                        if line and len(line) > 2 and len(line) < 100:
                            if any(k in line for k in ["テナント", "titk", "QA", "マルチ", "検証", "切替", "池田"]):
                                print(f"    {line}")

                    # titkを探してクリック
                    titk = page.locator('text=titk')
                    if titk.count() > 0:
                        print("  titk発見! クリック...")
                        titk.first.click()
                        time.sleep(5)
                        page.wait_for_load_state("networkidle")
                        print(f"  titk URL: {page.url}")
                        page.screenshot(path=str(SCREENSHOTS_DIR / "titk_switched.png"), full_page=True)

                        base2 = "/".join(page.url.split("/")[:3])
                        sidebar2 = extract_sidebar(page)
                        print(f"  titkサイドバー: {len(sidebar2)}項目")
                        for s in sidebar2:
                            print(f"    {s['text']}: {s['href']}")

                        tenant = {"subdomain": sd, "tenant": "titk", "base": base2, "sidebar": sidebar2, "user_screens": []}
                        seen = set()
                        paths = []
                        for s in sidebar2:
                            h = s["href"]
                            if h not in seen and not h.startswith("http"):
                                seen.add(h)
                                paths.append((h, s["text"]))
                        extras = [
                            ("/invoices", "請求書"), ("/auto_input_documents", "自動入力中書類"),
                            ("/national_tax_documents", "国税関係書類"),
                            ("/suppliers", "取引先"), ("/e_documents", "電子帳簿"),
                            ("/vendor_summaries", "仕入先集計"), ("/receipts", "領収書"),
                            ("/transactions", "経費"), ("/requests", "申請"),
                            ("/analyses", "集計"), ("/notifications", "通知"),
                        ]
                        for path, name in extras:
                            if path not in seen:
                                seen.add(path)
                                paths.append((path, name))

                        for i, (path, name) in enumerate(paths, 1):
                            url = base2 + path
                            try:
                                resp = page.goto(url, timeout=15000)
                                page.wait_for_load_state("networkidle", timeout=10000)
                                time.sleep(1.5)
                                status = resp.status if resp else 0
                                if status == 200 and "sign_in" not in page.url:
                                    safe = name.replace("/", "_")
                                    fname = f"titk_user_{i:02d}_{safe}.png"
                                    page.screenshot(path=str(SCREENSHOTS_DIR / fname), full_page=True)
                                    detail = extract_page_detail(page)
                                    detail["menu_name"] = name
                                    detail["target_path"] = path
                                    detail["screenshot"] = fname
                                    tenant["user_screens"].append(detail)
                                    print(f"      [{i}] {name}: OK")
                                elif status == 404:
                                    print(f"      [{i}] {name}: 404")
                                else:
                                    print(f"      [{i}] {name}: skip")
                            except Exception:
                                print(f"      [{i}] {name}: err")

                        results["tenants"].append(tenant)
                    else:
                        print("  titk不在")
                break
            else:
                err = page.evaluate("() => document.body.innerText.substring(0, 200)")
                print(f"  失敗: {err[:100]}")

        out = OUTPUT_DIR / "titk_screen_structure.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了!")
        browser.close()


if __name__ == "__main__":
    main()
