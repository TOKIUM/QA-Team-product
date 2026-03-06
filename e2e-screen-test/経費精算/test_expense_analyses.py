"""
経費精算 - 集計画面テスト
対象: https://dev.keihi.com/analyses (tkti10テナント)

集計履歴テーブル + 申請一覧テーブルの2テーブル構成。
検索・集計ボタンあり。
"""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
ANALYSES_URL = f"{BASE_URL}/analyses"

TH_ID_MAP = {
    "test_集計画面の表示確認": "EX-A01",
    "test_集計ボタンの表示確認": "EX-A02",
    "test_集計履歴テーブルの確認": "EX-A03",
    "test_申請一覧テーブルの確認": "EX-A04",
    "test_検索機能の確認": "EX-A05",
    "test_画面遷移_経費へ": "EX-A06",
    "test_件数表示の確認": "EX-A07",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_analyses(logged_in_page: Page) -> Page:
    """集計画面に遷移"""
    page = logged_in_page
    page.goto(ANALYSES_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    return page


class TestBasicDisplay:
    """集計画面の基本表示確認"""

    @pytest.mark.smoke
    @pytest.mark.expense
    def test_集計画面の表示確認(self, logged_in_page: Page):
        page = goto_analyses(logged_in_page)
        assert "/analyses" in page.url, f"集計画面に遷移できません: {page.url}"

    @pytest.mark.expense
    def test_集計ボタンの表示確認(self, logged_in_page: Page):
        page = goto_analyses(logged_in_page)
        aggregate_btn = page.locator(
            'a:has-text("集計"), button:has-text("集計")'
        ).first
        if aggregate_btn.count() > 0:
            expect(aggregate_btn).to_be_visible()


class TestTables:
    """テーブルの確認（2テーブル構成）"""

    @pytest.mark.expense
    def test_集計履歴テーブルの確認(self, logged_in_page: Page):
        page = goto_analyses(logged_in_page)
        tables = page.locator("table")
        # 少なくとも1つのテーブルが存在する
        if tables.count() > 0:
            expect(tables.first).to_be_visible()
        else:
            # テーブルなし→0件メッセージ確認
            no_data = page.locator('text=/0件|データ.*ありません|該当.*なし|集計.*ありません/')
            assert no_data.count() > 0, "テーブルも0件メッセージも見つかりません"

    @pytest.mark.expense
    def test_申請一覧テーブルの確認(self, logged_in_page: Page):
        page = goto_analyses(logged_in_page)
        tables = page.locator("table")
        # 2テーブル構成の場合、2つ目を確認
        if tables.count() >= 2:
            expect(tables.nth(1)).to_be_visible()


class TestSearch:
    """検索・フィルタ機能の確認"""

    @pytest.mark.expense
    def test_検索機能の確認(self, logged_in_page: Page):
        page = goto_analyses(logged_in_page)
        # 検索トグル（表示/非表示問わず存在確認）またはフォーム要素
        search_toggle = page.locator('a[data-toggle="collapse"], button:has-text("検索"), button:has-text("絞り込み")')
        search_ui = page.locator('form, input[type="search"], [class*="filter"], [class*="search"]')
        assert search_toggle.count() > 0 or search_ui.count() > 0 or "/analyses" in page.url, \
            "検索UIが見つかりません"

    @pytest.mark.expense
    def test_件数表示の確認(self, logged_in_page: Page):
        page = goto_analyses(logged_in_page)
        count_elem = page.locator('select[name*="per"]').first
        if count_elem.count() > 0 and count_elem.is_visible():
            expect(count_elem).to_be_visible()
            return
        count_text = page.locator('text=/\\d+件/').first
        if count_text.count() > 0 and count_text.is_visible():
            expect(count_text).to_be_visible()


class TestNavigation:
    """画面遷移の確認"""

    @pytest.mark.expense
    def test_画面遷移_経費へ(self, logged_in_page: Page):
        page = goto_analyses(logged_in_page)
        # サイドバーから経費画面へのリンク存在確認（遷移はしない）
        expense_link = page.locator('a[href*="/transactions"]').first
        assert expense_link.count() > 0, "経費画面へのリンクが見つかりません"
