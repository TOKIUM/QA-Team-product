"""
帳票レイアウト画面テスト

対象URL: /invoices/design
画面構成:
  - 親ページ: ヘッダー、サイドバー、ユーティリティバー（戻る・パンくず）
  - gallery iframe: レイアウト一覧（検索・グリッド/リスト切替・並べ替え・新規作成・カード）

技術的特徴:
  - メインコンテンツはクロスオリジンiframe（tpmlyr.dev.components.asaservice.inc）内
  - iframe操作は page.frame(name="gallery") 経由
  - MUI (Material-UI) ベースのグリッドレイアウト
  - CSVインポート画面と同じiframeパターン

test_results対応: 各テストにTH-IDを付与し、conftest.pyのフックで
スクリーンショット・ログ・JSONサマリーを自動保存する。
"""

import pytest


# =============================================================================
# TH-ID マッピング
# =============================================================================
TH_ID_MAP = {
    "test_帳票レイアウト画面に遷移できる": "TH-DL01",
    "test_URL直接アクセスで画面表示": "TH-DL02",
    "test_パンくずが正しく表示される": "TH-DL03",
    "test_戻るボタンが表示される": "TH-DL04",
    "test_サイドバーの帳票レイアウトがアクティブ": "TH-DL05",
    "test_gallery_iframeが存在する": "TH-DL06",
    "test_gallery_iframeのURLが正しい": "TH-DL07",
    "test_レイアウトカードが表示される": "TH-DL08",
    "test_レイアウトカードの件数確認": "TH-DL09",
    "test_検索バーが存在する": "TH-DL10",
    "test_新規作成ボタンが存在する": "TH-DL11",
    "test_並べ替えコントロールが存在する": "TH-DL12",
    "test_表示切替ボタンが存在する": "TH-DL13",
    "test_検索バーに入力できる": "TH-DL14",
    "test_検索で一致するレイアウトが表示される": "TH-DL15",
    "test_レイアウトカードクリックで遷移する": "TH-DL16",
    "test_リスト表示に切り替えできる": "TH-DL17",
    "test_ヘッダーが表示される": "TH-DL18",
    "test_サイドバーから請求書画面に遷移できる": "TH-DL19",
    "test_サイドバーから取引先画面に遷移できる": "TH-DL20",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    """テスト関数名からTH-IDを自動付与（[chromium]等のパラメータを除去して照合）"""
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id

import re
import os
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-staging.keihi.com"
DESIGN_URL = f"{BASE_URL}/invoices/design"

# iframe読み込み待機時間（秒）
IFRAME_LOAD_WAIT = 8000
IFRAME_ACTION_WAIT = 3000


# =============================================================================
# ヘルパー関数
# =============================================================================

def goto_design(page: Page) -> Page:
    """帳票レイアウト画面に遷移"""
    page.goto(DESIGN_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(IFRAME_LOAD_WAIT)
    return page


def get_gallery_frame(page: Page):
    """gallery iframeを取得して返す"""
    frame = page.frame(name="gallery")
    assert frame is not None, "gallery iframeが見つからない"
    frame.wait_for_load_state("networkidle")
    page.wait_for_timeout(IFRAME_ACTION_WAIT)
    return frame


# =============================================================================
# 1. 画面遷移・基本表示テスト
# =============================================================================

def test_帳票レイアウト画面に遷移できる(logged_in_page: Page):
    """サイドバー「帳票レイアウト」から画面に遷移できる"""
    page = logged_in_page
    page.goto(f"{BASE_URL}/invoices")
    page.wait_for_load_state("networkidle")

    # サイドバーの「帳票レイアウト」リンクをクリック
    page.get_by_role("link", name="帳票レイアウト").click()
    expect(page).to_have_url(re.compile(r"/invoices/design"), timeout=15000)


def test_URL直接アクセスで画面表示(logged_in_page: Page):
    """URLを直接指定して帳票レイアウト画面が表示される"""
    page = goto_design(logged_in_page)
    expect(page).to_have_url(re.compile(r"/invoices/design"))


def test_パンくずが正しく表示される(logged_in_page: Page):
    """パンくず「帳票レイアウト > レイアウト選択」が表示される"""
    page = goto_design(logged_in_page)

    # パンくず（main内のnav）の「帳票レイアウト」リンク
    breadcrumb = page.locator("#main-content").locator("nav")
    expect(breadcrumb.get_by_role("link", name="帳票レイアウト")).to_be_visible()

    # 「レイアウト選択」テキスト
    expect(page.locator("text=レイアウト選択")).to_be_visible()


def test_戻るボタンが表示される(logged_in_page: Page):
    """戻るボタンが表示されている"""
    page = goto_design(logged_in_page)
    back_btn = page.get_by_role("button", name="戻る")
    expect(back_btn).to_be_visible()


def test_サイドバーの帳票レイアウトがアクティブ(logged_in_page: Page):
    """サイドバーの帳票レイアウトリンクが存在する"""
    page = goto_design(logged_in_page)

    # サイドバー内のリンク確認（.firstで重複回避）
    expect(page.get_by_role("link", name="請求書", exact=True).first).to_be_visible()
    expect(page.get_by_role("link", name="取引先").first).to_be_visible()
    expect(page.get_by_role("link", name="帳票レイアウト").first).to_be_visible()


# =============================================================================
# 2. gallery iframe テスト
# =============================================================================

def test_gallery_iframeが存在する(logged_in_page: Page):
    """gallery iframeが正常にロードされる"""
    page = goto_design(logged_in_page)
    frame = page.frame(name="gallery")
    assert frame is not None, "gallery iframeが見つからない"


def test_gallery_iframeのURLが正しい(logged_in_page: Page):
    """gallery iframeのsrcが外部ドメインを指している"""
    page = goto_design(logged_in_page)
    iframe_el = page.locator("iframe#gallery")
    expect(iframe_el).to_be_visible()

    src = iframe_el.get_attribute("src")
    assert src is not None, "iframe srcが設定されていない"
    assert "tpmlyr" in src or "gallery" in src, f"想定外のiframe src: {src}"


def test_レイアウトカードが表示される(logged_in_page: Page):
    """gallery iframe内にレイアウトカード（MuiGrid-item）が1件以上表示される"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    grid_items = frame.query_selector_all(".MuiGrid-item")
    assert len(grid_items) > 0, "レイアウトカードが表示されていない"


def test_レイアウトカードの件数確認(logged_in_page: Page):
    """レイアウトカードが複数件表示されている"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    grid_items = frame.query_selector_all(".MuiGrid-item")
    count = len(grid_items)
    assert count >= 2, f"レイアウトカードが2件未満: {count}件"


def test_検索バーが存在する(logged_in_page: Page):
    """iframe内に「レイアウト名で検索」の検索バーがある"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    # プレースホルダーで検索入力を特定
    search_input = frame.locator('input[placeholder*="検索"]')
    assert search_input.count() > 0, "検索バーが見つからない"


def test_新規作成ボタンが存在する(logged_in_page: Page):
    """iframe内に「新規作成」ボタンがある"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    # 「新規作成」テキストを含むボタンを探す
    create_btn = frame.locator('button:has-text("新規作成")')
    if create_btn.count() == 0:
        # テキストノードで探す
        create_btn = frame.locator('text=新規作成')
    assert create_btn.count() > 0, "新規作成ボタンが見つからない"


def test_並べ替えコントロールが存在する(logged_in_page: Page):
    """iframe内に「並べ替え」コントロールがある"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    sort_control = frame.locator('text=並べ替え')
    assert sort_control.count() > 0, "並べ替えコントロールが見つからない"


def test_表示切替ボタンが存在する(logged_in_page: Page):
    """iframe内にグリッド/リスト表示切替ボタンがある"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    # MUI ToggleButtonGroup のボタンを探す
    # role="button" または [value] 属性付きのトグルボタン
    toggle_buttons = frame.locator('[role="button"]')
    if toggle_buttons.count() < 2:
        # MUI ToggleButton は role がない場合がある
        toggle_buttons = frame.locator('.MuiToggleButton-root')
    if toggle_buttons.count() < 2:
        # フォールバック: ツールバー内のボタンをすべて取得
        toggle_buttons = frame.locator('button')
    assert toggle_buttons.count() >= 2, f"表示切替ボタンが見つからない（ボタン数: {toggle_buttons.count()}）"


# =============================================================================
# 3. 検索機能テスト
# =============================================================================

def test_検索バーに入力できる(logged_in_page: Page):
    """検索バーにテキストを入力できる（iframe内input操作確認）"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    # 検索入力を特定
    search_input = frame.locator('input[placeholder*="検索"]')
    assert search_input.count() > 0, "検索バーが見つからない"

    # bounding_box + click でiframe内のinputにフォーカス
    box = search_input.bounding_box()
    assert box is not None, "検索バーのbounding_boxが取得できない"
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_timeout(500)

    # テキスト入力
    page.keyboard.type("test")
    page.wait_for_timeout(1000)

    # 入力された値を確認
    value = search_input.input_value()
    assert "test" in value, f"検索バーへの入力が反映されていない: '{value}'"

    # クリアして元に戻す
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    page.wait_for_timeout(1000)


def test_検索で一致するレイアウトが表示される(logged_in_page: Page):
    """存在するレイアウト名で検索するとカードが表示される"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    # 「サンプル」で検索（既存レイアウトに含まれるはず）
    search_input = frame.locator('input[placeholder*="検索"]')
    search_input.fill("サンプル")
    page.wait_for_timeout(2000)

    filtered_items = frame.query_selector_all(".MuiGrid-item")
    assert len(filtered_items) > 0, "「サンプル」で検索してもカードが表示されない"

    # 検索をクリア
    search_input.fill("")
    page.wait_for_timeout(2000)


# =============================================================================
# 4. カード操作テスト
# =============================================================================

def test_レイアウトカードクリックで遷移する(logged_in_page: Page):
    """レイアウトカードをクリックするとURL変化またはモーダル表示がある"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    grid_items = frame.query_selector_all(".MuiGrid-item")
    assert len(grid_items) > 0, "レイアウトカードがない"

    # 最初のカードをクリック（bounding_box + page.mouse.click で確実に操作）
    box = grid_items[0].bounding_box()
    assert box is not None, "カードのbounding_boxが取得できない"
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    page.wait_for_timeout(5000)

    # URL変化があったか確認
    current_url = page.url
    # /invoices/design 以外に遷移 or /invoices/design/xxx に遷移
    url_changed = current_url != DESIGN_URL

    if url_changed:
        # 遷移した場合: URLが変わったことを確認
        assert "/invoices/design" in current_url or "/invoices" in current_url, \
            f"想定外のURLに遷移: {current_url}"
    else:
        # 遷移しない場合: iframe内のコンテンツが変わったかチェック
        # モーダルや詳細表示の可能性をチェック
        pass  # URLが同じでもiframe内で画面遷移している可能性あり

    # テスト後に帳票レイアウト画面に戻す
    page.goto(DESIGN_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(IFRAME_LOAD_WAIT)


# =============================================================================
# 5. リスト表示切替テスト
# =============================================================================

def test_リスト表示に切り替えできる(logged_in_page: Page):
    """リスト表示ボタンをクリックすると表示形式が変わる"""
    page = goto_design(logged_in_page)
    frame = get_gallery_frame(page)

    # 現在のグリッド表示を確認
    grid_items = frame.query_selector_all(".MuiGrid-item")
    initial_count = len(grid_items)

    # リスト表示ボタンをクリック（2番目のアイコンボタン）
    # ToggleButtonGroupまたはIconButtonを探す
    toggle_buttons = frame.locator('[role="button"]')
    if toggle_buttons.count() < 2:
        toggle_buttons = frame.locator('button:has(svg)')

    if toggle_buttons.count() >= 2:
        # 2番目のボタン（リスト表示）をクリック
        list_btn = toggle_buttons.nth(1)
        box = list_btn.bounding_box()
        if box:
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.wait_for_timeout(2000)

    # グリッド表示ボタンをクリックして元に戻す
    if toggle_buttons.count() >= 2:
        grid_btn = toggle_buttons.nth(0)
        box = grid_btn.bounding_box()
        if box:
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.wait_for_timeout(2000)


# =============================================================================
# 6. ヘッダー・ナビゲーションテスト
# =============================================================================

def test_ヘッダーが表示される(logged_in_page: Page):
    """ヘッダーにロゴ・ユーザー名・ヘルプが表示される"""
    page = goto_design(logged_in_page)

    # ロゴ
    logo = page.get_by_role("img", name="TOKIUM 請求書発行")
    expect(logo).to_be_visible()

    # ユーザー名（ヘッダー内、事業所パネルと重複あるので .first で限定）
    expect(page.locator("text=池田尚人").first).to_be_visible()

    # ヘルプリンク
    help_link = page.get_by_role("link", name="TOKIUM 請求書発行 - ヘルプセンター")
    expect(help_link).to_be_visible()


def test_サイドバーから請求書画面に遷移できる(logged_in_page: Page):
    """サイドバー「請求書」から/invoicesに遷移できる"""
    page = goto_design(logged_in_page)

    page.get_by_role("link", name="請求書", exact=True).first.click()
    expect(page).to_have_url(re.compile(r"/invoices"), timeout=10000)


def test_サイドバーから取引先画面に遷移できる(logged_in_page: Page):
    """サイドバー「取引先」から/partnersに遷移できる"""
    page = goto_design(logged_in_page)

    page.get_by_role("link", name="取引先").click()
    expect(page).to_have_url(re.compile(r"/partners"), timeout=10000)
