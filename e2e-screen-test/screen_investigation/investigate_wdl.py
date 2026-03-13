"""WDL (WEB Download Site) screen investigation script"""
import json
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# .envから認証情報を読み込み
load_dotenv(Path(__file__).parent.parent / "ログイン" / ".env")

BASE_URL = os.environ.get("WDL_BASE_URL", "https://invoicing-wdl-staging.keihi.com")
SCREENSHOT_DIR = Path(__file__).parent / "screenshots" / "wdl"
OUTPUT_JSON = Path(__file__).parent / "wdl_screen_structure.json"


def take_screenshot(page, name):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path.name}")
    return str(path.relative_to(Path(__file__).parent))


def get_page_structure(page):
    return page.evaluate("""() => {
        const result = {
            title: document.title,
            url: location.href,
            headings: [],
            nav_links: [],
            buttons: [],
            forms: [],
            tables: []
        };
        document.querySelectorAll('h1, h2, h3, h4').forEach(h => {
            result.headings.push({tag: h.tagName, text: h.textContent.trim().substring(0, 100)});
        });
        document.querySelectorAll('nav a, .nav a, .sidebar a, .menu a, [class*="nav"] a, [class*="menu"] a, [class*="sidebar"] a, header a').forEach(a => {
            const text = a.textContent.trim();
            const href = a.getAttribute('href');
            if (text && href && !href.startsWith('javascript:')) {
                result.nav_links.push({text: text.substring(0, 80), href: href});
            }
        });
        document.querySelectorAll('button, input[type="submit"], a.btn, [class*="btn"]').forEach(b => {
            const text = b.textContent.trim();
            if (text) result.buttons.push(text.substring(0, 80));
        });
        document.querySelectorAll('form').forEach(f => {
            const inputs = [];
            f.querySelectorAll('input, select, textarea').forEach(inp => {
                inputs.push({
                    type: inp.type || inp.tagName.toLowerCase(),
                    name: inp.name || '',
                    placeholder: inp.placeholder || ''
                });
            });
            result.forms.push({action: f.action, method: f.method, inputs: inputs});
        });
        document.querySelectorAll('table').forEach(t => {
            const headers = [];
            t.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim().substring(0, 50)));
            result.tables.push({headers: headers, row_count: t.querySelectorAll('tbody tr').length});
        });
        return result;
    }""")


def login(page, cred_email, cred_pw):
    print("=== WDL Login ===")
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    take_screenshot(page, "00_login_page")
    print(f"  Current URL: {page.url}")

    email_input = page.query_selector(
        'input[type="email"], input[name="email"], input[name*="mail"], '
        'input[id*="email"], input[id*="mail"]'
    )
    if not email_input:
        email_input = page.query_selector('input[type="text"]')
    pw_input = page.query_selector('input[type="password"]')

    if email_input and pw_input:
        print("  Login form found - filling...")
        email_input.fill(cred_email)
        pw_input.fill(cred_pw)
        take_screenshot(page, "00_login_filled")

        login_btn = page.query_selector(
            'button[type="submit"], input[type="submit"]'
        )
        if login_btn:
            login_btn.click()
        else:
            page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        take_screenshot(page, "00_after_login")
        print(f"  After login URL: {page.url}")
    else:
        print("  Login form not found. Checking page elements...")
        inputs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input, button')).map(el => ({
                tag: el.tagName, type: el.type, name: el.name, id: el.id,
                placeholder: el.placeholder, text: el.textContent?.trim()?.substring(0, 50)
            }));
        }""")
        print(f"  Elements: {json.dumps(inputs, ensure_ascii=False, indent=2)}")
        take_screenshot(page, "00_login_debug")


def discover_navigation(page):
    return page.evaluate("""() => {
        const links = new Map();
        const selectors = [
            'nav a', '.nav a', '.sidebar a', '.menu a',
            '[class*="nav"] a', '[class*="menu"] a', '[class*="sidebar"] a',
            'header a', '.header a', '[role="navigation"] a', 'aside a'
        ];
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(a => {
                const text = a.textContent.trim();
                const href = a.getAttribute('href');
                if (text && href && !href.startsWith('javascript:') && !href.startsWith('#')
                    && !links.has(href) && href !== '/') {
                    links.set(href, {text: text.substring(0, 80), href: href});
                }
            });
        });
        return Array.from(links.values());
    }""")


def investigate_page(page, name, url):
    print(f"\n--- {name} ({url}) ---")
    try:
        if not url.startswith("http"):
            url = BASE_URL + url
        page.goto(url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        structure = get_page_structure(page)
        screenshot = take_screenshot(page, name)
        return {
            "name": name, "url": page.url, "original_url": url,
            "screenshot": screenshot, "structure": structure,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"name": name, "url": url, "error": str(e), "timestamp": datetime.now().isoformat()}


def main():
    cred_email = os.environ["WDL_EMAIL"]
    cred_pw = os.environ["WDL_PW"]

    print("=" * 60)
    print("WDL (WEB Download Site) Screen Investigation")
    print(f"URL: {BASE_URL}")
    print("=" * 60)

    results = {
        "investigation_date": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "environment": "staging",
        "product": "WDL (WEB Download Site)",
        "screens": [],
        "navigation": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="ja-JP"
        )
        page = context.new_page()

        login(page, cred_email, cred_pw)

        top_structure = get_page_structure(page)
        results["screens"].append({
            "name": "top_after_login", "url": page.url,
            "screenshot": "screenshots/wdl/00_after_login.png",
            "structure": top_structure,
            "timestamp": datetime.now().isoformat()
        })

        nav_links = discover_navigation(page)
        results["navigation"] = nav_links
        print(f"\n=== Navigation links found: {len(nav_links)} ===")
        for link in nav_links:
            print(f"  {link['text']} -> {link['href']}")

        visited = set()
        for i, link in enumerate(nav_links, 1):
            href = link["href"]
            if href in visited:
                continue
            visited.add(href)
            safe_name = f"{i:02d}_{link['text'][:20].replace('/', '_').replace(' ', '_')}"
            screen_data = investigate_page(page, safe_name, href)
            results["screens"].append(screen_data)

            if "error" not in screen_data:
                sub_links = discover_navigation(page)
                new_links = [
                    l for l in sub_links
                    if l["href"] not in visited
                    and l["href"] not in [nl["href"] for nl in nav_links]
                ]
                if new_links:
                    print(f"  Sub-links found: {len(new_links)}")
                    for sl in new_links[:10]:
                        if sl["href"] not in visited:
                            visited.add(sl["href"])
                            sub_name = (
                                f"{i:02d}_{len(results['screens']):02d}_"
                                f"{sl['text'][:15].replace('/', '_').replace(' ', '_')}"
                            )
                            sub_data = investigate_page(page, sub_name, sl["href"])
                            results["screens"].append(sub_data)

        print(f"\n=== Investigation complete ===")
        print(f"  Screens: {len(results['screens'])}")
        print(f"  Navigation: {len(results['navigation'])}")

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  Saved: {OUTPUT_JSON}")

        browser.close()


if __name__ == "__main__":
    main()
