"""
TOKIUMインボイス - 自動入力中書類画面テスト
対象: https://dev.keihi.com/payment_requests/waiting_worker_document_inputs (tkti10テナント)

受領した請求書の自動入力待ち一覧。15件のデータあり。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
AUTO_INPUT_URL = f"{BASE_URL}/payment_requests/waiting_worker_document_inputs"

TH_ID_MAP = {
    "test_自動入力中書類一覧の表示確認": "TH-IA01",
    "test_テーブルヘッダーの表示確認": "TH-IA02",
    "test_テーブルデータの表示確認": "TH-IA03",
    "test_表示件数ボタンの表示確認": "TH-IA04",
    "test_最初のレコードクリックで詳細表示": "TH-IA05",
    "test_詳細画面のボタン確認": "TH-IA06",
    "test_サイドバーメニューリンクの確認": "TH-IA07",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_auto_input(logged_in_page: Page) -> Page:
    page = logged_in_page
    page.goto(AUTO_INPUT_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.locator("table").first.wait_for(state="visible", timeout=15000)
    return page


class TestBasicDisplay:

    @pytest.mark.smoke
    def test_自動入力中書類一覧の表示確認(self, logged_in_page: Page):
        page = goto_auto_input(logged_in_page)
        expect(page).to_have_url(re.compile(
            r"/payment_requests/waiting_worker_document_inputs"))
        expect(page.locator("table").first).to_be_visible()

    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_auto_input(logged_in_page)
        table = page.locator("table").first
        for header in ["受領日時", "取引先コード", "取引先名", "送付元", "担当"]:
            expect(table.locator(f"th:has-text(\"{header}\")")).to_be_visible()

    def test_テーブルデータの表示確認(self, logged_in_page: Page):
        page = goto_auto_input(logged_in_page)
        rows = page.locator("table tbody tr")
        count = rows.count()
        assert count > 0, "自動入力中書類データが0件"

    def test_表示件数ボタンの表示確認(self, logged_in_page: Page):
        page = goto_auto_input(logged_in_page)
        paging_btn = page.locator('button:has-text("30")').first
        expect(paging_btn).to_be_attached()


class TestDetailView:

    def test_最初のレコードクリックで詳細表示(self, logged_in_page: Page):
        page = goto_auto_input(logged_in_page)
        url_before = page.url
        # 最初の行をクリック
        first_row = page.locator("table tbody tr").first
        first_row.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        # クリック後にURL変化または詳細ペイン表示
        detail_visible = page.locator(
            'button:has-text("自動入力を待たずに手入力")').first.is_visible()
        url_changed = page.url != url_before
        assert detail_visible or url_changed, "詳細ペインが表示されない"

    def test_詳細画面のボタン確認(self, logged_in_page: Page):
        page = goto_auto_input(logged_in_page)
        first_row = page.locator("table tbody tr").first
        first_row.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        expect(page.locator(
            'button:has-text("自動入力を待たずに手入力")').first).to_be_visible()


class TestNavigation:

    def test_サイドバーメニューリンクの確認(self, logged_in_page: Page):
        page = goto_auto_input(logged_in_page)
        invoice_links = {
            "請求書": "/payment_requests/reports",
            "国税関係書類": "/payment_requests/national_tax_documents",
            "取引先": "/payment_requests/suppliers",
        }
        for text, href in invoice_links.items():
            link = page.locator(f'a[href="{href}"]')
            expect(link).to_be_attached()
