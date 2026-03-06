"""
WDL - 受信ポスト画面テスト
対象: https://invoicing-wdl-staging.keihi.com/invoice-posts

受信ポスト一覧テーブル + 検索フォーム。
"""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-wdl-staging.keihi.com"
POSTS_URL = f"{BASE_URL}/invoice-posts"

TH_ID_MAP = {
    "test_受信ポスト画面の表示確認": "WDL-P01",
    "test_テーブルヘッダーの表示確認": "WDL-P02",
    "test_テーブルデータの存在確認": "WDL-P03",
    "test_検索フォームの確認": "WDL-P04",
    "test_ナビゲーション_帳票への遷移": "WDL-P05",
    "test_検索実行の確認": "WDL-P06",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_posts(logged_in_page: Page) -> Page:
    """受信ポスト画面に遷移"""
    page = logged_in_page
    page.goto(POSTS_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.locator("table").first.wait_for(state="visible", timeout=15000)
    return page


class TestBasicDisplay:
    """受信ポストの基本表示確認"""

    @pytest.mark.smoke
    @pytest.mark.wdl
    def test_受信ポスト画面の表示確認(self, logged_in_page: Page):
        page = goto_posts(logged_in_page)
        expect(page.locator("h1")).to_have_text("受信ポスト")
        expect(page).to_have_url(POSTS_URL)


class TestTable:
    """受信ポストテーブルの確認"""

    @pytest.mark.wdl
    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_posts(logged_in_page)
        table = page.locator("table").first
        expected_headers = ["送付元名", "変更依頼", "未読", "閲覧可能"]
        for header in expected_headers:
            expect(table.locator("th", has_text=header).first).to_be_visible()

    @pytest.mark.wdl
    def test_テーブルデータの存在確認(self, logged_in_page: Page):
        page = goto_posts(logged_in_page)
        table = page.locator("table").first
        rows = table.locator("tbody tr")
        assert rows.count() > 0, "受信ポストデータが0件です"


class TestSearch:
    """検索機能の確認"""

    @pytest.mark.wdl
    def test_検索フォームの確認(self, logged_in_page: Page):
        page = goto_posts(logged_in_page)
        # 検索条件追加ボタンをクリック
        add_btn = page.locator('button:has-text("検索条件を追加")')
        if add_btn.count() > 0 and add_btn.first.is_visible():
            add_btn.first.click()
            page.wait_for_timeout(1000)

        form = page.locator("form").first
        # 送付元名
        assert form.locator('input[name="senderName"]').count() > 0, "送付元名フィールドが見つかりません"
        # 受信者メール
        assert form.locator('input[name="recipientEmail"]').count() > 0, "受信者メールフィールドが見つかりません"
        # 変更依頼チェックボックス
        assert form.locator('input[name="hasChangeRequest"]').count() > 0, "変更依頼チェックボックスが見つかりません"

    @pytest.mark.wdl
    def test_検索実行の確認(self, logged_in_page: Page):
        page = goto_posts(logged_in_page)
        search_btn = page.locator('button:has-text("この条件で検索")')
        expect(search_btn.first).to_be_visible()
        reset_btn = page.locator('button:has-text("リセット")')
        expect(reset_btn.first).to_be_visible()


class TestNavigation:
    """ナビゲーションの確認"""

    @pytest.mark.wdl
    def test_ナビゲーション_帳票への遷移(self, logged_in_page: Page):
        page = goto_posts(logged_in_page)
        invoices_link = page.locator('a[href="/invoices"]').first
        expect(invoices_link).to_be_visible()
        invoices_link.click()
        page.wait_for_url("**/invoices", timeout=10000)
        expect(page.locator("h1")).to_have_text("帳票")
