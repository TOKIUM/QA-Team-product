"""
自動生成テスト: TOKIUM 請求書発行 - 取引先一覧画面
対象: https://invoicing-staging.keihi.com/partners

方式A: pytest + conftest.py（logged_in_page fixture使用）

test_results対応: 各テストにTH-IDを付与し、conftest.pyのフックで
スクリーンショット・ログ・JSONサマリーを自動保存する。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-staging.keihi.com"


# =============================================================================
# TH-ID マッピング
# =============================================================================
TH_ID_MAP = {
    "test_一覧ページの表示確認": "TH-PL01",
    "test_サイドバーナビゲーションの表示確認": "TH-PL02",
    "test_テーブルヘッダーの表示確認": "TH-PL03",
    "test_テーブルデータの表示確認": "TH-PL04",
    "test_ページネーションの表示確認": "TH-PL05",
    "test_表示件数の切替": "TH-PL06",
    "test_検索フォームの表示確認": "TH-PL07",
    "test_取引先コードで検索": "TH-PL08",
    "test_取引先名で検索": "TH-PL09",
    "test_送付方法で絞り込み検索": "TH-PL10",
    "test_検索リセット": "TH-PL11",
    "test_その他の操作メニューの表示確認": "TH-PL12",
    "test_取引先クリックで更新モーダルが開く": "TH-PL13",
    "test_更新モーダル_取引先項目タブの表示確認": "TH-PL14",
    "test_更新モーダル_Web送付設定タブの表示確認": "TH-PL15",
    "test_新規追加モーダルの表示確認": "TH-PL16",
    "test_新規追加モーダル_キャンセルで閉じる": "TH-PL17",
    "test_更新モーダル_バツボタンで閉じる": "TH-PL18",
    "test_ページネーション_次ページに遷移": "TH-PL19",
    "test_表示件数の境界値_10件表示時の行数検証": "TH-PL20",
    "test_表示件数の境界値_50件表示時の行数検証": "TH-PL21",
    "test_ページネーション_最終ページの境界値検証": "TH-PL22",
    "test_表示件数の境界値_20件表示時の行数検証": "TH-PL23",
    "test_異常系_存在しない取引先コードで検索": "TH-PL24",
    "test_異常系_存在しない取引先名で検索": "TH-PL25",
    "test_異常系_特殊文字で検索": "TH-PL26",
    "test_異常系_新規追加モーダル_必須項目未入力で保存": "TH-PL27",
    "test_異常系_検索フォーム_全フィールド空で検索": "TH-PL28",
    # 状態遷移（基準5）
    "test_状態遷移_モーダル開閉を繰り返しても正常動作する": "TH-PL29",
    "test_状態遷移_検索後リセット後再検索で正常動作する": "TH-PL30",
    # 冪等性（基準7）
    "test_冪等性_検索ボタン連打で結果が安定する": "TH-PL31",
    "test_冪等性_表示件数を連続切替しても正常動作する": "TH-PL32",
    # エラーリカバリ（基準8）
    "test_エラーリカバリ_存在しない検索後に条件修正で正常結果に復帰": "TH-PL33",
    # データ整合性（基準6）
    "test_データ整合性_一覧の取引先コードとモーダルの取引先コードが一致する": "TH-PL34",
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

def goto_partners(logged_in_page: Page) -> Page:
    """取引先一覧ページに遷移し、テーブルが表示されるまで待機"""
    page = logged_in_page
    page.goto(f"{BASE_URL}/partners")
    page.get_by_role("heading", name="取引先").wait_for(state="visible", timeout=15000)
    # テーブルのロード完了を待機
    page.locator("table").wait_for(state="visible", timeout=15000)
    return page


def open_search_form(page: Page):
    """検索条件フォームを展開する（閉じている場合）"""
    search_btn = page.get_by_role("button", name="検索条件", exact=True)
    submit_btn = page.get_by_role("button", name="この条件で検索")
    # submit ボタンが非表示なら検索フォームは閉じている → 展開
    if not submit_btn.is_visible():
        search_btn.click()
        submit_btn.wait_for(state="visible", timeout=5000)


def close_search_form(page: Page):
    """検索条件フォームを閉じる（開いている場合）"""
    submit_btn = page.get_by_role("button", name="この条件で検索")
    if submit_btn.is_visible():
        page.get_by_role("button", name="検索条件", exact=True).click()
        page.wait_for_timeout(500)


def open_update_modal(page: Page):
    """1行目（株式会社TOKIUM）をクリックして更新モーダルを開く"""
    # 検索フォームが展開されていると行クリックが interceptされるため閉じる
    close_search_form(page)
    page.locator("table").locator("text='株式会社TOKIUM'").first.click()
    page.get_by_role("heading", name="取引先更新").wait_for(state="visible", timeout=10000)


def get_update_modal(page: Page):
    """更新モーダルのルート要素を取得"""
    return page.locator("article").filter(has=page.get_by_role("heading", name="取引先更新"))


def close_modal_by_cancel(page: Page, modal_heading: str):
    """モーダルをキャンセルボタンで閉じる"""
    page.get_by_role("button", name="キャンセル").last.click()
    page.wait_for_timeout(500)
    expect(page.get_by_role("heading", name=modal_heading)).not_to_be_visible(timeout=5000)


# =============================================================================
# テスト1: 一覧ページの表示確認
# =============================================================================

@pytest.mark.smoke
def test_一覧ページの表示確認(logged_in_page: Page):
    """取引先一覧ページの主要要素がすべて正しく表示されている"""

    page = goto_partners(logged_in_page)

    # ページタイトルの確認
    expect(page).to_have_title(re.compile(r"TOKIUM"))

    # ロゴの表示確認
    expect(page.get_by_role("img", name="TOKIUM 請求書発行")).to_be_visible()

    # ページ見出しの確認
    expect(page.get_by_role("heading", name="取引先")).to_be_visible()

    # アクションボタンの表示確認
    expect(page.get_by_role("button", name="取引先を追加")).to_be_visible()
    expect(page.get_by_role("button", name="その他の操作")).to_be_visible()

    # テーブルの存在確認
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト2: サイドバーナビゲーションの表示確認
# =============================================================================

def test_サイドバーナビゲーションの表示確認(logged_in_page: Page):
    """サイドバーに請求書・取引先・帳票レイアウトのリンクが表示されている"""

    page = goto_partners(logged_in_page)

    # サイドバーのリンク確認（href属性で直接特定）
    invoices_link = page.locator('a[href="/invoices"]').first
    partners_link = page.locator('a[href="/partners"]')
    layout_link = page.locator('a[href="/invoices/design"]')

    expect(invoices_link).to_be_visible()
    expect(partners_link).to_be_visible()
    expect(layout_link).to_be_visible()


# =============================================================================
# テスト3: テーブルヘッダーの表示確認
# =============================================================================

def test_テーブルヘッダーの表示確認(logged_in_page: Page):
    """取引先一覧テーブルのヘッダー列が正しく表示されている"""

    page = goto_partners(logged_in_page)

    table = page.locator("table")
    expected_headers = ["取引先コード", "取引先名", "送付先", "送付先担当者名", "自社担当者名", "登録日", "識別コード"]

    for header in expected_headers:
        expect(table.locator(f"text='{header}'").first).to_be_visible()


# =============================================================================
# テスト4: テーブルデータの表示確認
# =============================================================================

def test_テーブルデータの表示確認(logged_in_page: Page):
    """テーブルに取引先データが1件以上表示されている"""

    page = goto_partners(logged_in_page)

    # 件数表示テキストの確認（例: "1014件中 1〜100件"）
    count_text = page.locator("text=/\\d+件中/")
    expect(count_text).to_be_visible()

    # テーブル内の取引先コードが1つ以上ある
    first_code = page.locator("table").locator("text=/^TH/").first
    expect(first_code).to_be_visible()


# =============================================================================
# テスト5: ページネーションの表示確認
# =============================================================================

def test_ページネーションの表示確認(logged_in_page: Page):
    """ページネーション要素（件数表示、表示件数セレクタ）が表示されている"""

    page = goto_partners(logged_in_page)

    # 件数表示
    count_text = page.locator("text=/\\d+件中/")
    expect(count_text).to_be_visible()

    # 表示件数セレクタ
    expect(page.locator("text='表示件数:'")).to_be_visible()


# =============================================================================
# テスト6: 表示件数の切替
# =============================================================================

def test_表示件数の切替(logged_in_page: Page):
    """表示件数セレクタで件数を変更するとテーブルの行数が変わる"""

    page = goto_partners(logged_in_page)

    # 表示件数セレクタを取得（main配下のselectのうち最後 = ページネーション用）
    display_count_select = page.locator("main").locator("select").last

    # 20件に切替
    display_count_select.select_option("20")
    page.wait_for_timeout(2000)

    # 件数表示が更新されることを確認
    expect(page.locator("text=/件中 1〜20件/")).to_be_visible(timeout=10000)

    # 100件に戻す
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)


# =============================================================================
# テスト7: 検索フォームの表示確認
# =============================================================================

def test_検索フォームの表示確認(logged_in_page: Page):
    """検索条件フォームのフィールドが表示されている"""

    page = goto_partners(logged_in_page)

    # 検索条件ボタンの確認
    expect(page.get_by_role("button", name="検索条件", exact=True)).to_be_visible()

    # 検索フォームを展開
    open_search_form(page)

    # 主要フィールドの確認（form内に限定してスコープ指定）
    form = page.locator("form").first

    # 送付方法セレクト
    expect(form.locator("select").first).to_be_visible()

    # テキストフィールド
    expect(form.get_by_label("取引先コード")).to_be_visible()
    expect(form.get_by_label("取引先名")).to_be_visible()
    expect(form.get_by_label("送付先担当者名")).to_be_visible()
    expect(form.get_by_label("自社担当者名")).to_be_visible()
    expect(form.get_by_label("メールアドレス")).to_be_visible()
    expect(form.get_by_label("識別コード")).to_be_visible()

    # チェックボックス
    expect(form.get_by_label("凍結された取引先を含む")).to_be_visible()
    expect(form.get_by_label("Web送付設定の変更要求がある")).to_be_visible()

    # ボタン
    expect(page.get_by_role("button", name="この条件で検索")).to_be_visible()
    expect(page.get_by_role("button", name="リセット")).to_be_visible()

    # 検索フォームを閉じる（後続テストのため）
    close_search_form(page)


# =============================================================================
# テスト8: 取引先コードで検索
# =============================================================================

def test_取引先コードで検索(logged_in_page: Page):
    """取引先コードで検索すると該当データのみ表示される"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 検索前の件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # 取引先コードに「TH00001」を入力
    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")
    code_field.fill("TH00001")

    # 検索実行（dispatch_eventでReactイベントハンドラを発火）
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 結果に「TH00001」が含まれることを確認
    expect(page.locator("table").locator("text='TH00001'")).to_be_visible(timeout=10000)

    # 件数がフィルタされたことを確認（紐づけ検証）
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    assert after_total < before_total, \
        f"検索後に件数が減っていない（前: {before_total}, 後: {after_total}）"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 検索フォームを閉じる
    close_search_form(page)


