"""
作成した請求書のメモ欄に「自動生成」を記入するスクリプト v2
1. ログイン → VERIFY2検索 → 各請求書のUUID取得
2. 各詳細画面でメモ欄に「自動生成」入力 → 保存
"""

import re
import os
from playwright.sync_api import sync_playwright, expect

BASE_URL = "https://invoicing-staging.keihi.com"


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "ログイン", ".env")
    env_path = os.path.normpath(env_path)
    vals = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


def main():
    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")
    test_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(test_dir, "write_memo_v2_result.txt")
    out = open(output_path, "w", encoding="utf-8")

    def log(msg):
        out.write(msg + "\n")
        out.flush()
        print(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        page = context.new_page()

        # ===== ログイン =====
        log("=== ログイン ===")
        page.goto(f"{BASE_URL}/login")
        page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
        page.get_by_label("メールアドレス").fill(email)
        page.get_by_label("パスワード").fill(password)
        page.wait_for_timeout(500)
        page.get_by_role("button", name="ログイン", exact=True).click()
        for _ in range(30):
            if "/invoices" in page.url and "/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        log(f"ログイン完了: {page.url}")

        # ===== VERIFY2検索 → UUIDリスト取得 =====
        log("\n=== VERIFY2検索 ===")
        page.goto(f"{BASE_URL}/invoices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        page.evaluate("""() => {
            const input = document.querySelector('#documentNumber');
            if (!input) return false;
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(input, 'VERIFY2');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            const form = input.closest('form');
            if (form) { try { form.requestSubmit(); } catch(e) { form.submit(); } }
            return true;
        }""")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(8000)

        # 行クリックで遷移先URLを取得するため、各行をクリックしてURLを記録
        # まず行数確認
        row_count = page.evaluate("() => document.querySelectorAll('table tbody tr').length")
        log(f"検索結果: {row_count}件")

        # 各行をクリックしてUUIDを取得
        invoice_uuids = []
        for i in range(row_count):
            # 一覧画面に戻る
            if i > 0:
                page.go_back()
                page.wait_for_timeout(5000)

            # 行クリック
            page.evaluate(f"""() => {{
                const rows = document.querySelectorAll('table tbody tr');
                if (rows[{i}]) {{
                    rows[{i}].click();
                    return true;
                }}
                return false;
            }}""")
            page.wait_for_timeout(5000)

            # URL取得
            url = page.url
            uuid_match = re.search(r'/invoices/([0-9a-f-]+)', url)
            if uuid_match:
                uuid = uuid_match.group(1)
                invoice_uuids.append(uuid)
                log(f"  請求書{i+1}: UUID={uuid}")
            else:
                log(f"  請求書{i+1}: UUID取得失敗 (URL={url})")

        log(f"\nUUID一覧: {invoice_uuids}")

        # ===== 最初の請求書でメモ欄の構造を調査 =====
        if invoice_uuids:
            log("\n=== メモ欄構造調査 ===")
            page.goto(f"{BASE_URL}/invoices/{invoice_uuids[0]}")
            page.wait_for_timeout(10000)
            page.screenshot(path=os.path.join(test_dir, "memo_detail_v2.png"))

            body_text = page.evaluate("() => document.body.innerText")

            # 「メモ」を含む行
            log("「メモ」含む行:")
            for line in body_text.split('\n'):
                if 'メモ' in line:
                    log(f"  {line.strip()}")

            # 全入力フィールド
            all_fields = page.evaluate("""() => {
                const fields = document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea');
                return Array.from(fields).map(f => {
                    // ラベルを探す
                    let label = '';
                    // for属性
                    if (f.id) {
                        const lbl = document.querySelector(`label[for="${f.id}"]`);
                        if (lbl) label = (lbl.innerText || '').trim();
                    }
                    // 親要素内のラベル
                    if (!label) {
                        const parent = f.closest('.MuiFormControl-root, div, section');
                        if (parent) {
                            const lbl = parent.querySelector('label, .MuiInputLabel-root, .MuiFormLabel-root');
                            if (lbl) label = (lbl.innerText || '').trim();
                        }
                    }
                    // aria-label
                    if (!label) label = f.getAttribute('aria-label') || '';

                    return {
                        tag: f.tagName,
                        type: f.type || '',
                        name: f.name || '',
                        id: f.id || '',
                        placeholder: f.placeholder || '',
                        value: (f.value || '').substring(0, 100),
                        label: label.substring(0, 50),
                        visible: f.offsetHeight > 0,
                        editable: !f.disabled && !f.readOnly,
                        rect: f.offsetHeight > 0 ? {
                            x: f.getBoundingClientRect().x,
                            y: f.getBoundingClientRect().y,
                            w: f.getBoundingClientRect().width,
                            h: f.getBoundingClientRect().height
                        } : null
                    };
                });
            }""")

            log(f"\n入力フィールド ({len(all_fields)}):")
            for f in all_fields:
                if f['visible']:
                    log(f"  [{f['tag']}] name={f['name']}, id={f['id']}, label={f['label']}, "
                        f"placeholder={f['placeholder']}, value={f['value']}, editable={f['editable']}")

            # メモフィールドを特定
            memo_field = None
            for f in all_fields:
                if f['visible'] and (
                    'memo' in f['name'].lower() or
                    'メモ' in f['label'] or
                    'メモ' in f['placeholder'] or
                    'memo' in f['id'].lower()
                ):
                    memo_field = f
                    break

            if memo_field:
                log(f"\n★メモフィールド発見: {memo_field}")
            else:
                log("\nメモフィールドが見つかりません - 詳細テキストで探す")

                # contenteditable要素も確認
                editable_divs = page.evaluate("""() => {
                    const divs = document.querySelectorAll('[contenteditable="true"]');
                    return Array.from(divs).map(d => ({
                        tag: d.tagName,
                        text: (d.innerText || '').trim().substring(0, 100),
                        rect: {
                            x: d.getBoundingClientRect().x,
                            y: d.getBoundingClientRect().y
                        }
                    }));
                }""")
                if editable_divs:
                    log(f"contenteditable要素: {len(editable_divs)}")
                    for d in editable_divs:
                        log(f"  {d}")

                # ページ全テキスト
                log(f"\nページテキスト（先頭3000文字）:\n{body_text[:3000]}")

        # ===== 各請求書のメモ欄に「自動生成」を記入 =====
        log("\n=== メモ欄記入 ===")
        for i, uuid in enumerate(invoice_uuids):
            log(f"\n--- 請求書{i+1}: {uuid} ---")
            page.goto(f"{BASE_URL}/invoices/{uuid}")
            page.wait_for_timeout(10000)

            # メモフィールドを探して入力
            # パターン1: name=memo or id=memo
            memo_input = page.query_selector('input[name="memo"], textarea[name="memo"], #memo')
            if not memo_input:
                # パターン2: ラベル「メモ」の近くのinput
                memo_input = page.evaluate("""() => {
                    const labels = document.querySelectorAll('label, span, div, dt, th');
                    for (const lbl of labels) {
                        const text = (lbl.textContent || '').trim();
                        if (text === 'メモ' || text === 'メモ欄') {
                            // 兄弟 or 親のinput/textarea
                            const parent = lbl.closest('div, tr, dl, section');
                            if (parent) {
                                const input = parent.querySelector('input, textarea');
                                if (input) {
                                    return {
                                        found: true,
                                        selector: input.tagName.toLowerCase() +
                                            (input.name ? `[name="${input.name}"]` : '') +
                                            (input.id ? `#${input.id}` : '')
                                    };
                                }
                            }
                        }
                    }
                    return { found: false };
                }""")

                if memo_input and memo_input.get('found'):
                    selector = memo_input['selector']
                    log(f"  メモフィールド発見: {selector}")
                    memo_el = page.query_selector(selector)
                    if memo_el:
                        # React互換入力
                        page.evaluate(f"""() => {{
                            const el = document.querySelector('{selector}');
                            if (!el) return false;
                            el.focus();
                            const setter = Object.getOwnPropertyDescriptor(
                                el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
                                'value'
                            ).set;
                            setter.call(el, '自動生成');
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}""")
                        log("  「自動生成」入力完了")
                    else:
                        log(f"  セレクター {selector} の要素が見つからない")
                else:
                    log("  メモフィールドが見つからない - getByLabelで試行")
                    # Playwright getByLabel
                    memo_by_label = page.get_by_label("メモ")
                    if memo_by_label.count() > 0:
                        memo_by_label.first.fill("自動生成")
                        log("  getByLabel('メモ')で入力完了")
                    else:
                        log("  getByLabelでも見つからない")
                        # フォールバック: 全フィールドの中からメモっぽいものを探す
                        fallback = page.evaluate("""() => {
                            const inputs = document.querySelectorAll('input[type="text"], textarea');
                            for (const inp of inputs) {
                                if (inp.offsetHeight > 0 && !inp.disabled && !inp.readOnly) {
                                    // 空のフィールドでメモっぽい位置にあるもの
                                    const rect = inp.getBoundingClientRect();
                                    if (rect.y > 400) { // ページ下部
                                        return {
                                            found: true,
                                            name: inp.name,
                                            id: inp.id,
                                            y: rect.y
                                        };
                                    }
                                }
                            }
                            return { found: false };
                        }""")
                        log(f"  フォールバック: {fallback}")
                        continue
            else:
                # 直接入力
                page.evaluate("""() => {
                    const el = document.querySelector('input[name="memo"], textarea[name="memo"], #memo');
                    if (!el) return false;
                    el.focus();
                    const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                    setter.call(el, '自動生成');
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }""")
                log("  「自動生成」入力完了（直接）")

            page.wait_for_timeout(1000)

            # 保存ボタンを探してクリック
            save_result = page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    const text = (b.innerText || '').trim();
                    if (text === '保存' || text === '更新' || text.includes('保存')) {
                        if (!b.disabled && b.offsetHeight > 0) {
                            b.scrollIntoView({ block: 'center' });
                            return { found: true, text: text };
                        }
                    }
                }
                return { found: false };
            }""")
            log(f"  保存ボタン: {save_result}")

            if save_result.get('found'):
                # 保存ボタンクリック
                page.evaluate("""() => {
                    const btns = document.querySelectorAll('button');
                    for (const b of btns) {
                        const text = (b.innerText || '').trim();
                        if (text === '保存' || text === '更新' || text.includes('保存')) {
                            if (!b.disabled && b.offsetHeight > 0) {
                                b.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                log("  保存クリック")
                page.wait_for_timeout(5000)

                # 保存結果確認
                body_after = page.evaluate("() => document.body.innerText")
                if "保存" in body_after or "更新" in body_after or "成功" in body_after:
                    for line in body_after.split('\n'):
                        if any(kw in line for kw in ['保存', '更新', '成功', 'エラー', '自動生成']):
                            log(f"  結果: {line.strip()}")
            else:
                log("  保存ボタンが見つからない")

            page.screenshot(path=os.path.join(test_dir, f"memo_saved_{i+1}.png"))

        # ===== 結果確認: 一覧でメモ欄を確認 =====
        log("\n=== メモ欄確認（一覧） ===")
        page.goto(f"{BASE_URL}/invoices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        page.evaluate("""() => {
            const input = document.querySelector('#documentNumber');
            if (!input) return false;
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(input, 'VERIFY2');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            const form = input.closest('form');
            if (form) { try { form.requestSubmit(); } catch(e) { form.submit(); } }
        }""")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(8000)

        rows_final = page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr');
            return Array.from(rows).map(r => {
                const cells = r.querySelectorAll('td');
                return Array.from(cells).map(c => (c.innerText || '').trim());
            });
        }""")

        log(f"最終確認テーブル行: {len(rows_final)}")
        for i, cells in enumerate(rows_final):
            relevant = [c for c in cells if c]
            log(f"  行{i+1}: {' | '.join(c[:40] for c in relevant)}")

        page.screenshot(path=os.path.join(test_dir, "memo_final_list.png"))

        browser.close()
        log("\n=== 完了 ===")

    out.close()
    print(f"結果: {output_path}")


if __name__ == "__main__":
    main()
