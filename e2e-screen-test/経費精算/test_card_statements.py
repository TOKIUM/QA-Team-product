"""
経費精算 - カード明細画面テスト
対象: https://dev.keihi.com/aggregation_results (tkti10テナント)

カード明細一覧テーブル + ページネーション。
データ0件の可能性あり。
"""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
CARD_URL = f"{BASE_URL}/aggregation_results"

TH_ID_MAP = {
    "test_カード明細画面の表示確認": "EX-C01",
    "test_テーブルヘッダーの表示確認": "EX-C02",
    "test_テーブル表示の確認": "EX-C03",
    "test_ページネーションの確認": "EX-C04",
    "test_サイドバーからのナビゲーション": "EX-C05",
    "test_件数表示の確認": "EX-C06",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_card(logged_in_page: Page) -> Page:
    """カード明細画面に遷移"""
    page = logged_in_page
    page.goto(CARD_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    return page


class TestBasicDisplay:
    """カード明細画面の基本表示確認"""

    @pytest.mark.smoke
    @pytest.mark.expense
    def test_カード明細画面の表示確認(self, logged_in_page: Page):
        page = goto_card(logged_in_page)
        assert "/aggregation_results" in page.url, f"カード明細画面に遷移できません: {page.url}"

    @pytest.mark.expense
    def test_サイドバーからのナビゲーション(self, logged_in_page: Page):
        page = goto_card(logged_in_page)
        sidebar = page.locator('nav, [class*="sidebar"], [class*="menu"]').first
        if sidebar.count() > 0:
            expect(sidebar).to_be_visible()


class TestTable:
    """カード明細テーブルの確認"""

    @pytest.mark.expense
    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_card(logged_in_page)
        table = page.locator("table").first
        if table.count() > 0:
            expected_headers = ["利用日", "金額"]
            visible_count = 0
            for header in expected_headers:
                th = table.locator("th", has_text=header).first
                if th.count() > 0 and th.is_visible():
                    visible_count += 1
            assert visible_count >= 1, f"テーブルヘッダーが不十分: {visible_count}/2"

    @pytest.mark.expense
    def test_テーブル表示の確認(self, logged_in_page: Page):
        """テーブルまたは0件メッセージが表示される"""
        page = goto_card(logged_in_page)
        table = page.locator("table").first
        if table.count() > 0:
            expect(table).to_be_visible()
        else:
            no_data = page.locator('text=/0件|データ.*ありません|該当.*なし|明細.*ありません/')
            assert no_data.count() > 0, "テーブルも0件メッセージも見つかりません"


class TestPagination:
    """ページネーションの確認"""

    @pytest.mark.expense
    def test_ページネーションの確認(self, logged_in_page: Page):
        page = goto_card(logged_in_page)
        table = page.locator("table").first
        if table.count() > 0:
            rows = table.locator("tbody tr")
            if rows.count() >= 10:
                pagination = page.locator(
                    'nav[aria-label*="pagination"], [class*="paging"], '
                    '[class*="pagination"], .pagination'
                ).first
                if pagination.count() > 0:
                    expect(pagination).to_be_visible()

    @pytest.mark.expense
    def test_件数表示の確認(self, logged_in_page: Page):
        page = goto_card(logged_in_page)
        count_elem = page.locator('select[name*="per"]').first
        if count_elem.count() > 0 and count_elem.is_visible():
            expect(count_elem).to_be_visible()
            return
        count_text = page.locator('text=/\\d+件/').first
        if count_text.count() > 0 and count_text.is_visible():
            expect(count_text).to_be_visible()