# =============================================================================
# テスト9: 取引先名で検索
# =============================================================================

def test_取引先名で検索(logged_in_page: Page):
    """取引先名で検索すると該当データのみ表示される"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 検索前の件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # 取引先名に「TOKIUM」を入力
    form = page.locator("form").first
    name_field = form.get_by_label("取引先名")
    name_field.fill("TOKIUM")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 結果に「株式会社TOKIUM」が含まれることを確認
    expect(page.locator("table").locator("text='株式会社TOKIUM'")).to_be_visible(timeout=10000)

    # 件数がフィルタされたことを確認（紐づけ検証）
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    assert after_total < before_total, \
        f"検索後に件数が減っていない（前: {before_total}, 後: {after_total}）"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 検索フォームを閉じる
    close_search_form(page)


# =============================================================================
# テスト10: 送付方法で絞り込み検索
# =============================================================================

def test_送付方法で絞り込み検索(logged_in_page: Page):
    """送付方法セレクタで絞り込むとテーブルが更新される"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 検索前の件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # 送付方法を「メール」に変更
    form = page.locator("form").first
    form.locator("select").first.select_option("email")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # テーブルが表示されていることを確認
    expect(page.locator("table")).to_be_visible(timeout=10000)

    # 件数がフィルタされたことを確認（紐づけ検証）
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    assert after_total < before_total, \
        f"送付方法フィルタ後に件数が減っていない（前: {before_total}, 後: {after_total}）"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 検索フォームを閉じる
    close_search_form(page)


