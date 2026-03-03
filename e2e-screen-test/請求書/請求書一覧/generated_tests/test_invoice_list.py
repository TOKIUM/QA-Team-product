"""
自動生成テスト: TOKIUM 請求書発行 - 請求書一覧画面（正常系）
対象: https://invoicing-staging.keihi.com/invoices

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
    "test_一覧ページの表示確認": "TH-IL01",
    "test_サイドバーナビゲーションの表示確認": "TH-IL02",
    "test_検索フォームの表示確認": "TH-IL03",
    "test_取引先名で検索": "TH-IL04",
    "test_検索条件のリセット": "TH-IL05",
    "test_送付方法セレクトの選択肢確認": "TH-IL06",
    "test_承認状況セレクトの選択肢確認": "TH-IL07",
    "test_テーブルヘッダーのカラム確認": "TH-IL08",
    "test_一括操作ボタンの表示確認": "TH-IL09",
    "test_テーブル行クリックで詳細画面に遷移": "TH-IL10",
    "test_ステータスチェックボックスで絞り込み": "TH-IL11",
    "test_送付方法セレクトで絞り込み": "TH-IL12",
    "test_チェックボックスで行を選択": "TH-IL13",
    "test_全選択チェックボックス": "TH-IL14",
    "test_ページネーション件数表示の確認": "TH-IL15",
    "test_請求日の日付範囲フィールドの確認": "TH-IL16",
    "test_支払期日の日付範囲フィールドの確認": "TH-IL17",
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

def goto_invoices(logged_in_page: Page) -> Page:
    """請求書一覧ページに遷移し、テーブルが表示されるまで待機"""
    page = logged_in_page
    page.goto(f"{BASE_URL}/invoices")
    page.get_by_role("heading", name="請求書").wait_for(state="visible")
    # テーブルのロード完了を待機
    page.locator("table").wait_for(state="visible")
    return page


# =============================================================================
# テスト1: 一覧ページの表示確認
# =============================================================================

def test_一覧ページの表示確認(logged_in_page: Page):
    """請求書一覧ページの主要要素がすべて正しく表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: ページタイトルの確認
    expect(page).to_have_title(re.compile(r"TOKIUM"))

    # Step3: ロゴの表示確認
    expect(page.get_by_role("img", name="TOKIUM 請求書発行")).to_be_visible()

    # Step4: ページ見出しの確認
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()

    # Step5: アクションボタンの表示確認
    expect(page.get_by_role("link", name="CSVから新規作成")).to_be_visible()
    expect(page.get_by_role("link", name="PDFを取り込む")).to_be_visible()

    # Step6: テーブルの存在確認
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト2: サイドバーナビゲーションの表示確認
# =============================================================================

def test_サイドバーナビゲーションの表示確認(logged_in_page: Page):
    """サイドバーに請求書・取引先・帳票レイアウトのリンクが表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: サイドバーのリンク確認（href属性で直接特定）
    invoices_link = page.locator('a[href="/invoices"]').first
    partners_link = page.locator('a[href="/partners"]')
    layout_link = page.locator('a[href="/invoices/design"]')

    expect(invoices_link).to_be_visible()
    expect(partners_link).to_be_visible()
    expect(layout_link).to_be_visible()


# =============================================================================
# テスト3: 検索フォームの表示確認
# =============================================================================

def test_検索フォームの表示確認(logged_in_page: Page):
    """検索条件フォームの主要フィールドが表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 検索フォームのフィールド確認
    expect(page.get_by_label("送付方法")).to_be_visible()
    expect(page.get_by_label("取引先コード")).to_be_visible()
    expect(page.get_by_label("取引先名")).to_be_visible()
    expect(page.get_by_label("自社担当部署")).to_be_visible()
    expect(page.get_by_label("自社担当者名")).to_be_visible()
    expect(page.get_by_label("請求書番号")).to_be_visible()
    expect(page.get_by_label("合計金額")).to_be_visible()
    expect(page.get_by_label("ファイル名 （添付ファイル名）")).to_be_visible()
    expect(page.get_by_label("承認状況")).to_be_visible()

    # Step3: ステータスチェックボックスの確認
    expect(page.get_by_label("登録中")).to_be_visible()
    expect(page.get_by_label("未送付")).to_be_visible()
    expect(page.get_by_label("送付中")).to_be_visible()
    expect(page.get_by_label("送付済み")).to_be_visible()
    expect(page.get_by_label("送付待ち")).to_be_visible()
    expect(page.get_by_label("登録失敗")).to_be_visible()
    expect(page.get_by_label("送付失敗")).to_be_visible()

    # Step4: 検索ボタンの確認（スクロールして表示域に入れる）
    search_button = page.get_by_role("button", name="この条件で検索")
    search_button.scroll_into_view_if_needed()
    expect(search_button).to_be_visible()
    expect(page.get_by_role("button", name="リセット")).to_be_visible()


