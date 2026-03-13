"""WDL user settings screen investigation script.

Explores whether a user settings/profile page exists on the WDL staging site.
"""
import time
import os
from dotenv import load_dotenv
from pathlib import Path
n# .envから認証情報を読み込み
load_dotenv(Path(__file__).parent.parent / "ログイン" / ".env")
from playwright.sync_api import sync_playwright

BASE_URL = "https://invoicing-wdl-staging.keihi.com"
EMAIL = os.environ.get("WDL_EMAIL", "")
PASSWORD = os.environ.get("WDL_PW", "")
SCREENSHOT_DIR = Path(__file__).parent / "screenshots" / "wdl_settings"


def screenshot(page, name):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [Screenshot] {path.name}")


def login(page):
    """Login to WDL. SPA: URL may stay /login after success."""
    print("=" * 60)
    print("STEP 0: Login")
    print("=" * 60)
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    time.sleep(2)
    screenshot(page, "00_login_page")

    # Use exact selectors from proven conftest.py
    email_input = page.locator('input[name="email"]').first
    pw_input = page.locator('input[type="password"]').first

    email_input.fill(EMAIL)
    pw_input.fill(PASSWORD)
    screenshot(page, "00b_filled_form")
    page.locator('button[type="submit"]').first.click()

    # Wait for SPA to load post-login content
    time.sleep(5)
    page.wait_for_load_state("networkidle")
    screenshot(page, "00c_after_submit")

    # Check page content after submit
    body_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 1000) : ''")
    print(f"  Body after submit: {body_text[:200]}")

    # WDL SPA: confirm login by waiting for nav link to /invoices
    nav = page.locator('a[href="/invoices"]')
    try:
        nav.wait_for(state="visible", timeout=15000)
        print("  Login confirmed: a[href='/invoices'] visible")
    except Exception as e:
        print(f"  WARNING: nav link not found, trying to continue anyway: {e}")
        # Check all links on page
        all_links = page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => ({text: a.textContent.trim(), href: a.getAttribute('href')}))")
        print(f"  Links on page: {all_links}")

    # Navigate explicitly to /invoices
    page.goto(f"{BASE_URL}/invoices", wait_until="networkidle")
    time.sleep(2)
    screenshot(page, "01_after_login")
    print(f"  Current URL: {page.url}")
    print(f"  Title: {page.title()}")


def step1_investigate_header(page):
    """Investigate header area for user name, avatar, dropdown."""
    print("\n" + "=" * 60)
    print("STEP 1: Header area investigation")
    print("=" * 60)

    header_info = page.evaluate("""() => {
        const result = {
            header_html: '',
            user_elements: [],
            clickable_in_header: [],
            dropdowns: []
        };

        // Get header area
        const headerSel = 'header, .header, nav, .navbar, [class*="header"], [class*="Header"], [class*="nav-bar"], [class*="topbar"]';
        const headers = document.querySelectorAll(headerSel);
        headers.forEach((h, i) => {
            result.header_html += `[Header ${i}] ` + h.outerHTML.substring(0, 2000) + '\\n';
        });

        // Look for user-related elements
        const userSelectors = [
            '[class*="user"]', '[class*="User"]',
            '[class*="avatar"]', '[class*="Avatar"]',
            '[class*="account"]', '[class*="Account"]',
            '[class*="profile"]', '[class*="Profile"]',
            '[class*="dropdown"]', '[class*="Dropdown"]',
            '[class*="menu"]', '[class*="Menu"]',
            'img[src*="avatar"]', 'img[src*="user"]',
            '[data-testid*="user"]', '[data-testid*="avatar"]'
        ];
        userSelectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                result.user_elements.push({
                    selector: sel,
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 200),
                    classes: el.className.toString().substring(0, 200),
                    id: el.id || ''
                });
            });
        });

        // Clickable elements in header
        headers.forEach(h => {
            h.querySelectorAll('a, button, [role="button"], [onclick]').forEach(el => {
                result.clickable_in_header.push({
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 100),
                    href: el.getAttribute('href') || '',
                    classes: el.className.toString().substring(0, 200)
                });
            });
        });

        // Dropdown/popover elements
        document.querySelectorAll('[class*="dropdown"], [class*="popover"], [class*="popup"], [role="menu"]').forEach(el => {
            result.dropdowns.push({
                tag: el.tagName,
                classes: el.className.toString().substring(0, 200),
                visible: el.offsetParent !== null,
                text: el.textContent.trim().substring(0, 300)
            });
        });

        return result;
    }""")

    print(f"  User-related elements found: {len(header_info['user_elements'])}")
    for el in header_info['user_elements']:
        print(f"    {el['selector']} -> <{el['tag']}> text='{el['text'][:80]}' class='{el['classes'][:80]}'")

    print(f"\n  Clickable elements in header: {len(header_info['clickable_in_header'])}")
    for el in header_info['clickable_in_header']:
        print(f"    <{el['tag']}> text='{el['text'][:60]}' href='{el['href']}' class='{el['classes'][:60]}'")

    print(f"\n  Dropdown elements: {len(header_info['dropdowns'])}")
    for el in header_info['dropdowns']:
        print(f"    <{el['tag']}> visible={el['visible']} text='{el['text'][:80]}'")

    return header_info