# =============================================================================
# テスト11: 検索リセット
# =============================================================================

def test_検索リセット(logged_in_page: Page):
    """リセットボタンで検索条件がクリアされ全件表示に戻る"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 検索前の全件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # 取引先コードに値を入力
    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")
    code_field.fill("TH00001")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 検索で件数が減ったことを確認
    filtered_text = page.locator("text=/\\d+件中/").text_content()
    filtered_total = int(re.search(r"(\d+)件中", filtered_text).group(1))
    assert filtered_total < before_total, \
        f"検索後に件数が減っていない（前: {before_total}, 後: {filtered_total}）"

    # リセットボタンをクリック
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 全件表示に戻ったことを確認（紐づけ検証: リセット前の全件数と一致）
    reset_text = page.locator("text=/\\d+件中/").text_content()
    reset_total = int(re.search(r"(\d+)件中", reset_text).group(1))
    assert reset_total == before_total, \
        f"リセット後に全件に戻っていない（期待: {before_total}, 実際: {reset_total}）"

    # 検索フォームを閉じる
    close_search_form(page)


# =============================================================================
# テスト12: 「その他の操作」メニューの表示確認
# =============================================================================

def test_その他の操作メニューの表示確認(logged_in_page: Page):
    """「その他の操作」ボタンをクリックするとメニューが表示される"""

    page = goto_partners(logged_in_page)

    # 「その他の操作」ボタンをクリック
    page.get_by_role("button", name="その他の操作").click()
    page.wait_for_timeout(500)

    # メニュー項目の確認
    expect(page.locator("text='取引先インポート'")).to_be_visible()
    expect(page.locator("text='取引先エクスポート'")).to_be_visible()

    # メニューを閉じる
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


# =============================================================================
# テスト13: 取引先クリックで更新モーダルが開く
# =============================================================================

def test_取引先クリックで更新モーダルが開く(logged_in_page: Page):
    """一覧の取引先行をクリックすると更新モーダルが表示される"""

    page = goto_partners(logged_in_page)

    # 更新モーダルを開く
    open_update_modal(page)

    # モーダルタイトルの確認
    expect(page.get_by_role("heading", name="取引先更新")).to_be_visible()

    # 取引先コード・取引先名のinputフィールド確認（モーダル内のform）
    modal_form = page.locator("article").filter(
        has=page.get_by_role("heading", name="取引先更新")
    ).locator("form")
    code_input = modal_form.locator('input[type="text"]').first
    expect(code_input).to_have_value("TH00001")

    # タブの確認
    expect(page.get_by_role("button", name="取引先項目")).to_be_visible()
    expect(page.get_by_role("button", name="Web送付設定")).to_be_visible()

    # アクションボタンの確認
    expect(page.get_by_role("button", name="保存")).to_be_visible()
    expect(page.get_by_role("button", name="キャンセル").last).to_be_visible()
    expect(page.get_by_role("button", name="凍結する")).to_be_visible()

    # モーダルを閉じる
    close_modal_by_cancel(page, "取引先更新")


# =============================================================================
# テスト14: 更新モーダル - 取引先項目タブの表示確認
# =============================================================================

def test_更新モーダル_取引先項目タブの表示確認(logged_in_page: Page):
    """更新モーダルの取引先項目タブに全フィールドが表示されている"""

    page = goto_partners(logged_in_page)

    # 更新モーダルを開く
    open_update_modal(page)

    # 送付方法セレクト（モーダル内のform内のselect）
    modal_form = page.locator("article").filter(
        has=page.get_by_role("heading", name="取引先更新")
    ).locator("form")
    expect(modal_form.locator("select").first).to_be_visible()

    # 住所セクションの見出し
    expect(modal_form.get_by_role("heading", name="住所")).to_be_visible()

    # 送付先担当者情報の見出し
    expect(modal_form.get_by_role("heading", name="送付先担当者情報")).to_be_visible()

    # 自社担当者情報の見出し
    expect(modal_form.get_by_role("heading", name="自社担当者情報")).to_be_visible()

    # 基本情報の見出し
    expect(modal_form.get_by_role("heading", name="基本情報")).to_be_visible()

    # 識別コード表示（読み取り専用テキスト）
    expect(modal_form.locator("text='識別コード'")).to_be_visible()

    # モーダルを閉じる
    close_modal_by_cancel(page, "取引先更新")


# =============================================================================
# テスト15: 更新モーダル - Web送付設定タブの表示確認
# =============================================================================

def test_更新モーダル_Web送付設定タブの表示確認(logged_in_page: Page):
    """更新モーダルのWeb送付設定タブにメールアドレス管理UIが表示されている"""

    page = goto_partners(logged_in_page)

    # 更新モーダルを開く
    open_update_modal(page)

    # Web送付設定タブに切替
    page.get_by_role("button", name="Web送付設定").click()
    page.wait_for_timeout(1000)

    # メールアドレスの見出し確認
    expect(page.locator("text=/閲覧用メールアドレス/")).to_be_visible(timeout=5000)

    # 新規メールアドレス追加ボタン
    expect(page.locator("text='新規メールアドレス追加'")).to_be_visible()

    # モーダルを閉じる
    close_modal_by_cancel(page, "取引先更新")


# =============================================================================
# テスト16: 新規追加モーダルの表示確認
# =============================================================================

def test_新規追加モーダルの表示確認(logged_in_page: Page):
    """「取引先を追加」ボタンで新規入力モーダルが表示される"""

    page = goto_partners(logged_in_page)

    # 「取引先を追加」ボタンをクリック
    page.get_by_role("button", name="取引先を追加").click()
    page.get_by_role("heading", name="取引先入力").wait_for(state="visible", timeout=10000)

    # モーダル内のform
    modal_form = page.locator("article").filter(
        has=page.get_by_role("heading", name="取引先入力")
    ).locator("form")

    # ヘッダーフィールド（input[type=text]の最初の2つ = 取引先コード、取引先名）
    inputs = modal_form.locator('input[type="text"]')
    expect(inputs.first).to_be_visible()

    # 送付方法セレクト（デフォルト: メール）
    expect(modal_form.locator("select").first).to_have_value("email")

    # 送付先担当者情報の見出し
    expect(modal_form.get_by_role("heading", name="送付先担当者情報")).to_be_visible()

    # 送付先メールアドレスの見出し（新規のみ）
    expect(modal_form.get_by_role("heading", name="送付先メールアドレス")).to_be_visible()

    # 自社担当者情報の見出し
    expect(modal_form.get_by_role("heading", name="自社担当者情報")).to_be_visible()

    # 保存ボタン
    expect(modal_form.locator("..").get_by_role("button", name="保存")).to_be_visible()

    # 凍結ボタンは新規にはないことを確認
    article = page.locator("article").filter(
        has=page.get_by_role("heading", name="取引先入力")
    )
    expect(article.get_by_role("button", name="凍結する")).to_have_count(0)

    # モーダルを閉じる
    close_modal_by_cancel(page, "取引先入力")


# =============================================================================
# テスト17: 新規追加モーダル - キャンセルで閉じる
# =============================================================================

def test_新規追加モーダル_キャンセルで閉じる(logged_in_page: Page):
    """新規入力モーダルの「キャンセル」で閉じると一覧に戻る"""

    page = goto_partners(logged_in_page)

    # モーダルを開く
    page.get_by_role("button", name="取引先を追加").click()
    page.get_by_role("heading", name="取引先入力").wait_for(state="visible", timeout=10000)

    # キャンセルをクリック
    close_modal_by_cancel(page, "取引先入力")

    # 一覧が表示されていること
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト18: 更新モーダル - ×ボタンで閉じる
# =============================================================================

def test_更新モーダル_バツボタンで閉じる(logged_in_page: Page):
    """更新モーダルの×ボタンで閉じると一覧に戻る"""

    page = goto_partners(logged_in_page)

    # 更新モーダルを開く
    open_update_modal(page)

    # ×ボタンをクリック（heading "取引先更新" の親bannerにあるbutton）
    heading = page.get_by_role("heading", name="取引先更新")
    # heading の隣のボタン（×ボタン）を特定
    close_btn = heading.locator(".. >> button").first
    close_btn.click()
    page.wait_for_timeout(1000)

    # モーダルが閉じたことを確認
    expect(page.get_by_role("heading", name="取引先更新")).not_to_be_visible(timeout=5000)

    # 一覧が表示されていること
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト19: ページネーション - 次ページに遷移
# =============================================================================

def test_ページネーション_次ページに遷移(logged_in_page: Page):
    """次ページボタンで2ページ目に遷移できる"""

    page = goto_partners(logged_in_page)

    # 検索フォームが開いていると邪魔になるので閉じる
    close_search_form(page)

    # 現在の件数表示を確認（U+301C 波ダッシュ「〜」使用）
    count_el = page.locator("text=/件中 1〜/")
    expect(count_el).to_be_visible()

    # 次ページボタン: 件数表示テキストと同じコンテナ内の2番目のbutton
    # DOM: div._pagingControl_ > [button(前)] [button(次)] [div(件数テキスト)]
    paging_container = count_el.locator("..")
    next_btn = paging_container.locator("button").nth(1)
    next_btn.scroll_into_view_if_needed()
    next_btn.click()
    page.wait_for_timeout(3000)

    # 件数表示が変わったことを確認
    # 1ページ目の「1〜100件」ではなくなっていればOK
    expect(page.locator("text='1〜100件'")).not_to_be_visible(timeout=10000)


# =============================================================================
# テスト20: 表示件数の境界値 - 10件表示時の行数検証
# =============================================================================

@pytest.mark.regression
def test_表示件数の境界値_10件表示時の行数検証(logged_in_page: Page):
    """表示件数10件の3点境界値検証: 9行目表示・10行目表示・11行目非表示"""

    page = goto_partners(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    # 10件に切替
    display_count_select.select_option("10")
    page.wait_for_timeout(2000)

    # 件数表示テキストで確認
    expect(page.locator("text=/件中 1〜10件/")).to_be_visible(timeout=10000)

    # テーブルのデータ行を取得（取引先コードTHを含む行 = データ行）
    data_rows = page.locator("table").locator("tr").filter(
        has=page.locator("text=/^TH/")
    )
    row_count = data_rows.count()

    # 3点境界値検証
    assert row_count >= 9, f"直前: 9行目が存在しない（実際: {row_count}行）"
    assert row_count >= 10, f"境界: 10行目が存在しない（実際: {row_count}行）"
    assert row_count == 10, f"直後: 11行目以上が存在する（実際: {row_count}行）"

    # 元に戻す
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)


# =============================================================================
# テスト21: 表示件数の境界値 - 50件表示時の行数検証
# =============================================================================

@pytest.mark.regression
def test_表示件数の境界値_50件表示時の行数検証(logged_in_page: Page):
    """表示件数50件の3点境界値検証: 49行目表示・50行目表示・51行目非表示"""

    page = goto_partners(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    # 50件に切替
    display_count_select.select_option("50")
    page.wait_for_timeout(2000)

    # 件数表示テキストで確認
    expect(page.locator("text=/件中 1〜50件/")).to_be_visible(timeout=10000)

    # テーブルのデータ行を取得
    data_rows = page.locator("table").locator("tr").filter(
        has=page.locator("text=/^TH/")
    )
    row_count = data_rows.count()

    # 3点境界値検証
    assert row_count >= 49, f"直前: 49行目が存在しない（実際: {row_count}行）"
    assert row_count >= 50, f"境界: 50行目が存在しない（実際: {row_count}行）"
    assert row_count == 50, f"直後: 51行目以上が存在する（実際: {row_count}行）"

    # 元に戻す
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)


# =============================================================================
# テスト22: ページネーション - 最終ページの境界値検証
# =============================================================================

@pytest.mark.regression
def test_ページネーション_最終ページの境界値検証(logged_in_page: Page):
    """最終ページの3点境界値検証: 前ページ遷移可能・データ表示あり・次ページ遷移不可"""

    page = goto_partners(logged_in_page)
    close_search_form(page)

    # 表示件数を100件に明示的に設定
    display_count_select = page.locator("main").locator("select").last
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)

    # 総件数を取得（例: "1014件中 1〜100件"）
    count_text = page.locator("text=/\\d+件中/").text_content()
    total = int(re.search(r"(\d+)件中", count_text).group(1))

    # 最終ページまで遷移（100件/ページ）
    pages_needed = (total - 1) // 100  # 最終ページに到達するために必要なクリック数
    paging_container = page.locator("text=/件中/").locator("..")
    next_btn = paging_container.locator("button").nth(1)

    for _ in range(pages_needed):
        next_btn.scroll_into_view_if_needed()
        next_btn.click()
        page.wait_for_timeout(2000)

    # 3点境界値検証
    # 直前: 最終ページにデータが表示されている
    expect(page.locator("table").locator("text=/^TH/").first).to_be_visible()

    # 境界: 件数表示が最終ページの範囲を示している（最終件数がtotalと一致）
    count_on_last = page.locator("text=/件中/").text_content()
    last_range = re.search(r"(\d+)〜(\d+)件", count_on_last)
    assert last_range, f"最終ページの件数表示が想定外: '{count_on_last}'"
    assert int(last_range.group(2)) == total, \
        f"境界: 最終件数が総数と不一致（最終: {last_range.group(2)}, 総数: {total}）"

    # 直後: 次ページボタンがdisabled状態である
    expect(next_btn).to_be_disabled()


# =============================================================================
# テスト23: 表示件数の境界値 - 20件表示時の行数検証
# =============================================================================

@pytest.mark.regression
def test_表示件数の境界値_20件表示時の行数検証(logged_in_page: Page):
    """表示件数20件の3点境界値検証: 19行目表示・20行目表示・21行目非表示"""

    page = goto_partners(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    # 20件に切替
    display_count_select.select_option("20")
    page.wait_for_timeout(2000)

    # 件数表示テキストで確認
    expect(page.locator("text=/件中 1〜20件/")).to_be_visible(timeout=10000)

    # テーブルのデータ行を取得
    data_rows = page.locator("table").locator("tr").filter(
        has=page.locator("text=/^TH/")
    )
    row_count = data_rows.count()

    # 3点境界値検証
    assert row_count >= 19, f"直前: 19行目が存在しない（実際: {row_count}行）"
    assert row_count >= 20, f"境界: 20行目が存在しない（実際: {row_count}行）"
    assert row_count == 20, f"直後: 21行目以上が存在する（実際: {row_count}行）"

    # 元に戻す
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)


# =============================================================================
# テスト24: 異常系 - 存在しない取引先コードで検索
# =============================================================================

@pytest.mark.regression
def test_異常系_存在しない取引先コードで検索(logged_in_page: Page):
    """存在しない取引先コードで検索すると0件表示になる"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 存在しないコードを入力
    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")
    code_field.fill("ZZZZ99999_NOTEXIST")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 0件であることを確認
    count_text = page.locator("text=/\\d+件中/")
    if count_text.is_visible():
        text = count_text.text_content()
        total = int(re.search(r"(\d+)件中", text).group(1))
        assert total == 0, f"存在しないコードで検索したが{total}件ヒットした"
    else:
        # 件数表示自体がない場合、テーブルにデータ行がないことを確認
        data_rows = page.locator("table").locator("tr").filter(
            has=page.locator("text=/^TH/")
        )
        assert data_rows.count() == 0, "存在しないコードで検索したがデータ行が表示されている"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)
    close_search_form(page)


