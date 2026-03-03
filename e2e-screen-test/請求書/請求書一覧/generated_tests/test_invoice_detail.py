"""
自動生成テスト: TOKIUM 請求書発行 - 請求書詳細画面（正常系）
対象: https://invoicing-staging.keihi.com/invoices/{UUID}

test_results対応: 各テストにTH-IDを付与し、conftest.pyのフックで
動画・ログ・JSONサマリーを自動保存する。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-staging.keihi.com"


# =============================================================================
# TH-ID マッピング
# =============================================================================
TH_ID_MAP = {
    "test_詳細ページの表示確認": "TH-ID01",
    "test_パンくずナビゲーションの確認": "TH-ID02",
    "test_アクションボタンの表示確認": "TH-ID03",
    "test_タブナビゲーションの確認": "TH-ID04",
    "test_取引先情報セクションの確認": "TH-ID05",
    "test_送付先情報セクションの確認": "TH-ID06",
    "test_帳票項目セクションの確認": "TH-ID07",
    "test_基本情報セクションの確認": "TH-ID08",
    "test_メモフォームの確認": "TH-ID09",
    "test_添付ファイルタブへの切替": "TH-ID10",
    "test_戻るボタンで一覧に戻る": "TH-ID11",
    "test_次の請求書ボタンでページ送り": "TH-ID12",
    "test_パンくずリンクで一覧に戻る": "TH-ID13",
    "test_取引先選択ダイアログの表示": "TH-ID14",
    "test_前の請求書ボタンでページ戻り": "TH-ID15",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    """テスト関数名からTH-IDを自動付与（[chromium]等のパラメータを除去して照合）"""
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


# =============================================================================
# ヘルパー関数
# =============================================================================

def goto_invoice_detail(logged_in_page: Page) -> Page:
    """請求書一覧から最初の行をクリックして詳細画面に遷移する"""
    page = logged_in_page
    page.goto(f"{BASE_URL}/invoices")
    page.locator("table").wait_for(state="visible")
    # 最初のデータ行の取引先名セルをクリック（チェックボックスを避ける）
    page.locator("table tbody tr").first.locator("td").nth(1).click()
    # 詳細画面のロード完了を待機
    page.get_by_role("heading", name="請求書").wait_for(state="visible")
    page.wait_for_url(re.compile(r"/invoices/[0-9a-f\-]{36}"), timeout=15000)
    return page


# =============================================================================
# テスト1: 詳細ページの表示確認
# =============================================================================

def test_詳細ページの表示確認(logged_in_page: Page):
    """請求書詳細ページの主要要素が正しく表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: ページタイトルの確認
    expect(page).to_have_title(re.compile(r"TOKIUM"))

    # Step3: 見出しの確認
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()

    # Step4: ステータス表示の確認（いずれかのステータスが表示されている）
    main = page.locator("main")
    has_status = (
        main.get_by_text("未送付").count() > 0
        or main.get_by_text("送付済み").count() > 0
        or main.get_by_text("送付中").count() > 0
    )
    assert has_status, "送付ステータスが表示されていない"


# =============================================================================
# テスト2: パンくず・ナビゲーション要素の確認
# =============================================================================

def test_パンくずナビゲーションの確認(logged_in_page: Page):
    """パンくず・ページ送り・戻るボタンが表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 戻るボタンの確認
    expect(page.get_by_role("button", name="戻る")).to_be_visible()

    # Step3: パンくず内の確認
    breadcrumb_nav = page.locator("main").locator("nav").first
    expect(breadcrumb_nav.get_by_role("link", name="請求書")).to_be_visible()
    expect(breadcrumb_nav.get_by_text("帳票情報")).to_be_visible()

    # Step4: ページ送りボタン・位置表示の確認
    expect(page.get_by_role("button", name="前の請求書")).to_be_visible()
    expect(page.get_by_role("button", name="次の請求書")).to_be_visible()
    expect(page.get_by_text(re.compile(r"\d+ / \d+件"))).to_be_visible()


# =============================================================================
# テスト3: アクションボタンの表示確認
# =============================================================================

def test_アクションボタンの表示確認(logged_in_page: Page):
    """送付済み・承認・削除ボタンが表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: アクションボタンの表示確認
    expect(page.get_by_role("button", name="送付済みにする")).to_be_visible()
    expect(page.get_by_role("button", name="承認する")).to_be_visible()
    expect(page.get_by_role("button", name="削除")).to_be_visible()


