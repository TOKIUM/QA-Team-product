"""
CSVインポート → 確認ダイアログ「作成開始」クリック → 一覧確認
★前回の問題: 「帳票作成を開始する」クリック後に確認ダイアログが表示される
  → 「作成開始」ボタンをクリックする必要がある
"""

import re
import os
import time
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


def create_test_csv(directory: str) -> str:
    header = "請求書番号,請求日,期日,取引先コード,取引先名称,取引先敬称,取引先郵便番号,取引先都道府県,取引先住所１,取引先住所２,当月請求額,備考,取引日付,内容,数量,単価,単位,金額,税率"
    rows = [
        "VERIFY2-001,2025/01/15,2025/02/15,TH003,,,,,,,,,,,1,10000,式,10000,10",
        "VERIFY2-002,2025/01/15,2025/02/15,TH003,,,,,,,,,,,1,20000,式,20000,10",
        "VERIFY2-003,2025/01/15,2025/02/15,TH003,,,,,,,,,,,1,30000,式,30000,8",
    ]
    csv_content = header + "\n" + "\n".join(rows) + "\n"
    csv_path = os.path.join(directory, "test_verify2.csv")
    with open(csv_path, "w", encoding="cp932") as f:
        f.write(csv_content)
    return csv_path


def main():
    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")
    test_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(test_dir, "import_verify_v2_result.txt")
    out = open(output_path, "w", encoding="utf-8")

    def log(msg):
        out.write(msg + "\n")
        out.flush()
        print(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        page = context.new_page()

        # ===== ログイン =====
        log("=== STEP1: ログイン ===")
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

        # ===== レイアウト選択 =====
        log("\n=== STEP2: レイアウト選択 ===")
        page.goto(f"{BASE_URL}/invoices/import")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(8000)
        gallery = page.frame(name="gallery")
        if not gallery:
            page.wait_for_timeout(5000)
            gallery = page.frame(name="gallery")
        gallery.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        gallery.query_selector_all(".MuiGrid-item")[0].click()
        expect(page).to_have_url(re.compile(r"/invoices/import/\d+"), timeout=15000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)
        log(f"レイアウト選択完了: {page.url}")

        # ===== CSVアップロード =====
        log("\n=== STEP3: CSVアップロード ===")
        dt = page.frame(name="datatraveler")
        csv_path = create_test_csv(test_dir)
        log(f"テストCSV: {csv_path}")

        dt.query_selector('input[type="file"]').set_input_files(csv_path)
        page.wait_for_timeout(5000)

        mapping_btn = dt.query_selector('button:has-text("項目のマッピングへ")')
        if mapping_btn:
            mapping_btn.click()
            page.wait_for_timeout(8000)
            log("マッピング画面到達")

        # ===== データの確認へ =====
        log("\n=== STEP4: データの確認へ ===")
        dt.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText && b.innerText.includes('データの確認')) {
                    b.scrollIntoView({ block: 'center' });
                    break;
                }
            }
        }""")
        page.wait_for_timeout(1000)

        confirm_btn = dt.query_selector('button:has-text("データの確認へ")')
        if confirm_btn:
            cbox = confirm_btn.bounding_box()
            if cbox:
                page.mouse.click(cbox['x'] + cbox['width']/2, cbox['y'] + cbox['height']/2)
                page.wait_for_timeout(10000)

                confirm_text = dt.evaluate("() => document.body.innerText")
                has_error = "エラーが発生" in confirm_text
                log(f"エラー: {has_error}")
                for line in confirm_text.split('\n'):
                    if "問題なし" in line or "件" in line:
                        log(f"  {line.strip()}")

        # ===== 帳票プレビューへ =====
        log("\n=== STEP5: 帳票プレビューへ ===")
        preview_btn = dt.query_selector('button:has-text("帳票プレビューへ")')
        if preview_btn:
            pbox = preview_btn.bounding_box()
            if pbox:
                page.mouse.click(pbox['x'] + pbox['width']/2, pbox['y'] + pbox['height']/2)
                page.wait_for_timeout(15000)
                log("プレビュー画面到達")

        # ===== 帳票作成を開始する → 確認ダイアログ → 作成開始 =====
        log("\n=== STEP6: 帳票作成を開始する ===")

        # 「帳票作成を開始する」ボタンクリック
        create_btn = dt.query_selector('button:has-text("帳票作成を開始する")')
        if create_btn:
            crbox = create_btn.bounding_box()
            if crbox:
                page.mouse.click(crbox['x'] + crbox['width']/2, crbox['y'] + crbox['height']/2)
                log("「帳票作成を開始する」クリック")
                page.wait_for_timeout(3000)

                # 確認ダイアログが表示される
                dialog_text = dt.evaluate("() => document.body.innerText")
                if "作成開始" in dialog_text:
                    log("確認ダイアログ表示！")
                    for line in dialog_text.split('\n'):
                        if any(kw in line for kw in ['作成', '開始', 'キャンセル', '時間', '帳票']):
                            log(f"  ダイアログ: {line.strip()}")

                    page.screenshot(path=os.path.join(test_dir, "import_v2_dialog.png"))

                    # 「作成開始」ボタンをクリック
                    # ダイアログ内のボタンを探す
                    start_btn = dt.query_selector('[role="dialog"] button:has-text("作成開始")')
                    if not start_btn:
                        # role="dialog"がない場合、テキストで探す
                        start_btn = dt.query_selector('button:has-text("作成開始")')

                    if start_btn:
                        sbox = start_btn.bounding_box()
                        if sbox:
                            log(f"「作成開始」ボタン位置: ({sbox['x']:.0f}, {sbox['y']:.0f})")
                            page.mouse.click(sbox['x'] + sbox['width']/2, sbox['y'] + sbox['height']/2)
                            log("「作成開始」クリック！")

                            # 作成処理を待つ（長めに）
                            log("作成処理待機中...")
                            page.wait_for_timeout(30000)

                            log(f"作成後URL: {page.url}")
                            page.screenshot(path=os.path.join(test_dir, "import_v2_after_create.png"))

                            # 画面状態確認
                            main_text = page.evaluate("() => document.body.innerText")

                            # 完了/成功/エラーメッセージ
                            for line in main_text.split('\n'):
                                line = line.strip()
                                if any(kw in line for kw in ['完了', '成功', '作成', '処理', 'エラー', '失敗', '件', 'VERIFY']):
                                    log(f"  メイン: {line}")

                            # datatraveler内確認
                            dt2 = page.frame(name="datatraveler")
                            if dt2:
                                dt_text = dt2.evaluate("() => document.body.innerText")
                                for line in dt_text.split('\n'):
                                    line = line.strip()
                                    if any(kw in line for kw in ['完了', '成功', '作成', '処理', 'エラー', '失敗', 'VERIFY']):
                                        log(f"  DT: {line}")
                                log(f"\nDT全テキスト:\n{dt_text[:2000]}")
                    else:
                        log("「作成開始」ボタンが見つからない")
                        # 全ボタンのリスト
                        all_btns = dt.evaluate("""() => {
                            const btns = document.querySelectorAll('button');
                            return Array.from(btns).map(b => ({
                                text: (b.innerText || '').trim(),
                                disabled: b.disabled,
                                visible: b.offsetHeight > 0
                            }));
                        }""")
                        log(f"全ボタン ({len(all_btns)}):")
                        for btn in all_btns:
                            if btn['visible']:
                                log(f"  [{btn['text']}] disabled={btn['disabled']}")
                else:
                    log("確認ダイアログが表示されていない")
                    log(f"画面テキスト:\n{dialog_text[:1000]}")

        # ===== 一覧で確認 =====
        log("\n=== STEP7: 一覧で確認 ===")
        page.goto(f"{BASE_URL}/invoices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        # VERIFYで検索
        search_result = page.evaluate("""() => {
            const input = document.querySelector('#documentNumber');
            if (!input) return 'no input';
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(input, 'VERIFY2');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            const form = input.closest('form');
            if (form) { try { form.requestSubmit(); return 'submitted'; } catch(e) { form.submit(); return 'submit'; } }
            return 'no form';
        }""")
        log(f"検索: {search_result}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(8000)

        log(f"検索URL: {page.url}")
        body_list = page.evaluate("() => document.body.innerText")
        count = re.search(r'(\d+)件中', body_list)
        if count:
            log(f"検索結果: {count.group(0)}")
        else:
            log("検索結果: 件数表示なし（0件の可能性）")

        rows = page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr');
            return Array.from(rows).map(r => {
                const cells = r.querySelectorAll('td');
                const hrefs = Array.from(r.querySelectorAll('a')).map(a => a.href);
                return {
                    cells: Array.from(cells).map(c => (c.innerText || '').trim()),
                    hrefs
                };
            });
        }""")

        log(f"テーブル行: {len(rows)}")
        for i, row in enumerate(rows[:10]):
            relevant = [c for c in row['cells'] if c]
            has_v = any('VERIFY' in c for c in row['cells'])
            marker = "★" if has_v else " "
            log(f" {marker}行{i+1}: {' | '.join(c[:40] for c in relevant[:8])}")
            if row['hrefs']:
                for h in row['hrefs']:
                    log(f"   リンク: {h}")

        page.screenshot(path=os.path.join(test_dir, "import_v2_list.png"))

        browser.close()
        log("\n=== 完了 ===")

    out.close()
    print(f"結果: {output_path}")


if __name__ == "__main__":
    main()