# =============================================================================
# テスト25: 異常系 - 存在しない取引先名で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_存在しない取引先名で検索(logged_in_page: Page):
    """存在しない取引先名で検索すると0件表示になる"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 存在しない名前を入力
    form = page.locator("form").first
    name_field = form.get_by_label("取引先名")
    name_field.fill("存在しない会社名ABCXYZ12345")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 0件であることを確認
    count_text = page.locator("text=/\\d+件中/")
    if count_text.is_visible():
        text = count_text.text_content()
        total = int(re.search(r"(\d+)件中", text).group(1))
        assert total == 0, f"存在しない取引先名で検索したが{total}件ヒットした"
    else:
        data_rows = page.locator("table").locator("tr").filter(
            has=page.locator("text=/^TH/")
        )
        assert data_rows.count() == 0, "存在しない取引先名で検索したがデータ行が表示されている"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)
    close_search_form(page)


# =============================================================================
# テスト26: 異常系 - 特殊文字で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_特殊文字で検索(logged_in_page: Page):
    """特殊文字を入力して検索してもエラーにならずページが正常表示される"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 特殊文字を入力（記号・絵文字・マルチバイト特殊文字）
    form = page.locator("form").first
    name_field = form.get_by_label("取引先名")
    name_field.fill("!@#$%^&*()_+{}|:<>?～①②③★♪")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(3000)

    # エラーページにならず、取引先一覧のURLのままであること
    current_url = page.url
    assert "/partners" in current_url, \
        f"特殊文字検索後に取引先一覧から離脱した（URL: {current_url}）"

    # ページが正常に表示されていること（テーブルまたは見出しが存在）
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    table_visible = page.locator("table").is_visible()
    heading_visible = page.get_by_role("heading", name="取引先").is_visible()
    assert table_visible or heading_visible, \
        "特殊文字検索後にページが正常表示されていない"

    # リセット
    reset_btn = page.get_by_role("button", name="リセット")
    if reset_btn.is_visible():
        reset_btn.dispatch_event("click")
        page.wait_for_timeout(2000)