def step2_click_user_elements(page):
    """Try clicking user name, avatar, or any header dropdown trigger."""
    print("\n" + "=" * 60)
    print("STEP 2: Click user elements to find dropdown menus")
    print("=" * 60)

    # Try various selectors that might be user menu triggers
    selectors_to_try = [
        ('[class*="user"]', 'user class'),
        ('[class*="User"]', 'User class'),
        ('[class*="avatar"]', 'avatar'),
        ('[class*="Avatar"]', 'Avatar'),
        ('[class*="account"]', 'account'),
        ('[class*="profile"]', 'profile'),
        ('header [class*="dropdown"] > a', 'header dropdown link'),
        ('header [class*="dropdown"] > button', 'header dropdown button'),
        ('nav [class*="dropdown"] > a', 'nav dropdown link'),
        ('nav [class*="dropdown"] > button', 'nav dropdown button'),
        ('[class*="dropdown-toggle"]', 'dropdown-toggle'),
        ('header button', 'header button'),
        ('nav button', 'nav button'),
        ('[class*="header"] button', 'header-class button'),
        # Japanese text patterns
        ('text=設定', 'settings text'),
        ('text=プロフィール', 'profile text'),
        ('text=アカウント', 'account text'),
        ('text=ログアウト', 'logout text'),
    ]

    for selector, desc in selectors_to_try:
        try:
            elements = page.locator(selector)
            count = elements.count()
            if count > 0:
                print(f"\n  Found {count} elements for '{desc}' ({selector})")
                for i in range(min(count, 3)):
                    el = elements.nth(i)
                    if el.is_visible():
                        text = el.text_content() or ""
                        print(f"    [{i}] visible, text='{text.strip()[:60]}'")
                        try:
                            el.click()
                            time.sleep(1)
                            screenshot(page, f"02_click_{desc.replace(' ', '_')}_{i}")
                            print(f"    -> Clicked! Checking for new menus...")

                            # Check if any new menus appeared
                            new_menus = page.evaluate("""() => {
                                const menus = [];
                                document.querySelectorAll('[class*="dropdown-menu"], [class*="popover"], [role="menu"], [class*="menu-list"], ul[class*="show"]').forEach(el => {
                                    if (el.offsetParent !== null) {
                                        menus.push({
                                            classes: el.className.toString().substring(0, 200),
                                            text: el.textContent.trim().substring(0, 500),
                                            links: Array.from(el.querySelectorAll('a')).map(a => ({text: a.textContent.trim(), href: a.getAttribute('href') || ''}))
                                        });
                                    }
                                });
                                return menus;
                            }""")

                            if new_menus:
                                print(f"    -> Menu appeared!")
                                for menu in new_menus:
                                    print(f"       class: {menu['classes'][:80]}")
                                    print(f"       text: {menu['text'][:200]}")
                                    for link in menu.get('links', []):
                                        print(f"       link: '{link['text']}' -> {link['href']}")
                            else:
                                print(f"    -> No dropdown menu appeared")

                            # Check URL change
                            print(f"    -> URL: {page.url}")
                        except Exception as e:
                            print(f"    -> Click error: {e}")
                    else:
                        print(f"    [{i}] hidden")
        except Exception:
            pass


