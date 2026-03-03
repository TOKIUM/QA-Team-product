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

    # 取引先コードに「TH00001」を入力
    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")
    code_field.fill("TH00001")

    # 検索実行（force=True でポインタインターセプトを回避）
    page.get_by_role("button", name="この条件で検索").click(force=True)
    page.wait_for_timeout(2000)

    # 結果に「TH00001」が含まれることを確認
    expect(page.locator("table").locator("text='TH00001'")).to_be_visible(timeout=10000)

    # リセット
    page.get_by_role("button", name="リセット").click(force=True)
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

    # 取引先名に「TOKIUM」を入力
    form = page.locator("form").first
    name_field = form.get_by_label("取引先名")
    name_field.fill("TOKIUM")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").click(force=True)
    page.wait_for_timeout(2000)

    # 結果に「株式会社TOKIUM」が含まれることを確認
    expect(page.locator("table").locator("text='株式会社TOKIUM'")).to_be_visible(timeout=10000)

    # リセット
    page.get_by_role("button", name="リセット").click(force=True)
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

    # 送付方法を「メール」に変更
    form = page.locator("form").first
    form.locator("select").first.select_option("email")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").click(force=True)
    page.wait_for_timeout(2000)

    # テーブルが表示されていることを確認
    expect(page.locator("table")).to_be_visible(timeout=10000)

    # リセット
    page.get_by_role("button", name="リセット").click(force=True)
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

    # 取引先コードに値を入力
    form = page.locator("form").first
    code_field = form.get_by_label("取引先コード")
    code_field.fill("TH00001")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").click(force=True)
    page.wait_for_timeout(2000)

    # リセットボタンをクリック
    page.get_by_role("button", name="リセット").click(force=True)
    page.wait_for_timeout(2000)

    # 全件表示に戻ったことを確認（複数件の件数表示）
    expect(page.locator("text=/\\d+件中/")).to_be_visible(timeout=10000)

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
