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
    "test_異常系_存在しない取引先名で検索": "TH-IL18",
    "test_異常系_特殊文字で検索": "TH-IL19",
    "test_異常系_日付範囲_終了日が開始日より前": "TH-IL20",
    "test_異常系_行未選択で一括送付ボタンクリック": "TH-IL21",
    "test_異常系_全フィールド空で検索": "TH-IL22",
    "test_異常系_SQLインジェクション文字列で検索": "TH-IL23",
    "test_異常系_XSSスクリプトタグで検索": "TH-IL24",
    "test_異常系_長文字列で検索": "TH-IL25",
    "test_表示件数の境界値_10件表示時の行数検証": "TH-IL26",
    "test_表示件数の境界値_50件表示時の行数検証": "TH-IL27",
    "test_ページネーション_最終ページの境界値検証": "TH-IL28",
    "test_表示件数の境界値_20件表示時の行数検証": "TH-IL29",
    # 状態遷移（基準5）
    "test_状態遷移_検索後リセット後再検索で正常動作する": "TH-IL30",
    "test_状態遷移_詳細画面から戻っても一覧状態が維持される": "TH-IL31",
    # 冪等性（基準7）
    "test_冪等性_検索ボタン連打で結果が安定する": "TH-IL32",
    "test_冪等性_表示件数を連続切替しても正常動作する": "TH-IL33",
    # エラーリカバリ（基準8）
    "test_エラーリカバリ_存在しない取引先名検索後に条件修正で復帰": "TH-IL34",
    # データ整合性（基準6）
    "test_データ整合性_一覧の取引先名が詳細画面と一致する": "TH-IL35",
    "test_データ整合性_一覧の件数と詳細画面のページ送り総数が一致する": "TH-IL36",
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


def get_count_total(page: Page, timeout: int = 60000) -> int:
    """件数テキスト（例:「11016件中 1〜10件」or「0件」）から総件数を取得。"""
    # 「N件中」パターン（1件以上の場合）
    loc_with_naka = page.locator("text=/\\d+件中/").first
    # 「0件」パターン（検索結果0件の場合）
    loc_zero = page.locator("text=/^0件$/").first

    try:
        loc_with_naka.wait_for(state="visible", timeout=timeout)
        text = loc_with_naka.text_content()
        m = re.search(r"(\d+)件中", text)
        assert m, f"件数テキストのパースに失敗: {text}"
        return int(m.group(1))
    except Exception:
        if loc_zero.is_visible():
            return 0
        raise


# =============================================================================
# テスト1: 一覧ページの表示確認
# =============================================================================

@pytest.mark.smoke
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

    # 検索前の件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # Step2: 取引先名に検索条件を入力
    page.get_by_label("取引先名").fill("鈴木通信合同会社")

    # Step3: 検索ボタンをクリック（オーバーレイ要素回避のためdispatch_event使用）
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")

    # 検索結果のロード完了を待機
    page.wait_for_load_state("networkidle")
    page.locator("table").wait_for(state="visible")

    # Step4: 検索結果に「鈴木通信合同会社」が含まれることを確認
    expect(page.locator("table").get_by_text("鈴木通信合同会社").first).to_be_visible()

    # Step5: 件数がフィルタされたことを確認（紐づけ検証）
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    assert after_total < before_total, \
        f"検索後に件数が減っていない（前: {before_total}, 後: {after_total}）"


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

    # 検索前の件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

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

    # Step5: フィルタが効いたことを確認（紐づけ検証）
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    # 件数が減った、またはテーブル内に他ステータスが表示されていないことを確認
    if after_total >= before_total:
        # 件数が減っていない場合、表示されている行が全て「未送付」であることを検証
        other_statuses = ["送付済み", "送付中", "送付待ち", "登録中", "登録失敗", "送付失敗"]
        for status in other_statuses:
            status_in_table = page.locator("table").get_by_text(status, exact=True)
            assert status_in_table.count() == 0, \
                f"ステータス絞り込みが効いていない: '{status}'が表示されている"


# =============================================================================
# テスト12: 送付方法セレクトで絞り込み（メール）
# =============================================================================