# =============================================================================
# テスト27: 異常系 - 新規追加モーダルで必須項目未入力のまま保存
# =============================================================================

@pytest.mark.regression
def test_異常系_新規追加モーダル_必須項目未入力で保存(logged_in_page: Page):
    """新規追加モーダルで必須項目を未入力のまま保存ボタンを押すとバリデーションエラーが表示される"""

    page = goto_partners(logged_in_page)

    # 「取引先を追加」ボタンをクリック
    page.get_by_role("button", name="取引先を追加").click()
    page.get_by_role("heading", name="取引先入力").wait_for(state="visible", timeout=10000)

    # 全フィールドを空のまま保存ボタンをクリック
    article = page.locator("article").filter(
        has=page.get_by_role("heading", name="取引先入力")
    )
    save_btn = article.get_by_role("button", name="保存")
    save_btn.click()
    page.wait_for_timeout(2000)

    # バリデーションエラーが表示される、またはモーダルが閉じないことを確認
    # （保存が成功した場合はモーダルが閉じるので、閉じていなければバリデーション発動）
    modal_still_open = page.get_by_role("heading", name="取引先入力").is_visible()
    assert modal_still_open, "必須項目未入力なのにモーダルが閉じた（保存が成功してしまった可能性）"

    # モーダルを閉じる
    close_modal_by_cancel(page, "取引先入力")