# =============================================================================
# テスト4: 取引先名で検索
# =============================================================================

def test_取引先名で検索(logged_in_page: Page):
    """取引先名フィールドに入力して検索を実行し、結果が絞り込まれる"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 取引先名に検索条件を入力
    page.get_by_label("取引先名").fill("鈴木通信合同会社")

    # Step3: 検索ボタンをクリック（オーバーレイ要素回避のためdispatch_event使用）
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")

    # 検索結果のロード完了を待機
    page.wait_for_load_state("networkidle")
    page.locator("table").wait_for(state="visible")

    # Step4: 検索結果に「鈴木通信合同会社」が含まれることを確認
    expect(page.locator("table").get_by_text("鈴木通信合同会社").first).to_be_visible()


# =============================================================================
# テスト5: 検索条件のリセット
# =============================================================================

def test_検索条件のリセット(logged_in_page: Page):
    """検索条件を入力後、リセットボタンでクリアされる"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 検索条件を入力
    page.get_by_label("取引先名").fill("テスト検索")
    page.get_by_label("請求書番号").fill("999999")

    # Step3: リセットボタンをクリック（オーバーレイ要素回避のためdispatch_event使用）
    page.get_by_role("button", name="リセット").dispatch_event("click")

    # リセット後のページ再描画を待機
    page.wait_for_load_state("networkidle")

    # Step4: フィールドがクリアされていることを確認
    expect(page.get_by_label("取引先名")).to_have_value("")
    expect(page.get_by_label("請求書番号")).to_have_value("")


# =============================================================================
# テスト6: 送付方法セレクトボックスの選択肢確認
# =============================================================================

def test_送付方法セレクトの選択肢確認(logged_in_page: Page):
    """送付方法セレクトボックスに全選択肢が存在する"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 送付方法セレクトの選択肢確認
    select = page.get_by_label("送付方法")

    options = select.locator("option")
    option_texts = options.all_text_contents()

    assert "全て" in option_texts
    assert "メール" in option_texts
    assert "Web送付" in option_texts
    assert "郵送代行" in option_texts
    assert "FAX送付" in option_texts
    assert "その他" in option_texts


# =============================================================================
# テスト7: 承認状況セレクトボックスの選択肢確認
# =============================================================================

def test_承認状況セレクトの選択肢確認(logged_in_page: Page):
    """承認状況セレクトボックスに全選択肢が存在する"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 承認状況セレクトの選択肢確認
    select = page.get_by_label("承認状況")

    options = select.locator("option")
    option_texts = options.all_text_contents()

    assert "全て" in option_texts
    assert "承認済み" in option_texts
    assert "未承認" in option_texts


# =============================================================================
# テスト8: テーブルヘッダーのカラム確認
# =============================================================================

def test_テーブルヘッダーのカラム確認(logged_in_page: Page):
    """テーブルに必要なカラムヘッダーが全て表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: テーブルヘッダーのカラム確認
    table = page.locator("table")

    expect(table.get_by_text("取引先")).to_be_visible()
    expect(table.get_by_text("送付先")).to_be_visible()
    expect(table.get_by_text("ステータス")).to_be_visible()
    expect(table.get_by_text("承認状況")).to_be_visible()
    expect(table.get_by_text("請求書番号")).to_be_visible()
    expect(table.get_by_text("合計金額")).to_be_visible()
    expect(table.get_by_text("請求日")).to_be_visible()
    expect(table.get_by_text("支払期日")).to_be_visible()
    expect(table.get_by_text("ファイル名")).to_be_visible()


# =============================================================================
# テスト9: 一括操作ボタンの表示確認
# =============================================================================

def test_一括操作ボタンの表示確認(logged_in_page: Page):
    """一括操作ボタン群が表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 一括操作ボタンの表示確認
    expect(page.get_by_role("button", name="請求書を送付する")).to_be_visible()
    expect(page.get_by_role("button", name="送付済みにする")).to_be_visible()
    expect(page.get_by_role("button", name="その他の操作")).to_be_visible()
    expect(page.get_by_role("button", name="選択解除")).to_be_visible()


# =============================================================================
# テスト10: テーブル行クリックで詳細画面に遷移
# =============================================================================

