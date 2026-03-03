"""
CSVインポート統合実行スクリプト

1. CSV生成 → 2. CSVインポート → 3. 結果確認（ポーリング）を一括実行

使い方:
  python run_csv_import.py                        # デフォルト: 3000件, プレフィックスAUTO3K
  python run_csv_import.py --count 10             # 10件
  python run_csv_import.py --count 100 --prefix TEST100
  python run_csv_import.py --count 3000 --prefix AUTO3K --date 2025/03/01 --due 2025/04/30
  python run_csv_import.py --skip-generate        # CSV生成をスキップ（既存CSVを使用）
  python run_csv_import.py --skip-import          # インポートをスキップ（結果確認のみ）
"""

import argparse
import re
import os
import time
from playwright.sync_api import sync_playwright


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


# ========== STEP1: CSV生成 ==========
def generate_csv(test_dir, count, prefix, invoice_date, due_date, remark):
    header = "請求書番号,請求日,期日,取引先コード,取引先名称,取引先敬称,取引先郵便番号,取引先都道府県,取引先住所１,取引先住所２,当月請求額,備考,取引日付,内容,数量,単価,単位,金額,税率"

    rows = []
    for i in range(1, count + 1):
        inv_num = f"{prefix}-{i:04d}"
        tax_rate = 8 if i % 2 == 0 else 10
        amount = 10000 + (i * 30) % 90001
        row = f"{inv_num},{invoice_date},{due_date},TH003,,,,,,,,{remark},,,1,{amount},式,{amount},{tax_rate}"
        rows.append(row)

    csv_content = header + "\n" + "\n".join(rows) + "\n"
    csv_path = os.path.join(test_dir, f"{prefix.lower()}_invoices.csv")

    with open(csv_path, "w", encoding="cp932") as f:
        f.write(csv_content)

    return csv_path, len(rows)


