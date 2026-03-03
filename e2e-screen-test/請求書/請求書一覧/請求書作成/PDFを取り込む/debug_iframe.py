"""
organizer iframeの内部要素を調査するデバッグスクリプト
"""
import os
import re
import sys

# .env読み込み
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ログイン", ".env")
env_path = os.path.normpath(env_path)
if os.path.exists(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

from playwright.sync_api import sync_playwright

BASE_URL = "https://invoicing-staging.keihi.com"
TEST_EMAIL = os.environ.get("TEST_EMAIL")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720}, locale="ja-JP")
        page = context.new_page()

        # ログイン
        page.goto(f"{BASE_URL}/login")
        page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
        page.get_by_label("メールアドレス").fill(TEST_EMAIL)
        page.get_by_label("パスワード").fill(TEST_PASSWORD)
        page.get_by_role("button", name="ログイン", exact=True).click()
        page.wait_for_url(re.compile(r"/invoices"), timeout=30000)

        # ファイル分割モードに遷移
        page.goto(f"{BASE_URL}/invoices/pdf-organizer/separation")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(10000)  # iframe読み込み待機を長めに

        # 全フレーム情報を出力
        print("=== All Frames ===")
        for i, frame in enumerate(page.frames):
            print(f"  Frame[{i}]: name='{frame.name}', url='{frame.url[:100]}...'")

        # organizer frameをURLパターンで取得
        organizer = None
        for frame in page.frames:
            if "organizer" in frame.url:
                organizer = frame
                break

        if organizer is None:
            print("\n*** organizer frame NOT FOUND by URL pattern ***")
            # IDで試行
            organizer = page.frame(url=lambda url: "tpmlyr" in url)
            if organizer:
                print(f"  Found by tpmlyr pattern: {organizer.url[:100]}")
            else:
                print("  Also not found by tpmlyr pattern")
                browser.close()
                return

        print(f"\n=== Organizer Frame ===")
        print(f"  URL: {organizer.url[:120]}")
        print(f"  Name: '{organizer.name}'")

        # iframe内のフレーム待機
        try:
            organizer.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"  networkidle wait error: {e}")

        # iframe内のコンテンツ取得を試す
        print("\n=== Attempting to read iframe content ===")

        # 方法1: テキスト検索
        texts_to_find = [
            "ファイルアップロード",
            "ファイルの分割",
            "プレビュー",
            "アップロードするファイルを選択し",
            "キャンセル",
            "次へ",
            "コンパクトモード",
        ]
        for text in texts_to_find:
            try:
                loc = organizer.locator(f"text={text}")
                count = loc.count()
                visible = False
                if count > 0:
                    try:
                        visible = loc.first.is_visible()
                    except:
                        pass
                print(f"  text='{text}' -> count={count}, visible={visible}")
            except Exception as e:
                print(f"  text='{text}' -> ERROR: {e}")

        # 方法2: ボタン検索
        print("\n=== Button search ===")
        try:
            buttons = organizer.locator("button")
            count = buttons.count()
            print(f"  Total buttons: {count}")
            for i in range(min(count, 10)):
                try:
                    text = buttons.nth(i).text_content()
                    visible = buttons.nth(i).is_visible()
                    print(f"    button[{i}]: text='{text}', visible={visible}")
                except Exception as e:
                    print(f"    button[{i}]: ERROR: {e}")
        except Exception as e:
            print(f"  Button query error: {e}")

        # 方法3: 全テキストコンテンツ
        print("\n=== Page body text (first 2000 chars) ===")
        try:
            body_text = organizer.locator("body").text_content()
            if body_text:
                print(f"  {body_text[:2000]}")
            else:
                print("  (empty body)")
        except Exception as e:
            print(f"  Body text error: {e}")

        # 方法4: innerHTML
        print("\n=== Body innerHTML (first 3000 chars) ===")
        try:
            html = organizer.locator("body").inner_html()
            if html:
                print(f"  {html[:3000]}")
            else:
                print("  (empty HTML)")
        except Exception as e:
            print(f"  innerHTML error: {e}")

        browser.close()

if __name__ == "__main__":
    main()
