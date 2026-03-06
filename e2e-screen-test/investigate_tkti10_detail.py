"""
tkti10テナントのインボイス画面を深掘り調査:
- 各画面のサブタブ
- 詳細画面（レコードクリック先）
- 新規作成フォーム
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
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots" / "tkti10_detail"
OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def extract_detail(page):
    return page.evaluate("""() => {
        const r = {
            title: document.title, url: location.href,
            headings: [], buttons: [], inputs: [], tables: [],
            tabs: [], selects: [], labels: [], links: [],
            body_text: document.body ? document.body.innerText.substring(0, 3000) : ''
        };
        document.querySelectorAll('h1,h2,h3,h4').forEach(h => {
            r.headings.push({tag: h.tagName, text: h.textContent.trim().substring(0, 100)});
        });
        document.querySelectorAll('button, [role="button"]').forEach(b => {
            const t = b.textContent?.trim() || b.getAttribute('aria-label') || '';
            if (t && t.length < 100) r.buttons.push(t);
        });
        document.querySelectorAll('input:not([type="hidden"]), textarea').forEach(inp => {
            r.inputs.push({
                type: inp.type || 'text', name: inp.name || '',
                placeholder: inp.placeholder || '', id: inp.id || '',
                disabled: inp.disabled
            });
        });
        document.querySelectorAll('table').forEach(t => {
            const h = [];
            t.querySelectorAll('th').forEach(th => h.push(th.textContent.trim().substring(0, 50)));
            r.tables.push({headers: h, rowCount: t.querySelectorAll('tbody tr').length});
        });
        document.querySelectorAll('[role="tab"], .tab, [class*="tab-item"], [class*="TabItem"]').forEach(t => {
            r.tabs.push(t.textContent.trim().substring(0, 80));
        });
        document.querySelectorAll('select').forEach(s => {
            const o = [];
            s.querySelectorAll('option').forEach(op => o.push(op.textContent.trim().substring(0, 50)));
            r.selects.push({name: s.name || '', id: s.id || '', options: o});
        });
        document.querySelectorAll('label').forEach(l => {
            const t = l.textContent.trim();
            if (t && t.length < 100) r.labels.push(t);
        });
        // メインコンテンツ内のリンクも取得
        const main = document.querySelector('main, [class*="content"], [class*="Content"]') || document.body;
        main.querySelectorAll('a[href]').forEach(a => {
            const text = a.textContent.trim();
            const href = a.getAttribute('href');
            if (text && href && text.length < 100 && !href.startsWith('javascript:')) {
                r.links.push({text: text.substring(0, 80), href});
            }
        });
        return r;
    }""")


def login_to_tkti10(page):
    """th-02経由でth4ログイン→テナント切替でtkti10に入る"""
    th3 = os.environ.get("TOKIUM_ID_EMAIL", "")
    th4 = th3.replace("+th3", "+th4")
    pw = os.environ.get("TOKIUM_ID_PASSWORD", "")

    print("[Login] th-02経由でth4ログイン...")
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

    # ログイン後、トップページに遷移して確認
    current_base = "/".join(page.url.split("/")[:3])
    page.goto(current_base + "/transactions", wait_until="networkidle")
    time.sleep(2)

    if "sign_in" in page.url:
        print("  ログイン失敗")
        return False

    print(f"  ログイン成功: {page.url}")

    # テナント切替
    print("[Login] tkti10に切替...")
    page.goto("/".join(page.url.split("/")[:3]), wait_until="networkidle")
    time.sleep(2)

    dropdown = page.locator('button:has-text("マルチテナント検証用")').first
    if not dropdown.is_visible():
        dropdown = page.locator('button:has-text("テナント切り替え")').first
    dropdown.click()
    time.sleep(1)

    search = page.locator('input[placeholder*="テナント名"]').first
    if search.is_visible():
        search.click()
        page.keyboard.type("QA", delay=100)
        time.sleep(2)
        suggestion = page.locator('li.react-autosuggest-suggestion').first
        if suggestion.count() > 0:
            suggestion.click()
            time.sleep(5)
            page.wait_for_load_state("networkidle")
            # tkti10はサブドメインなしテナントなのでdev.keihi.comに遷移
            # まだth-02ドメインにいる場合はdev.keihi.comに移動
            if "th-02" in page.url:
                page.goto("https://dev.keihi.com/transactions", wait_until="networkidle")
                time.sleep(3)
            print(f"  tkti10切替成功: {page.url}")
            return True

    print("  テナント切替失敗")
    return False


def investigate_sub_tabs(page, base_url, results):
    """取引先画面のサブタブ調査"""
    print("\n[A] 取引先画面のサブタブ調査...")
    page.goto(base_url + "/payment_requests/suppliers", wait_until="networkidle")
    time.sleep(2)

    # body_textからサブタブを特定
    body = page.evaluate("() => document.body.innerText.substring(0, 1000)")
    print(f"  取引先body冒頭:")
    for line in body.split("\n")[:20]:
        line = line.strip()
        if line:
            print(f"    {line}")

    page.screenshot(path=str(SCREENSHOTS_DIR / "suppliers_list.png"), full_page=True)

    # 「定期支払設定」タブがあるか
    periodic = page.locator('text=定期支払設定')
    if periodic.count() > 0:
        print("  「定期支払設定」発見、クリック...")
        periodic.first.click()
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "suppliers_periodic.png"), full_page=True)
        detail = extract_detail(page)
        detail["sub_tab"] = "定期支払設定"
        results["sub_tabs"]["suppliers_periodic"] = detail
        print(f"  URL: {page.url}")

    # 取引先設定タブ
    settings = page.locator('text=取引先設定')
    if settings.count() > 0:
        print("  「取引先設定」発見、クリック...")
        settings.first.click()
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "suppliers_settings.png"), full_page=True)
        detail = extract_detail(page)
        detail["sub_tab"] = "取引先設定"
        results["sub_tabs"]["suppliers_settings"] = detail


def investigate_detail_pages(page, base_url, results):
    """各画面で最初のレコードをクリックして詳細画面を調査"""

    screens = [
        ("/payment_requests/reports", "請求書", "invoice"),
        ("/payment_requests/waiting_worker_document_inputs", "自動入力中書類", "auto_input"),
        ("/payment_requests/national_tax_documents", "国税関係書類", "national_tax"),
        ("/payment_requests/suppliers", "取引先", "suppliers"),
    ]

    for path, name, key in screens:
        print(f"\n[B] {name}の詳細画面調査...")
        page.goto(base_url + path, wait_until="networkidle")
        time.sleep(2)

        # テーブルの最初のリンクをクリック
        # tbodyの最初の行のリンクを探す
        first_row_link = page.evaluate("""() => {
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const rows = table.querySelectorAll('tbody tr');
                if (rows.length > 0) {
                    const link = rows[0].querySelector('a[href]');
                    if (link) return {href: link.getAttribute('href'), text: link.textContent.trim().substring(0, 50)};
                }
            }
            return null;
        }""")

        if first_row_link:
            print(f"  最初のレコードリンク: {first_row_link}")
            href = first_row_link["href"]
            if not href.startswith("http"):
                href = base_url + href
            page.goto(href, wait_until="networkidle")
            time.sleep(2)
            page.screenshot(path=str(SCREENSHOTS_DIR / f"detail_{key}.png"), full_page=True)
            detail = extract_detail(page)
            results["detail_pages"][key] = detail
            print(f"  詳細URL: {page.url}")
            print(f"  ボタン: {detail['buttons'][:10]}")
            print(f"  ラベル: {detail['labels'][:15]}")
            print(f"  テーブル: {len(detail['tables'])}件")
        else:
            # テーブル行自体をクリック
            row = page.locator('table tbody tr').first
            if row.count() > 0:
                print("  行クリックで詳細を開く...")
                row.click()
                time.sleep(2)
                page.wait_for_load_state("networkidle")
                page.screenshot(path=str(SCREENSHOTS_DIR / f"detail_{key}.png"), full_page=True)
                detail = extract_detail(page)
                results["detail_pages"][key] = detail
                print(f"  詳細URL: {page.url}")
            else:
                print(f"  レコードなし（0行）")


def investigate_create_forms(page, base_url, results):
    """新規作成フォームの調査"""

    forms = [
        ("/payment_requests/reports", "請求書を登録する", "invoice_create"),
        ("/payment_requests/national_tax_documents", "国税関係書類を登録する", "national_tax_create"),
        ("/payment_requests/suppliers", "新規取引先追加", "supplier_create"),
    ]

    for path, btn_text, key in forms:
        print(f"\n[C] {btn_text}フォーム調査...")
        page.goto(base_url + path, wait_until="networkidle")
        time.sleep(2)

        create_btn = page.locator(f'button:has-text("{btn_text}")').first
        if not create_btn.is_visible():
            create_btn = page.locator(f'a:has-text("{btn_text}")').first
        if create_btn.is_visible():
            create_btn.click()
            time.sleep(3)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"create_{key}.png"), full_page=True)
            detail = extract_detail(page)
            results["create_forms"][key] = detail
            print(f"  URL: {page.url}")
            print(f"  入力: {len(detail['inputs'])}件")
            print(f"  ラベル: {detail['labels'][:20]}")
            print(f"  セレクト: {len(detail['selects'])}件")
            for s in detail["selects"]:
                print(f"    {s['name']}: {s['options'][:5]}")

            # 閉じる（戻る）
            page.go_back()
            time.sleep(1)
        else:
            print(f"  ボタン「{btn_text}」が見つかりません")


def investigate_aggregation_detail(page, base_url, results):
    """集計画面の深掘り"""
    print("\n[D] 集計画面の深掘り...")
    page.goto(base_url + "/payment_requests/analyses", wait_until="networkidle")
    time.sleep(2)

    # 集計履歴のセクション
    detail = extract_detail(page)
    results["aggregation_detail"] = {
        "list_page": detail
    }

    page.screenshot(path=str(SCREENSHOTS_DIR / "aggregation_list.png"), full_page=True)

    # 集計履歴の最初のレコードをクリック
    first_link = page.evaluate("""() => {
        const tables = document.querySelectorAll('table');
        for (const table of tables) {
            const rows = table.querySelectorAll('tbody tr');
            if (rows.length > 0) {
                const link = rows[0].querySelector('a[href]');
                if (link) return link.getAttribute('href');
            }
        }
        return null;
    }""")

    if first_link:
        href = first_link if first_link.startswith("http") else base_url + first_link
        page.goto(href, wait_until="networkidle")
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "aggregation_detail.png"), full_page=True)
        detail2 = extract_detail(page)
        results["aggregation_detail"]["detail_page"] = detail2
        print(f"  集計詳細URL: {page.url}")
        print(f"  ボタン: {detail2['buttons'][:10]}")


def main():
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tenant": "TOKIUM QA テナント切替 tkti10",
        "sub_tabs": {},
        "detail_pages": {},
        "create_forms": {},
        "aggregation_detail": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ja-JP")
        page = ctx.new_page()

        if not login_to_tkti10(page):
            browser.close()
            return

        base_url = "/".join(page.url.split("/")[:3])

        investigate_sub_tabs(page, base_url, results)
        investigate_detail_pages(page, base_url, results)
        investigate_create_forms(page, base_url, results)
        investigate_aggregation_detail(page, base_url, results)

        # 保存
        out = OUTPUT_DIR / "tkti10_detail_structure.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了!")
        print(f"  サブタブ: {len(results['sub_tabs'])}件")
        print(f"  詳細画面: {len(results['detail_pages'])}件")
        print(f"  作成フォーム: {len(results['create_forms'])}件")
        browser.close()


if __name__ == "__main__":
    main()