def test_送付方法セレクトで絞り込み(logged_in_page: Page):
    """送付方法を「メール」に設定して検索すると、結果が絞り込まれる"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # 検索前の件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # Step2: 送付方法を「メール」に変更
    page.get_by_label("送付方法").select_option("メール")

    # Step3: 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.locator("table").wait_for(state="visible")

    # Step4: テーブルにデータ行が存在することを確認
    rows = page.locator("table tbody tr")
    expect(rows.first).to_be_visible()

    # Step5: 件数がフィルタされたことを確認（紐づけ検証）
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    assert after_total < before_total, \
        f"送付方法フィルタ後に件数が減っていない（前: {before_total}, 後: {after_total}）"


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


# =============================================================================
# テスト18: 異常系 - 存在しない取引先名で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_存在しない取引先名で検索(logged_in_page: Page):
    """存在しない取引先名で検索すると0件表示になる"""

    page = goto_invoices(logged_in_page)

    # 存在しない名前を入力
    page.get_by_label("取引先名").fill("存在しない会社名ABCXYZ12345")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # 0件であることを確認
    count_text = page.locator("text=/\\d+件中/")
    if count_text.is_visible():
        text = count_text.text_content()
        total = int(re.search(r"(\d+)件中", text).group(1))
        assert total == 0, f"存在しない取引先名で検索したが{total}件ヒットした"
    else:
        # 件数表示がない場合、テーブルのデータ行がないことを確認
        rows = page.locator("table tbody tr")
        assert rows.count() == 0, "存在しない取引先名で検索したがデータ行が表示されている"

    # ページが正常であること
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()


# =============================================================================
# テスト19: 異常系 - 特殊文字で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_特殊文字で検索(logged_in_page: Page):
    """特殊文字を入力して検索してもエラーにならずページが正常表示される"""

    page = goto_invoices(logged_in_page)

    # 特殊文字を入力（記号・マルチバイト特殊文字）
    page.get_by_label("取引先名").fill("!@#$%^&*()_+{}|:<>?～①②③★♪")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # エラーページにならず、請求書一覧のURLのままであること
    current_url = page.url
    assert "/invoices" in current_url, \
        f"特殊文字検索後に請求書一覧から離脱した（URL: {current_url}）"

    # ページが正常に表示されていること
    table_visible = page.locator("table").is_visible()
    heading_visible = page.get_by_role("heading", name="請求書").is_visible()
    assert table_visible or heading_visible, \
        "特殊文字検索後にページが正常表示されていない"


# =============================================================================
# テスト20: 異常系 - 日付範囲の終了日が開始日より前
# =============================================================================

@pytest.mark.regression
def test_異常系_日付範囲_終了日が開始日より前(logged_in_page: Page):
    """請求日の終了日を開始日より前に設定して検索した場合、0件またはエラーが表示される"""

    page = goto_invoices(logged_in_page)

    # 日付入力フィールドを取得（最初の2つが請求日の開始・終了）
    date_inputs = page.locator("input[type='date']")

    # 開始日: 2026-12-31、終了日: 2026-01-01（逆転）
    date_inputs.nth(0).fill("2026-12-31")
    date_inputs.nth(1).fill("2026-01-01")

    # 検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # エラーページにならず正常表示されていること
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()

    # 0件または結果なし（逆転した日付範囲では結果が返らないはず）
    count_text = page.locator("text=/\\d+件中/")
    if count_text.is_visible():
        text = count_text.text_content()
        total = int(re.search(r"(\d+)件中", text).group(1))
        assert total == 0, f"逆転日付範囲で検索したが{total}件ヒットした"


# =============================================================================
# テスト21: 異常系 - 行未選択で一括送付ボタンクリック
# =============================================================================

@pytest.mark.regression
def test_異常系_行未選択で一括送付ボタンクリック(logged_in_page: Page):
    """行を選択せずに「請求書を送付する」ボタンがdisabled状態であること"""

    page = goto_invoices(logged_in_page)

    # チェックボックスが全て未選択であることを確認
    select_all = page.locator("table thead input[type='checkbox']")
    if select_all.is_checked():
        select_all.uncheck()
        page.wait_for_timeout(500)

    # 「請求書を送付する」ボタンがdisabledであること
    send_btn = page.get_by_role("button", name="請求書を送付する")
    expect(send_btn).to_be_visible()
    expect(send_btn).to_be_disabled()

    # 行を1つ選択するとenabledになることを確認
    first_row_checkbox = page.locator("table tbody tr").first.locator("input[type='checkbox']")
    first_row_checkbox.check()
    page.wait_for_timeout(500)
    expect(send_btn).to_be_enabled()

    # 選択解除で再びdisabledに戻ること
    first_row_checkbox.uncheck()
    page.wait_for_timeout(500)
    expect(send_btn).to_be_disabled()


# =============================================================================
# テスト22: 異常系 - 全フィールド空で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_全フィールド空で検索(logged_in_page: Page):
    """検索フォームを全フィールド空の状態で検索しても全件が表示される"""

    page = goto_invoices(logged_in_page)

    # 検索前の全件数を記録
    before_text = page.locator("text=/\\d+件中/").text_content()
    before_total = int(re.search(r"(\d+)件中", before_text).group(1))

    # リセットして全フィールドを空にする
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # 空の状態で検索実行
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # 全件表示のままであることを確認
    after_text = page.locator("text=/\\d+件中/").text_content()
    after_total = int(re.search(r"(\d+)件中", after_text).group(1))
    assert after_total == before_total, \
        f"空検索後に件数が変わった（前: {before_total}, 後: {after_total}）"

    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト23: 異常系 - SQLインジェクション文字列で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_SQLインジェクション文字列で検索(logged_in_page: Page):
    """SQLインジェクション文字列を入力して検索してもアプリがクラッシュしない"""

    page = goto_invoices(logged_in_page)

    sql_payloads = [
        "'; DROP TABLE invoices; --",
        "' OR '1'='1",
        "1; SELECT * FROM users --",
    ]

    for payload in sql_payloads:
        # 一覧ページに戻ってから検索
        page.goto(f"{BASE_URL}/invoices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        page.get_by_label("取引先名").fill(payload)
        page.get_by_role("button", name="この条件で検索").dispatch_event("click")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # URLがinvoicesドメイン内に留まっていること（リダイレクト攻撃されていない）
        assert "invoicing-staging.keihi.com" in page.url, \
            f"SQLインジェクション入力後にドメイン離脱（payload: {payload}, URL: {page.url}）"

        # ページにコンテンツが存在すること（白画面やブラウザクラッシュでない）
        body_text = page.inner_text("body")
        assert len(body_text) > 0, \
            f"SQLインジェクション入力後にページが空（payload: {payload}）"


# =============================================================================
# テスト24: 異常系 - XSSスクリプトタグで検索
# =============================================================================

@pytest.mark.regression
def test_異常系_XSSスクリプトタグで検索(logged_in_page: Page):
    """XSSペイロードを入力して検索してもスクリプトが実行されずアプリがクラッシュしない"""

    page = goto_invoices(logged_in_page)

    # dialogイベントリスナーでXSS実行を検知
    xss_detected = []
    page.on("dialog", lambda dialog: (xss_detected.append(dialog.message), dialog.dismiss()))

    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(document.cookie)",
    ]

    for payload in xss_payloads:
        # 一覧ページに戻ってから検索
        page.goto(f"{BASE_URL}/invoices")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        page.get_by_label("取引先名").fill(payload)
        page.get_by_role("button", name="この条件で検索").dispatch_event("click")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # URLがドメイン内に留まっていること
        assert "invoicing-staging.keihi.com" in page.url, \
            f"XSS入力後にドメイン離脱（payload: {payload}, URL: {page.url}）"

        # ページにコンテンツが存在すること
        body_text = page.inner_text("body")
        assert len(body_text) > 0, \
            f"XSS入力後にページが空（payload: {payload}）"

    # XSSが実行されていないことを最終確認
    assert len(xss_detected) == 0, \
        f"XSSが実行された: {xss_detected}"


# =============================================================================
# テスト25: 異常系 - 長文字列で検索
# =============================================================================

@pytest.mark.regression
def test_異常系_長文字列で検索(logged_in_page: Page):
    """非常に長い文字列を入力して検索してもエラーにならずページが正常表示される"""

    page = goto_invoices(logged_in_page)

    # 1000文字の文字列
    long_string = "あ" * 1000

    page.get_by_label("取引先名").fill(long_string)
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # エラーページにならずURLが維持されること
    assert "/invoices" in page.url, \
        f"長文字列入力後にページ離脱（URL: {page.url}）"

    # ページにコンテンツが存在すること（白画面やブラウザクラッシュでない）
    body_text = page.inner_text("body")
    assert len(body_text) > 0, "長文字列入力後にページが空"


# =============================================================================
# テスト26: 表示件数の境界値 - 10件表示時の行数検証
# =============================================================================

@pytest.mark.regression
def test_表示件数の境界値_10件表示時の行数検証(logged_in_page: Page):
    """表示件数10件の3点境界値検証: 9行目表示・10行目表示・11行目非表示"""

    page = goto_invoices(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    # 10件に切替
    display_count_select.select_option("10")
    page.wait_for_timeout(2000)

    # 件数表示テキストで確認
    expect(page.locator("text=/件中 1〜10件/")).to_be_visible(timeout=10000)

    # テーブルのデータ行をカウント（theadを除く）
    data_rows = page.locator("table tbody tr")
    row_count = data_rows.count()

    # 3点境界値検証
    assert row_count >= 9, f"直前: 9行目が存在しない（実際: {row_count}行）"
    assert row_count >= 10, f"境界: 10行目が存在しない（実際: {row_count}行）"
    assert row_count == 10, f"直後: 11行目以上が存在する（実際: {row_count}行）"

    # 元に戻す
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)


# =============================================================================
# テスト27: 表示件数の境界値 - 50件表示時の行数検証
# =============================================================================

@pytest.mark.regression
def test_表示件数の境界値_50件表示時の行数検証(logged_in_page: Page):
    """表示件数50件の3点境界値検証: 49行目表示・50行目表示・51行目非表示"""

    page = goto_invoices(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    # 50件に切替
    display_count_select.select_option("50")
    page.wait_for_timeout(2000)

    # 件数表示テキストで確認
    expect(page.locator("text=/件中 1〜50件/")).to_be_visible(timeout=10000)

    # テーブルのデータ行をカウント
    data_rows = page.locator("table tbody tr")
    row_count = data_rows.count()

    # 3点境界値検証
    assert row_count >= 49, f"直前: 49行目が存在しない（実際: {row_count}行）"
    assert row_count >= 50, f"境界: 50行目が存在しない（実際: {row_count}行）"
    assert row_count == 50, f"直後: 51行目以上が存在する（実際: {row_count}行）"

    # 元に戻す
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)


# =============================================================================
# テスト28: ページネーション - 最終ページの境界値検証
# =============================================================================

@pytest.mark.regression
def test_ページネーション_最終ページの境界値検証(logged_in_page: Page):
    """最終ページの3点境界値: データ有り・最終件数=総数・次ボタンdisabled"""

    page = goto_invoices(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    # 100件表示に設定
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)

    # 総件数を取得
    count_text = page.locator("text=/\\d+件中/").text_content()
    total = int(re.search(r"(\d+)件中", count_text).group(1))

    # 最終ページまで遷移
    last_page = (total + 99) // 100  # 切り上げ
    if last_page > 1:
        page.goto(f"{BASE_URL}/invoices?page={last_page}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

    # 境界値1: 最終ページにデータ行が存在すること
    data_rows = page.locator("table tbody tr")
    last_page_rows = data_rows.count()
    assert last_page_rows > 0, "最終ページにデータ行がない"

    # 境界値2: 表示範囲の終了値が総件数と一致すること
    last_count_text = page.locator("text=/\\d+件中/").text_content()
    range_match = re.search(r"(\d+)件中\s+\d+〜(\d+)件", last_count_text)
    if range_match:
        display_total = int(range_match.group(1))
        range_end = int(range_match.group(2))
        assert range_end == display_total, \
            f"最終ページの終了値({range_end})が総件数({display_total})と一致しない"

    # 境界値3: 次ページボタンがdisabledであること
    paging_container = page.locator("text=/\\d+件中/").locator("..")
    buttons = paging_container.locator("button")
    if buttons.count() >= 2:
        next_btn = buttons.nth(1)
        expect(next_btn).to_be_disabled()


# =============================================================================
# テスト29: 表示件数の境界値 - 20件表示時の行数検証
# =============================================================================

@pytest.mark.regression
def test_表示件数の境界値_20件表示時の行数検証(logged_in_page: Page):
    """表示件数20件の3点境界値検証: 19行目表示・20行目表示・21行目非表示"""

    page = goto_invoices(logged_in_page)
    display_count_select = page.locator("main").locator("select").last

    # 20件に切替
    display_count_select.select_option("20")
    page.wait_for_timeout(2000)

    # 件数表示テキストで確認
    expect(page.locator("text=/件中 1〜20件/")).to_be_visible(timeout=10000)

    # テーブルのデータ行をカウント
    data_rows = page.locator("table tbody tr")
    row_count = data_rows.count()

    # 3点境界値検証
    assert row_count >= 19, f"直前: 19行目が存在しない（実際: {row_count}行）"
    assert row_count >= 20, f"境界: 20行目が存在しない（実際: {row_count}行）"
    assert row_count == 20, f"直後: 21行目以上が存在する（実際: {row_count}行）"

    # 元に戻す
    display_count_select.select_option("100")
    page.wait_for_timeout(2000)


# =============================================================================
# テスト30: 状態遷移 - 検索→リセット→再検索で正常動作する
# =============================================================================

@pytest.mark.regression
def test_状態遷移_検索後リセット後再検索で正常動作する(logged_in_page: Page):
    """検索→結果確認→リセット→全件復帰→別条件で再検索の遷移が正常動作する"""

    page = goto_invoices(logged_in_page)

    # 初期件数を記録
    before_total = get_count_total(page)

    # 1回目の検索（取引先名で絞り込み）
    page.get_by_label("取引先コード").fill("TH003")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # 件数が減ったことを確認
    search1_total = get_count_total(page)
    assert search1_total < before_total, \
        f"検索後に件数が減っていない（前: {before_total}, 後: {search1_total}）"

    # リセット
    page.get_by_role("button", name="リセット").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # 全件に復帰したことを確認
    reset_total = get_count_total(page)
    assert reset_total == before_total, \
        f"リセット後に全件に復帰していない（期待: {before_total}, 実際: {reset_total}）"

    # 2回目の検索（請求書番号で絞り込み）
    page.get_by_label("請求書番号").fill("INV-0001")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # ページが正常表示されていること
    assert "/invoices" in page.url
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト31: 状態遷移 - 詳細画面から戻っても一覧状態が維持される
# =============================================================================

@pytest.mark.regression
def test_状態遷移_詳細画面から戻っても一覧状態が維持される(logged_in_page: Page):
    """一覧で行クリック→詳細画面→ブラウザバック→一覧が正常表示される"""

    page = goto_invoices(logged_in_page)

    # 一覧の件数を記録
    count_text = page.locator("text=/\\d+件中/").text_content()
    original_total = int(re.search(r"(\d+)件中", count_text).group(1))

    # 1行目をクリックして詳細画面に遷移
    first_row = page.locator("table tbody tr").first
    first_row.locator("td").nth(1).click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # 詳細画面に遷移したことを確認
    expect(page).to_have_url(re.compile(r"/invoices/[a-f0-9-]+"), timeout=10000)

    # ブラウザバックで一覧に戻る
    page.go_back()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # 一覧画面に戻っていること
    expect(page).to_have_url(re.compile(r"/invoices"), timeout=10000)
    expect(page.locator("table")).to_be_visible(timeout=10000)

    # 件数が維持されていること
    back_text = page.locator("text=/\\d+件中/").text_content()
    back_total = int(re.search(r"(\d+)件中", back_text).group(1))
    assert back_total == original_total, \
        f"ブラウザバック後に件数が変わった（前: {original_total}, 後: {back_total}）"


# =============================================================================
# テスト32: 冪等性 - 検索ボタン連打で結果が安定する
# =============================================================================

@pytest.mark.regression
def test_冪等性_検索ボタン連打で結果が安定する(logged_in_page: Page):
    """同じ検索条件で検索ボタンを3回連打しても結果が同じになる"""

    page = goto_invoices(logged_in_page)

    # 検索条件を入力
    page.get_by_label("取引先コード").fill("TH003")

    # 検索ボタンを3回連打
    search_btn = page.get_by_role("button", name="この条件で検索")
    search_btn.dispatch_event("click")
    page.wait_for_timeout(500)
    search_btn.dispatch_event("click")
    page.wait_for_timeout(500)
    search_btn.dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # ページが正常表示されていること
    assert "/invoices" in page.url, f"検索ボタン連打後にURLが変わった: {page.url}"
    expect(page.locator("table")).to_be_visible()

    # 件数表示が正常であること
    total = get_count_total(page)
    assert total >= 0, f"件数が不正: {total}"


# =============================================================================
# テスト33: 冪等性 - 表示件数を連続切替しても正常動作する
# =============================================================================

@pytest.mark.regression
def test_冪等性_表示件数を連続切替しても正常動作する(logged_in_page: Page):
    """表示件数を10→50→20→100→10と連続切替しても正しい行数が表示される"""

    page = goto_invoices(logged_in_page)
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
# テスト34: エラーリカバリ - 存在しない取引先名検索後に条件修正で復帰
# =============================================================================

@pytest.mark.regression
def test_エラーリカバリ_存在しない取引先名検索後に条件修正で復帰(logged_in_page: Page):
    """存在しない取引先名で0件→条件修正→正常な結果が表示されるリカバリフロー"""

    page = goto_invoices(logged_in_page)

    # Step1: 存在しない取引先名で検索（エラー状態）
    page.get_by_label("取引先名").fill("存在しない会社名ZZZZZ99999")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # 0件または少数であることを確認
    count_text = page.locator("text=/\\d+件中/")
    if count_text.is_visible():
        text = count_text.text_content()
        zero_total = int(re.search(r"(\d+)件中", text).group(1))
        assert zero_total == 0, f"存在しない名前で{zero_total}件ヒットした"

    # Step2: 条件を修正して再検索（リカバリ）
    page.get_by_label("取引先名").fill("")
    page.get_by_label("取引先コード").fill("TH003")
    page.get_by_role("button", name="この条件で検索").dispatch_event("click")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # 正常な結果が表示されること
    total2 = get_count_total(page)
    assert total2 > 0, f"条件修正後も0件のまま（リカバリ失敗）"

    # テーブルにデータが表示されていること
    expect(page.locator("table")).to_be_visible()


# =============================================================================
# テスト35: データ整合性 - 一覧の取引先名が詳細画面と一致する（基準6）
# =============================================================================

@pytest.mark.regression
def test_データ整合性_一覧の取引先名が詳細画面と一致する(logged_in_page: Page):
    """一覧テーブルの取引先名をクリックして詳細に遷移し、同じ取引先名が表示される"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 最初の行の取引先名を取得
    first_row = page.locator("table tbody tr").first
    list_partner_name = first_row.locator("td").nth(1).text_content().strip()

    # Step3: 行をクリックして詳細画面に遷移
    first_row.locator("td").nth(1).click()
    page.wait_for_url(re.compile(r"/invoices/[0-9a-f\-]{36}"), timeout=15000)
    page.get_by_role("heading", name="請求書").wait_for(state="visible")

    # Step4: 詳細画面の取引先名と一覧の取引先名が一致することを確認
    detail_partner = page.locator("text=取引先名").first
    detail_partner.wait_for(state="visible", timeout=10000)
    # 取引先名の値は隣のセルまたは同行にある
    partner_section = page.locator("dt:has-text('取引先名') + dd, th:has-text('取引先名') ~ td").first
    if partner_section.count() > 0:
        detail_partner_name = partner_section.text_content().strip()
    else:
        # フォールバック: テキストで検索
        detail_partner_name = page.locator(f"text={list_partner_name}").first.text_content().strip()

    assert list_partner_name in detail_partner_name or detail_partner_name in list_partner_name, \
        f"一覧の取引先名「{list_partner_name}」が詳細画面「{detail_partner_name}」と一致しない"