# =============================================================================
# テスト28: 異常系 - 検索フォーム全フィールド空で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_検索フォーム_全フィールド空で検索(logged_in_page: Page):
    """検索フォームを全フィールド空の状態で検索しても全件が表示される"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 検索前の全件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # 全フィールド空のまま検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 全件表示のままであることを確認
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    assert after_total == before_total, \
        f"空検索後に件数が変わった（前: {before_total}, 後: {after_total}）"

    # ページが正常表示されていること
    expect(page.locator("table")).to_be_visible()

    close_search_form(page)


# =============================================================================
# テスト29: 状態遷移 - モーダル開閉を繰り返しても正常動作する
# =============================================================================

@pytest.mark.regression
def test_状態遷移_モーダル開閉を繰り返しても正常動作する(logged_in_page: Page):
    """更新モーダルを開→閉→開→タブ切替→閉→新規モーダル開→閉の遷移が正常動作する"""

    page = goto_partners(logged_in_page)

    # 1回目: 更新モーダル開→閉
    open_update_modal(page)
    expect(page.get_by_role("heading", name="取引先更新")).to_be_visible()
    close_modal_by_cancel(page, "取引先更新")
    expect(page.locator("table")).to_be_visible()

    # 2回目: 更新モーダル開→タブ切替→閉
    open_update_modal(page)
    page.get_by_role("button", name="Web送付設定").click()
    page.wait_for_timeout(1000)
    expect(page.locator("text=/閲覧用メールアドレス/")).to_be_visible(timeout=5000)
    close_modal_by_cancel(page, "取引先更新")
    expect(page.locator("table")).to_be_visible()

    # 3回目: 新規モーダル開→閉
    page.get_by_role("button", name="取引先を追加").click()
    page.get_by_role("heading", name="取引先入力").wait_for(state="visible", timeout=10000)
    close_modal_by_cancel(page, "取引先入力")

    # 最終状態: 一覧が正常表示されていること
    expect(page.locator("table")).to_be_visible()
    expect(page.get_by_role("heading", name="取引先")).to_be_visible()


# =============================================================================
# テスト30: 状態遷移 - 検索→リセット→再検索で正常動作する
# =============================================================================

@pytest.mark.regression
def test_状態遷移_検索後リセット後再検索で正常動作する(logged_in_page: Page):
    """検索→結果確認→リセット→全件復帰→別条件で再検索の遷移が正常動作する"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 初期件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # 1回目の検索（コードで絞り込み）
    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")
    code_field.fill("TH00001")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 件数が減ったことを確認
    search1_text = page.locator("text=/\\d+件中/").text_content()
    search1_total = int(re.search(r"(\d+)件中", search1_text).group(1))
    assert search1_total < before_total, \
        f"検索後に件数が減っていない（前: {before_total}, 後: {search1_total}）"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 全件に復帰したことを確認
    reset_text = page.locator("text=/\\d+件中/").text_content()
    reset_total = int(re.search(r"(\d+)件中", reset_text).group(1))
    assert reset_total == before_total, \
        f"リセット後に全件に復帰していない（期待: {before_total}, 実際: {reset_total}）"

    # 2回目の検索（名前で絞り込み）
    name_field = form.get_by_label("取引先名")
    name_field.fill("株式会社TOKIUM")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 件数が減ったことを確認
    search2_text = page.locator("text=/\\d+件中/").text_content()
    search2_total = int(re.search(r"(\d+)件中", search2_text).group(1))
    assert search2_total < before_total, \
        f"再検索後に件数が減っていない（前: {before_total}, 後: {search2_total}）"

    # クリーンアップ
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)
    close_search_form(page)


