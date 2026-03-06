"""
TOKIUMインボイス - 取引先一覧画面テスト
対象: https://dev.keihi.com/payment_requests/suppliers (tkti10テナント)

取引先設定タブ（一覧）と定期支払設定タブの2タブ構成。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://dev.keihi.com"
SUPPLIERS_URL = f"{BASE_URL}/payment_requests/suppliers"

TH_ID_MAP = {
    "test_取引先一覧ページの表示確認": "TH-IS01",
    "test_サイドバーにTOKIUMインボイスメニューが表示される": "TH-IS02",
    "test_テーブルヘッダーの表示確認": "TH-IS03",
    "test_テーブルデータの表示確認": "TH-IS04",
    "test_検索フォームの表示確認": "TH-IS05",
    "test_新規取引先追加ボタンの表示確認": "TH-IS06",
    "test_インポートエクスポートボタンの表示確認": "TH-IS07",
    "test_定期支払設定タブへの切替": "TH-IS08",
    "test_定期支払設定テーブルヘッダーの表示確認": "TH-IS09",
    "test_取引先設定タブへ戻る": "TH-IS10",
    "test_取引先コードで検索": "TH-IS11",
    "test_取引先名で検索": "TH-IS12",
    "test_表示件数の切替": "TH-IS13",
    "test_異常系_存在しない取引先で検索": "TH-IS14",
    "test_検索条件リセット": "TH-IS15",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_suppliers(logged_in_page: Page) -> Page:
    """取引先一覧ページに遷移し、テーブルが表示されるまで待機"""
    page = logged_in_page
    page.goto(SUPPLIERS_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    # テーブルまたは取引先設定タブの表示を待機
    page.locator("table").first.wait_for(state="visible", timeout=15000)
    return page


# =============================================================================
# 基本表示テスト
# =============================================================================


class TestBasicDisplay:
    """取引先一覧の基本表示確認"""

    @pytest.mark.smoke
    def test_取引先一覧ページの表示確認(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        expect(page).to_have_url(re.compile(r"/payment_requests/suppliers"))
        # 取引先設定タブが表示されている
        expect(page.locator("text=取引先設定")).to_be_visible()

    def test_サイドバーにTOKIUMインボイスメニューが表示される(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        # TOKIUMインボイスのサイドバーメニュー項目（リンクで確認）
        invoice_links = {
            "自動入力中書類": "/payment_requests/waiting_worker_document_inputs",
            "国税関係書類": "/payment_requests/national_tax_documents",
        }
        for text, href in invoice_links.items():
            link = page.locator(f'a[href="{href}"]')
            expect(link).to_be_attached()

    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        table = page.locator("table").first
        expected_headers = [
            "取引先コード", "取引先名", "支払方法", "登録番号",
            "登録事業者名", "電話番号", "メールアドレス",
            "担当者", "担当部署", "識別コード",
        ]
        for header in expected_headers:
            expect(table.locator(f"th:has-text(\"{header}\")")).to_be_visible()

    def test_テーブルデータの表示確認(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        rows = page.locator("table tbody tr")
        count = rows.count()
        assert count > 0, "取引先データが0件"


# =============================================================================
# 操作ボタンテスト
# =============================================================================


class TestButtons:
    """操作ボタンの表示・動作確認"""

    def test_検索フォームの表示確認(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        # Bootstrap accordion を JS で展開
        page.evaluate("""() => {
            const trigger = document.querySelector('[data-toggle="collapse"]');
            if (trigger) trigger.click();
        }""")
        page.wait_for_timeout(1500)
        # 検索用ラベルが表示される
        for label in ["取引先コード", "取引先名"]:
            expect(page.locator(f"label:has-text(\"{label}\")").first).to_be_visible()

    def test_新規取引先追加ボタンの表示確認(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        expect(page.locator('button:has-text("新規取引先追加")')).to_be_visible()

    def test_インポートエクスポートボタンの表示確認(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        expect(page.locator('button:has-text("インポート")')).to_be_visible()
        expect(page.locator('button:has-text("エクスポート")')).to_be_visible()


# =============================================================================
# タブ切替テスト
# =============================================================================


class TestTabs:
    """取引先設定/定期支払設定タブの切替"""

    def test_定期支払設定タブへの切替(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        page.locator("text=定期支払設定").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        expect(page).to_have_url(
            re.compile(r"/payment_requests/periodic_reports"))
        # 定期支払設定のテーブルが表示される
        expect(page.locator("table").first).to_be_visible()

    def test_定期支払設定テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        page.locator("text=定期支払設定").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        table = page.locator("table").first
        for header in ["登録日", "有効期間", "取引先", "支払期日"]:
            expect(table.locator(f"th:has-text(\"{header}\")")).to_be_visible()

    def test_取引先設定タブへ戻る(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        # 定期支払に移動
        page.locator("text=定期支払設定").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        # 取引先設定に戻る
        page.locator("text=取引先設定").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        expect(page).to_have_url(
            re.compile(r"/payment_requests/suppliers"))


# =============================================================================
# 検索テスト
# =============================================================================


class TestSearch:
    """検索機能のテスト"""

    def _open_search(self, page: Page):
        """検索フォームを開く（headerのpointer interception回避）"""
        # Bootstrap accordion を JS で展開
        page.evaluate("""() => {
            const trigger = document.querySelector('[data-toggle="collapse"]');
            if (trigger) trigger.click();
        }""")
        page.wait_for_timeout(1500)

    def _click_search_button(self, page: Page):
        """検索ボタンをクリック（headerのpointer interception回避）"""
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.trim() === '検索') { b.click(); return; }
            }
        }""")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

    def test_取引先コードで検索(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        self._open_search(page)
        code_label = page.locator("label:has-text('取引先コード')").first
        code_input = code_label.locator("..").locator("input").first
        code_input.fill("12345")
        self._click_search_button(page)
        table = page.locator("table").first
        expect(table).to_be_visible()

    def test_取引先名で検索(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        self._open_search(page)
        name_label = page.locator("label:has-text('取引先名')").first
        name_input = name_label.locator("..").locator("input").first
        name_input.fill("取引先A")
        self._click_search_button(page)
        rows = page.locator("table tbody tr")
        count = rows.count()
        assert count > 0, "「取引先A」の検索結果が0件"

    def test_表示件数の切替(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        table = page.locator("table").first
        expect(table).to_be_visible()
        # ページネーションのボタンが存在する
        paging_btn = page.locator('button:has-text("30")').first
        expect(paging_btn).to_be_attached()

    def test_異常系_存在しない取引先で検索(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        # 検索前の件数を記録
        before_count = page.locator("table tbody tr").count()
        self._open_search(page)
        name_label = page.locator("label:has-text('取引先名')").first
        name_input = name_label.locator("..").locator("input").first
        name_input.fill("存在しない取引先ZZZZZZZ")
        self._click_search_button(page)
        after_count = page.locator("table tbody tr").count()
        assert after_count < before_count, \
            f"検索で件数が減っていない（前: {before_count}, 後: {after_count}）"

    def test_検索条件リセット(self, logged_in_page: Page):
        page = goto_suppliers(logged_in_page)
        self._open_search(page)
        name_label = page.locator("label:has-text('取引先名')").first
        name_input = name_label.locator("..").locator("input").first
        name_input.fill("テスト")
        # ページリロードでリセット
        page.goto(SUPPLIERS_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        rows = page.locator("table tbody tr")
        assert rows.count() > 0, "リセット後にデータが表示されない"