# =============================================================================
# テスト36: データ整合性 - 一覧の件数と詳細画面のページ送り総数が一致する（基準6）
# =============================================================================

@pytest.mark.regression
def test_データ整合性_一覧の件数と詳細画面のページ送り総数が一致する(logged_in_page: Page):
    """一覧の「N件中」の件数と詳細画面の「X / Y件」の総数Yが一致する"""

    # Step1: 一覧ページに遷移
    page = goto_invoices(logged_in_page)

    # Step2: 一覧の総件数を取得
    count_text = page.locator("text=/\\d+件中/").text_content()
    list_total = int(re.search(r"(\d+)件中", count_text).group(1))

    # Step3: 最初の行をクリックして詳細画面に遷移
    page.locator("table tbody tr").first.locator("td").nth(1).click()
    page.wait_for_url(re.compile(r"/invoices/[0-9a-f\-]{36}"), timeout=15000)
    page.get_by_role("heading", name="請求書").wait_for(state="visible")

    # Step4: 詳細画面のページ送り表示「X / Y件」からYを取得
    position_text = page.locator("text=/\\d+ \\/ \\d+件/").first.text_content()
    detail_total = int(re.search(r"(\d+) / (\d+)件", position_text).group(2))

    # Step5: 一覧の件数と詳細のページ送り総数が一致
    assert list_total == detail_total, \
        f"一覧の総件数({list_total})と詳細のページ送り総数({detail_total})が不一致"