# =============================================================================
# テスト4: タブナビゲーションの確認
# =============================================================================

def test_タブナビゲーションの確認(logged_in_page: Page):
    """帳票情報タブと添付ファイルタブが表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: タブナビゲーションの確認
    expect(page.get_by_role("button", name="帳票情報")).to_be_visible()
    expect(page.get_by_role("button", name="添付ファイル")).to_be_visible()


# =============================================================================
# テスト5: 取引先情報セクションの確認
# =============================================================================

def test_取引先情報セクションの確認(logged_in_page: Page):
    """取引先情報セクションが正しく表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: セクション見出し・ラベルの確認
    expect(page.get_by_role("heading", name="取引先情報")).to_be_visible()
    expect(page.get_by_text("取引先コード")).to_be_visible()
    expect(page.get_by_text("取引先名").first).to_be_visible()

    # Step3: サブセクション見出しの確認
    expect(page.get_by_role("heading", name="送付先担当者情報")).to_be_visible()
    expect(page.get_by_role("heading", name="自社担当者情報")).to_be_visible()

    # Step4: 取引先選択ボタン
    expect(page.get_by_role("button", name="取引先を選択する")).to_be_visible()


# =============================================================================
# テスト6: 送付先情報セクションの確認
# =============================================================================

def test_送付先情報セクションの確認(logged_in_page: Page):
    """送付先情報セクションが正しく表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 送付先情報セクションの確認
    expect(page.get_by_role("heading", name="送付先情報")).to_be_visible()
    expect(page.get_by_text("送付方法")).to_be_visible()


# =============================================================================
# テスト7: 帳票項目セクションの確認
# =============================================================================

def test_帳票項目セクションの確認(logged_in_page: Page):
    """帳票項目セクションのラベルが正しく表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 帳票項目セクションの確認
    expect(page.get_by_role("heading", name="帳票項目")).to_be_visible()
    expect(page.get_by_text("合計金額")).to_be_visible()
    expect(page.get_by_text("請求日")).to_be_visible()
    expect(page.get_by_text("支払期日")).to_be_visible()
    expect(page.get_by_text("請求書番号")).to_be_visible()


# =============================================================================
# テスト8: 基本情報セクションの確認
# =============================================================================

def test_基本情報セクションの確認(logged_in_page: Page):
    """基本情報セクションが正しく表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 基本情報セクションの確認
    expect(page.get_by_role("heading", name="基本情報")).to_be_visible()
    expect(page.get_by_text("管理ID")).to_be_visible()
    expect(page.get_by_text("登録日時")).to_be_visible()
    expect(page.get_by_text("登録方法")).to_be_visible()
    expect(page.get_by_text("登録者")).to_be_visible()


# =============================================================================
# テスト9: メモフォームの確認
# =============================================================================

def test_メモフォームの確認(logged_in_page: Page):
    """メモ入力欄と保存ボタンが正しく表示されている"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: メモ入力欄の確認
    memo = page.get_by_role("textbox", name="メモ")
    expect(memo).to_be_visible()

    # Step3: 保存ボタンの確認
    expect(page.get_by_role("button", name="メモを保存する")).to_be_visible()


# =============================================================================
# テスト10: 添付ファイルタブへの切替
# =============================================================================