# ========== STEP2: CSVインポート ==========
def import_csv(page, test_dir, csv_path, count, log):
    # --- レイアウト選択 ---
    log("--- レイアウト選択 ---")
    page.goto(f"{BASE_URL}/invoices/import")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(8000)
    gallery = page.frame(name="gallery")
    if not gallery:
        page.wait_for_timeout(5000)
        gallery = page.frame(name="gallery")
    if not gallery:
        log("ERROR: gallery iframe が見つかりません")
        return False
    gallery.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    items = gallery.query_selector_all(".MuiGrid-item")
    if not items:
        log("ERROR: レイアウトが見つかりません")
        return False
    items[0].click()
    from playwright.sync_api import expect
    expect(page).to_have_url(re.compile(r"/invoices/import/\d+"), timeout=15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    log(f"レイアウト選択完了: {page.url}")

    # --- CSVアップロード ---
    log("--- CSVアップロード ---")
    dt = page.frame(name="datatraveler")
    if not dt:
        log("ERROR: datatraveler iframe が見つかりません")
        return False
    dt.query_selector('input[type="file"]').set_input_files(csv_path)
    log("ファイル選択完了、アップロード待機...")
    wait_sec = max(15, count // 200)
    page.wait_for_timeout(wait_sec * 1000)

    mapping_btn = dt.query_selector('button:has-text("項目のマッピングへ")')
    if mapping_btn:
        mapping_btn.click()
        log("マッピングへ")
        page.wait_for_timeout(max(15000, count * 5))
        log("マッピング画面到達")
    else:
        log("ERROR: マッピングボタンが見つかりません")
        return False

    # マッピングエラーチェック
    body_text = dt.evaluate("() => document.body.innerText")
    if "ファイル項目が見つからないため" in body_text or "見つからない" in body_text:
        log("ERROR: マッピングに問題あり")
        for line in body_text.split('\n'):
            if '見つからない' in line or 'エラー' in line:
                log(f"  {line.strip()}")
        return False

    # --- データの確認へ ---
    log("--- データの確認へ ---")
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
    if not confirm_btn:
        log("ERROR: データの確認ボタンが見つかりません")
        return False
    cbox = confirm_btn.bounding_box()
    if not cbox:
        log("ERROR: bounding_box取得失敗")
        return False
    page.mouse.click(cbox['x'] + cbox['width']/2, cbox['y'] + cbox['height']/2)
    log("データ確認処理中...")
    page.wait_for_timeout(max(30000, count * 20))

    confirm_text = dt.evaluate("() => document.body.innerText")
    for line in confirm_text.split('\n'):
        if any(kw in line for kw in ['問題なし', 'エラー', '件のデータ', '件']):
            log(f"  {line.strip()}")
    if "エラーが発生" in confirm_text:
        log("ERROR: データ確認でエラー")
        for line in confirm_text.split('\n'):
            if 'エラー' in line or '項目' in line:
                log(f"  {line.strip()}")
        return False

    # --- 帳票プレビューへ ---
    log("--- 帳票プレビューへ ---")
    preview_disabled = dt.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.innerText && b.innerText.includes('帳票プレビュー')) return b.disabled;
        }
        return null;
    }""")
    if preview_disabled is not False:
        log("ERROR: プレビューボタンが無効")
        return False
    preview_btn = dt.query_selector('button:has-text("帳票プレビューへ")')
    pbox = preview_btn.bounding_box()
    page.mouse.click(pbox['x'] + pbox['width']/2, pbox['y'] + pbox['height']/2)
    log("プレビュー生成中...")
    page.wait_for_timeout(max(30000, count * 20))

    # --- 帳票作成を開始する → 確認ダイアログ ---
    log("--- 帳票作成を開始する ---")
    create_disabled = dt.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.innerText && b.innerText.includes('帳票作成を開始する')) return b.disabled;
        }
        return null;
    }""")
    if create_disabled is not False:
        log("ERROR: 作成ボタンが無効")
        return False
    create_btn = dt.query_selector('button:has-text("帳票作成を開始する")')
    crbox = create_btn.bounding_box()
    page.mouse.click(crbox['x'] + crbox['width']/2, crbox['y'] + crbox['height']/2)
    log("確認ダイアログ待機...")
    page.wait_for_timeout(3000)

    dialog_text = dt.evaluate("() => document.body.innerText")
    if "作成開始" not in dialog_text:
        log("ERROR: 確認ダイアログが表示されません")
        return False
    log("確認ダイアログ表示")

    start_btn = dt.query_selector('button:has-text("作成開始")')
    if not start_btn:
        log("ERROR: 作成開始ボタンが見つかりません")
        return False
    sbox = start_btn.bounding_box()
    page.mouse.click(sbox['x'] + sbox['width']/2, sbox['y'] + sbox['height']/2)
    log("作成開始!")

    # 一覧画面遷移待機
    max_wait = max(60, count // 10)
    for wait_i in range(max_wait):
        page.wait_for_timeout(5000)
        if '/invoices' in page.url and '/import' not in page.url:
            log(f"一覧画面に遷移: {page.url}")
            break
        if wait_i % 6 == 0:
            log(f"  待機中... ({(wait_i+1)*5}秒経過)")

    page.screenshot(path=os.path.join(test_dir, "import_result.png"))
    return True


# ========== STEP3: 結果確認（ポーリング） ==========
def check_status(page, prefix, log, max_attempts=15, interval_sec=30):
    log(f"--- 結果確認（{prefix}で検索、最大{max_attempts}回 x {interval_sec}秒） ---")

    for attempt in range(max_attempts):
        log(f"試行 {attempt + 1}/{max_attempts}")
        search_url = f"{BASE_URL}/invoices?statuses=processing%2Cavailable%2Csending%2Cscheduled%2Cfailed_to_process%2Cfailed_to_send&documentNumber={prefix}&page=1"
        page.goto(search_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        body_text = page.evaluate("() => document.body.innerText")
        count_match = re.search(r'(\d+)件中', body_text)

        if count_match:
            total = int(count_match.group(1))
            log(f"検索結果: {count_match.group(0)} (total={total})")
            if total > 0:
                # テーブル先頭5行表示
                rows = page.evaluate("""() => {
                    const rows = document.querySelectorAll('table tbody tr');
                    return Array.from(rows).slice(0, 5).map(r => {
                        const cells = r.querySelectorAll('td');
                        return Array.from(cells).map(c => (c.innerText || '').trim());
                    });
                }""")
                for i, cells in enumerate(rows):
                    relevant = [c for c in cells if c]
                    log(f"  行{i+1}: {' | '.join(c[:40] for c in relevant[:8])}")

                # ステータス別確認
                for status_name, status_val in [
                    ("処理中", "processing"),
                    ("利用可能", "available"),
                    ("処理失敗", "failed_to_process"),
                ]:
                    status_url = f"{BASE_URL}/invoices?statuses={status_val}&documentNumber={prefix}&page=1"
                    page.goto(status_url)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(3000)
                    status_body = page.evaluate("() => document.body.innerText")
                    status_count = re.search(r'(\d+)件中', status_body)
                    if status_count:
                        log(f"  {status_name}: {status_count.group(0)}")
                    else:
                        log(f"  {status_name}: 0件")
                return total
        else:
            log("0件")

        if attempt < max_attempts - 1:
            log(f"{interval_sec}秒後にリトライ...")
            page.wait_for_timeout(interval_sec * 1000)

    log("最大試行回数に達しました")
    return 0


def main():
    parser = argparse.ArgumentParser(description="CSVインポート統合実行")
    parser.add_argument("--count", type=int, default=3000, help="生成件数 (default: 3000)")
    parser.add_argument("--prefix", type=str, default="AUTO3K", help="請求書番号プレフィックス (default: AUTO3K)")
    parser.add_argument("--date", type=str, default="2025/02/16", help="請求日 (default: 2025/02/16)")
    parser.add_argument("--due", type=str, default="2025/03/31", help="期日 (default: 2025/03/31)")
    parser.add_argument("--remark", type=str, default="自動生成", help="備考 (default: 自動生成)")
    parser.add_argument("--skip-generate", action="store_true", help="CSV生成をスキップ")
    parser.add_argument("--skip-import", action="store_true", help="インポートをスキップ（結果確認のみ）")
    parser.add_argument("--skip-check", action="store_true", help="結果確認をスキップ")
    parser.add_argument("--headed", action="store_true", help="ブラウザを表示して実行")
    parser.add_argument("--max-check", type=int, default=15, help="結果確認の最大試行回数 (default: 15)")
    parser.add_argument("--check-interval", type=int, default=30, help="結果確認のポーリング間隔(秒) (default: 30)")
    args = parser.parse_args()

    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")
    test_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(test_dir, "run_csv_import_result.txt")
    out = open(output_path, "w", encoding="utf-8")

    start_time = time.time()

    def log(msg):
        elapsed = time.time() - start_time
        line = f"[{elapsed:6.1f}s] {msg}"
        out.write(line + "\n")
        out.flush()
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("ascii", "replace").decode())

    log(f"=== CSVインポート統合実行 ===")
    log(f"件数: {args.count}, プレフィックス: {args.prefix}")
    log(f"請求日: {args.date}, 期日: {args.due}, 備考: {args.remark}")
    log(f"スキップ: generate={args.skip_generate}, import={args.skip_import}, check={args.skip_check}")
    log("")

    # --- STEP1: CSV生成 ---
    csv_path = os.path.join(test_dir, f"{args.prefix.lower()}_invoices.csv")
    if not args.skip_generate:
        log("=== STEP1: CSV生成 ===")
        csv_path, row_count = generate_csv(test_dir, args.count, args.prefix, args.date, args.due, args.remark)
        file_size = os.path.getsize(csv_path)
        log(f"生成完了: {csv_path}")
        log(f"行数: {row_count}, サイズ: {file_size:,} bytes")
    else:
        log("=== STEP1: CSV生成 (SKIP) ===")
        if os.path.exists(csv_path):
            log(f"既存CSV使用: {csv_path} ({os.path.getsize(csv_path):,} bytes)")
        else:
            log(f"ERROR: CSVファイルが見つかりません: {csv_path}")
            out.close()
            return

    # --- ブラウザ起動・ログイン ---
    if not args.skip_import or not args.skip_check:
        log("\n=== ログイン ===")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headed)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="ja-JP",
                timezone_id="Asia/Tokyo",
            )
            context.set_default_timeout(120000)
            page = context.new_page()

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

            # --- STEP2: CSVインポート ---
            if not args.skip_import:
                log("\n=== STEP2: CSVインポート ===")
                success = import_csv(page, test_dir, csv_path, args.count, log)
                if success:
                    log("インポート完了")
                else:
                    log("ERROR: インポート失敗")
            else:
                log("\n=== STEP2: CSVインポート (SKIP) ===")

            # --- STEP3: 結果確認 ---
            if not args.skip_check:
                log("\n=== STEP3: 結果確認 ===")
                found = check_status(page, args.prefix, log, args.max_check, args.check_interval)
                if found > 0:
                    log(f"\n結果: {args.prefix}で{found}件発見")
                else:
                    log(f"\n結果: {args.prefix}で0件（処理中の可能性あり）")
            else:
                log("\n=== STEP3: 結果確認 (SKIP) ===")

            browser.close()

    total_elapsed = time.time() - start_time
    log(f"\n=== 完了（総処理時間: {total_elapsed:.0f}秒 = {total_elapsed/60:.1f}分） ===")
    out.close()
    print(f"\n結果ログ: {output_path}")


if __name__ == "__main__":
    main()
