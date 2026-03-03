"""
Step 2（確認画面）→ Step 3（完了画面）の画面遷移を詳細分析するスクリプト
"""
import os
import sys
import json

sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright, expect

RESULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results")
os.makedirs(RESULT_DIR, exist_ok=True)


def load_env():
    env_path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "ログイン", ".env")
    )
    vals = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def get_dialog_tree(page, max_depth=5):
    """ダイアログのDOM構造を取得"""
    return page.evaluate(
        """(maxDepth) => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return 'No dialog';
        function tree(el, depth) {
            if (depth > maxDepth) return '';
            const tag = el.tagName.toLowerCase();
            const role = el.getAttribute('role') ? ' role="' + el.getAttribute('role') + '"' : '';
            const cls = el.className ? ' class="' + (typeof el.className === 'string' ? el.className : '').substring(0, 80) + '"' : '';
            const text = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 ? ' "' + (el.textContent || '').trim().substring(0, 80) + '"' : '';
            const disabled = el.disabled ? ' disabled' : '';
            const indent = '  '.repeat(depth);
            let result = indent + '<' + tag + role + cls + disabled + '>' + text + '\\n';
            for (const child of el.children) {
                result += tree(child, depth + 1);
            }
            return result;
        }
        return tree(d, 0);
    }""",
        max_depth,
    )


def get_dialog_buttons(page):
    """ダイアログ内のボタン一覧"""
    return page.evaluate(
        """() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return [];
        const btns = [];
        d.querySelectorAll('button').forEach(b => {
            const r = b.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) {
                btns.push({
                    text: b.innerText.trim(),
                    disabled: b.disabled,
                    x: Math.round(r.x),
                    y: Math.round(r.y),
                    w: Math.round(r.width),
                    h: Math.round(r.height),
                    classes: (b.className || '').substring(0, 100)
                });
            }
        });
        return btns;
    }"""
    )


def get_dialog_tables(page):
    """ダイアログ内のテーブル"""
    return page.evaluate(
        """() => {
        const d = document.querySelector('[role="dialog"]');
        if (!d) return [];
        const tables = [];
        d.querySelectorAll('table').forEach(t => {
            const headers = Array.from(t.querySelectorAll('th')).map(th => th.innerText.trim());
            const rows = [];
            t.querySelectorAll('tbody tr').forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim().substring(0, 100));
                rows.push(cells);
            });
            tables.push({headers: headers, rows: rows});
        });
        return tables;
    }"""
    )


def main():
    env = load_env()
    test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "拡張子", "sample.pdf")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        ctx.set_default_timeout(30000)
        page = ctx.new_page()

        # ===== ログイン =====
        page.goto("https://invoicing-staging.keihi.com/login")
        page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
        page.get_by_label("メールアドレス").fill(env["TEST_EMAIL"])
        page.get_by_label("パスワード").fill(env["TEST_PASSWORD"])
        page.wait_for_timeout(500)
        page.get_by_role("button", name="ログイン", exact=True).click()
        for _ in range(30):
            if "/invoices" in page.url and "/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        print(f"Login: {page.url}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        # ===== チェックボックス選択（添付が — のもの） =====
        cbs = page.query_selector_all('table tbody tr td input[type="checkbox"]')
        print(f"Checkboxes: {len(cbs)}")
        # 6件目以降で添付なしの請求書を選択
        cbs[6].click(force=True)
        page.wait_for_timeout(500)

        # ===== モーダルを開く =====
        page.get_by_role("button", name="その他の操作").click()
        page.wait_for_timeout(1000)
        page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付").first.click()
        page.locator('[role="dialog"] h2:has-text("共通添付ファイルの一括添付")').wait_for(
            state="visible", timeout=10000
        )
        page.wait_for_timeout(1000)

        # ===== Step 1: ファイルアップロード =====
        print("\n" + "=" * 60)
        print("Step 1: ファイル選択")
        print("=" * 60)

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files([test_file])
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(RESULT_DIR, "flow_step1.png"))
        print("ファイルアップロード完了")

        # ===== Step 2: 確認へ進む =====
        confirm_btn = page.get_by_role("button", name="確認へ進む")
        expect(confirm_btn).to_be_enabled(timeout=5000)
        confirm_btn.click()
        page.wait_for_timeout(2000)

        print("\n" + "=" * 60)
        print("Step 2-a: 確認画面（判定中）")
        print("=" * 60)

        page.screenshot(path=os.path.join(RESULT_DIR, "flow_step2a_judging.png"))

        step2a_text = page.evaluate(
            """() => {
            const d = document.querySelector('[role="dialog"]');
            return d ? d.innerText : '';
        }"""
        )
        print(f"テキスト:\n{step2a_text}")

        print("\nボタン:")
        for b in get_dialog_buttons(page):
            print(f'  "{b["text"]}" disabled={b["disabled"]} ({b["w"]}x{b["h"]})')

        print(f"\nDOM構造:\n{get_dialog_tree(page, 6)[:3000]}")

        # ===== 判定完了待ち =====
        exec_btn = page.get_by_role("button", name="添付を実行する").first
        print("\n--- 添付を実行する ボタン enabled 待機中... ---")
        expect(exec_btn).to_be_enabled(timeout=30000)
        print("enabled になりました")

        print("\n" + "=" * 60)
        print("Step 2-b: 確認画面（判定完了）")
        print("=" * 60)

        page.screenshot(path=os.path.join(RESULT_DIR, "flow_step2b_ready.png"))

        step2b_text = page.evaluate(
            """() => {
            const d = document.querySelector('[role="dialog"]');
            return d ? d.innerText : '';
        }"""
        )
        print(f"テキスト:\n{step2b_text}")

        print("\nボタン:")
        for b in get_dialog_buttons(page):
            print(f'  "{b["text"]}" disabled={b["disabled"]} ({b["w"]}x{b["h"]})')

        print("\nテーブル:")
        for i, t in enumerate(get_dialog_tables(page)):
            print(f"  Table {i}: headers={t['headers']}")
            for j, row in enumerate(t["rows"]):
                print(f"    Row {j}: {row}")

        print(f"\nDOM構造:\n{get_dialog_tree(page, 6)[:4000]}")

        # ===== 添付を実行する =====
        print("\n" + "=" * 60)
        print("添付を実行する クリック")
        print("=" * 60)

        exec_btn.click(force=True)
        page.wait_for_timeout(8000)

        # ===== Step 3: 完了画面 =====
        print("\n" + "=" * 60)
        print("Step 3: 完了画面")
        print("=" * 60)

        page.screenshot(path=os.path.join(RESULT_DIR, "flow_step3.png"))

        step3_text = page.evaluate(
            """() => {
            const d = document.querySelector('[role="dialog"]');
            return d ? d.innerText : 'No dialog';
        }"""
        )
        print(f"テキスト:\n{step3_text}")

        print("\nボタン:")
        for b in get_dialog_buttons(page):
            print(f'  "{b["text"]}" disabled={b["disabled"]} ({b["w"]}x{b["h"]})')

        print(f"\nDOM構造:\n{get_dialog_tree(page, 6)[:3000]}")

        browser.close()

    print("\n=== 分析完了 ===")


if __name__ == "__main__":
    main()