def test_添付ファイルタブへの切替(logged_in_page: Page):
    """添付ファイルタブに切り替えると、アップロード領域が表示される"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 添付ファイルタブをクリック
    page.get_by_role("button", name="添付ファイル").click()
    expect(page).to_have_url(re.compile(r"tab=attachment"))

    # Step3: アップロード領域の確認
    expect(page.get_by_role("button", name="ファイルを選択")).to_be_visible()
    expect(page.get_by_text("ここにファイルをドラッグ&ドロップ")).to_be_visible()

    # Step4: 使用状況セクションの確認
    expect(page.get_by_role("heading", name="添付ファイルの使用状況")).to_be_visible()
    expect(page.get_by_role("heading", name="添付件数")).to_be_visible()
    expect(page.get_by_role("heading", name="ファイルサイズ")).to_be_visible()


# =============================================================================
# テスト11: 戻るボタンで一覧に戻る
# =============================================================================

def test_戻るボタンで一覧に戻る(logged_in_page: Page):
    """戻るボタンをクリックすると請求書一覧画面に戻る"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 戻るボタンをクリック
    page.get_by_role("button", name="戻る").click()

    # Step3: 一覧画面に戻ったことを確認
    expect(page).to_have_url(re.compile(r"/invoices(\?|$)"))
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト12: 次の請求書ボタンでページ送り
# =============================================================================

def test_次の請求書ボタンでページ送り(logged_in_page: Page):
    """次の請求書ボタンをクリックすると別の詳細画面に遷移する"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 現在のURLを取得
    current_url = page.url

    # Step3: 次の請求書ボタンをクリック
    page.get_by_role("button", name="次の請求書").click()

    # Step4: ページ位置が「2 /」に変わるのを待機
    expect(page.get_by_text(re.compile(r"2 / \d+件"))).to_be_visible(timeout=15000)
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()


# =============================================================================
# テスト13: パンくず「請求書」リンクで一覧に戻る
# =============================================================================

def test_パンくずリンクで一覧に戻る(logged_in_page: Page):
    """パンくずの「請求書」リンクをクリックすると一覧画面に戻る"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: パンくず内の「請求書」リンクをクリック
    breadcrumb_nav = page.locator("main").locator("nav").first
    breadcrumb_nav.get_by_role("link", name="請求書").click()

    # Step3: 一覧画面に戻ったことを確認
    expect(page).to_have_url(re.compile(r"/invoices(\?|$)"), timeout=15000)
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト14: 取引先選択ダイアログの表示
# =============================================================================

def test_取引先選択ダイアログの表示(logged_in_page: Page):
    """「取引先を選択する」ボタンをクリックするとダイアログが表示される"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: 取引先選択ボタンをクリック
    page.get_by_role("button", name="取引先を選択する").click()

    # Step3: ダイアログの見出しが表示されることを確認
    expect(page.get_by_role("heading", name="取引先選択")).to_be_visible(timeout=10000)
    expect(page.get_by_text("現在の取引先")).to_be_visible()
    expect(page.get_by_role("button", name="検索")).to_be_visible()

    # Step4: 閉じるボタンの存在確認
    close_button = page.locator("button[class*='closeButton']").first
    expect(close_button).to_be_visible()


# =============================================================================
# テスト15: 前の請求書ボタンでページ戻り
# =============================================================================

def test_前の請求書ボタンでページ戻り(logged_in_page: Page):
    """次の請求書に進んだ後、前の請求書ボタンで元に戻れる"""

    # Step1: 詳細ページに遷移
    page = goto_invoice_detail(logged_in_page)

    # Step2: まず次の請求書へ移動
    page.get_by_role("button", name="次の請求書").click()
    expect(page.get_by_text(re.compile(r"2 / \d+件"))).to_be_visible(timeout=15000)

    # Step3: 前の請求書ボタンをクリック
    page.get_by_role("button", name="前の請求書").click()

    # Step4: ページ位置が「1 /」に戻ることを確認
    expect(page.get_by_text(re.compile(r"1 / \d+件"))).to_be_visible(timeout=15000)
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()
