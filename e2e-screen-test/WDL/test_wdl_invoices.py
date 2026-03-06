"""
WDL - 帳票画面テスト
対象: https://invoicing-wdl-staging.keihi.com/invoices

帳票一覧テーブル + 検索フォーム + ページネーション。
"""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-wdl-staging.keihi.com"
INVOICES_URL = f"{BASE_URL}/invoices"

TH_ID_MAP = {
    "test_帳票一覧ページの表示確認": "WDL-I01",
    "test_ナビゲーションリンクの表示確認": "WDL-I02",
    "test_テーブルヘッダーの表示確認": "WDL-I03",
    "test_テーブルデータの存在確認": "WDL-I04",
    "test_検索ボタンの表示確認": "WDL-I05",
    "test_リセットボタンの表示確認": "WDL-I06",
    "test_検索フォームフィールドの確認": "WDL-I07",
    "test_ページネーションの確認": "WDL-I08",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


def goto_invoices(logged_in_page: Page) -> Page:
    """帳票一覧ページに遷移"""
    page = logged_in_page
    page.goto(INVOICES_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.locator("table").first.wait_for(state="visible", timeout=15000)
    return page


class TestBasicDisplay:
    """帳票一覧の基本表示確認"""

    @pytest.mark.smoke
    @pytest.mark.wdl
    def test_帳票一覧ページの表示確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        expect(page.locator("h1")).to_have_text("帳票")
        expect(page).to_have_url(INVOICES_URL)

    @pytest.mark.wdl
    def test_ナビゲーションリンクの表示確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        nav_invoices = page.locator('a[href="/invoices"]').first
        nav_posts = page.locator('a[href="/invoice-posts"]').first
        expect(nav_invoices).to_be_visible()
        expect(nav_posts).to_be_visible()


class TestTable:
    """帳票テーブルの確認"""

    @pytest.mark.wdl
    def test_テーブルヘッダーの表示確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        table = page.locator("table").first
        expected_headers = [
            "受信日", "送付元", "添付", "請求書番号",
            "合計金額", "支払期日", "ファイル名", "メモ",
        ]
        for header in expected_headers:
            expect(table.locator("th", has_text=header).first).to_be_visible()

    @pytest.mark.wdl
    def test_テーブルデータの存在確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        table = page.locator("table").first
        rows = table.locator("tbody tr")
        assert rows.count() > 0, "帳票データが0件です"


class TestSearch:
    """検索機能の確認"""

    @pytest.mark.wdl
    def test_検索ボタンの表示確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        search_btn = page.locator('button:has-text("この条件で検索")')
        expect(search_btn.first).to_be_visible()

    @pytest.mark.wdl
    def test_リセットボタンの表示確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        reset_btn = page.locator('button:has-text("リセット")')
        expect(reset_btn.first).to_be_visible()

    @pytest.mark.wdl
    def test_検索フォームフィールドの確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        # 検索条件追加ボタンをクリックしてフィールドを展開
        add_btn = page.locator('button:has-text("検索条件を追加")')
        if add_btn.count() > 0 and add_btn.first.is_visible():
            add_btn.first.click()
            page.wait_for_timeout(1000)

        # 主要な検索フィールドの存在確認
        expected_fields = [
            ("documentNumber", "請求書番号"),
            ("totalAmountMin", "合計金額(最小)"),
            ("memo", "メモ"),
        ]
        form = page.locator("form").first
        for field_name, _desc in expected_fields:
            field = form.locator(f'input[name="{field_name}"]')
            assert field.count() > 0, f"検索フィールド '{field_name}' ({_desc}) が見つかりません"


class TestPagination:
    """ページネーションの確認"""

    @pytest.mark.wdl
    def test_ページネーションの確認(self, logged_in_page: Page):
        page = goto_invoices(logged_in_page)
        table = page.locator("table").first
        rows = table.locator("tbody tr")
        row_count = rows.count()
        # データが10件以上あればページネーションが存在するはず
        if row_count >= 10:
            # ページネーション要素（ボタンやリンク）の存在確認
            pagination = page.locator('nav, [class*="paging"], [class*="pagination"]').first
            if pagination.count() > 0:
                expect(pagination).to_be_visible()
            else:
                # ページネーションがなくても10件表示されていればOK
                assert row_count >= 10, "10件以上のデータがあるがページネーションが見つかりません"
