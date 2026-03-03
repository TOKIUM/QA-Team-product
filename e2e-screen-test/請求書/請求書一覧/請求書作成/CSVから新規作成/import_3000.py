"""
3000件CSVインポート完全フロー
- auto3k_invoices.csv（3000件、請求書番号AUTO3K-0001〜3000、備考:自動生成）
- レイアウト選択 → アップロード → マッピング → データ確認 → プレビュー → 作成開始 → 確認ダイアログ「作成開始」
- 3000件のため各ステップの待機時間を延長
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


def main():
    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")
    test_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(test_dir, "auto3k_invoices.csv")
    output_path = os.path.join(test_dir, "import_3000_result.txt")
    out = open(output_path, "w", encoding="utf-8")

    start_time = time.time()

    def log(msg):
        elapsed = time.time() - start_time
        out.write(f"[{elapsed:6.1f}s] {msg}\n")
        out.flush()
        print(f"[{elapsed:6.1f}s] {msg}")

    log(f"CSVファイル: {csv_path}")
    log(f"ファイルサイズ: {os.path.getsize(csv_path):,} bytes")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        # タイムアウトを延長（3000件処理のため）
        context.set_default_timeout(120000)  # 2分
        page = context.new_page()

        # ===== STEP1: ログイン =====
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

        # ===== STEP2: レイアウト選択 =====
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

        # ===== STEP3: CSVアップロード =====
        log("\n=== STEP3: CSVアップロード（3000件） ===")
        dt = page.frame(name="datatraveler")
        dt.query_selector('input[type="file"]').set_input_files(csv_path)
        log("ファイル選択完了、アップロード待機...")
        # 3000件のため長めに待機
        page.wait_for_timeout(15000)
        page.screenshot(path=os.path.join(test_dir, "3k_step3_uploaded.png"))

        mapping_btn = dt.query_selector('button:has-text("項目のマッピングへ")')
        if mapping_btn:
            mapping_btn.click()
            log("「項目のマッピングへ」クリック")
            # 3000件のマッピング処理は時間がかかる
            page.wait_for_timeout(15000)
            log("マッピング画面到達")
        else:
            log("ERROR: 「項目のマッピングへ」ボタンが見つからない")
            dt_text = dt.evaluate("() => document.body.innerText")
            log(f"画面テキスト:\n{dt_text[:1000]}")

        page.screenshot(path=os.path.join(test_dir, "3k_step3_mapping.png"))

        # マッピング状態確認
        body_text = dt.evaluate("() => document.body.innerText")
        key_error = "ファイル項目が見つからないため" in body_text
        has_warning = "見つからない" in body_text
        log(f"キーエラー: {key_error}")
        log(f"警告あり: {has_warning}")

        if key_error or has_warning:
            log("ERROR: マッピングに問題あり")
            for line in body_text.split('\n'):
                if '見つからない' in line or 'エラー' in line:
                    log(f"  {line.strip()}")

        # ===== STEP4: データの確認へ =====
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
                log("「データの確認へ」クリック")
                # 3000件のデータ確認処理 - 長めに待機
                log("3000件のデータ確認処理中...")
                page.wait_for_timeout(60000)  # 1分待機

                page.screenshot(path=os.path.join(test_dir, "3k_step4_confirm.png"))

                confirm_text = dt.evaluate("() => document.body.innerText")
                has_error = "エラーが発生" in confirm_text
                has_undefined = "undefined" in confirm_text
                log(f"エラー: {has_error}")
                log(f"undefined: {has_undefined}")

                # 件数確認
                for line in confirm_text.split('\n'):
                    if any(kw in line for kw in ['問題なし', 'エラー', '件のデータ', '件']):
                        log(f"  {line.strip()}")

                if has_error:
                    log("ERROR: データ確認でエラー")
                    for line in confirm_text.split('\n'):
                        if 'エラー' in line or '項目' in line or 'undefined' in line:
                            log(f"  {line.strip()}")
        else:
            log("ERROR: 「データの確認へ」ボタンが見つからない")

        # ===== STEP5: 帳票プレビューへ =====
        log("\n=== STEP5: 帳票プレビューへ ===")
        preview_disabled = dt.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText && b.innerText.includes('帳票プレビュー')) return b.disabled;
            }
            return null;
        }""")
        log(f"プレビューボタン disabled: {preview_disabled}")

        if preview_disabled == False:
            preview_btn = dt.query_selector('button:has-text("帳票プレビューへ")')
            if preview_btn:
                pbox = preview_btn.bounding_box()
                if pbox:
                    page.mouse.click(pbox['x'] + pbox['width']/2, pbox['y'] + pbox['height']/2)
                    log("「帳票プレビューへ」クリック")
                    # 3000件のプレビュー生成 - 長めに待機
                    log("3000件のプレビュー生成中...")
                    page.wait_for_timeout(60000)  # 1分待機

                    page.screenshot(path=os.path.join(test_dir, "3k_step5_preview.png"))

                    preview_text = dt.evaluate("() => document.body.innerText")
                    for line in preview_text.split('\n'):
                        if any(kw in line for kw in ['件', 'レイアウト', 'AUTO3K', '作成']):
                            log(f"  {line.strip()}")
        else:
            log("ERROR: プレビューボタンが無効（エラーあり）")

        # ===== STEP6: 帳票作成を開始する → 確認ダイアログ → 作成開始 =====
        log("\n=== STEP6: 帳票作成を開始する ===")
        create_disabled = dt.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText && b.innerText.includes('帳票作成を開始する')) return b.disabled;
            }
            return null;
        }""")
        log(f"作成ボタン disabled: {create_disabled}")

        if create_disabled == False:
            create_btn = dt.query_selector('button:has-text("帳票作成を開始する")')
            if create_btn:
                crbox = create_btn.bounding_box()
                if crbox:
                    page.mouse.click(crbox['x'] + crbox['width']/2, crbox['y'] + crbox['height']/2)
                    log("「帳票作成を開始する」クリック")
                    page.wait_for_timeout(3000)

                    # 確認ダイアログ
                    dialog_text = dt.evaluate("() => document.body.innerText")
                    if "作成開始" in dialog_text:
                        log("確認ダイアログ表示")
                        page.screenshot(path=os.path.join(test_dir, "3k_step6_dialog.png"))

                        # 「作成開始」ボタンをクリック
                        start_btn = dt.query_selector('button:has-text("作成開始")')
                        if start_btn:
                            sbox = start_btn.bounding_box()
                            if sbox:
                                page.mouse.click(sbox['x'] + sbox['width']/2, sbox['y'] + sbox['height']/2)
                                log("「作成開始」クリック！")

                                # 3000件の作成処理 - 非常に長い待機
                                log("3000件の帳票作成処理中... (最大5分待機)")
                                # 5秒ごとにURLチェック
                                for wait_i in range(60):  # 最大5分
                                    page.wait_for_timeout(5000)
                                    current_url = page.url
                                    if '/invoices' in current_url and '/import' not in current_url:
                                        log(f"一覧画面に遷移！ URL: {current_url}")
                                        break
                                    if wait_i % 6 == 0:
                                        log(f"  待機中... ({(wait_i+1)*5}秒経過)")

                                log(f"作成後URL: {page.url}")
                                page.screenshot(path=os.path.join(test_dir, "3k_step6_result.png"))

                                # 画面テキスト確認
                                main_text = page.evaluate("() => document.body.innerText")
                                for line in main_text.split('\n'):
                                    if any(kw in line for kw in ['AUTO3K', '件中', '件のデータ', '完了', '作成', 'エラー']):
                                        log(f"  {line.strip()}")
                        else:
                            log("ERROR: 「作成開始」ボタンが見つからない")
                    else:
                        log("確認ダイアログが表示されない")
        else:
            log("ERROR: 作成ボタンが無効")

        # ===== STEP7: 一覧で確認 =====
        log("\n=== STEP7: 一覧で確認 ===")
        page.goto(f"{BASE_URL}/invoices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        # AUTO3Kで検索
        page.evaluate("""() => {
            const input = document.querySelector('#documentNumber');
            if (!input) return false;
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(input, 'AUTO3K');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            const form = input.closest('form');
            if (form) { try { form.requestSubmit(); } catch(e) { form.submit(); } }
        }""")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(8000)

        log(f"検索URL: {page.url}")
        body_list = page.evaluate("() => document.body.innerText")
        count = re.search(r'(\d+)件中', body_list)
        if count:
            log(f"検索結果: {count.group(0)}")
        else:
            log("件数表示なし")

        # テーブル行（先頭5件）
        rows = page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr');
            return Array.from(rows).slice(0, 5).map(r => {
                const cells = r.querySelectorAll('td');
                return Array.from(cells).map(c => (c.innerText || '').trim());
            });
        }""")
        log(f"テーブル行数: {len(rows)}（先頭5件表示）")
        for i, cells in enumerate(rows):
            relevant = [c for c in cells if c]
            log(f"  行{i+1}: {' | '.join(c[:40] for c in relevant[:8])}")

        page.screenshot(path=os.path.join(test_dir, "3k_step7_list.png"))

        total_elapsed = time.time() - start_time
        log(f"\n=== 完了（総処理時間: {total_elapsed:.0f}秒 = {total_elapsed/60:.1f}分） ===")

        browser.close()

    out.close()
    print(f"結果: {output_path}")


if __name__ == "__main__":
    main()
