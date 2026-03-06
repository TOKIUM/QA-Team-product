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
    "test_異常系_存在しないUUIDで直接アクセス": "TH-ID16",
    "test_異常系_メモに特殊文字を入力して保存": "TH-ID17",
    "test_異常系_取引先選択ダイアログで存在しない名前を検索": "TH-ID18",
    "test_境界値_1件目で前の請求書ボタンがdisabled": "TH-ID19",
    "test_境界値_最終件で次の請求書ボタンがdisabled": "TH-ID20",
    # 状態遷移（基準5）
    "test_状態遷移_タブ切替を繰り返しても正常動作する": "TH-ID21",
    "test_状態遷移_ページ送り後ブラウザバックで元の請求書に戻る": "TH-ID22",
    # 冪等性（基準7）
    "test_冪等性_ページ送りボタン連打で安定する": "TH-ID23",
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


# =============================================================================
# テスト16: 異常系 - 存在しないUUIDで直接アクセス
# =============================================================================

def test_異常系_存在しないUUIDで直接アクセス(logged_in_page: Page):
    """存在しないUUIDの詳細URLにアクセスするとエラー表示またはリダイレクトされる"""

    page = logged_in_page
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    page.goto(f"{BASE_URL}/invoices/{fake_uuid}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # アプリがクラッシュしていないこと（コンテンツが存在する）
    body_text = page.inner_text("body")
    assert len(body_text) > 0, "存在しないUUIDアクセス後にページが空"

    # エラーページ表示、または一覧にリダイレクト（どちらも許容）
    url = page.url
    is_error_page = "エラー" in body_text or "見つかりません" in body_text
    is_redirected = "/invoices" in url and fake_uuid not in url
    is_on_detail = fake_uuid in url

    # 詳細ページに留まっている場合はエラー表示があるはず
    if is_on_detail:
        assert is_error_page, \
            f"存在しないUUIDでアクセスしたがエラー表示もリダイレクトもない（URL: {url}）"


# =============================================================================
# テスト17: 異常系 - メモに特殊文字を入力して保存
# =============================================================================

def test_異常系_メモに特殊文字を入力して保存(logged_in_page: Page):
    """メモにXSS/特殊文字を入力して保存してもページが正常動作する"""

    page = goto_invoice_detail(logged_in_page)

    # メモフォームに特殊文字を入力
    memo = page.get_by_role("textbox", name="メモ")
    original_value = memo.input_value()
    test_value = "<script>alert('XSS')</script> '; DROP TABLE; -- 日本語テスト★♪"
    memo.fill(test_value)

    # 保存ボタンをクリック
    page.get_by_role("button", name="メモを保存する").click()
    page.wait_for_timeout(3000)

    # ページが正常であること（クラッシュしていない）
    expect(page.get_by_role("heading", name="請求書")).to_be_visible(timeout=10000)

    # メモフォームが引き続き表示されていること
    expect(memo).to_be_visible()

    # 元の値に戻す（テストデータ汚染防止）
    memo.fill(original_value)
    page.get_by_role("button", name="メモを保存する").click()
    page.wait_for_timeout(2000)


# =============================================================================
# テスト18: 異常系 - 取引先選択ダイアログで存在しない名前を検索
# =============================================================================

def test_異常系_取引先選択ダイアログで存在しない名前を検索(logged_in_page: Page):
    """取引先選択ダイアログで存在しない名前を検索すると0件になる"""

    page = goto_invoice_detail(logged_in_page)

    # 取引先選択ダイアログを開く
    page.get_by_role("button", name="取引先を選択する").click()
    dialog = page.locator("article").filter(
        has=page.get_by_role("heading", name="取引先選択")
    )
    expect(dialog).to_be_visible(timeout=10000)

    # ダイアログ内のテキスト入力欄を探す
    search_input = dialog.get_by_role("textbox").first
    search_input.fill("存在しない会社名ZZZZZ99999")
    dialog.get_by_role("button", name="検索").click()
    page.wait_for_timeout(2000)

    # ダイアログが正常に表示されていること（クラッシュしていない）
    expect(page.get_by_role("heading", name="取引先選択")).to_be_visible()

    # 検索結果が0件（ラジオボタンがない = 取引先なし）
    dialog_text = dialog.inner_text()
    radio_count = dialog.get_by_role("radio").count()
    has_no_results = radio_count == 0 or "0件" in dialog_text
    assert has_no_results, \
        f"存在しない取引先名で検索したが{radio_count}件のラジオボタンが表示されている"

    # ダイアログを閉じる
    close_button = dialog.locator("button").first
    close_button.click()
    page.wait_for_timeout(1000)


# =============================================================================
# テスト19: 境界値 - 1件目で前の請求書ボタンがdisabled
# =============================================================================

def test_境界値_1件目で前の請求書ボタンがdisabled(logged_in_page: Page):
    """1件目の請求書表示時、前の請求書ボタンがdisabledであること（境界値: 先頭）"""

    page = goto_invoice_detail(logged_in_page)

    # 1件目であることを確認
    expect(page.get_by_text(re.compile(r"1 / \d+件"))).to_be_visible(timeout=10000)

    # 前の請求書ボタンがdisabledであること
    prev_btn = page.get_by_role("button", name="前の請求書")
    expect(prev_btn).to_be_disabled()

    # 次の請求書ボタンはenabledであること（対比確認）
    next_btn = page.get_by_role("button", name="次の請求書")
    expect(next_btn).to_be_enabled()


# =============================================================================
# テスト20: 境界値 - 最終件で次の請求書ボタンがdisabled
# =============================================================================

def test_境界値_最終件で次の請求書ボタンがdisabled(logged_in_page: Page):
    """最終件の請求書表示時、次の請求書ボタンがdisabledであること（境界値: 末尾）"""

    page = logged_in_page

    # 一覧ページで100件表示に設定して総件数を取得
    page.goto(f"{BASE_URL}/invoices")
    page.locator("table").wait_for(state="visible")
    display_select = page.locator("main").locator("select").last
    display_select.select_option("100")
    page.wait_for_timeout(2000)
    count_text = page.locator("text=/\\d+件中/").text_content()
    total = int(re.search(r"(\d+)件中", count_text).group(1))

    # 最終ページを計算（100件表示）
    last_page = (total + 99) // 100
    page.goto(f"{BASE_URL}/invoices?page={last_page}&perPage=100")
    page.wait_for_load_state("networkidle")
    page.locator("table").wait_for(state="visible")
    page.wait_for_timeout(2000)

    # 最終ページの最後の行をクリック
    rows = page.locator("table tbody tr")
    row_count = rows.count()
    assert row_count > 0, f"最終ページ({last_page})にデータ行がない"
    rows.last.locator("td").nth(1).click()
    page.wait_for_url(re.compile(r"/invoices/[0-9a-f\-]{36}"), timeout=15000)
    page.wait_for_timeout(1000)

    # 最終件であることを確認
    position_text = page.get_by_text(re.compile(r"\d+ / \d+件")).text_content()
    current_match = re.search(r"(\d+) / (\d+)件", position_text)
    current_pos = int(current_match.group(1))
    total_count = int(current_match.group(2))

    assert current_pos == total_count, \
        f"最終件ではない（{current_pos} / {total_count}）"

    # 次の請求書ボタンがdisabledであること
    next_btn = page.get_by_role("button", name="次の請求書")
    expect(next_btn).to_be_disabled()

    # 前の請求書ボタンはenabledであること（対比確認）
    prev_btn = page.get_by_role("button", name="前の請求書")
    expect(prev_btn).to_be_enabled()


# =============================================================================
# テスト21: 状態遷移 - タブ切替を繰り返しても正常動作する
# =============================================================================

def test_状態遷移_タブ切替を繰り返しても正常動作する(logged_in_page: Page):
    """帳票情報→添付ファイル→帳票情報→添付ファイルとタブを繰り返し切替しても正常動作する"""

    page = goto_invoice_detail(logged_in_page)

    # 初回: 帳票情報タブが表示されていること
    expect(page.locator("text=取引先情報").first).to_be_visible(timeout=5000)

    # 添付ファイルタブに切替
    page.get_by_role("button", name="添付ファイル").click()
    page.wait_for_timeout(2000)
    expect(page).to_have_url(re.compile(r"tab=attachment"))

    # 帳票情報タブに戻る
    page.get_by_role("button", name="帳票情報").click()
    page.wait_for_timeout(2000)
    expect(page.locator("text=取引先情報").first).to_be_visible(timeout=5000)

    # もう一度添付ファイルタブに切替
    page.get_by_role("button", name="添付ファイル").click()
    page.wait_for_timeout(2000)
    expect(page).to_have_url(re.compile(r"tab=attachment"))

    # 最終状態: ページが正常表示されていること
    body_text = page.inner_text("body")
    assert len(body_text) > 0, "タブ切替後にページが空"
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()


# =============================================================================
# テスト22: 状態遷移 - ページ送り後ブラウザバックで元の請求書に戻る
# =============================================================================

def test_状態遷移_ページ送り後ブラウザバックで元の請求書に戻る(logged_in_page: Page):
    """次の請求書に遷移後、ブラウザバックで元の請求書に戻れる"""

    page = goto_invoice_detail(logged_in_page)

    # 元のURLを記録
    original_url = page.url

    # 位置情報を記録
    position_text = page.locator("text=/\\d+ \\/ \\d+/").first.text_content()

    # 次の請求書に遷移
    next_btn = page.get_by_role("button", name="次の請求書")
    if next_btn.is_enabled():
        next_btn.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # URLが変わったことを確認
        assert page.url != original_url, "次の請求書ボタンでURLが変わらなかった"

        # ブラウザバック
        page.go_back()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 元のURLに戻ったことを確認
        assert page.url == original_url, \
            f"ブラウザバック後にURLが異なる（期待: {original_url}, 実際: {page.url}）"

        # 位置情報が元に戻っていること
        back_position = page.locator("text=/\\d+ \\/ \\d+/").first.text_content()
        assert back_position == position_text, \
            f"ブラウザバック後に位置が異なる（期待: {position_text}, 実際: {back_position}）"


# =============================================================================
# テスト23: 冪等性 - ページ送りボタン連打で安定する
# =============================================================================

def test_冪等性_ページ送りボタン連打で安定する(logged_in_page: Page):
    """次の請求書ボタンを素早く3回クリックしても画面が安定する"""

    page = goto_invoice_detail(logged_in_page)

    next_btn = page.get_by_role("button", name="次の請求書")
    if not next_btn.is_enabled():
        pytest.skip("次の請求書ボタンがdisabled（1件目が最後の場合）")

    # 3回素早くクリック
    next_btn.click()
    page.wait_for_timeout(300)
    next_btn = page.get_by_role("button", name="次の請求書")
    if next_btn.is_enabled():
        next_btn.click()
        page.wait_for_timeout(300)
        next_btn = page.get_by_role("button", name="次の請求書")
        if next_btn.is_enabled():
            next_btn.click()

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # ページが正常表示されていること
    expect(page).to_have_url(re.compile(r"/invoices/[a-f0-9-]+"))
    expect(page.get_by_role("heading", name="請求書")).to_be_visible(timeout=10000)

    # 位置情報が正常であること
    position_text = page.locator("text=/\\d+ \\/ \\d+/").first.text_content()
    match = re.search(r"(\d+) / (\d+)", position_text)
    assert match, f"位置情報が取得できない: {position_text}"
    current = int(match.group(1))
    total = int(match.group(2))
    assert 1 <= current <= total, f"位置が範囲外: {current} / {total}"