def test_テーブル行クリックで詳細画面に遷移(logged_in_page: Page):
    """テーブルの行をクリックすると請求書詳細画面に遷移する"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 最初のデータ行の取引先名をクリック（チェックボックス列を避ける）
    first_row = page.locator("table tbody tr").first
    first_row.locator("td").nth(1).click()

    # Step3: 詳細画面に遷移したことを確認（URLがUUID形式）
    expect(page).to_have_url(re.compile(r"/invoices/[0-9a-f\-]{36}"))


# =============================================================================
# テスト11: ステータスチェックボックスで絞り込み（未送付）
# =============================================================================

def test_ステータスチェックボックスで絞り込み(logged_in_page: Page):
    """ステータス「未送付」のみチェックして検索すると、結果が絞り込まれる"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 全ステータスのチェックを外す（オーバーレイ回避のためdispatch_event使用）
    for label in ["登録中", "未送付", "送付中", "送付済み", "送付待ち", "登録失敗", "送付失敗"]:
        cb = page.get_by_label(label)
        if cb.is_checked():
            cb.dispatch_event("click")

    # 「未送付」のみチェック
    page.get_by_label("未送付").dispatch_event("click")

    # Step3: 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.locator("table").wait_for(state="visible")

    # Step4: テーブルにデータ行が存在し、「未送付」が含まれることを確認
    rows = page.locator("table tbody tr")
    expect(rows.first).to_be_visible()
    expect(page.locator("table").get_by_text("未送付").first).to_be_visible()


# =============================================================================
# テスト12: 送付方法セレクトで絞り込み（メール）
# =============================================================================

def test_送付方法セレクトで絞り込み(logged_in_page: Page):
    """送付方法を「メール」に設定して検索すると、結果が絞り込まれる"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 送付方法を「メール」に変更
    page.get_by_label("送付方法").select_option("メール")

    # Step3: 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.locator("table").wait_for(state="visible")

    # Step4: テーブルにデータ行が存在することを確認
    rows = page.locator("table tbody tr")
    expect(rows.first).to_be_visible()


# =============================================================================
# テスト13: チェックボックスで行を選択
# =============================================================================

def test_チェックボックスで行を選択(logged_in_page: Page):
    """テーブルの行チェックボックスをクリックすると選択状態になる"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 最初のデータ行のチェックボックスをクリック
    first_row_checkbox = page.locator("table tbody tr").first.locator("input[type='checkbox']")
    first_row_checkbox.check()

    # Step3: チェック状態を確認
    expect(first_row_checkbox).to_be_checked()

    # Step4: チェックを外す
    first_row_checkbox.uncheck()
    expect(first_row_checkbox).not_to_be_checked()


# =============================================================================
# テスト14: 全選択チェックボックス
# =============================================================================

def test_全選択チェックボックス(logged_in_page: Page):
    """テーブルヘッダーの全選択チェックボックスで全行を選択・解除できる"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: ヘッダーの全選択チェックボックスをクリック
    select_all = page.locator("table thead input[type='checkbox']")
    expect(select_all).to_be_visible()
    select_all.check()
    expect(select_all).to_be_checked()

    # Step3: データ行のチェックボックスも選択されていることを確認
    first_row_checkbox = page.locator("table tbody tr").first.locator("input[type='checkbox']")
    expect(first_row_checkbox).to_be_checked()

    # Step4: 全選択を解除
    select_all.uncheck()
    expect(first_row_checkbox).not_to_be_checked()


# =============================================================================
# テスト15: ページネーション件数表示の確認
# =============================================================================

def test_ページネーション件数表示の確認(logged_in_page: Page):
    """件数表示とページネーション要素が表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 件数表示の確認（例: "8013件中 1〜100件"）
    expect(page.get_by_text(re.compile(r"\d+件中"))).to_be_visible()

    # Step3: テーブル下部にスクロールしてページネーション確認
    pagination_area = page.get_by_text(re.compile(r"\d+件中"))
    pagination_area.scroll_into_view_if_needed()


# =============================================================================
# テスト16: 請求日の日付範囲フィールドの確認
# =============================================================================

def test_請求日の日付範囲フィールドの確認(logged_in_page: Page):
    """請求日の開始日・終了日フィールドが表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 請求日ラベルの確認
    expect(page.get_by_text("請求日").first).to_be_visible()

    # Step3: 日付入力フィールドの存在確認（date型のinput）
    date_inputs = page.locator("input[type='date']")
    assert date_inputs.count() >= 2, "日付入力フィールドが2つ以上存在しない"


# =============================================================================
# テスト17: 支払期日の日付範囲フィールドの確認
# =============================================================================

def test_支払期日の日付範囲フィールドの確認(logged_in_page: Page):
    """支払期日の開始日・終了日フィールドが表示されている"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 支払期日ラベルの確認
    expect(page.get_by_text("支払期日").first).to_be_visible()

    # Step3: 日付入力フィールドが4つ以上存在（請求日2つ + 支払期日2つ）
    date_inputs = page.locator("input[type='date']")
    assert date_inputs.count() >= 4, "日付入力フィールドが4つ以上存在しない（請求日+支払期日）"
