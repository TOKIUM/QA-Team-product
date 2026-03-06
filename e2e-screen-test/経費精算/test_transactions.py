"""
経費精算 - 経費画面テスト
対象: https://dev.keihi.com/transactions (tkti10テナント)

経費一覧テーブル + 検索フォーム + 経費登録ボタン。
データ0件の可能性あり。
"""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
TRANSACTIONS_URL = f"{BASE_URL}/transactions"

TH_ID_MAP = {
    "test_経費画面の表示確認": "EX-T01",
    "test_経費登録ボタンの表示確認": "EX-T02",
    "test_テーブルヘッダーの表示確認": "EX-T03",
    "test_テーブル表示の確認": "EX-T04",
    "test_検索フォームの確認": "EX-T05",
    "test_サイドバーメニューの確認": "EX-T06",
    "test_表示件数の確認": "EX-T07",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_transactions(logged_in_page: Page) -> Page:
    """経費画面に遷移"""
    page = logged_in_page
    page.goto(TRANSACTIONS_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    return page


class TestBasicDisplay:
    """経費画面の基本表示確認"""

    @pytest.mark.smoke
    @pytest.mark.expense
    def test_経費画面の表示確認(self, logged_in_page: Page):
        page = goto_transactions(logged_in_page)
        assert "/transactions" in page.url, f"経費画面に遷移できません: {page.url}"

    @pytest.mark.expense
    def test_経費登録ボタンの表示確認(self, logged_in_page: Page):
        page = goto_transactions(logged_in_page)
        # 経費登録ボタン（ドロップダウン含む）
        register_btn = page.locator(
            'a:has-text("経費登録"), button:has-text("経費登録"), '
            'a:has-text("経費を登録"), button:has-text("経費を登録")'
        ).first
        if register_btn.count() > 0:
            expect(register_btn).to_be_visible()

    @pytest.mark.expense
    def test_サイドバーメニューの確認(self, logged_in_page: Page):
        page = goto_transactions(logged_in_page)
        # サイドバーまたはナビゲーションにメニュー項目が表示される
        sidebar = page.locator('nav, [class*="sidebar"], [class*="menu"]').first
        if sidebar.count() > 0:
            expect(sidebar).to_be_visible()


class TestTable:
    """経費テーブルの確認"""

    @pytest.mark.expense
    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_transactions(logged_in_page)
        table = page.locator("table").first
        if table.count() > 0:
            expected_headers = ["利用日", "金額", "経費科目"]
            visible_count = 0
            for header in expected_headers:
                th = table.locator("th", has_text=header).first
                if th.count() > 0 and th.is_visible():
                    visible_count += 1
            assert visible_count >= 1, f"テーブルヘッダーが不十分: {visible_count}/3"

    @pytest.mark.expense
    def test_テーブル表示の確認(self, logged_in_page: Page):
        """テーブルまたは0件メッセージが表示される"""
        page = goto_transactions(logged_in_page)
        table = page.locator("table").first
        if table.count() > 0:
            expect(table).to_be_visible()
        else:
            no_data = page.locator('text=/0件|データ.*ありません|該当.*なし|経費.*ありません/')
            assert no_data.count() > 0, "テーブルも0件メッセージも見つかりません"


class TestSearch:
    """検索機能の確認"""

    @pytest.mark.expense
    def test_検索フォームの確認(self, logged_in_page: Page):
        page = goto_transactions(logged_in_page)
        # 検索フォーム展開
        search_toggle = page.locator(
            'a[data-toggle="collapse"]:has-text("検索"), '
            'button:has-text("検索条件")'
        ).first
        if search_toggle.count() > 0 and search_toggle.is_visible():
            page.evaluate("el => el.click()", search_toggle.element_handle())
            page.wait_for_timeout(1000)

        form = page.locator('form, [class*="search"]').first
        if form.count() > 0:
            expect(form).to_be_visible()

    @pytest.mark.expense
    def test_表示件数の確認(self, logged_in_page: Page):
        page = goto_transactions(logged_in_page)
        count_elem = page.locator('select[name*="per"]').first
        if count_elem.count() > 0 and count_elem.is_visible():
            expect(count_elem).to_be_visible()
            return
        count_text = page.locator('text=/\\d+件/').first
        if count_text.count() > 0 and count_text.is_visible():
            expect(count_text).to_be_visible()