def step3_direct_url_access(page):
    """Try accessing settings-related URLs directly."""
    print("\n" + "=" * 60)
    print("STEP 3: Direct URL access attempts")
    print("=" * 60)

    urls_to_try = [
        "/user-settings",
        "/settings",
        "/profile",
        "/account",
        "/my-page",
        "/mypage",
        "/user",
        "/users/edit",
        "/preferences",
        "/config",
        "/password",
        "/change-password",
        "/notification-settings",
        "/notifications",
        "/#/settings",
        "/#/profile",
        "/#/account",
        "/#/user",
    ]

    results = []
    for url_path in urls_to_try:
        full_url = f"{BASE_URL}{url_path}"
        try:
            response = page.goto(full_url, wait_until="networkidle", timeout=10000)
            time.sleep(1)
            status = response.status if response else "no response"
            final_url = page.url
            title = page.title()

            # Check page content
            body_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 500) : ''")
            has_content = len(body_text.strip()) > 50

            result = {
                "path": url_path,
                "status": status,
                "final_url": final_url,
                "title": title,
                "has_content": has_content,
                "redirected": final_url != full_url,
                "body_preview": body_text.strip()[:150]
            }
            results.append(result)

            indicator = "FOUND?" if (status == 200 and has_content and not "/login" in final_url) else "->redirect/empty"
            print(f"  {url_path:25s} status={status} final={final_url} {indicator}")

            if status == 200 and has_content and "/login" not in final_url:
                safe_name = url_path.replace("/", "_").replace("#", "hash")
                screenshot(page, f"03_url{safe_name}")

        except Exception as e:
            print(f"  {url_path:25s} ERROR: {e}")
            results.append({"path": url_path, "error": str(e)})

    return results


def step4_sidebar_footer_links(page):
    """Check sidebar and footer for settings links."""
    print("\n" + "=" * 60)
    print("STEP 4: Sidebar and footer investigation")
    print("=" * 60)

    # Go back to main page
    page.goto(f"{BASE_URL}/invoices", wait_until="networkidle")
    time.sleep(2)

    info = page.evaluate("""() => {
        const result = {
            sidebar: [],
            footer: [],
            all_nav: []
        };

        // Sidebar
        const sidebarSel = 'aside, .sidebar, [class*="sidebar"], [class*="Sidebar"], [class*="side-nav"], [class*="sidenav"]';
        document.querySelectorAll(sidebarSel).forEach(sb => {
            sb.querySelectorAll('a, button').forEach(el => {
                result.sidebar.push({
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 100),
                    href: el.getAttribute('href') || '',
                    classes: el.className.toString().substring(0, 100)
                });
            });
        });

        // Footer
        const footerSel = 'footer, .footer, [class*="footer"], [class*="Footer"]';
        document.querySelectorAll(footerSel).forEach(ft => {
            ft.querySelectorAll('a, button').forEach(el => {
                result.footer.push({
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 100),
                    href: el.getAttribute('href') || '',
                    classes: el.className.toString().substring(0, 100)
                });
            });
        });

        // All nav-like elements
        document.querySelectorAll('nav a, [role="navigation"] a').forEach(el => {
            result.all_nav.push({
                text: el.textContent.trim().substring(0, 100),
                href: el.getAttribute('href') || ''
            });
        });

        return result;
    }""")

    print(f"  Sidebar links: {len(info['sidebar'])}")
    for el in info['sidebar']:
        print(f"    <{el['tag']}> text='{el['text'][:60]}' href='{el['href']}'")

    print(f"\n  Footer links: {len(info['footer'])}")
    for el in info['footer']:
        print(f"    <{el['tag']}> text='{el['text'][:60]}' href='{el['href']}'")

    print(f"\n  Nav links: {len(info['all_nav'])}")
    for el in info['all_nav']:
        print(f"    text='{el['text'][:60]}' href='{el['href']}'")

    return info


