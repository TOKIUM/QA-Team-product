"""WDL profile page deep investigation.

Click the profile menu item and explore the profile page structure.
"""
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# .envから認証情報を読み込み
load_dotenv(Path(__file__).parent.parent / "ログイン" / ".env")

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
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Set WDL_EMAIL and WDL_PW environment variables")
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    time.sleep(2)
    page.locator('input[name="email"]').first.fill(EMAIL)
    page.locator('input[type="password"]').first.fill(PASSWORD)
    page.locator('button[type="submit"]').first.click()
    time.sleep(5)
    page.wait_for_load_state("networkidle")
    page.locator('a[href="/invoices"]').wait_for(state="visible", timeout=15000)
    page.goto(f"{BASE_URL}/invoices", wait_until="networkidle")
    time.sleep(2)
    print("Login successful")


def investigate_profile(page):
    print("\n" + "=" * 60)
    print("STEP 1: Open user dropdown and click profile")
    print("=" * 60)

    # Click user button to open dropdown
    # From step1 investigation: class is _userData_1sd5f_11, button class _button_1sd5f_6
    # The div with userData contains a button with user name + email
    user_btn = page.locator('button').filter(has_text=EMAIL.split("@")[0]).first
    if not user_btn.is_visible():
        # Fallback: find any button in the header area
        user_btn = page.locator('header button, nav button').first
    print(f"  User button visible: {user_btn.is_visible()}")
    user_btn.click()
    time.sleep(1)

    # Get dropdown menu items
    menu_info = page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('[class*="menuItem"], [class*="menu-item"], [role="menuitem"]').forEach(el => {
            items.push({
                tag: el.tagName,
                text: el.textContent.trim(),
                href: el.getAttribute('href') || '',
                classes: el.className.toString().substring(0, 200)
            });
        });
        document.querySelectorAll('[class*="menu"] a, [class*="Menu"] a').forEach(el => {
            items.push({
                tag: el.tagName,
                text: el.textContent.trim(),
                href: el.getAttribute('href') || '',
                classes: el.className.toString().substring(0, 200),
                type: 'menu-link'
            });
        });
        return items;
    }""")

    print(f"  Menu items found: {len(menu_info)}")
    for item in menu_info:
        print(f"    <{item['tag']}> text='{item['text']}' href='{item.get('href', '')}' class='{item['classes'][:80]}'")

    screenshot(page, "10_dropdown_open")

    # Click on profile link
    profile_clicked = False
    for text in ['プロフィール', 'Profile']:
        try:
            link = page.get_by_text(text, exact=False).first
            if link.is_visible():
                link.click()
                profile_clicked = True
                print(f"  Clicked '{text}'")
                break
        except Exception:
            pass

    if not profile_clicked:
        try:
            page.locator('a[href*="profile"], a[href*="user"]').first.click()
            profile_clicked = True
            print("  Clicked profile via href")
        except Exception:
            print("  WARNING: Could not find profile link to click")

    time.sleep(3)
    page.wait_for_load_state("networkidle")
    screenshot(page, "11_profile_page")
    print(f"  Current URL: {page.url}")
    print(f"  Title: {page.title()}")

    # Investigate profile page structure
    print("\n" + "=" * 60)
    print("STEP 2: Profile page structure analysis")
    print("=" * 60)

    structure = page.evaluate("""() => {
        const result = {
            url: location.href,
            title: document.title,
            headings: [],
            forms: [],
            inputs: [],
            buttons: [],
            labels: [],
            text_content: [],
            all_links: []
        };
        document.querySelectorAll('h1, h2, h3, h4, h5').forEach(h => {
            result.headings.push({tag: h.tagName, text: h.textContent.trim()});
        });
        document.querySelectorAll('form').forEach((f, i) => {
            const formInputs = [];
            f.querySelectorAll('input, select, textarea').forEach(inp => {
                formInputs.push({
                    type: inp.type || inp.tagName.toLowerCase(),
                    name: inp.name || '',
                    placeholder: inp.placeholder || '',
                    value: inp.value || '',
                    id: inp.id || '',
                    disabled: inp.disabled,
                    readonly: inp.readOnly
                });
            });
            result.forms.push({index: i, action: f.action || '', method: f.method || '', inputs: formInputs});
        });
        document.querySelectorAll('input, select, textarea').forEach(inp => {
            if (inp.offsetParent !== null) {
                result.inputs.push({
                    type: inp.type || inp.tagName.toLowerCase(),
                    name: inp.name || '',
                    placeholder: inp.placeholder || '',
                    value: inp.value ? inp.value.substring(0, 100) : '',
                    id: inp.id || '',
                    disabled: inp.disabled,
                    readonly: inp.readOnly
                });
            }
        });
        document.querySelectorAll('label').forEach(l => {
            if (l.offsetParent !== null) {
                result.labels.push({text: l.textContent.trim(), for: l.getAttribute('for') || ''});
            }
        });
        document.querySelectorAll('button, input[type="submit"]').forEach(b => {
            if (b.offsetParent !== null) {
                result.buttons.push({text: b.textContent.trim(), type: b.type || '', disabled: b.disabled});
            }
        });
        document.querySelectorAll('main, [class*="content"], [class*="Content"], [class*="page"], [class*="Page"]').forEach(el => {
            const text = el.innerText || el.textContent || '';
            if (text.trim().length > 10) {
                result.text_content.push(text.trim().substring(0, 1000));
            }
        });
        document.querySelectorAll('a[href]').forEach(a => {
            if (a.offsetParent !== null) {
                result.all_links.push({text: a.textContent.trim(), href: a.getAttribute('href')});
            }
        });
        return result;
    }""")

    print(f"\n  URL: {structure['url']}")
    print(f"  Headings: {structure['headings']}")
    print(f"\n  Labels:")
    for label in structure['labels']:
        print(f"    '{label['text']}' for='{label['for']}'")
    print(f"\n  Visible inputs: {len(structure['inputs'])}")
    for inp in structure['inputs']:
        print(f"    type={inp['type']} name='{inp['name']}' placeholder='{inp['placeholder']}' value='{inp['value'][:50]}' disabled={inp['disabled']} readonly={inp.get('readonly', False)}")
    print(f"\n  Forms: {len(structure['forms'])}")
    for form in structure['forms']:
        print(f"    Form {form['index']}: action='{form['action']}' method='{form['method']}'")
        for inp in form['inputs']:
            print(f"      {inp['type']} name='{inp['name']}' value='{inp['value'][:50]}' disabled={inp['disabled']}")
    print(f"\n  Buttons:")
    for btn in structure['buttons']:
        print(f"    '{btn['text']}' type={btn['type']} disabled={btn['disabled']}")
    print(f"\n  Links:")
    for link in structure['all_links']:
        print(f"    '{link['text']}' -> {link['href']}")
    if structure['text_content']:
        print(f"\n  Main content text (first 500 chars):")
        print(f"    {structure['text_content'][0][:500]}")

    # Check for tabs/sections
    print("\n" + "=" * 60)
    print("STEP 3: Tabs and sections")
    print("=" * 60)

    tabs = page.evaluate("""() => {
        const result = {tabs: [], sections: []};
        document.querySelectorAll('[role="tab"], [class*="tab"], .nav-pills a, .nav-tabs a').forEach(el => {
            if (el.offsetParent !== null) {
                result.tabs.push({text: el.textContent.trim(), href: el.getAttribute('href') || ''});
            }
        });
        document.querySelectorAll('section, [class*="section"], [class*="Section"]').forEach(el => {
            if (el.offsetParent !== null) {
                const heading = el.querySelector('h1, h2, h3, h4');
                result.sections.push({heading: heading ? heading.textContent.trim() : '', classes: el.className.toString().substring(0, 100)});
            }
        });
        return result;
    }""")
    print(f"  Tabs: {tabs['tabs']}")
    print(f"  Sections: {tabs['sections']}")

    screenshot(page, "12_profile_full")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    screenshot(page, "13_profile_scrolled")

    return structure


def main():
    print("WDL Profile Page Deep Investigation")
    print(f"Target: {BASE_URL}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        try:
            login(page)
            investigate_profile(page)
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            screenshot(page, "error_profile")
        finally:
            browser.close()

    print("\n" + "=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