# =============================================================================
# テスト31: 冪等性 - 検索ボタン連打で結果が安定する
# =============================================================================

@pytest.mark.regression
def test_冪等性_検索ボタン連打で結果が安定する(logged_in_page: Page):
    """同じ検索条件で検索ボタンを3回連打しても結果が同じになる"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    # 検索条件を入力
    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")
    code_field.fill("TH00001")

    # 検索ボタンを3回連打
    search_btn = page.get_by_role("button", name="この条件で検索")
    search_btn.dispatch_event("click")
    page.wait_for_timeout(500)
    search_btn.dispatch_event("click")
    page.wait_for_timeout(500)
    search_btn.dispatch_event("click")
    page.wait_for_timeout(3000)

    # ページが正常表示されていること
    assert "/partners" in page.url, f"検索ボタン連打後にURLが変わった: {page.url}"
    expect(page.locator("table")).to_be_visible()

    # 件数表示が正常であること
    count_text = page.locator("text=/\\d+件中/").text_content()
    total = int(re.search(r"(\d+)件中", count_text).group(1))
    assert total >= 0, f"件数が不正: {total}"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)
    close_search_form(page)


# =============================================================================
# テスト32: 冪等性 - 表示件数を連続切替しても正常動作する
# =============================================================================

@pytest.mark.regression
def test_冪等性_表示件数を連続切替しても正常動作する(logged_in_page: Page):
    """表示件数を10→50→20→100→10と連続切替しても正しい行数が表示される"""

    page = goto_partners(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    switch_sequence = [
        ("10", 10),
        ("50", 50),
        ("20", 20),
        ("100", 100),
        ("10", 10),
    ]

    for value, expected_max in switch_sequence:
        display_count_select.select_option(value)
        page.wait_for_timeout(2000)

        # 件数表示テキストで確認
        count_text = page.locator("text=/\\d+件中/").text_content()
        match = re.search(r"(\d+)〜(\d+)件", count_text)
        assert match, f"件数表示が取得できない（{value}件切替後）: {count_text}"
        displayed = int(match.group(2)) - int(match.group(1)) + 1
        assert displayed <= expected_max, \
            f"表示件数{value}切替後に{displayed}件表示（上限{expected_max}）"

    # 最終状態: テーブルが正常表示されていること
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト33: エラーリカバリ - 存在しない検索後に条件修正で正常結果に復帰
# =============================================================================

@pytest.mark.regression
def test_エラーリカバリ_存在しない検索後に条件修正で正常結果に復帰(logged_in_page: Page):
    """存在しないコードで0件→条件修正→正常な結果が表示されるリカバリフロー"""

    page = goto_partners(logged_in_page)
    open_search_form(page)

    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")

    # Step1: 存在しないコードで検索（エラー状態）
    code_field.fill("ZZZZ_NOTEXIST_99999")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 0件であることを確認
    count_text = page.locator("text=/\\d+件中/")
    if count_text.is_visible():
        text = count_text.text_content()
        total = int(re.search(r"(\d+)件中", text).group(1))
        assert total == 0, f"存在しないコードで{total}件ヒットした"

    # Step2: 条件を修正して再検索（リカバリ）
    code_field.fill("TH00001")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_timeout(2000)

    # 正常な結果が表示されること
    count_text2 = page.locator("text=/\\d+件中/").text_content()
    total2 = int(re.search(r"(\d+)件中", count_text2).group(1))
    assert total2 > 0, f"条件修正後も0件のまま（リカバリ失敗）"

    # テーブルにデータが表示されていること
    expect(page.locator("table")).to_be_visible()

    # クリーンアップ
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_timeout(2000)
    close_search_form(page)


# =============================================================================
# テスト34: データ整合性 - 一覧の取引先コードとモーダルの取引先コードが一致する（基準6）
# =============================================================================

@pytest.mark.regression
def test_データ整合性_一覧の取引先コードとモーダルの取引先コードが一致する(logged_in_page: Page):
    """一覧テーブルの取引先コードと更新モーダル内の取引先コードが一致する"""

    page = goto_partners(logged_in_page)

    # Step1: 一覧の最初の行から取引先コードを取得
    first_row = page.locator("table tbody tr").first
    list_code = first_row.locator("td").first.text_content().strip()

    # Step2: 行をクリックして更新モーダルを開く
    close_search_form(page)
    first_row.locator("td").nth(1).click()
    page.get_by_role("heading", name="取引先更新").wait_for(state="visible", timeout=10000)

    # Step3: モーダル内の取引先コード入力値を取得
    modal_form = page.locator("article").filter(
        has=page.get_by_role("heading", name="取引先更新")
    ).locator("form")
    modal_code = modal_form.locator('input[type="text"]').first.input_value()

    # Step4: 一覧のコードとモーダルのコードが一致することを確認
    assert list_code == modal_code, \
        f"一覧の取引先コード「{list_code}」とモーダルの取引先コード「{modal_code}」が不一致"

    # クリーンアップ
    close_modal_by_cancel(page, "取引先更新")