def step5_all_links(page):
    """Collect all anchor links and filter for settings/profile/account."""
    print("\n" + "=" * 60)
    print("STEP 5: All page links analysis")
    print("=" * 60)

    page.goto(f"{BASE_URL}/invoices", wait_until="networkidle")
    time.sleep(2)

    links = page.evaluate("""() => {
        const all = [];
        document.querySelectorAll('a[href]').forEach(a => {
            all.push({
                text: a.textContent.trim().substring(0, 100),
                href: a.getAttribute('href'),
                visible: a.offsetParent !== null
            });
        });
        return all;
    }""")

    print(f"  Total links on page: {len(links)}")

    # Filter for settings-related
    keywords = ['setting', 'profile', 'account', 'user', 'config', 'preference',
                'password', '設定', 'プロフィール', 'アカウント', 'ユーザー',
                'パスワード', 'ログアウト', 'logout', 'sign-out']

    print("\n  All links:")
    for link in links:
        print(f"    [{('V' if link['visible'] else 'H')}] text='{link['text'][:50]}' href='{link['href']}'")

    settings_links = []
    for link in links:
        href = (link['href'] or '').lower()
        text = (link['text'] or '').lower()
        for kw in keywords:
            if kw in href or kw in text:
                settings_links.append(link)
                break

    print(f"\n  Settings/profile related links: {len(settings_links)}")
    for link in settings_links:
        print(f"    text='{link['text'][:60]}' href='{link['href']}' visible={link['visible']}")

    # Also check the received posts page
    print("\n  Checking /received_posts page...")
    page.goto(f"{BASE_URL}/received_posts", wait_until="networkidle")
    time.sleep(2)
    screenshot(page, "05_received_posts")

    links2 = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.textContent.trim().substring(0, 100),
            href: a.getAttribute('href'),
            visible: a.offsetParent !== null
        }));
    }""")

    print(f"  Total links on received_posts: {len(links2)}")
    for link in links2:
        print(f"    [{('V' if link['visible'] else 'H')}] text='{link['text'][:50]}' href='{link['href']}'")

    settings_links2 = [l for l in links2 if any(kw in (l['href'] or '').lower() + (l['text'] or '').lower() for kw in keywords)]
    if settings_links2:
        print(f"\n  Settings links on received_posts: {len(settings_links2)}")
        for link in settings_links2:
            print(f"    text='{link['text'][:60]}' href='{link['href']}'")

    return {"invoices_links": links, "received_posts_links": links2, "settings_related": settings_links + settings_links2}


def main():
    print("WDL User Settings Investigation")
    print(f"Target: {BASE_URL}")
    print(f"Date: {__import__('datetime').datetime.now().isoformat()}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        steps = [
            ("login", lambda: login(page)),
            ("step1", lambda: step1_investigate_header(page)),
            ("step2", lambda: step2_click_user_elements(page)),
            ("step3", lambda: step3_direct_url_access(page)),
            ("step4", lambda: step4_sidebar_footer_links(page)),
            ("step5", lambda: step5_all_links(page)),
        ]
        for name, fn in steps:
            try:
                fn()
            except Exception as e:
                print(f"\n  ERROR in {name}: {e}")
                import traceback
                traceback.print_exc()
                screenshot(page, f"error_{name}")

        browser.close()

    print("\n" + "=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
