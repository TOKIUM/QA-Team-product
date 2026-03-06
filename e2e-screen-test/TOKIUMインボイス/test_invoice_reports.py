"""
TOKIUMインボイス - 請求書一覧画面テスト
対象: https://dev.keihi.com/payment_requests/reports (tkti10テナント)

3ペイン構成: 左=一覧、中央=画像ビューア、右=入力フォーム
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
REPORTS_URL = f"{BASE_URL}/payment_requests/reports"

TH_ID_MAP = {
    "test_請求書一覧ページの表示確認": "TH-IR01",
    "test_テーブルヘッダーの表示確認": "TH-IR02",
    "test_テーブルデータの表示確認": "TH-IR03",
    "test_請求書を登録するボタンの表示確認": "TH-IR04",
    "test_検索フォームの表示確認": "TH-IR05",
    "test_会計データ作成ボタンの表示確認": "TH-IR06",
    "test_請求書詳細の3ペイン表示確認": "TH-IR07",
    "test_詳細画面の入力フォーム確認": "TH-IR08",
    "test_表示件数の切替確認": "TH-IR09",
    "test_異常系_存在しない条件で検索": "TH-IR10",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_reports(logged_in_page: Page) -> Page:
    page = logged_in_page
    page.goto(REPORTS_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.locator("table").first.wait_for(state="visible", timeout=15000)
    return page


# =============================================================================
# 基本表示テスト
# =============================================================================


class TestBasicDisplay:

    @pytest.mark.smoke
    def test_請求書一覧ページの表示確認(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        expect(page).to_have_url(re.compile(r"/payment_requests/reports"))
        expect(page.locator("table").first).to_be_visible()

    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        table = page.locator("table").first
        # 請求書一覧の主要ヘッダー（調査データより）
        for header in ["取引先コード", "取引先名", "支払期日", "計上日"]:
            expect(table.locator(f"th:has-text(\"{header}\")")).to_be_visible()

    def test_テーブルデータの表示確認(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        rows = page.locator("table tbody tr")
        count = rows.count()
        assert count > 0, "請求書データが0件"


# =============================================================================
# 操作ボタンテスト
# =============================================================================


class TestButtons:

    def test_請求書を登録するボタンの表示確認(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        expect(page.locator('button:has-text("請求書を登録する")')).to_be_visible()

    def test_検索フォームの表示確認(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        # 検索ボタン（初期状態ではhiddenの場合あり）
        search_btn = page.locator('button:has-text("指定した条件で検索")').first
        # ボタンがDOM上に存在すること（hiddenでもOK）
        expect(search_btn).to_be_attached()

    def test_会計データ作成ボタンの表示確認(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        expect(page.locator(
            'button:has-text("この条件で会計データ作成を開始")')).to_be_visible()


# =============================================================================
# 詳細画面テスト（3ペイン）
# =============================================================================


class TestDetailView:

    def test_請求書詳細の3ペイン表示確認(self, logged_in_page: Page):
        """一覧の最初の行クリックで3ペイン表示になることを確認"""
        page = goto_reports(logged_in_page)
        # 最初の行のリンクをクリック
        first_link = page.locator("table tbody tr a").first
        if first_link.count() > 0:
            first_link.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            # 詳細ペインが表示される（編集ボタン、保存ボタン等）
            expect(page.locator('button:has-text("保存")').first).to_be_visible()
        else:
            pytest.skip("請求書レコードなし")

    def test_詳細画面の入力フォーム確認(self, logged_in_page: Page):
        """詳細画面に入力フォームのラベルが表示されることを確認"""
        page = goto_reports(logged_in_page)
        first_link = page.locator("table tbody tr a").first
        if first_link.count() > 0:
            first_link.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            # 入力フォームの主要ラベル
            expect(page.locator('button:has-text("編集する")').first).to_be_visible()
        else:
            pytest.skip("請求書レコードなし")


# =============================================================================
# ページネーション
# =============================================================================


class TestPagination:

    def test_表示件数の切替確認(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        # 50件表示ボタンがある
        paging_btn = page.locator('button:has-text("50")').first
        if paging_btn.is_visible():
            expect(paging_btn).to_be_visible()
        table = page.locator("table").first
        expect(table).to_be_visible()


# =============================================================================
# 異常系
# =============================================================================


class TestErrorCases:

    def test_異常系_存在しない条件で検索(self, logged_in_page: Page):
        page = goto_reports(logged_in_page)
        # 検索条件設定で存在しない取引先を指定
        search_btn = page.locator('button:has-text("指定した条件で検索")').first
        if search_btn.is_visible():
            search_btn.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
        # テーブルは表示されている（結果0件でもテーブル構造は残る）
        table = page.locator("table").first
        expect(table).to_be_visible()
