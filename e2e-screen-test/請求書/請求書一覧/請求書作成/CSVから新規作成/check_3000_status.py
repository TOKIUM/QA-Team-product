"""
3000件CSVインポート結果確認
- サーバーサイドでバックグラウンド処理中のため、一覧画面で検索して確認
- 処理中/完了の両方のステータスで確認
"""

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


def main():
    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")
    test_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(test_dir, "check_3000_result.txt")
    out = open(output_path, "w", encoding="utf-8")

    start_time = time.time()

    def log(msg):
        elapsed = time.time() - start_time
        out.write(f"[{elapsed:6.1f}s] {msg}\n")
        out.flush()
        print(f"[{elapsed:6.1f}s] {msg}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
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

        # ===== ポーリング: AUTO3Kで検索 =====
        log("\n=== AUTO3Kで検索（ポーリング） ===")

        for attempt in range(10):  # 最大10回試行（各30秒間隔）
            log(f"\n--- 試行 {attempt + 1}/10 ---")

            # 全ステータスで検索
            search_url = f"{BASE_URL}/invoices?statuses=processing%2Cavailable%2Csending%2Cscheduled%2Cfailed_to_process%2Cfailed_to_send&documentNumber=AUTO3K&page=1"
            page.goto(search_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)

            body_text = page.evaluate("() => document.body.innerText")
            count_match = re.search(r'(\d+)件中', body_text)

            if count_match:
                total = int(count_match.group(1))
                log(f"検索結果: {count_match.group(0)} (total={total})")

                # テーブル行確認
                rows = page.evaluate("""() => {
                    const rows = document.querySelectorAll('table tbody tr');
                    return Array.from(rows).slice(0, 10).map(r => {
                        const cells = r.querySelectorAll('td');
                        return Array.from(cells).map(c => (c.innerText || '').trim());
                    });
                }""")
                log(f"テーブル行数: {len(rows)}（先頭10件表示）")
                for i, cells in enumerate(rows):
                    relevant = [c for c in cells if c]
                    log(f"  行{i+1}: {' | '.join(c[:50] for c in relevant[:8])}")

                if total > 0:
                    log(f"\n✅ 3000件中 {total}件 発見！")

                    # ステータス別確認
                    for status_name, status_val in [
                        ("処理中", "processing"),
                        ("利用可能", "available"),
                        ("送付中", "sending"),
                        ("処理失敗", "failed_to_process"),
                    ]:
                        status_url = f"{BASE_URL}/invoices?statuses={status_val}&documentNumber=AUTO3K&page=1"
                        page.goto(status_url)
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(3000)
                        status_body = page.evaluate("() => document.body.innerText")
                        status_count = re.search(r'(\d+)件中', status_body)
                        if status_count:
                            log(f"  {status_name}: {status_count.group(0)}")
                        else:
                            log(f"  {status_name}: 0件")

                    page.screenshot(path=os.path.join(test_dir, "3k_check_found.png"))
                    break
            else:
                log("件数表示なし（0件）")

                # テーブルに行がないか確認
                rows = page.evaluate("""() => {
                    const rows = document.querySelectorAll('table tbody tr');
                    return rows.length;
                }""")
                log(f"テーブル行数: {rows}")

                if attempt < 9:
                    log(f"30秒後にリトライ...")
                    page.wait_for_timeout(30000)
                else:
                    log("10回試行しても見つかりません")
                    page.screenshot(path=os.path.join(test_dir, "3k_check_notfound.png"))

        total_elapsed = time.time() - start_time
        log(f"\n=== 完了（総処理時間: {total_elapsed:.0f}秒 = {total_elapsed/60:.1f}分） ===")

        browser.close()

    out.close()
    print(f"結果: {output_path}")


if __name__ == "__main__":
    main()
