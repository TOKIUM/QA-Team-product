"""
TOKIUMインボイス - 国税関係書類画面テスト
対象: https://dev.keihi.com/payment_requests/national_tax_documents (tkti10テナント)

3ペイン構成（請求書画面と同様）。書類種別/タイトル/取引日/金額等のテーブル。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
NATIONAL_TAX_URL = f"{BASE_URL}/payment_requests/national_tax_documents"

TH_ID_MAP = {
    "test_国税関係書類一覧の表示確認": "TH-IN01",
    "test_テーブルヘッダーの表示確認": "TH-IN02",
    "test_テーブルデータの表示確認": "TH-IN03",
    "test_登録ボタンの表示確認": "TH-IN04",
    "test_検索ボタンの表示確認": "TH-IN05",
    "test_ファイル出力ボタンの表示確認": "TH-IN06",
    "test_一括編集ボタンの表示確認": "TH-IN07",
    "test_表示件数ボタンの確認": "TH-IN08",
    "test_検索ラベルの確認": "TH-IN09",
    "test_最初のレコードクリックで詳細表示": "TH-IN10",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_national_tax(logged_in_page: Page) -> Page:
    page = logged_in_page
    page.goto(NATIONAL_TAX_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.locator("table").first.wait_for(state="visible", timeout=15000)
    return page


class TestBasicDisplay:

    @pytest.mark.smoke
    def test_国税関係書類一覧の表示確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        expect(page).to_have_url(re.compile(
            r"/payment_requests/national_tax_documents"))
        expect(page.locator("table").first).to_be_visible()

    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        table = page.locator("table").first
        for header in ["書類種別", "書類タイトル", "取引日", "取引先コード",
                        "取引先名", "取引金額"]:
            expect(table.locator(f"th:has-text(\"{header}\")")).to_be_visible()

    def test_テーブルデータの表示確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        rows = page.locator("table tbody tr")
        count = rows.count()
        assert count > 0, "国税関係書類データが0件"


class TestButtons:

    def test_登録ボタンの表示確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        expect(page.locator(
            'button:has-text("国税関係書類を登録する")')).to_be_visible()

    def test_検索ボタンの表示確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        btn = page.locator('button:has-text("指定した条件で検索")').first
        expect(btn).to_be_attached()

    def test_ファイル出力ボタンの表示確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        expect(page.locator(
            'button:has-text("この条件でファイル出力する")')).to_be_visible()

    def test_一括編集ボタンの表示確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        expect(page.locator('button:has-text("一括編集")')).to_be_visible()

    def test_表示件数ボタンの確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        paging_btn = page.locator('button:has-text("30")').first
        expect(paging_btn).to_be_attached()


class TestSearch:

    def test_検索ラベルの確認(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        # 検索フォームのラベルが存在する（DOM上に）
        for label in ["書類種別", "書類タイトル", "取引先名", "取引先コード"]:
            expect(page.locator(
                f"label:has-text(\"{label}\")").first).to_be_attached()


class TestDetailView:

    def test_最初のレコードクリックで詳細表示(self, logged_in_page: Page):
        page = goto_national_tax(logged_in_page)
        first_row = page.locator("table tbody tr").first
        first_row.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        # 詳細ペイン表示確認
        expect(page.locator(
            'button:has-text("保存")').first).to_be_visible()
