"""
TOKIUMインボイス - 集計画面テスト
対象: https://dev.keihi.com/payment_requests/analyses (tkti10テナント)

集計履歴テーブル + 請求書一覧テーブルの2セクション構成。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
AGGREGATION_URL = f"{BASE_URL}/payment_requests/analyses"

TH_ID_MAP = {
    "test_集計画面の表示確認": "TH-AG01",
    "test_集計履歴テーブルヘッダーの確認": "TH-AG02",
    "test_請求書一覧テーブルヘッダーの確認": "TH-AG03",
    "test_検索ボタンの表示確認": "TH-AG04",
    "test_集計ボタンの表示確認": "TH-AG05",
    "test_選択集計ボタンの表示確認": "TH-AG06",
    "test_表示件数ボタンの確認": "TH-AG07",
    "test_検索ラベルの確認": "TH-AG08",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_aggregation(logged_in_page: Page) -> Page:
    page = logged_in_page
    page.goto(AGGREGATION_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    return page


class TestBasicDisplay:

    @pytest.mark.smoke
    def test_集計画面の表示確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        expect(page).to_have_url(re.compile(
            r"/payment_requests/analyses"))

    def test_集計履歴テーブルヘッダーの確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        # 集計履歴テーブル（最初のテーブル）
        tables = page.locator("table")
        # 集計履歴のヘッダーを確認
        for header in ["集計ID", "作成日", "集計名", "支払い状況",
                        "集計方法", "会計データ出力状況", "請求書数", "総額"]:
            expect(tables.locator(
                f"th:has-text(\"{header}\")").first).to_be_attached()

    def test_請求書一覧テーブルヘッダーの確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        # 請求書一覧テーブルのヘッダーを確認
        for header in ["支払期日", "取引先コード", "取引先名", "金額"]:
            expect(page.locator(
                f"th:has-text(\"{header}\")").first).to_be_attached()


class TestButtons:

    def test_検索ボタンの表示確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        btn = page.locator('button:has-text("この条件で検索")').first
        expect(btn).to_be_attached()

    def test_集計ボタンの表示確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        btn = page.locator('button:has-text("この条件で集計")').first
        expect(btn).to_be_attached()

    def test_選択集計ボタンの表示確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        btn = page.locator('button:has-text("請求書を集計する")').first
        expect(btn).to_be_attached()

    def test_表示件数ボタンの確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        paging_btn = page.locator('button:has-text("10")').first
        expect(paging_btn).to_be_attached()


class TestSearch:

    def test_検索ラベルの確認(self, logged_in_page: Page):
        page = goto_aggregation(logged_in_page)
        for label in ["集計名", "作成日", "支払い状況"]:
            expect(page.locator(
                f"label:has-text(\"{label}\")").first).to_be_attached()
